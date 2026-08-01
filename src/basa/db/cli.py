"""Perintah CLI untuk layer database (`basa db ...`).

Membungkus Alembic supaya migrasi bisa dijalankan lewat CLI aplikasi:
    basa db upgrade   # terapkan semua migrasi (ke DATABASE_URL)
    basa db current   # revisi migrasi saat ini
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

from basa.db.engine import get_session_factory, init_db

app = typer.Typer(help="Perintah database", no_args_is_help=True)


def _find_project_root() -> Path:
    """Lokasi root proyek (folder berisi alembic.ini + migrations/).

    Hardcode `parents[3]` hanya benar saat paket dipasang editable
    (src/basa/db/cli.py). Di image Docker paket di-copy ke site-packages
    sehingga `__file__` ada di /usr/local/lib/... — root harus dicari.

    Urutan prioritas:
      1. env BASA_PROJECT_ROOT (di-set Dockerfile → /app)
      2. naik dari lokasi modul sampai menemukan alembic.ini + migrations/
      3. CWD (dev lokal: root repo)
    """
    if env_root := os.environ.get("BASA_PROJECT_ROOT"):
        candidate = Path(env_root).resolve()
        if (candidate / "alembic.ini").is_file() and (candidate / "migrations").is_dir():
            return candidate

    # Naik dari lokasi modul (mencakup editable install: src/basa/db/ → root).
    for parent in Path(__file__).resolve().parents:
        if (parent / "alembic.ini").is_file() and (parent / "migrations").is_dir():
            return parent

    # Fallback: direktori kerja (dev menjalankan CLI dari root repo).
    cwd = Path.cwd()
    if (cwd / "alembic.ini").is_file() and (cwd / "migrations").is_dir():
        return cwd

    raise RuntimeError(
        "Tidak menemukan folder proyek (alembic.ini + migrations/). "
        "Set env BASA_PROJECT_ROOT ke root repo."
    )


_PROJECT_ROOT = _find_project_root()
_MIGRATIONS_DIR = _PROJECT_ROOT / "migrations"
_ALEMBIC_INI = _PROJECT_ROOT / "alembic.ini"


def _alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    return cfg


def run_migrations() -> None:
    """Terapkan semua migrasi Alembic ke database (idempoten).

    Dipakai CLI (`basa db upgrade`) dan entrypoint `basa run` supaya bot
    langsung siap jalan di database baru.
    """
    command.upgrade(_alembic_config(), "head")


@app.command()
def upgrade() -> None:
    """Terapkan semua migrasi Alembic ke database (DATABASE_URL)."""
    run_migrations()
    typer.echo("✅ Migrasi selesai.")


@app.command()
def current() -> None:
    """Tampilkan revisi migrasi saat ini."""
    command.current(_alembic_config())


@app.command()
def init() -> None:
    """Buat tabel langsung dari model (cepat, untuk dev/test lokal).

    Catatan: untuk proyek nyata gunakan `basa db upgrade` (Alembic).
    """
    init_db()
    typer.echo("✅ Tabel dibuat langsung dari model.")


@app.command()
def seed(data_dir: str = "data") -> None:
    """Muat data kosakata dari folder data/ ke database (idempoten).

    Menjalankan migrasi Alembic terlebih dahulu supaya bekerja juga pada
    database baru (sebelumnya gagal dengan 'no such table' jika tabel belum ada).
    """
    run_migrations()

    from basa.data.loaders import seed_data_dir

    with get_session_factory()() as session:
        results = seed_data_dir(session, Path(data_dir))
    if not results:
        typer.echo(f"Tidak ada file data di '{data_dir}'. Jalankan skrip impor Kaikki dulu.")
        raise typer.Exit(code=1)
    for path, counts in results.items():
        detail = ", ".join(f"+{n} {kind}" for kind, n in counts.items() if n)
        typer.echo(f"  {path}: {detail}")
    typer.echo("✅ Seed selesai.")
