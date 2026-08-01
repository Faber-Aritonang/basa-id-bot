"""Kontrak adapter platform — pola ports & adapters.

Semua adapter (console, telegram, whatsapp) menurunkan `PlatformAdapter`.
Tugasnya hanya dua:
  1. terima pesan mentah dari platform → ubah jadi `UserMessage` abstrak
  2. kirim `BotReply` dari core → render ke format platform

Logika bisnis 100% ada di `basa.core` — adapter tidak pernah memanggil
service/repository langsung, supaya semua platform berbagi perilaku sama.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from basa.core.messages import BotReply, UserMessage
from basa.core.router import Router


class PlatformAdapter(ABC):
    """Kontrak minimal adapter platform."""

    #: Nama platform — dipakai menandai user di database (lihat Platform enum).
    platform_name: str = "console"

    def __init__(self, router: Router | None = None) -> None:
        self.router = router or Router()

    def normalize(self, text: str, user_id: str) -> UserMessage:
        """Terjemahkan pesan mentah platform → `UserMessage` abstrak."""
        return UserMessage(user_id=user_id, text=text, platform=self.platform_name)

    def handle_text(self, text: str, user_id: str) -> BotReply:
        """Satu pesan masuk → balasan bot (diteruskan ke core Router)."""
        return self.router.handle(self.normalize(text, user_id))

    @abstractmethod
    def start(self) -> None:
        """Mulai melayani pesan (loop platform: polling/webhook/stdin)."""
        raise NotImplementedError
