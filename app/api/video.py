"""
app.api.video Docstring
"""
import logging
import re
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.models import VeditPreset

router = APIRouter(prefix="/api", tags=["video"])

_KEY_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_LOG = logging.getLogger("vedit")

class VideoMeta(BaseModel):
    duration_ms: int = Field(ge=1)
    width: int = Field(ge=1, le=16384)
    height: int = Field(ge=1, le=16384)
    fps: float = Field(gt=0, le=240)
    has_audio: bool = True


class Trim(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: Optional[int] = Field(default=None, ge=0)


class Segment(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=1)


class Crop(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1)
    h: int = Field(ge=1)


class Scale(BaseModel):
    width: Optional[int] = Field(default=None, ge=1, le=16384)
    height: Optional[int] = Field(default=None, ge=1, le=16384)
    keep_aspect: bool = True


class Bitrate(BaseModel):
    video_kbps: Optional[int] = Field(default=None, ge=100, le=200000)
    audio_kbps: Optional[int] = Field(default=None, ge=32, le=512)


class Audio(BaseModel):
    mode: Literal["keep", "mute", "extract"] = "keep"
    extract_format: Optional[Literal["aac", "mp3", "wav", "flac", "ogg"]] = None


class FrameCapture(BaseModel):
    at_ms: int = Field(ge=0)
    format: Literal["png"] = "png"


class Recipe(BaseModel):
    trim: Optional[Trim] = None
    remove_segments: list[Segment] = Field(default_factory=list)
    crop: Optional[Crop] = None
    scale: Optional[Scale] = None
    bitrate: Optional[Bitrate] = None
    audio: Optional[Audio] = None
    frame_capture: Optional[FrameCapture] = None
    container: Literal["mp4", "webm", "mkv"] = "mp4"


class ValidateRequest(BaseModel):
    meta: VideoMeta
    recipe: Recipe


class ValidateResponse(BaseModel):
    ok: bool
    normalized: Recipe


@dataclass(frozen=True)
class Preset:
    key: str
    label: str
    recipe_patch: dict

class PresetUpsertRequest(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=128)
    recipe_patch: dict


class PresetUpsertResponse(BaseModel):
    ok: bool
    key: str


PRESETS = [
    Preset(
        key="web_1080p",
        label="Web 1080p",
        recipe_patch={"scale": {"width": 1920, "height": 1080, "keep_aspect": True}, "bitrate": {"video_kbps": 6000}},
    ),
    Preset(
        key="web_720p",
        label="Web 720p",
        recipe_patch={"scale": {"width": 1280, "height": 720, "keep_aspect": True}, "bitrate": {"video_kbps": 2500}},
    ),
    Preset(
        key="mute",
        label="Mute Audio",
        recipe_patch={"audio": {"mode": "mute"}},
    ),
    Preset(
        key="audio_mp3",
        label="Extract MP3",
        recipe_patch={"audio": {"mode": "extract", "extract_format": "mp3"}},
    ),
]


def _clamp_end(meta: VideoMeta, trim: Trim) -> Trim:
    end = trim.end_ms or meta.duration_ms
    if end > meta.duration_ms:
        end = meta.duration_ms
    if trim.start_ms >= end:
        raise HTTPException(status_code=422, detail="invalid trim")
    return Trim(start_ms=trim.start_ms, end_ms=end)


def _merge_segments(meta: VideoMeta, segs: Iterable[Segment]) -> list[Segment]:
    valid = []
    for s in segs:
        a = max(0, min(s.start_ms, meta.duration_ms))
        b = max(0, min(s.end_ms, meta.duration_ms))
        if a < b:
            valid.append(Segment(start_ms=a, end_ms=b))
    valid.sort(key=lambda x: x.start_ms)
    merged: list[Segment] = []
    for s in valid:
        if not merged or s.start_ms > merged[-1].end_ms:
            merged.append(s)
        else:
            merged[-1] = Segment(start_ms=merged[-1].start_ms, end_ms=max(merged[-1].end_ms, s.end_ms))
    return merged


def _clamp_crop(meta: VideoMeta, crop: Crop) -> Crop:
    x = max(0, min(crop.x, meta.width - 1))
    y = max(0, min(crop.y, meta.height - 1))
    w = max(1, min(crop.w, meta.width - x))
    h = max(1, min(crop.h, meta.height - y))
    return Crop(x=x, y=y, w=w, h=h)


def _normalize_scale(scale: Scale) -> Scale:
    w = scale.width
    h = scale.height
    if w is not None:
        w = max(1, min(w, 16384))
    if h is not None:
        h = max(1, min(h, 16384))
    return Scale(width=w, height=h, keep_aspect=scale.keep_aspect)

def _db_presets(db: Session) -> list[dict]:
    rows = db.execute(select(VeditPreset)).scalars().all()
    return [{"key": r.preset_key, "label": r.label, "recipe_patch": r.recipe_patch} for r in rows]


@router.get("/presets")
def presets(db: Session = Depends(get_session)):
    base = {p.key: {"key": p.key, "label": p.label, "recipe_patch": p.recipe_patch} for p in PRESETS}
    try:
        for p in _db_presets(db):
            base[p["key"]] = p
    except Exception:
        pass
    return list(base.values())

@router.post("/presets/custom", response_model=PresetUpsertResponse)
def upsert_preset(req: PresetUpsertRequest, db: Session = Depends(get_session)):
    key = req.key.strip()
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=422, detail="invalid preset key")
    label = req.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="invalid label")
    row = db.execute(select(VeditPreset).where(VeditPreset.preset_key == key)).scalar_one_or_none()
    if row is None:
        row = VeditPreset(preset_key=key, label=label, recipe_patch=req.recipe_patch)
        db.add(row)
        _LOG.warning("preset_custom_upsert action=create key=%s", key)        
    else:
        row.label = label
        row.recipe_patch = req.recipe_patch
        _LOG.warning("preset_custom_upsert action=update key=%s", key)        
    db.commit()
    return PresetUpsertResponse(ok=True, key=key)

@router.delete("/presets/custom/{key}")
def delete_preset(key: str, db: Session = Depends(get_session)):
    k = (key or "").strip()
    if not _KEY_RE.match(k):
        raise HTTPException(status_code=422, detail="invalid preset key")
    row = db.execute(select(VeditPreset).where(VeditPreset.preset_key == k)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(row)
    db.commit()
    _LOG.warning("preset_custom_delete key=%s", k)    
    return {"ok": True}


@router.post("/recipe/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest) -> ValidateResponse:
    r = req.recipe
    meta = req.meta

    trim = _clamp_end(meta, r.trim) if r.trim else None
    segs = _merge_segments(meta, r.remove_segments)
    crop = _clamp_crop(meta, r.crop) if r.crop else None
    scale = _normalize_scale(r.scale) if r.scale else None

    if r.audio and r.audio.mode == "extract" and not r.audio.extract_format:
        raise HTTPException(status_code=422, detail="extract_format required")

    if r.frame_capture and r.frame_capture.at_ms > meta.duration_ms:
        raise HTTPException(status_code=422, detail="frame_capture out of range")

    normalized = Recipe(
        trim=trim,
        remove_segments=segs,
        crop=crop,
        scale=scale,
        bitrate=r.bitrate,
        audio=r.audio,
        frame_capture=r.frame_capture,
        container=r.container,
    )

    return ValidateResponse(ok=True, normalized=normalized)


def normalize_recipe(req: ValidateRequest) -> Recipe:
    return validate(req).normalized
