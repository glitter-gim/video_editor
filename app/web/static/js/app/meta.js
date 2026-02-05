function detectHasAudio(v) {
  const a1 = typeof v.mozHasAudio === "boolean" ? v.mozHasAudio : false;
  const a2 =
    typeof v.webkitAudioDecodedByteCount === "number"
      ? v.webkitAudioDecodedByteCount > 0
      : false;
  const a3 =
    v.audioTracks && typeof v.audioTracks.length === "number"
      ? v.audioTracks.length > 0
      : false;
  return Boolean(a1 || a2 || a3);
}

export function loadVideoMeta(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    v.preload = "metadata";
    v.muted = true;

    const cleanup = () => {
      try {
        v.removeAttribute("src");
        v.load();
      } catch (e) {}
      setTimeout(() => {
        try {
          URL.revokeObjectURL(url);
        } catch (e) {}
      }, 300);
    };

    v.onloadedmetadata = () => {
      const meta = {
        duration_ms: Math.max(1, Math.floor(v.duration * 1000)),
        width: v.videoWidth || 1920,
        height: v.videoHeight || 1080,
        fps: 30,
        has_audio: detectHasAudio(v),
      };
      cleanup();
      resolve(meta);
    };

    v.onerror = () => {
      cleanup();
      reject(new Error("Failed to load video metadata"));
    };

    v.src = url;
  });
}
