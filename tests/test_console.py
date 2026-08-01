"""Test Console Simulator (Langkah 5): adapter terminal + loop chat."""

import builtins

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.messages import BotReply, Button, UserMessage
from basa.core.router import Router
from basa.db.engine import Base
from basa.db.models import Word
from basa.db.repositories import LanguageRepository
from basa.platforms.base import PlatformAdapter
from basa.platforms.console import CONSOLE_USER_ID, ConsoleAdapter, EXIT_COMMANDS


@pytest.fixture()
def adapter() -> ConsoleAdapter:
    """ConsoleAdapter dengan Router + DB in-memory berisi 1 kata Jawa."""
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
    return ConsoleAdapter(router=Router(session_factory=factory))


def test_adapter_is_abstract():
    """PlatformAdapter adalah ABC — tidak bisa diinstansiasi langsung."""
    with pytest.raises(TypeError):
        PlatformAdapter()  # type: ignore[abstract]


def test_normalize_sets_platform_and_user(adapter):
    msg = adapter.normalize("/help", "u1")
    assert isinstance(msg, UserMessage)
    assert msg.platform == "console"
    assert msg.user_id == "u1"


def test_handle_text_routes_to_core(adapter):
    reply = adapter.handle_text("/kata jawa", CONSOLE_USER_ID)
    assert isinstance(reply, BotReply)
    assert "mangan" in reply.text


def test_plain_text_gets_help_hint(adapter):
    reply = adapter.handle_text("halo apa kabar", CONSOLE_USER_ID)
    assert "/help" in reply.text


def test_render_buttons(capsys, adapter):
    adapter.render(BotReply("teks utama", buttons=[Button("Ya", "yes"), Button("Tidak", "no")]))
    out = capsys.readouterr().out
    assert "teks utama" in out
    assert "[ Ya ]" in out and "[ Tidak ]" in out


def test_render_text_strips_markdown(monkeypatch, adapter):
    """Di luar tty (test), asterisk markdown dihilangkan."""
    monkeypatch.setattr("basa.platforms.console._is_tty", lambda: False)
    assert adapter._render_text("📖 *sapulu* (numeral)") == "📖 sapulu (numeral)"


def test_render_text_double_asterisk(monkeypatch, adapter):
    """Markdown tebal `**kata**` (kuis) ikut dibersihkan tanpa sisa asterisk."""
    monkeypatch.setattr("basa.platforms.console._is_tty", lambda: False)
    assert adapter._render_text("🧠 **dolok**") == "🧠 dolok"


def test_start_loop_help_then_quit(monkeypatch, capsys, adapter):
    inputs = iter(["/help", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
    adapter.start()
    out = capsys.readouterr().out
    assert "Basa.id" in out  # banner
    assert "/kata" in out  # isi balasan /help
    assert "Sampai jumpa" in out  # perpisahan


def test_start_loop_any_exit_command(monkeypatch, capsys, adapter):
    for cmd in ("/exit", "/keluar", "/QUIT"):
        inputs = iter([cmd])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
        adapter.start()
        assert "Sampai jumpa" in capsys.readouterr().out


def test_start_loop_eof(monkeypatch, capsys, adapter):
    def eof(prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr(builtins, "input", eof)
    adapter.start()
    assert "Sampai jumpa" in capsys.readouterr().out


def test_start_loop_empty_input_skips_router(monkeypatch, capsys, adapter):
    inputs = iter(["", "  ", "/quit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
    adapter.start()
    out = capsys.readouterr().out
    assert "basa ›" not in out  # input kosong tidak memanggil router


def test_exit_commands_defined():
    assert {"/quit", "/exit", "/keluar"} == EXIT_COMMANDS


def test_get_adapter_console():
    from basa.platforms import get_adapter

    assert isinstance(get_adapter("console"), ConsoleAdapter)


def test_get_adapter_unknown_raises():
    from basa.platforms import get_adapter

    # Platform tanpa adapter → error jelas.
    with pytest.raises(ValueError):
        get_adapter("slack")
