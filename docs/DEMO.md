# Demo — Simulator Konsol

> Transkrip **asli** dari sesi `PLATFORM=console .venv/bin/python -m basa run`.
> Semua fitur bot bisa dicoba di terminal tanpa token atau akun apa pun.
> Reproduksi sendiri: install dependensi → `cp .env.example .env` → jalankan perintah di atas.

```
╔══════════════════════════════════════════════════════╗
║   Basa.id — belajar bahasa daerah Indonesia 🇮🇩      ║
║   one conversation at a time                          ║
╚══════════════════════════════════════════════════════╝
Ketik /help untuk perintah · /quit untuk keluar

kamu › /help
basa › Selamat datang di Basa.id! 🇮🇩
       Belajar bahasa daerah Indonesia, satu percakapan dalam satu waktu.

       Perintah:
         /kata <bahasa>    → kata acak (default: jawa)
         /frase <bahasa>   → frasa percakapan harian
         /grammar <bahasa> → aturan grammar dasar
         /bahasa           → daftar bahasa yang tersedia
         /kuasai <kata>    → tandai kata yang sudah dikuasai
         /progres          → statistik belajarmu
         /kuis <bahasa>    → kuis interaktif 5 soal
         /help             → bantuan ini

       Contoh: /kata sunda, /frase batak, /grammar jawa, /kuasai mangan

kamu › /bahasa
basa › Bahasa yang tersedia:
         • bbc — Batak Toba
         • jv — Javanese
         • su — Sundanese

kamu › /kata batak
basa › 📖 ro (verb)
       → datang

       Ketik /kuasai <kata> kalau sudah hafal!

kamu › /frase sunda
basa › 💬 Kumaha damang?
       → Bagaimana kabarmu?

       🗂️ Konteks: greeting

       Ketik /frase <bahasa> lagi untuk frasa lain!

kamu › /grammar jawa
basa › 📐 Negasi 'ora'
       ora = tidak (ngoko); boten = tidak (krama). Diletakkan sebelum kata kerja/kata sifat.

       💬 Contoh: Aku ora ngerti.
          (Aku tidak mengerti.)

       🎚️ Level: 1

       Ketik /grammar <bahasa> lagi untuk materi lain!

kamu › /kuis jawa
basa › 🧠 Kuis Basa.id — soal 1/5
       Apa arti dari ibu (noun)?
         1. evening, night
         2. mother
         3. plate

       Balas dengan angka 1-3, atau ketik 'stop' untuk berhenti.
       [ 1. evening, night ]
       [ 2. mother ]
       [ 3. plate ]

kamu › 2
basa › ✅ Benar! ibu = mother

       🧠 Kuis Basa.id — soal 2/5
       Apa arti dari ꦕꦕꦃ (noun)?
         1. amount, number; census
         2. full, sated
         3. nineteen

       Balas dengan angka 1-3, atau ketik 'stop' untuk berhenti.
       [ 1. amount, number; census ]
       [ 2. full, sated ]
       [ 3. nineteen ]

kamu › stop
basa › Kuis dibatalkan. Ketik /kuis <bahasa> untuk mulai lagi ya! 👋

kamu › /progres
basa › 📊 Progres belajarmu
         • Total kosakata dilihat: 1
         • 🆕 Baru: 1
         • 📚 Dipelajari: 0
         • ✅ Dikuasai: 0

       Terus semangat! 🔥

kamu › /quit
Sampai jumpa! Horas! 👋
```

> 💡 Kuis interaktif juga berjalan di **Telegram** (inline keyboard) dan **WhatsApp**
> (tombol interaktif) dengan alur yang sama persis — jawaban berupa angka `1/2/3`
> atau ketuk tombol, karena logika inti tidak membedakan platform.
