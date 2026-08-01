# Basa.id — Roadmap Implementasi

> Alur kerja bertahap. Setiap langkah berhenti untuk persetujuan user sebelum lanjut.

## ✅ Langkah 1 — Rencana Arsitektur (SELESAI)
- Dokumen arsitektur, roadmap, riset data (folder `docs/`)
- `.gitignore` + `README.md` awal
- **Gate**: user menyetujui arsitektur & pilihan stack

## ✅ Langkah 2 — Setup Project (SELESAI)
- `git init` + branch `main`
- `pyproject.toml` (dependencies: sqlalchemy, alembic, pydantic-settings, python-telegram-bot, pytest, typer)
- `src/basa/config.py` (pydantic-settings) + `.env.example`
- Skeleton folder sesuai [ARCHITECTURE.md](ARCHITECTURE.md)

## ✅ Langkah 3 — Layer Database (SELESAI)
- `db/engine.py`, `db/models.py` (5 tabel: users, languages, words, user_word_progress, quiz_results)
- Alembic init + migration pertama (`d28290b68c50`)
- `db/repositories.py` (repository pattern)
- **Gate**: pytest untuk koneksi DB SQLite jalan ✅

## ✅ Langkah 4 — Modul Kosakata + Data Batak Toba (SELESAI)
- Dataset `data/batak_toba/basic_100.json` (sample kurasi manual 103 kata)
- `core/messages.py` (UserMessage, BotReply, Button)
- `core/services/vocabulary.py` + `core/router.py`
- `data/loaders.py` (seed: JSON → DB)
- **Gate**: unit test vocab + seed berhasil ✅ (46 test)

## ✅ Langkah 5 — Console Simulator (SELESAI)
- `platforms/base.py` (ABC PlatformAdapter) + `platforms/console.py`
- `platforms/__init__.py` (`get_adapter` factory)
- `main.py` + CLI `run` (auto-migrate + auto-seed jika DB kosong)
- Demo fitur vocab via terminal
- **Gate**: bot berfungsi penuh di terminal ✅

## ✅ Langkah 6 — Platform Telegram (SELESAI)
- `platforms/telegram/bot.py` (python-telegram-bot v21, polling, inline keyboard, fallback markdown)
- `get_adapter("telegram")` + `supported_platforms` + token via `.env`
- Router menerima `/kata@BotName`
- Fix logging startup (fileConfig Alembic tidak mematikan logger aplikasi)
- **Gate**: `/kata` jalan live di Telegram ✅ — user platform `telegram` tercatat di DB beserta progres & kuis
  - Verifikasi: user `telegram` dibuat, `/kuasai` → status `mastered`, `/kuis` → `quiz_results` terisi

## ⏭️ Langkah 7 — Platform WhatsApp (kode selesai; live test menunggu kredensial Meta)
- Provider dipilih user: **Meta WhatsApp Cloud API**
- `platforms/whatsapp/bot.py` (webhook stdlib + Graph API, interactive buttons, tanpa markdown)
- `get_adapter("whatsapp")` + kredensial via `.env` (`WHATSAPP_API_TOKEN`, `PHONE_NUMBER_ID`, `VERIFY_TOKEN`)
- Ambil kredensial dari Meta for Developers → isi `.env` → `PLATFORM=whatsapp basa run` (+ ngrok)
- **Gate**: command yang sama jalan di WhatsApp tanpa ubah core — MENUNGGU kredensial dari user

## ⏭️ Langkah 8 — Fitur Lanjutan (percakapan, grammar & kuis interaktif selesai)
- ✅ **Percakapan harian — fitur #2 (SELESAI)**: tabel `phrases` + migrasi, `PhraseRepository`, `ConversationService`, command `/frase <bahasa>`, data frasa kurasi (batak/jawa/sunda), loader diperluas (dukung field `phrases`)
- ✅ **Grammar dasar — fitur #3 (SELESAI)**: tabel `grammar_rules` + migrasi, `GrammarRepository`, `GrammarService`, command `/grammar <bahasa>`, data grammar kurasi (batak/jawa/sunda), loader dukung field `grammar`
- ✅ **Kuis interaktif — fitur #4 (SELESAI)**: tabel `quiz_sessions` + migrasi, `QuizSessionRepository`, `QuizService` (start/answer/stop), command `/kuis <bahasa>` multi-pesan, 3 opsi jawaban (konsisten dengan batas tombol WhatsApp), skor asli tercatat ke `quiz_results` (bukan lagi placeholder 0), jawaban via tombol ATAU angka di Telegram/WhatsApp/console
- ✅ `/progres` — sudah jalan sejak Langkah 4
- **Gate**: semua fitur berfungsi di console + Telegram

## ✅ Langkah 9 — Dokumentasi Portofolio & Finalisasi (SELESAI)
- ✅ Import data Kaikki Jawa/Sunda — `jawa.json` (3.523 kata) & `sunda.json` (3.262 kata) via `scripts/import_kaikki.py`
- ✅ README final profesional (nama + tagline + fitur + quick start + struktur + atribusi) — tautan demo
- ✅ `docs/DEMO.md` — transkrip demo console asli
- ✅ `docs/DEPLOYMENT.md` — Postgres (`DATABASE_URL` swap + extra `postgres`), hosting Railway/Render, WhatsApp webhook, Docker
- ✅ `Dockerfile` + `.dockerignore` + `docker-compose.yml` (Postgres lokal) — build terverifikasi
- ✅ `LICENSE` (MIT) + `.gitignore` diperluas (AppImage Freebuff, raw `*.jsonl`)
- ✅ Data & atribusi CC BY-SA (Kaikki/Wiktionary) dicatat di README + `data/README.md`
- **Gate**: repo siap di-publish ke GitHub — TINGGAL commit & push (belum ada commit sama sekali)
