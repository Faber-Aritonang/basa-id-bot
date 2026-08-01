"""Adapter platform — tipis, satu per platform (Telegram, WhatsApp, console).

Tugas adapter: menerjemahkan pesan masuk/keluar antara format platform dan
tipe abstrak di `basa.core`. Semua logika bisnis tinggal di `basa.core`.

Gunakan `get_adapter(name)` untuk membuat adapter dari nama platform.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from basa.platforms.base import PlatformAdapter

if TYPE_CHECKING:
    from basa.core.router import Router


def get_adapter(name: str, router: Router | None = None) -> PlatformAdapter:
    """Buat adapter untuk platform `name` (console | telegram | whatsapp)."""
    if name == "console":
        from basa.platforms.console import ConsoleAdapter

        return ConsoleAdapter(router=router)
    if name == "telegram":
        from basa.config import get_settings
        from basa.platforms.telegram.bot import TelegramAdapter

        # Token dibaca dari .env — error jelas jika kosong.
        return TelegramAdapter(token=get_settings().telegram_bot_token, router=router)
    if name == "whatsapp":
        from basa.config import get_settings
        from basa.platforms.whatsapp.bot import WhatsAppAdapter

        # Kredensial Meta dibaca dari .env — error jelas jika belum lengkap.
        settings = get_settings()
        return WhatsAppAdapter(
            api_token=settings.whatsapp_api_token,
            phone_number_id=settings.whatsapp_phone_number_id,
            verify_token=settings.whatsapp_verify_token,
            port=settings.whatsapp_webhook_port,
            router=router,
        )
    raise ValueError(f"Platform '{name}' belum punya adapter.")

__all__ = ["PlatformAdapter", "get_adapter"]
