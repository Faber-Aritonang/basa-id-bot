# Basa.id — Riset Sumber Data Kosakata

> Ringkasan temuan riset data untuk materi pembelajaran (Batak, Jawa, Sunda). Diperbarui saat langkah impor tiba.

## Rekomendasi singkat

**Mulai dengan sample kurasi manual (±100 kata Batak Toba)** — sumber otomatis untuk Batak Toba sangat terbatas, sedangkan kurasi manual memberi kualitas terkontrol, lisensi aman, dan langsung bisa dipakai. **Jawa & Sunda menyusul via Kaikki.org** (data terstruktur Wiktionary) yang siap diunduh dalam format JSONL.

## Hasil riset per bahasa

### 1. Batak Toba (ISO: `bbc`) — 🟡 sumber terbatas

| Sumber | Format | Lisensi | Status |
|---|---|---|---|
| **Kurasi manual** (kamus cetak daring, penutur, Wiktionary entri per-entri) | JSON buatan sendiri | Aman (karya sendiri) | ✅ **Rekomendasi awal** |
| Wiktionary (en.wiktionary / id.wiktionary) | Halaman per kata | CC BY-SA | 🟡 Parsial — entri Batak Toba masih sedikit & tidak ada dump JSONL terstruktur di Kaikki |
| Kamus daring (belajarbahasabatak.com dll.) | HTML/web | ⚠️ Perlu cek lisensi | 🟡 Manual scraping — verifikasi izin dulu |
| UDHR (Universal Declaration of Human Rights) | TXT | Public domain | 🟢 Ada terjemahan Batak — bagus untuk kalimat contoh nanti |

### 2. Jawa (ISO: `jv`) — 🟢 sumber bagus

| Sumber | Format | Lisensi | Status |
|---|---|---|---|
| **Kaikki.org — Javanese dictionary** | JSONL (7.8 MB, ±7.600 senses), download postprocessed data | CC BY-SA (Wiktionary) | ✅ Siap diunduh & diparsing |
| Wiktionary | Halaman per kata | CC BY-SA | 🟢 Lengkap |
| HuggingFace (dataset terjemahan jv↔id) | Parquet/JSON | bervariasi | 🟢 Untuk korpus terjemahan |

### 3. Sunda (ISO: `su`) — 🟢 sumber bagus

| Sumber | Format | Lisensi | Status |
|---|---|---|---|
| **Kaikki.org — Sundanese dictionary** | JSONL (3.5 MB, ±4.200 senses) | CC BY-SA (Wiktionary) | ✅ Siap diunduh & diparsing |
| Wiktionary | Halaman per kata | CC BY-SA | 🟢 Lengkap |
| UDHR (terjemahan Sunda) | TXT | Public domain | 🟢 Kalimat contoh |

### 4. Indonesia (ISO: `id`) — 🟢 reference

| Sumber | Format | Lisensi | Status |
|---|---|---|---|
| **Kaikki.org — Indonesian dictionary** | JSONL (54.896 senses) | CC BY-SA | ✅ Untuk glosari terjemahan |

## Detail teknis Kaikki.org

- URL kamus: `https://kaikki.org/dictionary/<Language>/index.html`
- Struktur JSONL per sense: `word`, `pos`, `senses[].glosses[]`, `senses[].tags[]`, `forms[]`
- Download link "postprocessed JSONL data" tersedia langsung di halaman tiap bahasa
- Skema parsial untuk impor: `{word, pos, glosses}` → `words(term, translation, part_of_speech)`
- Data di-extract dari dump enwiktionary (wiktextract) — CC BY-SA 3.0

## Rencana data awal (Langkah 4)

1. Buat `data/batak_toba/basic_100.json` kurasi manual — kategori: sapaan, angka, keluarga, makanan, kata kerja umum, kata sifat. ±10–20 kata per kategori, tiap kata: `{term, translation, part_of_speech, example, example_translation}`.
2. Skema JSON didokumentasikan di `data/README.md` supaya penambahan bahasa baru konsisten.
3. Nanti (Langkah 9): `scripts/import_kaikki.py` untuk Jawa & Sunda + kurasi manual lanjutan.

## Verifikasi lisensi (sebelum publish)

- Kaikki/Wiktionary → CC BY-SA 3.0: wajib **atribusi** di README/catatan data
- Sample manual → bebas lisensi (karya sendiri)
- UDHR → public domain
