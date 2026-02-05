import { FFmpeg } from "/static/ffmpeg/index.js";

const ffmpeg = new FFmpeg();
let loaded = false;
let hooksBound = false;

export async function ensureFfmpeg(log) {
  if (!hooksBound) {
    ffmpeg.on("log", ({ message }) => {
      if (message) log(message);
    });
    ffmpeg.on("progress", ({ progress, time }) => {
      const pct = Math.max(0, Math.min(100, Math.floor((progress || 0) * 100)));
      log(`Progress: ${pct}% time_ms=${time ?? 0}`);
    });
    hooksBound = true;
  }

  if (loaded) return;
  log("Loading ffmpeg.wasm...");
  await ffmpeg.load({
    coreURL: "/static/ffmpeg/ffmpeg-core.js",
    wasmURL: "/static/ffmpeg/ffmpeg-core.wasm",
    workerURL: "/static/ffmpeg/worker.js",
  });
  loaded = true;
  log("ffmpeg.wasm loaded");
}

async function fileToU8(file) {
  const ab = await file.arrayBuffer();
  return new Uint8Array(ab);
}

export async function runPlan({ file, planRes, log }) {
  const inName = "input";
  const inExt = (file.name || "").split(".").pop()?.toLowerCase() || "mp4";
  const inputName = `${inName}.${inExt}`;

  const outputs = Array.isArray(planRes.outputs) ? planRes.outputs : [];
  const out = outputs[0] || {
    name: `output.${planRes.container || "mp4"}`,
    kind: "video",
  };
  const outName = out.name || `output.${planRes.container || "mp4"}`;

  await ensureFfmpeg(log);

  try {
    await ffmpeg.deleteFile(inputName);
  } catch (_) {}
  try {
    await ffmpeg.deleteFile(outName);
  } catch (_) {}

  log("Writing input...");
  await ffmpeg.writeFile(inputName, await fileToU8(file));

  const args = ["-y", "-i", inputName, ...(planRes.ffmpeg_args || []), outName];
  log(`Exec: ffmpeg ${args.join(" ")}`);
  await ffmpeg.exec(args);

  log("Reading output...");
  const data = await ffmpeg.readFile(outName);
  return { out, outName, data };
}
