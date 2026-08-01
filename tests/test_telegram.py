"""Test adapter Telegram (Langkah 6) — tanpa jaringan, pakai fake update.

Kita tidak bisa (dan tidak boleh) menguji live di test; yang diuji adalah
kontrak adapter: routing pesan → core, render markdown + inline keyboard,
dan fallback saat markdown ditolak Telegram.
"""

import asyncio

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker
from telegram.constants import ParseMode
from telegram.error import TelegramError

from basa.core.messages import BotReply, Button
from basa.core.router import Router
from basa.db.engine import Base
from basa.db.models import Word
from basa.db.repositories import LanguageRepository
from basa.platforms.telegram.bot import TelegramAdapter


class FakeUser:
    id = 999


class FakeMessage:
    def __init__(self, text: str | None):
        self.text = text
        self.replies: list[dict] = []
        self.fail_markdown = False

    async def reply_text(self, text: str, **kwargs):
        if self.fail_markdown and kwargs.get("parse_mode"):
            raise TelegramError("can't parse entities")
        self.replies.append({"text": text, **kwargs})
        return None


class FakeUpdate:
    def __init__(self, text: str | None):
        self.message = FakeMessage(text)
        self.effective_user = FakeUser()


@pytest.fixture()
def adapter() -> TelegramAdapter:
    """TelegramAdapter dengan Router + DB in-memory berisi 1 kata Jawa."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        jv = LanguageRepository(session).get_or_create("jv", "Javanese")
        session.add(Word(language_id=jv.id, term="mangan", translation="to eat", part_of_speech="verb"))
        session.commit()
    return TelegramAdapter(token="123:test-token", router=Router(session_factory=factory))


def test_init_requires_token():
    with pytest.raises(ValueError):
        TelegramAdapter(token="")


def test_platform_name(adapter):
    assert adapter.platform_name == "telegram"


def test_build_app_registers_two_handlers(adapter):
    app = adapter._build_app()
    # Grup 0 berisi MessageHandler (teks) + CallbackQueryHandler.
    assert len(app.handlers[0]) == 2


def test_on_message_routes_to_core(adapter):
    update = FakeUpdate("/kata jawa")
    asyncio.run(adapter._on_message(update, None))
    sent = update.message.replies[0]
    assert "mangan" in sent["text"]
    assert sent["parse_mode"] == ParseMode.MARKDOWN
    assert sent["reply_markup"] is None


def test_on_message_without_text_ignored(adapter):
    update = FakeUpdate(None)
    asyncio.run(adapter._on_message(update, None))
    assert update.message.replies == []


def test_send_falls_back_to_plain_text_when_markdown_rejected(adapter):
    update = FakeUpdate("/kata jawa")
    update.message.fail_markdown = True
    asyncio.run(adapter._on_message(update, None))
    sent = update.message.replies[0]
    assert "mangan" in sent["text"]
    assert "parse_mode" not in sent  # kirim ulang tanpa markdown


def test_send_with_buttons_builds_inline_keyboard(adapter):
    update = FakeUpdate("/kata jawa")
    reply = BotReply("pilih jawaban", buttons=[Button("A", "a"), Button("B", "b")])
    asyncio.run(adapter._send(update.message, reply))
    sent = update.message.replies[0]
    assert sent["reply_markup"] is not None
    row = sent["reply_markup"].inline_keyboard[0]
    assert [b.text for b in row] == ["A", "B"]
    assert row[0].callback_data == "a"


def test_callback_query_routed_to_core(adapter):
    class FakeQuery:
        data = "/kata jawa"
        edited: dict | None = None

        async def answer(self) -> None:
            pass

        async def edit_message_text(self, text: str, **kwargs) -> None:
            self.edited = {"text": text, **kwargs}

    class FakeCallbackUpdate:
        callback_query = FakeQuery()
        effective_user = FakeUser()

    update = FakeCallbackUpdate()
    asyncio.run(adapter._on_callback(update, None))
    assert update.callback_query.edited is not None
    assert "mangan" in update.callback_query.edited["text"]


def test_callback_edit_passes_keyboard_when_reply_has_buttons(adapter):
    """Edit callback membawa tombol soal kuis berikutnya (kuis interaktif)."""
    class FakeQuery:
        data = "1"
        edited: dict | None = None

        async def answer(self) -> None:
            pass

        async def edit_message_text(self, text: str, **kwargs) -> None:
            self.edited = {"text": text, **kwargs}

    class FakeCallbackUpdate:
        callback_query = FakeQuery()
        effective_user = FakeUser()

    reply = BotReply("soal berikutnya", buttons=[Button("1. a", "1"), Button("2. b", "2")])
    adapter.router.handle = lambda _msg: reply

    update = FakeCallbackUpdate()
    asyncio.run(adapter._on_callback(update, None))
    edited = update.callback_query.edited
    assert edited is not None
    assert "soal berikutnya" in edited["text"]
    assert edited["reply_markup"] is not None
    row = edited["reply_markup"].inline_keyboard[0]
    assert [b.text for b in row] == ["1. a", "2. b"]


def test_callback_edit_clears_keyboard_when_no_buttons(adapter):
    """Hasil akhir kuis (tanpa tombol) → keyboard lama dibersihkan."""
    class FakeQuery:
        data = "2"
        edited: dict | None = None

        async def answer(self) -> None:
            pass

        async def edit_message_text(self, text: str, **kwargs) -> None:
            self.edited = {"text": text, **kwargs}

    class FakeCallbackUpdate:
        callback_query = FakeQuery()
        effective_user = FakeUser()

    adapter.router.handle = lambda _msg: BotReply("Kuis selesai! Skor: 5/5")

    update = FakeCallbackUpdate()
    asyncio.run(adapter._on_callback(update, None))
    edited = update.callback_query.edited
    assert edited is not None
    assert edited["reply_markup"] is not None
    # PTB menyimpan keyboard sebagai tuple — kosong berarti keyboard dibersihkan
    assert len(edited["reply_markup"].inline_keyboard) == 0


def test_get_adapter_telegram_requires_token(monkeypatch):
    """get_adapter('telegram') tanpa token → error jelas.

    Dipatch lewat `basa.config.get_settings` (bukan env) supaya test tetap
    hijau meskipun user sudah mengisi token asli di `.env` untuk uji live.
    """
    from basa.config import Settings
    from basa.platforms import get_adapter

    # Init kwargs mengalahkan env di pydantic-settings → token dipaksa kosong.
    monkeypatch.setattr("basa.config.get_settings", lambda: Settings(telegram_bot_token=""))

    with pytest.raises(ValueError):
        get_adapter("telegram")
