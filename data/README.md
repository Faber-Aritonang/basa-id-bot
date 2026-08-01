# Format Data Materi Basa.id

Folder ini berisi dataset materi pembelajaran, satu subfolder per bahasa:

```
data/
├── batak_toba/     # ISO bbc — kurasi manual (±100 kata + frasa harian)
├── jawa/           # ISO jv  — impor dari Kaikki.org (Wiktionary) + frasa kurasi
├── sunda/          # ISO su  — impor dari Kaikki.org (Wiktionary) + frasa kurasi
└── README.md       # dokumen ini
```

## Skema file JSON bahasa

Setiap file bahasa adalah satu JSON dengan struktur. File boleh berisi `words`,
`phrases`, dan/atau `grammar` — minimal salah satunya wajib ada:

```json
{
  "language": { "code": "jv", "name": "Javanese" },
  "source": "kaikki.org (Wiktionary, wiktextract)",
  "license": "CC BY-SA 3.0",
  "imported_at": "2026-08-01",
  "words": [
    {
      "term": "sun",
      "translation": "a kiss",
      "part_of_speech": "noun",
      "example": null,
      "example_translation": null
    }
  ],
  "phrases": [
    {
      "phrase": "Horas!",
      "translation": "Halo / salam khas Batak",
      "context": "greeting"
    }
  ],
  "grammar": [
    {
      "title": "Partikel penegas 'do'",
      "explanation": "Partikel 'do' menegaskan kata yang mendahuluinya.",
      "example": "Au do na laho.",
      "example_translation": "Sayalah yang pergi.",
      "level": 1
    }
  ]
}
```

### Field `words`

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `term` | string | ✅ | Kata dalam bahasa daerah (contoh: `sun`, `mangan`) |
| `translation` | string | ✅ | Arti. Untuk data Kaikki = gloss bahasa Inggris; untuk kurasi manual = bahasa Indonesia |
| `part_of_speech` | string | ✅ | `noun`, `verb`, `adjective`, `adverb`, `numeral`, `pronoun`, dll. |
| `example` | string | ⬜ | Contoh kalimat (dipakai fitur percakapan/grammar nanti) |
| `example_translation` | string | ⬜ | Terjemahan kalimat contoh |

### Field `phrases` (percakapan sehari-hari, Langkah 8)

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `phrase` | string | ✅ | Frasa dalam bahasa daerah (contoh: `Horas!`, `Piye kabare?`) |
| `translation` | string | ✅ | Arti dalam bahasa Indonesia |
| `context` | string | ⬜ | Kategori konteks: `greeting`, `food`, `travel`, `shopping`, `politeness`, `farewell`, `smalltalk`, dll. (kosong = umum) |

### Field `grammar` (aturan grammar dasar, Langkah 8)

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `title` | string | ✅ | Judul aturan (contoh: `Partikel penegas 'do'`) |
| `explanation` | string | ✅ | Penjelasan aturan dalam bahasa Indonesia |
| `example` | string | ⬜ | Contoh kalimat dalam bahasa daerah |
| `example_translation` | string | ⬜ | Terjemahan kalimat contoh |
| `level` | int | ⬜ | Tingkat kesulitan 1-3 (default 1) |

## Cara menambah bahasa baru

1. Buat folder `data/<kode_iso>/` dan file JSON mengikuti skema di atas.
2. Tidak perlu mengubah kode inti — loader (Langkah 4) membaca semua folder secara dinamis.

## Atribusi & lisensi

- **Kaikki.org / Wiktionary** → CC BY-SA 3.0. Wajib atribusi saat repo dipublish:
  *"Data leksikal dari Wiktionary via kaikki.org (wiktextract), Tatu Ylonen, lisensi CC BY-SA 3.0."*
- **Kurasi manual (Batak Toba)** → karya sendiri, bebas lisensi.
- Lihat [docs/DATA_SOURCES.md](../docs/DATA_SOURCES.md) untuk rincian.
