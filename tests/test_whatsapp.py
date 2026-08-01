"""Test adapter WhatsApp (Langkah 7) — tanpa jaringan, pakai fake client.

Kita tidak bisa (dan tidak boleh) menguji live di test; yang diuji adalah
kontrak adapter: verifikasi handshake webhook, routing pesan masuk → core,
dan payload Graph API (teks polos + interactive buttons).
"""

import httpx
import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.messages import BotReply, Button
from basa.core.router import Router
from basa.db.engine import Base
from basa.db.models import Word
from basa.db.repositories import LanguageRepository
from basa.platforms.whatsapp.bot import WhatsAppAdapter


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)  # type: ignore[arg-type]


class FakeClient:
    """Merekam request Graph API — tidak menyentuh jaringan."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse()


@pytest.fixture()
def adapter() -> WhatsAppAdapter:
    """WhatsAppAdapter dengan Router + DB in-memory berisi 1 kata Jawa."""
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
    return WhatsAppAdapter(
        api_token="tokentest",
        phone_number_id="123456789",
        verify_token="verifyme",
        router=Router(session_factory=factory),
        client=FakeClient(),
    )


def _text_payload(body: str, wa_id: str = "6281234567890") -> dict:
    """Payload webhook Meta untuk satu pesan teks masuk."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WBA",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "15551234567", "phone_number_id": "123456789"},
                            "contacts": [{"profile": {"name": "User"}, "wa_id": wa_id}],
                            "messages": [
                                {"from": wa_id, "id": "wamid.1", "timestamp": "1710000000", "type": "text", "text": {"body": body}}
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def test_init_requires_all_credentials():
    with pytest.raises(ValueError):
        WhatsAppAdapter(api_token="", phone_number_id="x", verify_token="y")
    with pytest.raises(ValueError):
        WhatsAppAdapter(api_token="x", phone_number_id="", verify_token="y")
    with pytest.raises(ValueError):
        WhatsAppAdapter(api_token="x", phone_number_id="y", verify_token="")


def test_platform_name(adapter):
    assert adapter.platform_name == "whatsapp"


def test_verify_webhook_ok(adapter):
    assert adapter.verify_webhook("subscribe", "verifyme", "challenge-123") == "challenge-123"


def test_verify_webhook_wrong_token(adapter):
    assert adapter.verify_webhook("subscribe", "salah", "challenge-123") is None


def test_verify_webhook_wrong_mode(adapter):
    assert adapter.verify_webhook("unsubscribe", "verifyme", "challenge-123") is None


def test_handle_webhook_routes_text_to_core(adapter):
    status = adapter.handle_webhook(_text_payload("/kata jawa"))
    assert status == 200
    sent = adapter._client.calls[0]
    assert sent["url"].endswith("/123456789/messages")
    assert sent["headers"]["Authorization"] == "Bearer tokentest"
    assert "mangan" in sent["json"]["text"]["body"]


def test_handle_webhook_plain_text_gets_help_hint(adapter):
    adapter.handle_webhook(_text_payload("halo apa kabar"))
    sent = adapter._client.calls[0]
    assert "/help" in sent["json"]["text"]["body"]


def test_handle_webhook_statuses_ignored(adapter):
    """Payload status (delivered/read) → di-ack, tidak ada kiriman balasan."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WBA",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "123456789"},
                            "statuses": [
                                {"id": "wamid.9", "status": "delivered", "timestamp": "1710000005", "recipient_id": "6281234567890"}
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    status = adapter.handle_webhook(payload)
    assert status == 200
    assert adapter._client.calls == []


def test_handle_webhook_button_reply_uses_callback_id(adapter):
    """Balasan tombol interaktif → `button_reply.id` diproses seperti callback."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WBA",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "123456789"},
                            "contacts": [{"profile": {"name": "User"}, "wa_id": "6281234567890"}],
                            "messages": [
                                {
                                    "from": "6281234567890",
                                    "id": "wamid.2",
                                    "timestamp": "1710000000",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "/kata jawa", "title": "Kata Jawa"},
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    status = adapter.handle_webhook(payload)
    assert status == 200
    sent = adapter._client.calls[0]
    assert "mangan" in sent["json"]["text"]["body"]


def test_send_text_strips_markdown(adapter):
    reply = BotReply("📖 *sapulu* (numeral)")  # markdown Telegram masuk dari core
    adapter._send("6281234567890", reply)
    payload = adapter._client.calls[0]["json"]
    assert payload["type"] == "text"
    assert payload["text"]["body"] == "📖 sapulu (numeral)"


def test_send_with_buttons_builds_interactive_payload(adapter):
    reply = BotReply("pilih bahasa", buttons=[Button("Jawa", "jawa"), Button("Batak", "batak")])
    adapter._send("6281234567890", reply)
    payload = adapter._client.calls[0]["json"]
    assert payload["type"] == "interactive"
    interactive = payload["interactive"]
    assert interactive["type"] == "button"
    assert interactive["body"]["text"] == "pilih bahasa"
    buttons = interactive["action"]["buttons"]
    assert [b["reply"]["id"] for b in buttons] == ["jawa", "batak"]
    assert [b["reply"]["title"] for b in buttons] == ["Jawa", "Batak"]


def test_send_buttons_capped_at_three(adapter):
    reply = BotReply(
        "pilih",
        buttons=[Button(f"Opsi {i}", f"opt{i}") for i in range(5)],
    )
    adapter._send("6281234567890", reply)
    payload = adapter._client.calls[0]["json"]
    assert len(payload["interactive"]["action"]["buttons"]) == 3


def test_send_long_text_with_buttons_falls_back_to_plain_text(adapter):
    """Teks > 1024 char + tombol → dikirim polos tanpa tombol (batas API)."""
    long_text = "kata kunci " * 200  # > 1024 karakter
    reply = BotReply(long_text, buttons=[Button("A", "a"), Button("B", "b")])
    adapter._send("6281234567890", reply)
    payload = adapter._client.calls[0]["json"]
    assert payload["type"] == "text"
    assert "interactive" not in payload
    assert payload["text"]["body"] == adapter._render_text(long_text)


def test_send_raises_on_api_error(adapter):
    adapter._client.post = lambda *a, **kw: FakeResponse(status_code=500)
    with pytest.raises(httpx.HTTPStatusError):
        adapter._send("6281234567890", BotReply("halo"))


def test_get_adapter_whatsapp_requires_credentials(monkeypatch):
    """get_adapter('whatsapp') tanpa kredensial → error jelas.

    Dipatch lewat `basa.config.get_settings` supaya test tetap hijau meski
    user sudah mengisi kredensial asli di `.env` untuk uji live.
    """
    from basa.config import Settings
    from basa.platforms import get_adapter

    # Init kwargs mengalahkan env di pydantic-settings → kredensial dipaksa kosong.
    monkeypatch.setattr(
        "basa.config.get_settings",
        lambda: Settings(whatsapp_api_token="", whatsapp_phone_number_id="", whatsapp_verify_token=""),
    )

    with pytest.raises(ValueError):
        get_adapter("whatsapp")
