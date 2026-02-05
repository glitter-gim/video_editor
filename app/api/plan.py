# pylint: disable=no-member
"""
app.api.plan Docstring
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.video import Recipe, ValidateRequest, ValidateResponse, validate

router = APIRouter(prefix="/api", tags=["plan"])


class PlanResponse(BaseModel):
    mode: str
    container: str
    ffmpeg_args: list[str]
    outputs: list[dict]


def _sec(ms: int) -> str:
    return f"{ms/1000:.3f}"


def _keep_segments(r: Recipe, duration_ms: int) -> list[tuple[int, int]]:
    start = r.trim.start_ms if r.trim else 0
    end = (r.trim.end_ms if r.trim and r.trim.end_ms else duration_ms)
    if start < 0:
        start = 0
    if end > duration_ms:
        end = duration_ms
    if start >= end:
        raise HTTPException(status_code=422, detail="no remaining segments")

    if not r.remove_segments:
        return [(start, end)]

    cuts = []
    for s in r.remove_segments:
        a = max(0, min(s.start_ms, duration_ms))
        b = max(0, min(s.end_ms, duration_ms))
        if a < b:
            cuts.append((a, b))
    cuts.sort()

    merged = []
    for a, b in cuts:
        if not merged or a > merged[-1][1]:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    cuts = [(x[0], x[1]) for x in merged]

    keep = []
    cursor = start
    for a, b in cuts:
        if b <= cursor:
            continue
        if a > cursor:
            keep.append((cursor, min(a, end)))
        cursor = max(cursor, b)
        if cursor >= end:
            break
    if cursor < end:
        keep.append((cursor, end))

    keep = [(a, b) for a, b in keep if a < b]
    if not keep:
        raise HTTPException(status_code=422, detail="no remaining segments")
    return keep


def _vf_chain(r: Recipe) -> Optional[str]:
    chain = []
    if r.crop:
        c = r.crop
        chain.append(f"crop={c.w}:{c.h}:{c.x}:{c.y}")
    if r.scale and (r.scale.width or r.scale.height):
        sc = r.scale
        w = sc.width if sc.width else -2
        h = sc.height if sc.height else -2
        chain.append(f"scale={w}:{h}:flags=bicubic")
    return ",".join(chain) if chain else None


def _build_concat_filter(r: Recipe, duration_ms: int, has_audio: bool) -> tuple[str, list[str]]:
    keep = _keep_segments(r, duration_ms)
    vf = _vf_chain(r)

    parts = []
    vlabels = []
    alabels = []

    for i, (a, b) in enumerate(keep):
        vlab = f"v{i}"
        alab = f"a{i}"
        vexpr = f"[0:v]trim=start={_sec(a)}:end={_sec(b)},setpts=PTS-STARTPTS"
        if vf:
            vexpr += f",{vf}"
        vexpr += f"[{vlab}]"
        parts.append(vexpr)
        vlabels.append(f"[{vlab}]")

        if has_audio and not (r.audio and r.audio.mode == "mute"):
            aexpr = f"[0:a]atrim=start={_sec(a)}:end={_sec(b)},asetpts=PTS-STARTPTS[{alab}]"
            parts.append(aexpr)
            alabels.append(f"[{alab}]")

    n = len(keep)

    if has_audio and not (r.audio and r.audio.mode == "mute"):
        parts.append("".join(vlabels + alabels) + f"concat=n={n}:v=1:a=1[v][a]")
        return ";".join(parts), ["-map", "[v]", "-map", "[a]"]

    parts.append("".join(vlabels) + f"concat=n={n}:v=1:a=0[v]")
    return ";".join(parts), ["-map", "[v]"]


@router.post("/plan", response_model=PlanResponse)
def plan(req: ValidateRequest):
    v: ValidateResponse = validate(req)
    r: Recipe = v.normalized
    meta = req.meta

    if r.audio and r.audio.mode == "extract":
        fmt = r.audio.extract_format
        if not fmt:
            raise HTTPException(status_code=422, detail="extract_format required")
        args = ["-vn"]
        if fmt == "mp3":
            args += ["-c:a", "libmp3lame"]
        elif fmt == "aac":
            args += ["-c:a", "aac"]
        elif fmt == "wav":
            args += ["-c:a", "pcm_s16le"]
        elif fmt == "flac":
            args += ["-c:a", "flac"]
        elif fmt == "ogg":
            args += ["-c:a", "libvorbis"]
        if r.bitrate and r.bitrate.audio_kbps:
            args += ["-b:a", f"{r.bitrate.audio_kbps}k"]
        return PlanResponse(
            mode="audio",
            container=fmt,
            ffmpeg_args=args,
            outputs=[{"name": f"output.{fmt}", "kind": "audio"}],
        )

    if r.frame_capture:
        vf = _vf_chain(r)
        args = ["-ss", _sec(r.frame_capture.at_ms), "-frames:v", "1"]
        if vf:
            args += ["-vf", vf]
        return PlanResponse(
            mode="frame",
            container="png",
            ffmpeg_args=args,
            outputs=[{"name": "frame.png", "kind": "image"}],
        )

    filter_complex, maps = _build_concat_filter(r, meta.duration_ms, meta.has_audio)
    args = ["-filter_complex", filter_complex] + maps

    if r.bitrate and r.bitrate.video_kbps:
        args += ["-b:v", f"{r.bitrate.video_kbps}k"]
    if r.bitrate and r.bitrate.audio_kbps and meta.has_audio and not (r.audio and r.audio.mode == "mute"):
        args += ["-b:a", f"{r.bitrate.audio_kbps}k"]

    return PlanResponse(
        mode="video",
        container=r.container,
        ffmpeg_args=args,
        outputs=[{"name": f"output.{r.container}", "kind": "video"}],
    )
