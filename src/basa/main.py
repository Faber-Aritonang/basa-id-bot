"""Entrypoint Basa.id — memilih adapter platform berdasarkan env PLATFORM.

Contoh:
    basa run                     → simulator terminal (console)
    PLATFORM=telegram basa run   → bot Telegram (isi TELEGRAM_BOT_TOKEN di .env)
    PLATFORM=whatsapp basa run   → bot WhatsApp (isi kredensial Meta di .env)
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from basa.config import get_settings
from basa.db.cli import app as db_app, run_migrations
from basa.platforms import get_adapter

app = typer.Typer(name="basa", help="Basa.id — belajar bahasa daerah Indonesia via bot.")
app.add_typer(db_app, name="db")


def _setup_logging(level: str) -> None:
    # force=True: membuang handler lama (termasuk milik fileConfig Alembic) supaya
    # tidak ada duplikasi dan level root selalu sesuai konfigurasi aplikasi.
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        force=True,
    )


def _seed_if_empty(data_dir: str = "data") -> None:
    """Seed otomatis hanya jika database belum punya bahasa (idempoten)."""
    from basa.data.loaders import seed_data_dir
    from basa.db.engine import get_session_factory
    from basa.db.repositories import LanguageRepository

    with get_session_factory()() as session:
        if LanguageRepository(session).list_all():
            return
        results = seed_data_dir(session, Path(data_dir))
    if results:
        logging.getLogger("basa.main").info(
            "Database kosong — seed otomatis: %s",
            ", ".join(f"{path}:+{sum(counts.values())}" for path, counts in results.items()),
        )


@app.command()
def run(platform: str | None = None, seed_if_empty: bool = True) -> None:
    """Menjalankan bot pada platform tertentu (default: dari env PLATFORM).

    Sebelum start: migrasi Alembic dijalankan (idempoten) dan, jika database
    kosong, data kosakata di-seed otomatis supaya demo langsung bisa dicoba.
    """
    settings = get_settings()
    _setup_logging(settings.log_level)
    log = logging.getLogger("basa.main")

    target = platform or settings.platform
    if target not in settings.supported_platforms:
        log.error(
            "Platform '%s' belum didukung. Yang tersedia: %s",
            target,
            ", ".join(settings.supported_platforms),
        )
        raise typer.Exit(code=1)

    # Database siap pakai: migrasi dulu (tidak berbahaya jika sudah termigrasi),
    # lalu seed otomatis bila kosong — hanya untuk dev SQLite lokal.
    run_migrations()
    # fileConfig Alembic (di migrations/env.py) me-reset level root ke WARN dan
    # menambah handler — panggil ulang setup agar log aplikasi kembali terlihat.
    _setup_logging(settings.log_level)
    if seed_if_empty and settings.database_url.startswith("sqlite"):
        _seed_if_empty()

    adapter = get_adapter(target)
    log.info("Basa.id v%s — platform '%s'. Tekan Ctrl+C untuk berhenti.", "0.1.0", target)
    adapter.start()


if __name__ == "__main__":
    app()
