# pylint: disable=global-statement
"""
app.core.db Docstring
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

_ENGINE: Engine | None = None
_SessionLocal: sessionmaker | None = None

def get_engine() -> Engine:
    global _ENGINE, _SessionLocal
    if _ENGINE is not None:
        return _ENGINE
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    pool_size = int(os.getenv("DB_POOL_SIZE", "6"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "2"))
    pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "20"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "900"))
    _ENGINE = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        future=True,
    )
    _SessionLocal = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False, future=True)
    return _ENGINE

def get_session():
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
