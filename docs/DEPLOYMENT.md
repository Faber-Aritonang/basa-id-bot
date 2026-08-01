# Basa.id — Panduan Deploy

> Dari SQLite lokal ke produksi: PostgreSQL + hosting (Railway/Render) + Docker.
> Prinsip arsitektur: **ganti database cukup ubah `DATABASE_URL`** — tidak ada
> query SQLite yang hardcode di kode.

## 1. Database Produksi: PostgreSQL

Aplikasi memakai SQLAlchemy ORM + Alembic, jadi migrasi SQLite → Postgres
hanya soal *connection string* (plus driver). Driver `psycopg` disediakan lewat
extra `postgres` — install sekali:

```bash
pip install -e '.[postgres]'        # atau '.[dev,postgres]' untuk dev + postgres
```

1. Buat instance Postgres (Railway, Render, Supabase, Neon…).
2. Set env var di hosting:

   ```bash
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
   ```

3. Jalankan migrasi + seed saat pertama deploy (bisa juga sebagai *release command*):

   ```bash
   basa db upgrade
   basa db seed
   ```

   > `basa run` juga otomatis migrate + seed jika tabel belum ada — aman untuk
   > start sederhana, tapi untuk produksi lebih baik eksplisit via *release command*.

4. **Sebelum pindah**: backup SQLite lokal (`cp data/basa.db backup.db`) bila ada
   data user. Migrasi data antar-DB tidak otomatis — cukup mulai DB produksi baru.

## 2. Platform

| Platform | Cara jalan | Kredensial di `.env` |
|---|---|---|
| **Console** | `PLATFORM=console basa run` | — (tanpa token) |
| **Telegram** | `PLATFORM=telegram basa run` | `TELEGRAM_BOT_TOKEN` |
| **WhatsApp** | `PLATFORM=whatsapp basa run` (+ webhook publik) | `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` |

### WhatsApp — webhook

Adapter WhatsApp memakai **Meta WhatsApp Cloud API** (webhook + Graph API, port
default `8080`). Bot harus bisa menerima webhook dari internet:

```bash
# uji lokal: expose port 8080
ngrok http 8080
# isi URL webhook di Meta App Dashboard:
#   https://<ngrok-url>/webhook
# lalu set WHATSAPP_VERIFY_TOKEN yang sama di .env dan dashboard Meta.
PLATFORM=whatsapp basa run
```

Pesan masuk diverifikasi (`X-Hub-Signature-256`), lalu `verify_token` dicocokkan
saat handshake webhook. Pengiriman balasan via Graph API
(`https://graph.facebook.com/v19.0/<PHONE_NUMBER_ID>/messages`).

## 3. Hosting — Railway / Render

Keduanya bisa *zero-config* (auto-detect Python) atau memakai `Dockerfile`
(yang sudah tersedia di repo ini — direkomendasikan agar perilaku konsisten).

### Railway

1. **New Project → Deploy from GitHub repo** (atau pakai CLI).
2. Tambah variabel: `PLATFORM=telegram`, `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`.
3. Tambah **PostgreSQL** plugin → Railway menyediakan `DATABASE_URL` otomatis.
4. Deploy. Release command (opsional): `basa db upgrade && basa db seed`.

### Render

Repo ini menyediakan **`render.yaml`** (blueprint): satu klik membuat PostgreSQL
+ Web Service Docker yang langsung migrate + seed + menjalankan bot.

**Health check penting:** Render Web Service mengharuskan proses bind ke `$PORT`
dan merespons HTTP, kalau tidak deploy dianggap gagal. Bot Telegram memakai
*long polling* (tanpa HTTP), jadi aplikasi menjalankan *health server* minimal
di thread sampingan (`src/basa/health.py`) yang menjawab `200` di `/` dan
`/healthz` — aktif otomatis saat env `PORT` ter-set (Render menyuntikkannya).

**Deploy (dashboard):**

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
   → pilih repo `Faber-Aritonang/basa-id-bot`.
2. Render membaca `render.yaml`: buat database `basa-db` (free) + service
   `basa-bot` (Docker, free).
3. **Isi rahasia**: Render meminta nilai `TELEGRAM_BOT_TOKEN` (sync: false —
   token tidak pernah ada di git). `DATABASE_URL` diisi otomatis dari database.
4. Klik **Apply** → Render membangun image (Dockerfile) lalu deploy.

   Start command otomatis: `basa db upgrade && basa db seed && basa run`
   (migrasi + seed idempoten, lalu bot mulai polling).

**Deploy (CLI, opsional):** butuh `render` CLI + API key:

```bash
pip install render-cli
render blueprint launch --repo Faber-Aritonang/basa-id-bot
```

**Catatan free tier:** Web Service free turun (sleep) setelah ±15 menit tanpa
trafik masuk, dan polling Telegram tidak menghasilkan trafik HTTP — bot akan
"tertidur" dan baru bangun (30–50 dtk) saat ada pesan masuk berikutnya.
Untuk bot 24/7 tanpa jeda, upgrade service ke plan *Starter* (atau aktifkan
pada *paid instance type*). Database Postgres free di Render juga **berakhir
otomatis setelah 30 hari** — upgrade ke *Starter* untuk data permanen.

> **Driver Postgres:** Render menyuntikkan `DATABASE_URL` tanpa driver
> (`postgres://...`), sedangkan proyek ini memakai psycopg3. Aplikasi
> otomatis menormalisasi URL ke `postgresql+psycopg://` di `create_db_engine`
> — tidak perlu konfigurasi tambahan.

**Verifikasi:** buka `https://<service>.onrender.com/healthz` → harus
membalas `ok` (health server berjalan).

## 4. Docker (opsional, lokal & produksi)

Repo ini menyediakan:

- **`Dockerfile`** — image minimal Python 3.12, migrasi otomatis saat start.
- **`docker-compose.yml`** — dua service: `db` (Postgres) + `bot` (aplikasi) — cara
  termudah menguji **Postgres lokal** sebelum deploy.

### Uji Postgres lokal (compose)

```bash
docker compose up --build -d db     # jalankan Postgres dulu
docker compose up --build bot        # bot tersambung ke Postgres lokal
```

### Build image manual

```bash
docker build -t basa-id .
docker run --env-file .env -e PLATFORM=telegram basa-id
```

> Di container, aplikasi membaca data dari folder `data/` (ikut terbundle di
> image) dan menulis DB sesuai `DATABASE_URL` — pakai volume/Postgres di
> produksi, jangan file SQLite dalam container (hilang saat rebuild).

## 5. Checklist Env Produksi

```bash
PLATFORM=telegram                 # atau whatsapp
DATABASE_URL=postgresql+psycopg://...# wajib Postgres di produksi
TELEGRAM_BOT_TOKEN=...            # Telegram
WHATSAPP_API_TOKEN=...            # WhatsApp (jika dipakai)
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
LOG_LEVEL=INFO
```

## 6. Keamanan

- `.env` **tidak pernah** masuk git (ada di `.gitignore`).
- Jangan commit token — jika token pernah bocor (mis. terkirim ke chat),
  **rotate** di BotFather / Meta dashboard sebelum repo publik.
- Gunakan `sslmode=require` untuk Postgres.
