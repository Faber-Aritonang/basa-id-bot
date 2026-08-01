"""Konfigurasi aplikasi — membaca environment variables via pydantic-settings.

Semua nilai diambil dari environment / file `.env` (yang TIDAK di-commit ke git).
Template: lihat `.env.example`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validasi & penyimpanan konfigurasi aplikasi."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Platform aktif: console | telegram | whatsapp
    platform: str = "console"

    # Database — SQLite untuk dev, PostgreSQL untuk produksi (ganti URL-nya saja)
    database_url: str = "sqlite:///data/basa.db"

    # Telegram
    telegram_bot_token: str = ""

    # WhatsApp (Meta WhatsApp Cloud API)
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_webhook_port: int = 8080

    # Logging
    log_level: str = "INFO"

    @property
    def supported_platforms(self) -> list[str]:
        """Daftar platform yang sudah ada adapter-nya."""
        return ["console", "telegram", "whatsapp"]


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — dipanggil sekali, di-cache untuk efisiensi."""
    return Settings()
