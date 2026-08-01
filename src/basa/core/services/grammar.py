"""Layanan grammar dasar — fitur #3 Basa.id.

Menampilkan aturan grammar (partikel, urutan kata, kata ganti, dll.) per
bahasa. Data diambil dari tabel `grammar_rules` via repository — tidak ada
logika platform di sini, sama seperti service lain.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.messages import BotReply
from basa.db.repositories import GrammarRepository, LanguageRepository


class GrammarService:
    """Fitur grammar: aturan acak per bahasa."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.languages = LanguageRepository(session)
        self.grammar = GrammarRepository(session)

    def random_rule(self, alias: str = "jawa") -> BotReply:
        """Ambil satu aturan grammar acak dari bahasa, lengkap dengan contoh."""
        language = self.languages.get_by_code(resolve_code(alias))
        if language is None:
            return BotReply(
                f"Bahasa '{alias}' belum tersedia. Coba: /bahasa untuk daftar, atau /grammar batak."
            )

        rules = self.grammar.get_random(language.id, limit=1)
        if not rules:
            return BotReply(
                f"Materi grammar bahasa {language.name} masih kosong. "
                "Jalankan `basa db seed` dulu ya."
            )

        rule = rules[0]
        reply = f"📐 *{rule.title}*\n"
        reply += rule.explanation
        if rule.example:
            reply += f"\n\n💬 Contoh: {rule.example}"
            if rule.example_translation:
                reply += f"\n   ({rule.example_translation})"
        reply += f"\n\n🎚️ Level: {rule.level}"
        reply += "\n\nKetik /grammar <bahasa> lagi untuk materi lain!"
        return BotReply(reply)
