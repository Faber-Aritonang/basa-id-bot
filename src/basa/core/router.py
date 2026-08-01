"""Router — dispatch pesan user ke service yang tepat.

Router menerima `UserMessage` abstrak dan mengembalikan `BotReply`. Ia satu-satunya
titik masuk logika inti yang dipanggil oleh adapter platform — sehingga semua
platform berbagi perilaku yang sama tanpa duplikasi kode.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session, sessionmaker

from basa.core.messages import BotReply, UserMessage
from basa.core.services.conversation import ConversationService
from basa.core.services.grammar import GrammarService
from basa.core.services.quiz import QuizService
from basa.core.services.vocabulary import VocabularyService
from basa.db.engine import get_session_factory
from basa.db.models import Platform

# `@BotName` (mis. /kata@BasaIdBot) di-abaikan — Telegram menambahkannya saat
# command diketik dari daftar command bot.
_COMMAND_RE = re.compile(r"^/(\w+)(?:@\w+)?(?:\s+(.*))?$")


class Router:
    """Jembatan perintah → service. Satu session DB per pesan."""

    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def handle(self, message: UserMessage) -> BotReply:
        text = message.text.strip()
        if not text:
            return BotReply("Ketik /help untuk melihat perintah.")

        platform = _parse_platform(message.platform)
        match = _COMMAND_RE.match(text)
        if not match:
            # Bukan command → mungkin jawaban kuis interaktif yang sedang berjalan.
            # Router memutuskan, service tidak bergantung pada platform mana pun.
            with self._session_factory() as session:
                reply = QuizService(session).answer(
                    message.user_id, platform, text
                )
                session.commit()
                if reply is not None:
                    return reply
            return BotReply(
                f"Ketik perintah dengan format /command. Coba /help ya, {message.user_id}!"
            )

        command, args = match.group(1).lower(), (match.group(2) or "").strip()

        with self._session_factory() as session:
            service = VocabularyService(session)

            if command == "start" or command == "help" or command == "mulai":
                reply = service.help_text()
            elif command == "bahasa":
                reply = service.list_languages()
            elif command == "kata":
                reply = service.random_word(args or "jawa", user_id=message.user_id, platform=platform)
            elif command == "kuasai":
                reply = service.mark_mastered(args, user_id=message.user_id, platform=platform)
            elif command == "progres":
                reply = service.progress_stats(user_id=message.user_id, platform=platform)
            elif command == "kuis":
                reply = QuizService(session).start(
                    args or "jawa", user_id=message.user_id, platform=platform
                )
            elif command == "frase":
                reply = ConversationService(session).random_phrase(args or "jawa")
            elif command == "grammar":
                reply = GrammarService(session).random_rule(args or "jawa")
            else:
                reply = BotReply(f"Perintah '/{command}' belum dikenal. Ketik /help untuk daftar.")

            # Perintah bisa menulis (progres, kuis) — simpan perubahan
            # sebelum session ditutup supaya tidak ter-rollback.
            session.commit()
            return reply


def _parse_platform(raw: str) -> Platform:
    try:
        return Platform(raw)
    except ValueError:
        return Platform.CONSOLE
