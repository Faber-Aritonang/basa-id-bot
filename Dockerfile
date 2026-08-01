# Basa.id — image produksi minimal (Python 3.12)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Root proyek untuk CLI (migrasi/seed). Di image, paket terpasang di
# site-packages sehingga lokasi modul tidak bisa dipakai untuk menemukan
# folder migrations/ — tunjuk eksplisit ke /app.
ENV BASA_PROJECT_ROOT=/app

# Install package + dependensi (termasuk driver Postgres via extra 'postgres')
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[postgres]'

# Data (seed) & migrasi (auto-migrate + auto-seed saat start)
COPY data ./data
COPY migrations ./migrations
COPY alembic.ini ./

# Jalankan migrasi + seed (idempoten), lalu bot.
# Perintah start ada di sini (bukan render.yaml) karena Render melarang
# `startCommand` pada service dengan `runtime: docker`.
# Platform & kredensial via env saat run:
#   PLATFORM=telegram|whatsapp, TELEGRAM_BOT_TOKEN, DATABASE_URL, dll.
CMD ["bash", "-c", "basa db upgrade && basa db seed && basa run"]
