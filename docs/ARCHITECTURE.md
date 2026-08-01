# Basa.id — Rencana Arsitektur (Langkah 1)

> Dokumen ini adalah **kontrak desain** sebelum menulis kode. Setelah disetujui, implementasi berjalan bertahap sesuai [ROADMAP.md](ROADMAP.md).

## 1. Ringkasan Eksekutif

Basa.id adalah bot belajar bahasa daerah Indonesia yang berjalan di **Telegram** dan **WhatsApp** dengan **satu logika inti** (single core) yang dibagikan kedua platform. Kunci arsitekturnya:

- **Logika inti (`core/`) tidak pernah menyentuh SDK platform.** Ia hanya mengenal tipe data abstrak (`UserMessage`, `BotReply`).
- **Adapter platform (`platforms/`) tipis** — tugasnya hanya menerjemahkan pesan masuk/keluar antara format platform dan format inti.
- **Database dipisah di balik repository layer** dengan SQLAlchemy ORM, sehingga SQLite → PostgreSQL adalah perubahan 1 baris (env var).
- **Testing lokal penuh** dilakukan lewat *console simulator* — bot bisa diuji tanpa token apa pun.

Pola ini disebut **Ports & Adapters (Hexagonal Architecture)** — cocok untuk portofolio karena menunjukkan pemisahan concern yang bersih.

## 2. Rekomendasi Stack

| Lapisan | Pilihan | Alasan |
|---|---|---|
| Bahasa | **Python 3.11+** | ORM (SQLAlchemy) yang diminta user; ekosistem bot matang; mudah dibaca untuk portofolio |
| Logika inti | **Pure Python** (stdlib + typing) | Zero dependency platform → benar-benar platform-agnostic |
| Database | **SQLAlchemy 2.0 (ORM)** | Wajib sesuai requirement; ganti DB cukup ubah `DATABASE_URL` |
| Dev DB | **SQLite** | Tanpa setup, file-based |
| Produksi DB | **PostgreSQL** | Via `postgresql+psycopg://...` — siap saat deploy |
| Migrasi | **Alembic** | Standar SQLAlchemy; memudahkan pindah DB & versioning skema |
| Telegram | **python-telegram-bot v21+** | SDK resmi, aktif, async |
| WhatsApp | **Adapter abstrak** (lihat §7) | Pilihan provider dibuat sebagai keputusan terpisah |
| Config | **pydantic-settings** | Validasi env var, auto-load `.env` |
| CLI dev | **Typer** (opsional) | Perintah `seed`, `run`, `test` yang rapi |
| Testing | **pytest** | Standar de facto |

> Catatan: semua library menunggu persetujuan; tidak ada yang dipasang dulu di Langkah 1.

## 3. Prinsip Desain

1. **DRY antar platform** — satu `core`, adapter hanya 10–20% dari total kode.
2. **DB-agnostic** — tidak ada query SQL mentah di luar repository layer; ORM di semua tempat.
3. **Tidak ada secret di kode** — 100% via `.env`; template `.env.example` di-commit, `.env` di-`.gitignore`.
4. **Extensible** — bahasa baru (Jawa, Sunda, Minang…) = data + tidak ada perubahan kode inti.
5. **Teruji** — core diuji dengan `pytest` tanpa perlu akun platform.

## 4. Struktur Folder

```
basa-id-bot/
├── README.md
├── .env.example            # template env (COMMIT ini)
├── .env                    # secret asli (JANGAN commit — sudah di .gitignore)
├── .gitignore
├── pyproject.toml          # metadata + dependencies (uv/pip)
├── alembic.ini
├── migrations/             # skema DB (Alembic)
├── docs/
│   ├── ARCHITECTURE.md     # dokumen ini
│   ├── ROADMAP.md
│   └── DATA_SOURCES.md
├── src/
│   └── basa/               # nama paket (nama repo: basa-id-bot)
│       ├── __init__.py
│       ├── config.py       # pydantic-settings: baca .env
│       ├── core/           # ⭐ LOGIKA INTI (bebas platform)
│       │   ├── __init__.py
│       │   ├── messages.py # UserMessage, BotReply, Button (abstrak)
│       │   ├── router.py   # dispatch command → service
│       │   └── services/
│       │       ├── vocabulary.py    # fitur #1
│       │       ├── conversation.py  # fitur #2 (nantinya)
│       │       ├── grammar.py       # fitur #3 (nantinya)
│       │       └── quiz.py          # fitur #4 (nantinya)
│       ├── db/             # layer database (ORM)
│       │   ├── __init__.py
│       │   ├── engine.py   # create_engine dari DATABASE_URL
│       │   ├── models.py   # User, Language, Word, Progress, QuizResult
│       │   └── repositories.py  # akses data (dipakai services)
│       ├── data/           # dataset kosakata
│       │   ├── batak_toba/
│       │   │   └── basic_100.json    # sample awal
│       │   ├── jawa/                 # (import dari Kaikki nanti)
│       │   ├── sunda/                # (import dari Kaikki nanti)
│       │   └── loaders.py            # load JSON → model
│       ├── platforms/      # ⭐ ADAPTER (tipis, per platform)
│       │   ├── __init__.py
│       │   ├── base.py     # ABC: PlatformAdapter (send, receive)
│       │   ├── console.py  # simulator lokal (tanpa akun)
│       │   ├── telegram/
│       │   │   ├── __init__.py
│       │   │   └── bot.py  # python-telegram-bot wiring
│       │   └── whatsapp/
│       │       ├── __init__.py
│       │       └── bot.py  # webhook + provider SDK
│       └── main.py         # entrypoint: pilih adapter dari env PLATFORM=
└── tests/
    ├── test_core/
    │   └── test_vocabulary.py
    └── test_platforms/
```

## 5. Alur Pesan (End-to-End)

```
 Telegram / WhatsApp
        │  (pesan user mentah)
        ▼
 platform adapter  ── normalize ──►  UserMessage(user_id, text)
        │                                  │
        ▼                                  ▼
                                    core.router.handle()
                                    │  (parse command, panggil service)
                                    │  (service → repository → SQLAlchemy → DB)
                                    ▼
                                  BotReply(text, buttons)
        │                                  │
        ◄────── render ke format platform ──┘
        ▼
 Telegram / WhatsApp (balasan ke user)
```

Contoh konkret: user kirim `/kata batak` →
1. Adapter Telegram → `UserMessage(chat_id, "/kata batak")`
2. `Router` kenali command `/kata` → panggil `VocabularyService.random(lang="batak")`
3. Service ambil kata via `WordRepository` (SQLAlchemy query)
4. Service kembalikan `BotReply("Horas! Kata hari ini: 'sai' — artinya 'selalu'")`
5. Adapter kirim teks itu ke Telegram.

Core **tidak tahu** pesan datang dari Telegram atau WhatsApp — hanya tahu `UserMessage`. Itulah kenapa kode tidak diduplikasi.

## 6. Model Data (SQLAlchemy)

| Tabel | Kolom penting | Keterangan |
|---|---|---|
| `users` | id, platform (`telegram`/`whatsapp`), platform_user_id, display_name, created_at | 1 user bisa di 2 platform (unique bersama platform+id) |
| `languages` | id, code (`bbc`, `jv`, `su`), name | Bahasa yang diajarkan |
| `words` | id, language_id, term, translation, part_of_speech, example, level | Kosakata |
| `user_word_progress` | user_id, word_id, status (`new`/`learning`/`mastered`), review_count, last_reviewed_at | Tracking kosakata yang dikuasai |
| `quiz_results` | user_id, language_id, quiz_type, score, total, taken_at | Skor kuis |

Relasi: `users 1—N user_word_progress N—1 words`, `words N—1 languages`.

**Repository pattern** — services memanggil `WordRepository.get_random(...)` dst., bukan query langsung. Ini yang membuat ganti SQLite→Postgres mulus.

## 7. Keputusan WhatsApp (didefer ke Langkah 7)

WhatsApp tidak punya SDK Python resmi se-sederhana Telegram. Opsi yang akan dievaluasi saat langkah itu tiba (dipilih bersama user):

| Opsi | Cara kerja | Pro / Kontra |
|---|---|---|
| **Meta Cloud API** | Webhook resmi, gratis untuk pesan dalam 24 jam | Resmi & stabil; butuh akun Meta Business + nomor WA |
| **Twilio WhatsApp** | Sandbox gratis untuk testing | Mudah dimulai; berbayar setelah sandbox |
| **Baileys (unofficial)** | Pakai protokol WhatsApp Web | Tanpa akun API; unofficial, risiko ban, bukan best practice portofolio |

Karena arsitektur **adapter-based**, keputusan ini tidak memblokir fitur #1: `console.py` + Telegram bisa jalan duluan, WhatsApp menyusul.

## 8. Keamanan & Config

`.env.example` (template, di-commit):

```bash
# Platform
PLATFORM=console            # console | telegram | whatsapp
# Database
DATABASE_URL=sqlite:///data/basa.db
# Telegram (isi saat Langkah 6)
TELEGRAM_BOT_TOKEN=
# WhatsApp (isi saat Langkah 7)
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

- `.env` tidak pernah masuk git (sudah di `.gitignore`).
- `config.py` memvalidasi env dan memberi error jelas jika token kosong saat dibutuhkan.

## 9. Strategi Pengujian Lokal

1. **Unit test core** — `pytest`: router, service kosakata, tracking progres (pakai SQLite in-memory).
2. **Console simulator** — `PLATFORM=console python -m basa` → chat langsung di terminal tanpa akun apa pun. Ini cara demo fitur di lokal.
3. **Telegram live test** — setelah token BotFather.
4. **WhatsApp live test** — setelah provider dipilih.

## 10. Anti-Scope (sengaja TIDAK dikerjakan)

- ❌ Web dashboard — fokus bot dulu
- ❌ NLP/AI — materi berbasis dataset statis, bukan model
- ❌ Multi-bahasa percakapan penuh — cukup frasa & dialog pendek
- ❌ Deployment — lokal dulu sampai semua fitur berfungsi (sesuai workflow user)
