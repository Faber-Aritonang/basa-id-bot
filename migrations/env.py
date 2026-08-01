"""Konfigurasi lingkungan Alembic untuk Basa.id.

Menggunakan metadata model dari `basa.db.engine.Base` dan URL database dari
`basa.config.get_settings()` — jadi ganti DB (SQLite → PostgreSQL) cukup
dengan mengubah env `DATABASE_URL`, tanpa menyentuh file ini.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Pastikan paket `basa` bisa diimpor saat alembic dijalankan dari mana saja.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from basa.config import get_settings  # noqa: E402
from basa.db import models  # noqa: E402, F401  # mendaftarkan model ke metadata
from basa.db.engine import Base  # noqa: E402

config = context.config

# URL database selalu diambil dari settings (env DATABASE_URL), bukan dari alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    # disable_existing_loggers=False: tanpa ini, Alembic mematikan logger aplikasi
    # (mis. basa.main) sehingga log bot tidak terlihat saat `basa run`.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Jalankan migrasi dalam mode 'offline' (generate SQL saja)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Jalankan migrasi dalam mode 'online' (terhubung ke engine)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
