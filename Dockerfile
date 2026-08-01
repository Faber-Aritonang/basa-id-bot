# Basa.id — image produksi minimal (Python 3.12)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install package + dependensi (termasuk driver Postgres via extra 'postgres')
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir '.[postgres]'

# Data (seed) & migrasi (auto-migrate + auto-seed saat start)
COPY data ./data
COPY migrations ./migrations
COPY alembic.ini ./

# Jalankan bot. Platform & kredensial via env saat run:
#   PLATFORM=telegram|whatsapp, TELEGRAM_BOT_TOKEN, DATABASE_URL, dll.
CMD ["basa", "run"]
