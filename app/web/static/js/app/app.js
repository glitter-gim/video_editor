import { plan, presets, validateRecipe } from "./api.js";
import { runPlan } from "./ffmpeg.js";
import { loadVideoMeta } from "./meta.js";
import { applyPatch, buildRecipeFromUi } from "./recipe.js";

let lastBlobUrl = null;

const el = {
  file: document.getElementById("file"),
  preset: document.getElementById("preset"),
  applyPreset: document.getElementById("applyPreset"),
  trimStart: document.getElementById("trimStart"),
  trimEnd: document.getElementById("trimEnd"),
  audioMode: document.getElementById("audioMode"),
  audioFormat: document.getElementById("audioFormat"),
  container: document.getElementById("container"),
  cropEnable: document.getElementById("cropEnable"),
  cropX: document.getElementById("cropX"),
  cropY: document.getElementById("cropY"),
  cropW: document.getElementById("cropW"),
  cropH: document.getElementById("cropH"),
  scaleEnable: document.getElementById("scaleEnable"),
  scaleW: document.getElementById("scaleW"),
  scaleH: document.getElementById("scaleH"),
  scaleKeepAspect: document.getElementById("scaleKeepAspect"),
  videoKbps: document.getElementById("videoKbps"),
  audioKbps: document.getElementById("audioKbps"),
  frameEnable: document.getElementById("frameEnable"),
  frameAt: document.getElementById("frameAt"),
  validate: document.getElementById("validate"),
  run: document.getElementById("run"),
  clear: document.getElementById("clear"),
  log: document.getElementById("log"),
  outVideo: document.getElementById("outVideo"),
  outAudio: document.getElementById("outAudio"),
  outImage: document.getElementById("outImage"),
  download: document.getElementById("download"),
  segStart: document.getElementById("segStart"),
  segEnd: document.getElementById("segEnd"),
  addSeg: document.getElementById("addSeg"),
  clearSegs: document.getElementById("clearSegs"),
  segList: document.getElementById("segList"),
  segHint: document.getElementById("segHint"),
};

const state = {
  presets: [],
  file: null,
  meta: null,
  recipeDraft: null,
  recipeNormalized: null,
  lastPlan: null,
  removeSegments: [],
  undoStack: [],
  redoStack: [],
  isRestoring: false,
};

function log(msg) {
  const maxLines = 400;
  const maxLineLen = 2000;
  const line = String(msg ?? "").slice(0, maxLineLen);
  const prev = el.log.textContent ? el.log.textContent.split("\n") : [];
  prev.push(line);
  if (prev.length > maxLines) prev.splice(0, prev.length - maxLines);
  el.log.textContent = prev.join("\n");
  el.log.scrollTop = el.log.scrollHeight;
}

function clearLog() {
  el.log.textContent = "";
}

function clearOutputs() {
  if (lastBlobUrl) {
    try {
      URL.revokeObjectURL(lastBlobUrl);
    } catch (e) {}
    lastBlobUrl = null;
  }
  el.outVideo.removeAttribute("src");
  el.outVideo.load();
  el.outAudio.removeAttribute("src");
  el.outAudio.load();
  el.outImage.removeAttribute("src");
  el.outImage.style.display = "none";
  el.download.href = "#";
  el.download.removeAttribute("download");
}

function setRunning(on) {
  el.run.disabled = on;
  el.validate.disabled = on;
  el.file.disabled = on;
  el.applyPreset.disabled = on;
}

function cloneRecipe(x) {
  if (!x || typeof x !== "object") return x;
  return JSON.parse(JSON.stringify(x));
}

function recipeKey(x) {
  if (!x || typeof x !== "object") return "";
  return JSON.stringify(x);
}

function applyRecipeToUi(recipe) {
  const clearCropUi = () => {
    if (el.cropX) el.cropX.value = "";
    if (el.cropY) el.cropY.value = "";
    if (el.cropW) el.cropW.value = "";
    if (el.cropH) el.cropH.value = "";
  };
  const clearScaleUi = () => {
    if (el.scaleW) el.scaleW.value = "";
    if (el.scaleH) el.scaleH.value = "";
    if (el.scaleKeepAspect) el.scaleKeepAspect.checked = true;
  };
  const clearBitrateUi = () => {
    if (el.videoKbps) el.videoKbps.value = "";
    if (el.audioKbps) el.audioKbps.value = "";
  };
  const clearFrameUi = () => {
    if (el.frameAt) el.frameAt.value = "";
  };

  const getEl = (id) => el[id] || document.getElementById(id);

  const setValue = (ids, v) => {
    for (const id of ids) {
      const e = getEl(id);
      if (!e) continue;
      e.value = v === null || v === undefined ? "" : String(v);
      return true;
    }
    return false;
  };

  const setChecked = (ids, v) => {
    for (const id of ids) {
      const e = getEl(id);
      if (!e) continue;
      e.checked = Boolean(v);
      return true;
    }
    return false;
  };

  if (!recipe || typeof recipe !== "object") return;

  if (recipe.trim) {
    setValue(["trimStart"], recipe.trim.start_ms ?? "");
    setValue(["trimEnd"], recipe.trim.end_ms ?? "");
  }

  if (recipe.remove_segments === null) {
    state.removeSegments = [];
    renderSegments();
  }
  if (Array.isArray(recipe.remove_segments)) {
    state.removeSegments = recipe.remove_segments.slice();
    renderSegments();
  }

  if (recipe.container) {
    setValue(["container"], recipe.container);
  }

  if (recipe.audio && recipe.audio.mode) {
    setValue(["audioMode"], recipe.audio.mode);
    if (recipe.audio.mode === "extract") {
      setValue(["audioFormat"], recipe.audio.extract_format ?? "");
    }
  }

  if (recipe.crop !== undefined) {
    setChecked(["cropEnable"], !!recipe.crop);
  }
  if (recipe.crop === null) {
    clearCropUi();
  }
  if (recipe.crop) {
    setValue(["cropX", "crop_x", "cropLeft", "crop_left"], recipe.crop.x ?? "");
    setValue(["cropY", "crop_y", "cropTop", "crop_top"], recipe.crop.y ?? "");
    setValue(
      ["cropW", "crop_w", "cropWidth", "crop_width"],
      recipe.crop.w ?? "",
    );
    setValue(
      ["cropH", "crop_h", "cropHeight", "crop_height"],
      recipe.crop.h ?? "",
    );
  }

  if (recipe.scale !== undefined) {
    setChecked(["scaleEnable"], !!recipe.scale);
  }
  if (recipe.scale === null) {
    clearScaleUi();
  }
  if (recipe.scale) {
    setValue(
      ["scaleW", "scale_w", "scaleWidth", "scale_width"],
      recipe.scale.width ?? "",
    );
    setValue(
      ["scaleH", "scale_h", "scaleHeight", "scale_height"],
      recipe.scale.height ?? "",
    );
    setChecked(
      ["scaleKeepAspect", "keepAspect", "keep_aspect", "scale_keep_aspect"],
      recipe.scale.keep_aspect ?? true,
    );
  }

  if (recipe.bitrate === null) {
    clearBitrateUi();
  }
  if (recipe.bitrate) {
    setValue(
      ["videoKbps", "video_kbps", "bitrateVideoKbps", "bitrate_video_kbps"],
      recipe.bitrate.video_kbps ?? "",
    );
    setValue(
      ["audioKbps", "audio_kbps", "bitrateAudioKbps", "bitrate_audio_kbps"],
      recipe.bitrate.audio_kbps ?? "",
    );
  }

  if (recipe.frame_capture !== undefined) {
    setChecked(["frameEnable"], !!recipe.frame_capture);
  }
  if (recipe.frame_capture === null) {
    clearFrameUi();
  }
  if (recipe.frame_capture) {
    setValue(["frameAt"], recipe.frame_capture.at_ms ?? "");
  }
}

function uiValues() {
  return {
    trimStart: el.trimStart.value,
    trimEnd: el.trimEnd.value,
    audioMode: el.audioMode.value,
    audioFormat: el.audioFormat.value,
    container: el.container.value,
    removeSegments: state.removeSegments.slice(),
    cropEnable: !!el.cropEnable?.checked,
    cropX: el.cropX?.value,
    cropY: el.cropY?.value,
    cropW: el.cropW?.value,
    cropH: el.cropH?.value,
    scaleEnable: !!el.scaleEnable?.checked,
    scaleW: el.scaleW?.value,
    scaleH: el.scaleH?.value,
    scaleKeepAspect: !!el.scaleKeepAspect?.checked,
    videoKbps: el.videoKbps?.value,
    audioKbps: el.audioKbps?.value,
    frameEnable: !!el.frameEnable?.checked,
    frameAt: el.frameAt?.value,
  };
}

function toMs(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return Math.max(0, Math.floor(n));
}

function mergeSegments(segs) {
  const list = (Array.isArray(segs) ? segs : [])
    .map((s) => ({ start_ms: toMs(s.start_ms), end_ms: toMs(s.end_ms) }))
    .filter(
      (s) => s.start_ms !== null && s.end_ms !== null && s.start_ms < s.end_ms,
    )
    .sort((a, b) => a.start_ms - b.start_ms);

  const out = [];
  for (const s of list) {
    const last = out[out.length - 1];
    if (!last || s.start_ms > last.end_ms) {
      out.push({ start_ms: s.start_ms, end_ms: s.end_ms });
    } else {
      last.end_ms = Math.max(last.end_ms, s.end_ms);
    }
  }
  return out;
}

function renderSegments() {
  const segs = state.removeSegments;
  el.segList.innerHTML = "";

  const dur =
    state.meta && state.meta.duration_ms ? state.meta.duration_ms : null;
  el.segHint.textContent = dur ? `duration_ms=${dur}` : "";

  if (!segs.length) {
    const empty = document.createElement("div");
    empty.className = "segitem";
    const meta = document.createElement("div");
    meta.className = "segmeta";
    const chip = document.createElement("span");
    chip.className = "segchip";
    chip.textContent = "none";
    meta.appendChild(chip);
    empty.appendChild(meta);
    el.segList.appendChild(empty);
    return;
  }

  segs.forEach((s, idx) => {
    const row = document.createElement("div");
    row.className = "segitem";

    const meta = document.createElement("div");
    meta.className = "segmeta";

    const chip = document.createElement("span");
    chip.className = "segchip";
    chip.textContent = `${s.start_ms}..${s.end_ms} (${s.end_ms - s.start_ms} ms)`;

    meta.appendChild(chip);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "segbtn";
    btn.textContent = "Remove";
    btn.onclick = () => {
      state.removeSegments = mergeSegments(
        state.removeSegments.filter((_, i) => i !== idx),
      );
      renderSegments();
    };

    row.appendChild(meta);
    row.appendChild(btn);
    el.segList.appendChild(row);
  });
}

function setSegments(next) {
  state.removeSegments = mergeSegments(next);
  renderSegments();
}

function addSegmentFromInputs() {
  const a = toMs(el.segStart.value);
  const b = toMs(el.segEnd.value);
  if (a === null || b === null) throw new Error("Segment start/end required");
  if (a >= b) throw new Error("Segment end must be greater than start");
  setSegments([...state.removeSegments, { start_ms: a, end_ms: b }]);
}

function updateUndoRedoUi() {
  const u = document.getElementById("undoBtn");
  const r = document.getElementById("redoBtn");
  if (u)
    u.disabled = state.undoStack.length === 0 || !state.file || !state.meta;
  if (r)
    r.disabled = state.redoStack.length === 0 || !state.file || !state.meta;
}

function commitNormalized(nextNormalized, opts) {
  const options = opts || {};
  const pushHistory = options.pushHistory !== false;
  const prev = state.recipeNormalized;
  const prevKey = recipeKey(prev);
  const nextKey = recipeKey(nextNormalized);

  if (
    !state.isRestoring &&
    pushHistory &&
    prev &&
    prevKey &&
    prevKey !== nextKey
  ) {
    state.undoStack.push(cloneRecipe(prev));
    if (state.undoStack.length > 50)
      state.undoStack.splice(0, state.undoStack.length - 50);
    state.redoStack = [];
  }

  state.recipeNormalized = nextNormalized;
  applyRecipeToUi(state.recipeNormalized);
  updateUndoRedoUi();
}

async function restoreFromSnapshot(snapshot, dir) {
  if (!snapshot) return;
  if (!state.file || !state.meta) throw new Error("No file/meta");

  state.isRestoring = true;
  try {
    const res = await validateRecipe({ meta: state.meta, recipe: snapshot });
    commitNormalized(res.normalized, { pushHistory: false });
    if (dir === "undo") {
      state.redoStack.push(cloneRecipe(snapshot));
      if (state.redoStack.length > 50)
        state.redoStack.splice(0, state.redoStack.length - 50);
    } else if (dir === "redo") {
      state.undoStack.push(cloneRecipe(snapshot));
      if (state.undoStack.length > 50)
        state.undoStack.splice(0, state.undoStack.length - 50);
    }
    updateUndoRedoUi();
  } finally {
    state.isRestoring = false;
  }
}

function initUndoRedoUi() {
  const anchor = el.preset;
  if (!anchor || !anchor.parentElement) return;

  const wrap = document.createElement("div");
  wrap.className = "undoredo";

  const undoBtn = document.createElement("button");
  undoBtn.type = "button";
  undoBtn.id = "undoBtn";
  undoBtn.textContent = "Undo";

  const redoBtn = document.createElement("button");
  redoBtn.type = "button";
  redoBtn.id = "redoBtn";
  redoBtn.textContent = "Redo";

  undoBtn.onclick = async () => {
    try {
      if (!state.undoStack.length) return;
      clearLog();
      const prev = state.undoStack.pop();
      const cur = cloneRecipe(state.recipeNormalized);
      await restoreFromSnapshot(prev, "undo");
      if (cur) state.redoStack[state.redoStack.length - 1] = cur;
      log("Undone");
    } catch (e) {
      log(String(e && e.message ? e.message : e));
    }
  };

  redoBtn.onclick = async () => {
    try {
      if (!state.redoStack.length) return;
      clearLog();
      const next = state.redoStack.pop();
      const cur = cloneRecipe(state.recipeNormalized);
      await restoreFromSnapshot(next, "redo");
      if (cur) state.undoStack[state.undoStack.length - 1] = cur;
      log("Redone");
    } catch (e) {
      log(String(e && e.message ? e.message : e));
    }
  };

  wrap.appendChild(undoBtn);
  wrap.appendChild(redoBtn);
  anchor.parentElement.appendChild(wrap);
  updateUndoRedoUi();
}

async function refreshDraftAndValidate() {
  if (!state.file || !state.meta) throw new Error("No file/meta");
  const draft = buildRecipeFromUi(uiValues());
  state.recipeDraft = draft;
  const res = await validateRecipe({ meta: state.meta, recipe: draft });
  commitNormalized(res.normalized);
  return res.normalized;
}

async function loadPresets() {
  const list = await presets();
  state.presets = Array.isArray(list) ? list : [];
  el.preset.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = "none";
  el.preset.appendChild(opt0);
  for (const p of state.presets) {
    const opt = document.createElement("option");
    opt.value = p.key;
    opt.textContent = `${p.label} (${p.key})`;
    el.preset.appendChild(opt);
  }
}

function mimeByKind(out, outName, container) {
  const kind = out && out.kind ? out.kind : "video";
  const name = outName || "";
  const ext = name.split(".").pop()?.toLowerCase() || container || "mp4";
  if (kind === "image") return "image/png";
  if (kind === "audio") {
    if (ext === "mp3") return "audio/mpeg";
    if (ext === "wav") return "audio/wav";
    if (ext === "aac") return "audio/aac";
    if (ext === "flac") return "audio/flac";
    if (ext === "ogg") return "audio/ogg";
    return "application/octet-stream";
  }
  if (ext === "webm") return "video/webm";
  if (ext === "mkv") return "video/x-matroska";
  return "video/mp4";
}

function showOutput({ out, outName, data, container }) {
  clearOutputs();
  const mime = mimeByKind(out, outName, container);
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  const blob = new Blob([bytes], { type: mime });
  const url = URL.createObjectURL(blob);
  lastBlobUrl = url;

  const kind = out && out.kind ? out.kind : "video";
  if (kind === "audio") {
    el.outAudio.src = url;
    el.outAudio.load();
  } else if (kind === "image") {
    el.outImage.src = url;
    el.outImage.style.display = "block";
  } else {
    el.outVideo.src = url;
    el.outVideo.load();
  }

  el.download.href = url;
  el.download.download = outName || "output";
}

el.clear.onclick = () => {
  clearLog();
  clearOutputs();
};

el.addSeg.onclick = () => {
  try {
    addSegmentFromInputs();
  } catch (e) {
    log(String(e && e.message ? e.message : e));
  }
};

el.clearSegs.onclick = () => {
  setSegments([]);
};

el.file.onchange = async () => {
  try {
    clearLog();
    clearOutputs();
    const f = el.file.files && el.file.files[0];
    if (!f) return;
    state.file = f;
    log("Loading meta...");
    state.meta = await loadVideoMeta(f);
    state.undoStack = [];
    state.redoStack = [];
    updateUndoRedoUi();
    log(
      `Meta: duration_ms=${state.meta.duration_ms} w=${state.meta.width} h=${state.meta.height} fps=${state.meta.fps} has_audio=${state.meta.has_audio}`,
    );
    renderSegments();
    log("Validating...");
    await refreshDraftAndValidate();
    log("Validated");
  } catch (e) {
    log(String(e && e.message ? e.message : e));
  }
};

el.applyPreset.onclick = async () => {
  try {
    if (!state.file || !state.meta) throw new Error("No file/meta");
    const key = el.preset.value;
    clearLog();
    if (!key) {
      log("Applying preset: none");
      const base = state.recipeNormalized || buildRecipeFromUi(uiValues());
      const next = { ...base };

      next.remove_segments = [];
      next.crop = null;
      next.scale = null;
      next.bitrate = null;
      next.frame_capture = null;

      applyRecipeToUi(next);

      state.recipeDraft = next;
      const res = await validateRecipe({ meta: state.meta, recipe: next });
      commitNormalized(res.normalized);
      log("Validated");
      return;
    }

    const p = state.presets.find((x) => x.key === key);
    if (!p) throw new Error("Preset not found");
    log(`Applying preset: ${p.key}`);
    const base = state.recipeNormalized || buildRecipeFromUi(uiValues());
    const next = applyPatch(base, p.recipe_patch || {});
    applyRecipeToUi(next);

    state.recipeDraft = next;
    const res = await validateRecipe({ meta: state.meta, recipe: next });
    commitNormalized(res.normalized);
    log("Validated");
  } catch (e) {
    log(String(e && e.message ? e.message : e));
  }
};

el.validate.onclick = async () => {
  try {
    if (!state.file || !state.meta) throw new Error("No file/meta");
    clearLog();
    log("Validating...");
    await refreshDraftAndValidate();
    log("Validated");
  } catch (e) {
    log(String(e && e.message ? e.message : e));
  }
};

el.run.onclick = async () => {
  try {
    if (!state.file || !state.meta) throw new Error("No file/meta");
    clearLog();
    setRunning(true);
    log("Validating...");
    const normalized = await refreshDraftAndValidate();
    log("Planning...");
    const p = await plan({ meta: state.meta, recipe: normalized });
    state.lastPlan = p;
    log(`Plan: mode=${p.mode} container=${p.container}`);
    log("Running...");
    const out = await runPlan({ file: state.file, planRes: p, log });
    showOutput({ ...out, container: p.container });
    log("Done");
  } catch (e) {
    log(String(e && e.message ? e.message : e));
  } finally {
    setRunning(false);
  }
};

await loadPresets();
initUndoRedoUi();
renderSegments();
