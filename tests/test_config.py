"""Setup awal: pastikan konfigurasi terbaca dari env/.env."""

from basa.config import Settings, get_settings


def test_default_settings_load(monkeypatch):
    # Isolasi dari .env/env luar supaya test tidak bergantung environment.
    for var in ("PLATFORM", "DATABASE_URL", "TELEGRAM_BOT_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    settings = get_settings()
    assert settings.platform == "console"
    assert settings.database_url.startswith("sqlite")


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("PLATFORM", "telegram")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test-token")
    s = Settings()
    assert s.platform == "telegram"
    assert s.telegram_bot_token == "123:test-token"


def test_supported_platforms_placeholder():
    assert "console" in get_settings().supported_platforms
