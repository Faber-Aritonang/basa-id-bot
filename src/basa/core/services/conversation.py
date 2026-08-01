"""Layanan percakapan sehari-hari — fitur #2 Basa.id.

Menampilkan frasa percakapan harian (greeting, food, travel, dll.) per bahasa.
Data diambil dari tabel `phrases` via repository — tidak ada logika platform
di sini, sama seperti service lain.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.messages import BotReply
from basa.db.repositories import LanguageRepository, PhraseRepository


class ConversationService:
    """Fitur percakapan: frasa harian acak per bahasa."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.languages = LanguageRepository(session)
        self.phrases = PhraseRepository(session)

    def random_phrase(self, alias: str = "jawa") -> BotReply:
        """Ambil satu frasa percakapan acak dari bahasa, lengkap dengan artinya."""
        language = self.languages.get_by_code(resolve_code(alias))
        if language is None:
            return BotReply(
                f"Bahasa '{alias}' belum tersedia. Coba: /bahasa untuk daftar, atau /frase batak."
            )

        phrases = self.phrases.get_random(language.id, limit=1)
        if not phrases:
            return BotReply(
                f"Frasa percakapan bahasa {language.name} masih kosong. "
                "Jalankan `basa db seed` dulu ya."
            )

        phrase = phrases[0]
        reply = f"💬 *{phrase.phrase}*\n"
        reply += f"→ {phrase.translation}"
        if phrase.context:
            reply += f"\n\n🗂️ Konteks: *{phrase.context}*"
        reply += "\n\nKetik /frase <bahasa> lagi untuk frasa lain!"
        return BotReply(reply)
