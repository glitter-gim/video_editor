"""
data.config._conf_.example Docstring
"""
import os
from datetime import datetime
from ipaddress import ip_network

import pytz

CGK_URL = os.getenv("CGK_URL", "https://captcha.example")
CHK_URL = os.getenv("CHK_URL", "https://cheer.example")
E44_URL = os.getenv("E44_URL", "https://404.example")
DGK_URL = os.getenv("DGK_URL", "https://deny.example")
GAT_URL = os.getenv("GAT_URL", "https://gate.example")
GBZ_URL = os.getenv("GBZ_URL", "https://example.bz")
GIM_URL = os.getenv("GIM_URL", "https://example.im")
GKR_URL = os.getenv("GKR_URL", "https://example.kr")
GMY_URL = os.getenv("GMY_URL", "https://example.my")
GTW_URL = os.getenv("GTW_URL", "https://example.tw")
MGK_URL = os.getenv("MGK_URL", "https://m.example.kr")
NGK_URL = os.getenv("NGK_URL", "https://new.example.kr")
MSG_URL = os.getenv("MSG_URL", "https://msg.example.kr")
PGK_URL = os.getenv("PGK_URL", "https://policy.example.kr")
VGK_URL = os.getenv("VGK_URL", "https://vlog.example.kr")
VGG_URL = os.getenv("VGG_URL", "https://vlog.example.kr/gate")
WGK_URL = os.getenv("WGK_URL", "https://whitepaper.example.kr")

VEK_ENV = os.getenv("APP_ENV_PATH", ".env")

FAV_VRO = os.getenv("FAVICON_ICO_PATH", "favicon.ico")
SHD_TXT = os.getenv("ROBOTS_TXT_PATH", "robots.txt")
SHD_XML = os.getenv("SITEMAP_XML_PATH", "sitemap.xml")

BLOCK_IP = os.getenv("BLOCK_IP_FILE", "blocked.json")

INTERNAL_IP_RANGES = [
    ip_network("127.0.0.0/8"),
    ip_network("::1/128"),
]

PRIVATE_OR_LOCAL_NETS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
    ip_network("::1/128"),
]

TRUSTED_BOTS = [
    "Googlebot",
    "Bingbot",
    "DuckDuckBot",
    "YandexBot",
]

tz = pytz.timezone(os.getenv("APP_TIMEZONE", "UTC"))

def now():
    return datetime.now(tz)

def get_plugin_state_change_time():
    return now().isoformat()

class Settings:
    APP_IS_DEBUG = os.getenv("APP_IS_DEBUG", "false").lower() == "true"

settings = Settings()
cache_plugin_state = {}

gg_tel = os.getenv("GG_TEL", "tel:+0000000000")
gg_mail = os.getenv("GG_MAIL", "admin@example.com")
gg_mail_to = os.getenv("GG_MAIL_TO", "mailto:admin@example.com")
kakao_js_key = os.getenv("KAKAO_JS_KEY", "")

VEDIT_API_KEY = os.getenv("VEDIT_API_KEY", "VEDIT_API_KEY")
VEDIT_API_COOKIE = os.getenv("VEDIT_API_COOKIE", "VEDIT_API_COOKIE")

TEMPLATES_CONTEXT = {
    "site_name": os.getenv("SITE_NAME", "Example Infra"),
    "author": os.getenv("SITE_AUTHOR", "Example"),
    "gg_tel": gg_tel,
    "gg_mail": gg_mail,
    "gg_mail_to": gg_mail_to,
    "gk_url": GKR_URL,
    "pg_url": PGK_URL,
    "vg_url": VGK_URL,
    "vgg_url": VGG_URL,
    "kakao_js_key": kakao_js_key,
}
