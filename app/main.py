# pylint: disable=global-statement,unused-argument,trailing-whitespace
"""
app.main Docstring
"""
import importlib.util
import json
import logging
import os
import re
import threading
import time
import uuid
from ipaddress import IPv6Address, ip_address, ip_network
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.plan import router as plan_router
from app.api.video import router as video_router
from app.core.db import get_engine
from app.core.models import Base
from app.web.router import router as web_router

_ROOT = Path(__file__).resolve().parents[1]
_CONF_PATH = _ROOT / "data" / "config" / "_conf_.py"
_spec = importlib.util.spec_from_file_location("_conf_", str(_CONF_PATH))
if _spec is None or _spec.loader is None:
    raise RuntimeError("Failed to load config module")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
const = _mod

if os.getenv("VEK_LOAD_DOTENV") == "1":
    env_path = os.getenv("VEK_ENV") or getattr(const, "VEK_ENV", None)
    if env_path:
        load_dotenv(env_path, override=True)

app = FastAPI(title="vedit", version="1.0.0")

log_level = os.getenv("VEDIT_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
_LOG = logging.getLogger("vedit")

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

origins = [
    "https://glitter.bz",
    "https://glitter.im",
    "https://glitter.kr",
    "https://glitter.my",
    "https://glitter.tw",
    "https://m.glitter.kr",
    "https://vlog.glitter.kr",
    "https://trigger.glitter.kr",
    "https://test.glitter.my",
    "https://dalmoi.pe.kr",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST"],
    allow_headers=["Content-Type", "X-App-Key"],
    max_age=600,
)

app.include_router(web_router)
app.include_router(video_router)
app.include_router(plan_router)

@app.on_event("startup")
def _startup():
    if os.getenv("DB_AUTO_CREATE", "0") == "1":
        try:
            Base.metadata.create_all(bind=get_engine())
        except Exception as e:
            _LOG.error("db_init_failed %s", str(e))

_DENY_RE = re.compile(
    r"""
    (?ix)
    (?!^/\.well-known/)
    (?:
        ^/(?:app|venv|\.vscode)(?:/|$)
      | ^/data/config(?:/|$)
      | (?:^|/)
        (?:
            \.env(?:\.[^/]+)?
          | \.(?:git|hg|svn)(?:/|$)
          | \.(?:DS_Store|htaccess|htpasswd)$
          | \.aws/credentials$
          | \.ssh/(?:id_rsa|id_ed25519|authorized_keys|known_hosts)$
          | (?:_conf_|_config)\.py$
          | .*?\.(?:py|pyc|pyo)$
          | .*?\.(?:log|bak|old|swp|tmp|orig|save)$
          | .*~
          | .*?\.(?:sql|sqlite|db)$
          | .*?\.(?:pem|key|p12|pfx|kdbx)$
        )
        (?:$|/)
    )
    """.strip()
)

_BLOCKS_MTIME = None
_BLOCKS_LOCK = threading.Lock()
BLOCKED_NETS: list = []

def _strip_port(host: str) -> str:
    if not host:
        return host
    host = host.strip()
    if host.startswith("["):
        m = re.match(r"^\[([^\]]+)\](?::\d+)?$", host)
        return m.group(1) if m else host
    if host.count(":") == 1:
        h, maybe_port = host.split(":", 1)
        if maybe_port.isdigit():
            return h
    return host

def _normalize_ip(text: str) -> str | None:
    try:
        ip_obj = ip_address(text)
    except ValueError:
        return None
    if isinstance(ip_obj, IPv6Address) and getattr(ip_obj, "ipv4_mapped", None):
        return str(ip_obj.ipv4_mapped)
    return str(ip_obj)

def _is_trusted_proxy(peer: str) -> bool:
    try:
        ipobj = ip_address(peer)
    except ValueError:
        return False
    return any(ipobj in net for net in const.INTERNAL_IP_RANGES)

def _is_public_candidate(ip_txt: str) -> bool:
    try:
        ipobj = ip_address(ip_txt)
    except ValueError:
        return False
    return not any(ipobj in net for net in const.PRIVATE_OR_LOCAL_NETS)

def get_client_ip(request: Request) -> str | None:
    peer = None
    if request.client and request.client.host:
        peer = _normalize_ip(_strip_port(request.client.host.strip()))
    if not peer:
        return None
    if not _is_trusted_proxy(peer):
        return peer
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        for raw in parts:
            cand = _normalize_ip(_strip_port(raw))
            if cand and _is_public_candidate(cand):
                return cand
    xri = request.headers.get("x-real-ip", "")
    if xri:
        cand = _normalize_ip(_strip_port(xri.strip()))
        if cand and _is_public_candidate(cand):
            return cand
    return peer

def _parse_nets(items: Iterable[str]):
    nets = []
    for raw in items:
        s = str(raw).replace("\ufeff", "").replace("\u200b", "").strip()
        if not s:
            continue
        try:
            nets.append(ip_network(s, strict=False))
            continue
        except ValueError:
            pass
        for suf in ("/32", "/128"):
            try:
                nets.append(ip_network(f"{s}{suf}", strict=False))
                break
            except ValueError:
                continue
    return nets

def _load_blocks():
    items = getattr(const, "BLOCK_IP", [])
    if isinstance(items, (list, tuple)):
        nets = _parse_nets(items)
        conf_file = getattr(const, "__file__", "") or str(_CONF_PATH)
        mtime = os.path.getmtime(conf_file)
        return nets, mtime
    path = str(items)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    nets = _parse_nets(data)
    return nets, os.path.getmtime(path)

def _refresh_blocks():
    global BLOCKED_NETS, _BLOCKS_MTIME
    nets, mtime = _load_blocks()
    with _BLOCKS_LOCK:
        BLOCKED_NETS = nets
        _BLOCKS_MTIME = mtime

def _watch_blocks(interval: int = 5):
    items = getattr(const, "BLOCK_IP", [])
    if isinstance(items, (list, tuple)):
        return
    path = str(items)
    while True:
        try:
            mtime = os.path.getmtime(path)
            if _BLOCKS_MTIME is None or mtime != _BLOCKS_MTIME:
                _refresh_blocks()
        except Exception:
            pass
        time.sleep(interval)

try:
    _refresh_blocks()
except Exception:
    BLOCKED_NETS = []
    _BLOCKS_MTIME = None

threading.Thread(target=_watch_blocks, daemon=True).start()


def is_internal_ip(ip_str: str) -> bool:
    try:
        ip = ip_address(ip_str)
        return any(ip in net for net in const.INTERNAL_IP_RANGES)
    except ValueError:
        return False

def is_trusted_bot(user_agent: str) -> bool:
    return bool(user_agent) and any(
        bot.lower() in user_agent.lower() for bot in const.TRUSTED_BOTS
    )

async def verify_request(request: Request) -> bool:
    client_ip = get_client_ip(request)
    if client_ip is None:
        raise HTTPException(status_code=400, detail="Client IP unavailable")
    if is_internal_ip(client_ip):
        return True
    ua = request.headers.get("user-agent", "")
    return is_trusted_bot(ua)

@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    start = time.time()
    ip_txt = get_client_ip(request) or "-"    
    try:
        resp: Response = await call_next(request)
    except Exception as e:
        dur_ms = int((time.time() - start) * 1000)
        _LOG.exception("req_error rid=%s ip=%s method=%s path=%s dur_ms=%d", rid, ip_txt, request.method, request.url.path, dur_ms)
        raise e
    dur_ms = int((time.time() - start) * 1000)
    _LOG.info("req rid=%s ip=%s method=%s path=%s status=%d dur_ms=%d", rid, ip_txt, request.method, request.url.path, resp.status_code, dur_ms)
    resp.headers.setdefault("X-Request-Id", rid)
    return resp

@app.middleware("http")
async def deny_sensitive_paths(request: Request, call_next):
    p = request.url.path
    if _DENY_RE.search(p.rstrip("/")):
        return PlainTextResponse("Not Found", status_code=404)
    return await call_next(request)

@app.middleware("http")
async def block_ip_middleware(request: Request, call_next):
    ip_txt = get_client_ip(request)
    if ip_txt is None:
        raise HTTPException(status_code=400, detail="Client IP unavailable")
    try:
        current_ip = ip_address(ip_txt)
    except ValueError:
        return await call_next(request)
    nets_snapshot = tuple(BLOCKED_NETS)
    if any(current_ip in net for net in nets_snapshot):
        return RedirectResponse(url=const.E44_URL, status_code=303)
    return await call_next(request)


@app.middleware("http")
async def api_gate_middleware(request: Request, call_next):
    key = os.getenv("VEDIT_API_KEY") or getattr(const, "VEDIT_API_KEY", "") or ""
    if not key:
        return await call_next(request)
    p = request.url.path
    if not p.startswith("/api/"):
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.method in ("GET", "HEAD") and p == "/api/presets":
        return await call_next(request)    
    cookie_name = os.getenv("VEDIT_API_COOKIE") or getattr(const, "VEDIT_API_COOKIE", "vedit_key")
    cookie_name = "vedit_key" if cookie_name == "VEDIT_API_COOKIE" else cookie_name
    cookie_val = request.cookies.get(cookie_name, "")
    hdr_val = request.headers.get("x-app-key", "")
    authed = (cookie_val == key or hdr_val == key)
    if p.startswith("/api/presets/custom"):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        ip_txt = get_client_ip(request) or "-"
        src = "cookie" if cookie_val == key else ("header" if hdr_val == key else "none")
        if authed:
            _LOG.warning("preset_custom_access rid=%s ip=%s method=%s path=%s auth=%s", rid, ip_txt, request.method, p, src)
            resp = await call_next(request)
            resp.headers.setdefault("X-Request-Id", rid)
            return resp
        return PlainTextResponse("Unauthorized", status_code=401)
    if authed:
        return await call_next(request)
    return PlainTextResponse("Unauthorized", status_code=401)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon(request: Request):
    if not await verify_request(request):
        raise HTTPException(status_code=404)
    file_path = const.FAV_VRO
    if file_path and os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/x-icon")
    raise HTTPException(status_code=404)

@app.get("/robots.txt", include_in_schema=False)
async def captcha_robots_txt(request: Request):
    if not await verify_request(request):
        raise HTTPException(status_code=404)
    file_path = const.SHD_TXT
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/plain; charset=utf-8")
    raise HTTPException(status_code=404)

@app.get("/sitemap.xml", include_in_schema=False)
async def captcha_sitemap_xml(request: Request):
    if not await verify_request(request):
        raise HTTPException(status_code=404)
    file_path = const.SHD_XML
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/xml")
    raise HTTPException(status_code=404)


@app.exception_handler(404)
async def custom_404_handler(request: Request, _exc):
    path = request.url.path
    accept = request.headers.get("accept", "")
    if path.startswith("/static/") or path.startswith("/api/"):
        return PlainTextResponse("Not Found", status_code=404)
    if any(path.endswith(ext) for ext in (".js", ".css", ".wasm", ".map", ".json")):
        return PlainTextResponse("Not Found", status_code=404)
    if "text/html" in accept:
        return RedirectResponse(url=const.E44_URL, status_code=303)
    return PlainTextResponse("Not Found", status_code=404)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp: Response = await call_next(request)
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'; "
        "object-src 'none'; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "font-src 'self' data:; "
        "style-src 'self'; "
        "script-src 'self' 'wasm-unsafe-eval'; "
        "connect-src 'self'; "
        "worker-src 'self' blob:; "
        "manifest-src 'self'"
    )
    resp.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(),camera=(),geolocation=(),gyroscope=(),"
        "magnetometer=(),microphone=(),payment=(),usb=(),browsing-topics=()",
    )
    resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    resp.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    p = request.url.path
    if p == "/t/min" or p.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-store"    
    return resp
