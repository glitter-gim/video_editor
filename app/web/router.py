"""
app.web.router Docstring
"""
import importlib.util
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

_ROOT = Path(__file__).resolve().parents[2]
_CONF_PATH = _ROOT / "data" / "config" / "_conf_.py"
_spec = importlib.util.spec_from_file_location("_conf_", str(_CONF_PATH))
if _spec is None or _spec.loader is None:
    raise RuntimeError("Failed to load config module")
const = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(const)

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root():
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <title>vedit.glitter.kr · status</title>
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link rel="stylesheet" href="/static/css/vedit.css">
        </head>
        <body class="cheer-body">
          <main class="cheer-main">
            <div class="cheer-badge">cheer</div>
            <h1 class="cheer-title">Video Editor, 💫 vedit.glitter.kr</h1>
            <p class="cheer-text">Service is running and reachable.</p>
            <div class="cheer-meta">
              <span class="cheer-meta-label">backend</span>
              <span class="cheer-meta-value">FastAPI · Uvicorn</span>
            </div>
          </main>
        </body>
        </html>
        """
    )

@router.head("/", include_in_schema=False)
def index_head():
    return HTMLResponse("")

@router.head("/t/app", include_in_schema=False)
def app_head():
    return Response(status_code=204)


@router.get("/t/app", include_in_schema=False)
def app_page():
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>vedit app</title>
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
  <main class="wrap">
    <header class="hdr">
      <h1 class="ttl">vedit</h1>
      <p class="sub">Local video editing in your browser (no upload)</p>
    </header>

    <section class="card">
      <div class="row">
        <label class="lbl" for="file">Input video</label>
        <input type="file" id="file" accept="video/*">
      </div>

      <div class="row">
        <label class="lbl" for="preset">Preset</label>
        <select id="preset"></select>
        <button id="applyPreset" type="button" class="ghost">Apply</button>
      </div>

      <div class="row">
        <label class="lbl" for="trimStart">Trim start (ms)</label>
        <input id="trimStart" type="number" min="0" step="100" placeholder="0">
        <label class="lbl" for="trimEnd">Trim end (ms)</label>
        <input id="trimEnd" type="number" min="0" step="100" placeholder="">
      </div>

      <div class="row">
        <label class="lbl" for="segStart">Remove segment (ms)</label>
        <input id="segStart" type="number" min="0" step="100" placeholder="start">
        <input id="segEnd" type="number" min="0" step="100" placeholder="end">
        <button id="addSeg" type="button" class="ghost">Add</button>
        <button id="clearSegs" type="button" class="ghost">Clear segments</button>
      </div>

      <div class="row">
        <div class="segbox">
          <div class="seghead">
            <span class="segttl">Segments to remove</span>
            <span id="segHint" class="seghint"></span>
          </div>
          <div id="segList" class="seglist"></div>
        </div>
      </div>

      <div class="row">
        <label class="lbl" for="audioMode">Audio</label>
        <select id="audioMode">
          <option value="keep">keep</option>
          <option value="mute">mute</option>
          <option value="extract">extract</option>
        </select>
        <select id="audioFormat">
          <option value="mp3">mp3</option>
          <option value="aac">aac</option>
          <option value="wav">wav</option>
          <option value="flac">flac</option>
          <option value="ogg">ogg</option>
        </select>
        <label class="lbl" for="container">Container</label>
        <select id="container">
          <option value="mp4">mp4</option>
          <option value="webm">webm</option>
          <option value="mkv">mkv</option>
        </select>
      </div>

      <div class="row">
        <label class="lbl" for="cropEnable">Crop</label>
        <input id="cropEnable" type="checkbox">
        <input id="cropX" type="number" min="0" step="1" placeholder="x">
        <input id="cropY" type="number" min="0" step="1" placeholder="y">
        <input id="cropW" type="number" min="1" step="1" placeholder="w">
        <input id="cropH" type="number" min="1" step="1" placeholder="h">
      </div>

      <div class="row">
        <label class="lbl" for="scaleEnable">Scale</label>
        <input id="scaleEnable" type="checkbox">
        <input id="scaleW" type="number" min="1" step="1" placeholder="width">
        <input id="scaleH" type="number" min="1" step="1" placeholder="height">
        <label class="lbl" for="scaleKeepAspect">Keep aspect</label>
        <input id="scaleKeepAspect" type="checkbox" checked>
      </div>

      <div class="row">
        <label class="lbl" for="videoKbps">Bitrate</label>
        <input id="videoKbps" type="number" min="100" step="100" placeholder="video kbps">
        <input id="audioKbps" type="number" min="32" step="1" placeholder="audio kbps">
      </div>

      <div class="row">
        <label class="lbl" for="frameEnable">Frame capture</label>
        <input id="frameEnable" type="checkbox">
        <input id="frameAt" type="number" min="0" step="100" placeholder="at ms">
      </div>      
      <div class="row">
        <button id="validate" type="button" class="ghost">Validate</button>
        <button id="run" type="button">Run</button>
        <button id="clear" type="button" class="ghost">Clear</button>
      </div>

      <pre id="log" class="log" aria-live="polite"></pre>

      <div class="out">
        <video id="outVideo" controls playsinline></video>
        <audio id="outAudio" controls></audio>
        <img id="outImage" alt="output frame">
        <div class="row">
          <a id="download" href="#" download>Download</a>
        </div>
      </div>
    </section>
  </main>

  <script type="module" src="/static/js/app/app.js?v=1"></script>
</body>
</html>"""
    resp = HTMLResponse(html)
    key = getattr(const, "VEDIT_API_KEY", "VEDIT_API_KEY")
    if key:
        cookie_name = getattr(const, "VEDIT_API_COOKIE", "vedit_key")
        resp.set_cookie(cookie_name, key, httponly=True, secure=True, samesite="lax", path="/", max_age=86400)
    return resp


@router.head("/t/min", include_in_schema=False)
def test_min_head():
    return Response(status_code=204)

@router.get("/healthz", include_in_schema=False)
def health():
    return PlainTextResponse("ok")

@router.get("/t/min", include_in_schema=False)
def test_min():
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>vedit</title>
  <link rel="stylesheet" href="/static/css/app.css">
</head>
<body>
  <main class="wrap">
    <header class="hdr">
      <h1 class="ttl">vedit</h1>
      <p class="sub">Local video editing in your browser (no upload)</p>
    </header>

    <section class="card">
      <div class="row">
        <label class="lbl" for="file">Input video</label>
        <input type="file" id="file" accept="video/*">
      </div>

      <div class="row">
        <button id="run" type="button">Run</button>
        <button id="clear" type="button" class="ghost">Clear</button>
      </div>

      <pre id="log" class="log" aria-live="polite"></pre>

      <div class="out">
        <video id="out" controls playsinline></video>
      </div>
    </section>
  </main>

  <script type="module" src="/static/js/t-min.js?v=2"></script>
</body>
</html>"""
    resp = HTMLResponse(html)
    key = getattr(const, "VEDIT_API_KEY", "") or ""
    if key:
        cookie_name = getattr(const, "VEDIT_API_COOKIE", "vedit_key")
        resp.set_cookie(cookie_name, key, httponly=True, secure=True, samesite="lax", path="/", max_age=86400)
    return resp
