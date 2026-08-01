"""Layer database — engine & session SQLAlchemy.

SQLite untuk development lokal, PostgreSQL untuk produksi. Ganti database
cukup dengan mengubah env `DATABASE_URL` — kode di sini tidak berubah.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from basa.config import get_settings


class Base(DeclarativeBase):
    """Base declarative untuk semua model."""


def _prepare_sqlite_path(url: str) -> str:
    """Pastikan folder database SQLite file-based sudah ada."""
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        db_path = url.removeprefix("sqlite:///")
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return url


def _normalize_postgres_url(url: str) -> str:
    """Pastikan URL PostgreSQL memakai driver psycopg3 (yang terpasang).

    Hosting seperti Render menyuntikkan `DATABASE_URL` tanpa driver eksplisit
    (mis. `postgres://...` atau `postgresql://...`), sedangkan SQLAlchemy 2.0
    default ke driver psycopg2 untuk URL tanpa driver — yang TIDAK terpasang
    di proyek ini (hanya `psycopg[binary]`/psycopg3 lewat extra `postgres`).
    Tanpa normalisasi, koneksi DB pertama di Render langsung gagal.
    """
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def create_db_engine(url: str | None = None, *, echo: bool = False, poolclass: Any = None) -> Engine:
    """Buat engine baru. Default: dari env `DATABASE_URL`.

    `poolclass` bisa di-set (mis. StaticPool) untuk database in-memory di test.
    """
    resolved = _prepare_sqlite_path(url or get_settings().database_url)
    # Render/Railway menyuntikkan URL Postgres tanpa driver — normalisasi dulu
    # agar selalu memakai psycopg3 (satu-satunya driver yang terpasang).
    resolved = _normalize_postgres_url(resolved)
    kwargs: dict[str, Any] = {"echo": echo}
    if resolved.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    if poolclass is not None:
        kwargs["poolclass"] = poolclass
    return create_engine(resolved, **kwargs)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Engine global (lazy, dibangun sekali dari DATABASE_URL)."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Session factory global (lazy)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)
    return _session_factory


def create_session() -> Session:
    """Buka session baru. Disarankan dipakai sebagai context manager."""
    return get_session_factory()()


def init_db() -> None:
    """Buat semua tabel langsung dari model (cepat, untuk dev/test).

    Untuk produksi gunakan migrasi Alembic (`basa db upgrade`).
    """
    from basa.db import models  # noqa: F401  # mendaftarkan model ke metadata

    Base.metadata.create_all(bind=get_engine())
