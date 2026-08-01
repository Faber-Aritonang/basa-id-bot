"""Layanan kosakata — fitur #1 Basa.id.

Semua method menerima/mengembalikan tipe abstrak (`UserMessage`/`BotReply`)
dan memakai repository dari `basa.db`. Tidak ada dependensi platform di sini.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.messages import BotReply
from basa.db.models import Platform, ProgressStatus
from basa.db.repositories import (
    LanguageRepository,
    ProgressRepository,
    UserRepository,
    WordRepository,
)


class VocabularyService:
    """Fitur kosakata: kata acak, daftar bahasa, tracking progres, kuis singkat."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.languages = LanguageRepository(session)
        self.words = WordRepository(session)
        self.progress = ProgressRepository(session)

    # --- utilitas ---

    def _resolve_language(self, alias: str) -> int | None:
        """Ubah alias (mis. 'batak') → language_id. None jika tidak dikenal."""
        language = self.languages.get_by_code(resolve_code(alias))
        return language.id if language else None

    # --- perintah utama ---

    def help_text(self) -> BotReply:
        return BotReply(
            "Selamat datang di Basa.id! 🇮🇩\n"
            "Belajar bahasa daerah Indonesia, satu percakapan dalam satu waktu.\n\n"
            "Perintah:\n"
            "  /kata <bahasa>    → kata acak (default: jawa)\n"
            "  /frase <bahasa>   → frasa percakapan harian\n"
            "  /grammar <bahasa> → aturan grammar dasar\n"
            "  /bahasa           → daftar bahasa yang tersedia\n"
            "  /kuasai <kata>    → tandai kata yang sudah dikuasai\n"
            "  /progres          → statistik belajarmu\n"
            "  /kuis <bahasa>    → kuis interaktif 5 soal\n"
            "  /help             → bantuan ini\n\n"
            "Contoh: /kata sunda, /frase batak, /grammar jawa, /kuasai mangan"
        )

    def list_languages(self) -> BotReply:
        languages = self.languages.list_all()
        if not languages:
            return BotReply("Belum ada bahasa. Jalankan `basa db seed` dulu ya.")
        lines = "\n".join(f"  • {lang.code} — {lang.name}" for lang in languages)
        return BotReply(f"Bahasa yang tersedia:\n{lines}")

    def random_word(self, alias: str = "jawa", user_id: str | None = None, platform: Platform | None = None) -> BotReply:
        """Ambil satu kata acak dari bahasa, lengkap dengan arti & contoh."""
        language_id = self._resolve_language(alias)
        if language_id is None:
            return BotReply(
                f"Bahasa '{alias}' belum tersedia. Coba: /bahasa untuk daftar, atau /kata jawa."
            )

        words = self.words.get_random(language_id, limit=1)
        if not words:
            return BotReply("Kosakata bahasa ini masih kosong. Jalankan `basa db seed` dulu.")

        word = words[0]

        # Catat progres (kata dilihat pertama kali → status 'new')
        if user_id is not None and platform is not None:
            user = self.users.get_or_create(platform, user_id)
            self.progress.record_review(user.id, word.id, ProgressStatus.NEW)

        reply = f"📖 *{word.term}* ({word.part_of_speech})\n"
        reply += f"→ {word.translation}"
        if word.example:
            reply += f"\n💬 Contoh: {word.example}"
            if word.example_translation:
                reply += f"\n   ({word.example_translation})"
        reply += "\n\nKetik /kuasai <kata> kalau sudah hafal!"
        return BotReply(reply)

    def mark_mastered(self, term: str, user_id: str, platform: Platform) -> BotReply:
        """Tandai satu kosakata sebagai dikuasai (by term, case-insensitive)."""
        user = self.users.get_or_create(platform, user_id)
        word = self.words.get_by_term(term, language_id=None)
        if word is None:
            return BotReply(f"Kata '{term}' tidak ditemukan. Coba /kata dulu.")
        self.progress.record_review(user.id, word.id, ProgressStatus.MASTERED)
        return BotReply(f"✅ Mantap! '{word.term}' sudah kamu kuasai. Semangat! 💪")

    def progress_stats(self, user_id: str, platform: Platform) -> BotReply:
        """Statistik progres belajar user."""
        user = self.users.get_or_create(platform, user_id)
        stats = self.progress.stats(user.id)
        total = sum(stats.values())
        if total == 0:
            return BotReply("Kamu belum belajar kosakata apa pun. Coba /kata jawa dulu! 😊")
        return BotReply(
            f"📊 *Progres belajarmu*\n"
            f"  • Total kosakata dilihat: {total}\n"
            f"  • 🆕 Baru: {stats['new']}\n"
            f"  • 📚 Dipelajari: {stats['learning']}\n"
            f"  • ✅ Dikuasai: {stats['mastered']}\n\n"
            "Terus semangat! 🔥"
        )
