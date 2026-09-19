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
| 5 | **Percakapan dengan LLM** | `/percakapan <bahasa>` | Dialog 3–5 tanya-jawab berbasis RAG, tema harian, terjemahan, dan daftar materi |
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
- **Aman dari awal** — semua token lewat `.env` (di-`.gitignore`); template di [`.env.example`](.env.example). API key Gemini dikirim melalui header, bukan query URL.
- **LLM berlapis** — Gemini menjadi provider utama; jika quota, rate limit, timeout, atau error provider terjadi, request diteruskan ke Bynara/NaraRouter dengan model `agnes-2.5-flash`.

## 🤖 LLM dan fallback provider

Fitur `/percakapan` memakai arsitektur adapter sehingga core tidak bergantung pada SDK provider tertentu:

```text
Gemini (primary)
      │ berhasil
      ▼
  BotReply
      │ error / quota / rate limit / timeout
      ▼
Bynara — agnes-2.5-flash (fallback)
      │ gagal juga
      ▼
Pesan error yang aman
```

Bynara diakses melalui endpoint OpenAI-compatible menggunakan dependency `httpx`. Konfigurasi lokal:

```env
# Primary
LLM_PROVIDER=gemini
LLM_API_KEY=TOKEN_GEMINI
LLM_MODEL=gemini-flash-lite-latest

# Fallback pay-as-you-go
LLM_FALLBACK_PROVIDER=bynara
LLM_FALLBACK_API_KEY=TOKEN_BYNARA
LLM_FALLBACK_MODEL=agnes-2.5-flash
LLM_FALLBACK_BASE_URL=https://router.bynara.id/v1
```

`LLM_API_KEY` dan `LLM_FALLBACK_API_KEY` harus berisi token yang berbeda. Jangan pernah menaruh token di README, source code, screenshot, URL, atau commit. File `.env` sudah diabaikan oleh Git.

Jika kedua provider tidak dikonfigurasi, aplikasi tetap dapat dijalankan menggunakan `MockLLMClient` untuk demo dan testing.

## 🚀 Quick Start (lokal)

```bash
# 1. Clone & masuk
git clone https://github.com/Faber-Aritonang/basa-id-bot.git
cd basa-id-bot

# 2. Virtual env & install
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'

# 3. Konfigurasi
cp .env.example .env               # isi token platform kalau mau (opsional untuk console)

# 4. Jalankan — langsung demo di terminal, tanpa token!
basa run
```

Saat pertama jalan, bot otomatis menjalankan migrasi DB & seed data. Coba:

```
/kata batak          → kata Batak Toba acak
/frase sunda         → frasa Sunda harian
/percakapan jawa     → dialog Jawa 3–5 tanya-jawab dari Gemini/Bynara
/grammar jawa        → aturan grammar Jawa
/kuis jawa           → kuis interaktif 5 soal (jawab 1-3 atau ketik 'stop')
/progres             → statistik belajarmu
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

Aktifkan virtual environment terlebih dahulu, lalu jalankan:

```bash
source .venv/bin/activate
PYTHONPATH=src pytest
```

Suite mencakup core, database, router, ketiga adapter platform, adapter LLM,
parser response Bynara, serta simulasi fallback primary → backup tanpa
menghabiskan quota provider. Test tidak membutuhkan API key nyata.

## 📁 Struktur

```
src/basa/
├── core/          # ⭐ logika inti (bebas platform): router, messages, services/
│   └── services/  # vocabulary, dialogue/RAG, conversation, grammar, quiz
├── db/            # engine, models (8 tabel), repositories (repository pattern)
├── platforms/     # ⭐ adapter tipis: console, telegram/, whatsapp/
├── llm/           # adapter mock, Gemini, Bynara, dan fallback chain
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
