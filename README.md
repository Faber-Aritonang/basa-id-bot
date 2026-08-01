# Basa.id 🇮🇩

> **Learn Indonesia's regional languages, one conversation at a time**

Bot pembelajaran bahasa daerah Indonesia (**Batak Toba**, **Jawa**, **Sunda**) yang berjalan di **Telegram** dan **WhatsApp** dengan **satu logika inti** yang sama — tanpa duplikasi kode antar platform (pola *ports & adapters*).

![Status](https://img.shields.io/badge/status-siap%20publish-brightgreen) ![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Fitur

| # | Fitur | Perintah | Keterangan |
|---|---|---|---|
| 1 | **Kosakata** | `/kata <bahasa>` | Kata acak + arti + contoh kalimat |
| 2 | **Percakapan harian** | `/frase <bahasa>` | Frasa nyata per konteks (sapaan, makanan, perjalanan…) |
| 3 | **Grammar** | `/grammar <bahasa>` | Aturan dasar + contoh (partikel, tingkat tutur, negasi…) |
| 4 | **Kuis interaktif** | `/kuis <bahasa>` | 5 soal pilihan ganda, skor tersimpan, bisa dijawab via tombol **atau** ketik angka |
| — | **Pelacakan progres** | `/progres` | Kosakata dilihat / dikuasai, skor kuis — per user per platform |

**Bahasa yang didukung:** `batak` (ISO `bbc` — kurasi manual), `jawa` (`jv`), `sunda` (`su`) — impor dari Kaikki.org (Wiktionary). Menambah bahasa baru = menambah folder data, **tanpa ubah kode inti**.

## 🧠 Desain Inti

```
 Telegram / WhatsApp / Konsol
        │  (pesan mentah platform)
        ▼
  adapter platform ──normalize──►  UserMessage  (abstrak, bebas SDK)
        │                                    │
        ▼                                    ▼
                              core.router → services → repository → SQLAlchemy → DB
        │                                    │
        ◄──── render BotReply ke format platform ──┘
        ▼
 Telegram / WhatsApp / Konsol (balasan)
```

- **Satu core, banyak platform** — logika bisnis di `src/basa/core/` murni, tidak pernah menyentuh SDK Telegram/WhatsApp.
- **Adapter tipis** (`src/basa/platforms/`) — hanya menerjemahkan pesan masuk/keluar. Telegram, WhatsApp, dan console memakai core yang sama persis.
- **Database agnostik** — SQLAlchemy 2.0 + Alembic. SQLite untuk dev lokal; ke PostgreSQL cukup ganti `DATABASE_URL` (lihat [DEPLOYMENT.md](docs/DEPLOYMENT.md)).
- **Aman dari awal** — semua token lewat `.env` (di-`.gitignore`); template di [`.env.example`](.env.example).

## 🚀 Quick Start (lokal)

```bash
# 1. Clone & masuk
git clone https://github.com/<username>/basa-id-bot.git
cd basa-id-bot

# 2. Virtual env & install
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e '.[dev]'

# 3. Konfigurasi
cp .env.example .env               # isi token platform kalau mau (opsional untuk console)

# 4. Jalankan — langsung demo di terminal, tanpa token!
basa run
```

Saat pertama jalan, bot otomatis menjalankan migrasi DB & seed data. Coba:

```
/kata batak      → kata Batak Toba acak
/frase sunda     → frasa Sunda harian
/grammar jawa    → aturan grammar Jawa
/kuis jawa       → kuis interaktif 5 soal (jawab 1-3 atau ketik 'stop')
/progres         → statistik belajarmu
```

> Demo transkrip asli: [docs/DEMO.md](docs/DEMO.md)

### Telegram

```bash
# Di .env:
TELEGRAM_BOT_TOKEN=<token dari @BotFather>

PLATFORM=telegram basa run
```

### WhatsApp (Meta Cloud API)

Kode adapter sudah siap (webhook + Graph API, tombol interaktif, tanpa markdown). Isi kredensial Meta di `.env` lalu:

```bash
PLATFORM=whatsapp basa run        # + ngrok untuk webhook publik
```

Detail setup di [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) dan [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

## 🧪 Testing

```bash
pytest                 # seluruh suite (core, db, router, ketiga adapter)
```

## 📁 Struktur

```
src/basa/
├── core/          # ⭐ logika inti (bebas platform): router, messages, services/
│   └── services/  # vocabulary, conversation, grammar, quiz
├── db/            # engine, models (8 tabel), repositories (repository pattern)
├── platforms/     # ⭐ adapter tipis: console, telegram/, whatsapp/
├── data/          # loader data → seed dari JSON
├── config.py      # pydantic-settings (baca .env)
└── main.py        # entrypoint: pilih adapter dari PLATFORM=
data/              # dataset per bahasa (words / phrases / grammar)
migrations/        # skema DB versi (Alembic)
docs/              # ARCHITECTURE, ROADMAP, DATA_SOURCES, DEPLOYMENT, DEMO
```

## 📖 Dokumen

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — kontrak desain & keputusan stack
- [docs/ROADMAP.md](docs/ROADMAP.md) — riwayat implementasi bertahap
- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — riset sumber data & lisensi
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Postgres, Railway/Render, Docker
- [docs/DEMO.md](docs/DEMO.md) — transkrip demo console

## 📜 Data & Atribusi

- **Batak Toba** (`data/batak_toba/`) — kurasi manual, karya sendiri, bebas lisensi.
- **Jawa & Sunda** (`data/jawa/`, `data/sunda/`) — data leksikal dari **Wiktionary** via **kaikki.org** (wiktextract), oleh *Tatu Ylonen*, lisensi **CC BY-SA 3.0**. Impor dengan [scripts/import_kaikki.py](scripts/import_kaikki.py).
- Lihat [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) untuk rincian.

## 📄 Lisensi

Kode di bawah lisensi **MIT** — lihat [LICENSE](LICENSE). Data leksikal Jawa/Sunda mengikuti lisensi sumbernya (CC BY-SA 3.0).

---

*Proyek portofolio pembelajaran arsitektur perangkat lunak: satu inti, banyak platform, database agnostik.*
