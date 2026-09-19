# Basa.id — Roadmap Implementasi

> Status roadmap ini mencerminkan kondisi repository `main` saat ini. Tahap yang
> berstatus **SELESAI** sudah tersedia di kode; item **PENDING** membutuhkan
> kredensial atau verifikasi live dari environment deployment.

## ✅ Langkah 1 — Rencana Arsitektur

- Dokumen arsitektur, roadmap, riset data di folder `docs/`
- `.gitignore` dan README awal
- Pola *ports & adapters*: satu core untuk banyak platform

## ✅ Langkah 2 — Setup Project

- Branch utama `main`
- `pyproject.toml` dan konfigurasi Python 3.11+
- `src/basa/config.py` berbasis `pydantic-settings`
- Template konfigurasi `.env.example`
- CLI `basa`

## ✅ Langkah 3 — Layer Database

- SQLAlchemy 2.0 dan Alembic
- Model user, bahasa, kosakata, progres, kuis, frasa, grammar, dan sesi kuis
- Repository pattern di `src/basa/db/repositories.py`
- SQLite untuk lokal dan dukungan PostgreSQL untuk deployment
- Migrasi database idempoten saat aplikasi dijalankan

## ✅ Langkah 4 — Kosakata dan Data Batak Toba

- Dataset Batak Toba kurasi manual
- `VocabularyService` dan command `/kata <bahasa>`
- Progres kosakata per user dan platform
- Loader data JSON → database

## ✅ Langkah 5 — Console Simulator

- Adapter console untuk development dan demo tanpa token platform
- Auto-migrate dan auto-seed database lokal
- Command interaktif untuk menguji fitur core

## ✅ Langkah 6 — Platform Telegram

- Adapter `python-telegram-bot` v21
- Polling, inline keyboard, dan fallback tampilan teks
- Dukungan `/kata@BotName`
- Pencatatan user, progres, dan hasil kuis per platform
- Command utama dapat diuji melalui Telegram

## 🟡 Langkah 7 — Platform WhatsApp

**Status kode: SELESAI — status live: PENDING kredensial Meta dan webhook publik.**

- Adapter Meta WhatsApp Cloud API
- Webhook verification dan validasi signature
- Graph API untuk pengiriman pesan
- Tombol interaktif dan format tanpa Markdown
- Konfigurasi melalui `WHATSAPP_API_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`,
  `WHATSAPP_VERIFY_TOKEN`, dan `WHATSAPP_WEBHOOK_PORT`

Verifikasi yang masih diperlukan:

- Mendaftarkan webhook publik di Meta for Developers
- Menguji pesan masuk dan balasan keluar secara live
- Memastikan tombol interaktif bekerja pada akun WhatsApp produksi

## ✅ Langkah 8 — Fitur Pembelajaran Lanjutan

### Percakapan statis

- Command `/frase <bahasa>`
- Tabel `phrases`, repository, service, dan data frasa kurasi
- Konteks frasa seperti sapaan, makanan, dan perjalanan

### Grammar dasar

- Command `/grammar <bahasa>`
- Tabel `grammar_rules`, repository, service, dan data grammar kurasi
- Contoh partikel, tingkat tutur, negasi, dan aturan dasar lainnya

### Kuis interaktif

- Command `/kuis <bahasa>`
- Lima soal pilihan ganda dengan tiga opsi
- Jawaban melalui tombol atau angka
- Dukungan multi-pesan dan command `stop`
- Skor tersimpan ke `quiz_results`
- Sesi kuis tersimpan melalui `quiz_sessions`

### Progres belajar

- Command `/progres`
- Statistik kosakata dilihat/dikuasai dan skor kuis per user/platform

## ✅ Langkah 9 — Percakapan LLM berbasis RAG

- Command `/percakapan <bahasa>`
- `DialogueService` mengambil kosakata, frasa, dan grammar dari database
- Prompt Gemini mewajibkan dialog 3–5 pasangan tanya-jawab
- Tema harian dipilih secara acak
- Format output mencakup `Tema:` dan `Materi:`
- Prompt menjaga dialog tetap grounded pada CONTEXT database
- Dukungan bahasa Batak, Jawa, dan Sunda
- Adapter mock tersedia untuk demo dan unit test tanpa API

## ✅ Langkah 10 — Provider LLM dan Fallback

- `GeminiLLMClient` melalui REST API Google AI Studio
- `BynaraLLMClient` melalui endpoint OpenAI-compatible NaraRouter
- Model fallback: `agnes-2.5-flash`
- `FallbackLLMClient` mencoba Gemini terlebih dahulu, lalu Bynara ketika primary
  gagal karena quota, rate limit, timeout, atau error provider
- API key Gemini dikirim melalui header `x-goog-api-key`, bukan query URL
- Konfigurasi terpisah untuk primary dan fallback:

  ```env
  LLM_PROVIDER=gemini
  LLM_API_KEY=TOKEN_GEMINI
  LLM_MODEL=gemini-flash-lite-latest

  LLM_FALLBACK_PROVIDER=bynara
  LLM_FALLBACK_API_KEY=TOKEN_BYNARA
  LLM_FALLBACK_MODEL=agnes-2.5-flash
  LLM_FALLBACK_BASE_URL=https://router.bynara.id/v1
  ```

- Test fallback menggunakan primary mock/error dan tidak menghabiskan quota
- Verifikasi Bynara live berhasil dengan response HTTP 200
- Verifikasi quota Gemini nyata belum dilakukan secara sengaja agar tidak
  menghabiskan quota; simulasi error primary digunakan untuk pengujian alur

## ✅ Langkah 11 — Data, Dokumentasi, dan Packaging

- Import data Kaikki Jawa dan Sunda
- Atribusi Wiktionary/Kaikki dengan lisensi CC BY-SA 3.0
- README mencakup fitur LLM dan konfigurasi fallback
- `docs/DEMO.md`, `docs/DATA_SOURCES.md`, dan `docs/DEPLOYMENT.md`
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, dan `render.yaml`
- LICENSE MIT
- `.env` diabaikan Git; token tidak boleh dimasukkan ke repository

## 🟡 Langkah 12 — Deployment dan Verifikasi Produksi

Prioritas berikutnya:

1. Menjalankan full test suite di virtual environment:

   ```bash
   python -m pip install -e '.[dev]'
   PYTHONPATH=src pytest
   ```

2. Memperbaiki `LLM_MODEL` agar memakai model Gemini yang valid dan memastikan
   `LLM_FALLBACK_MODEL=agnes-2.5-flash` hanya dipakai oleh Bynara.
3. Menguji output fallback dengan validator agar dialog selalu berakhir pada
   baris `B`, memiliki 3–5 pasangan dialog, dan menyertakan `Materi:`.
4. Deploy bot dengan PostgreSQL dan environment secret di Railway/Render.
5. Melakukan live test Telegram setelah deployment.
6. Melengkapi live test WhatsApp dengan webhook Meta.
7. Menambahkan observability: provider aktif, alasan fallback, latency, dan
   error rate tanpa mencatat API key atau isi secret.

## Status ringkas

| Area | Status |
|---|---|
| Core, database, migrasi, dan seed | ✅ Selesai |
| Console dan Telegram | ✅ Selesai |
| WhatsApp adapter | 🟡 Kode selesai, live test pending |
| Fitur kosakata, frasa, grammar, kuis, progres | ✅ Selesai |
| Percakapan LLM + RAG | ✅ Selesai |
| Gemini primary + Bynara fallback | ✅ Implementasi selesai |
| Full test di environment lokal saat ini | 🟡 Menunggu dependency Python |
| Deployment produksi dan verifikasi live | 🟡 Pending |
