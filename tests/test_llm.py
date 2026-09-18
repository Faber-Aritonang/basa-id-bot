"""Test factory & adapter LLM (mock fallback, determinisme).

Tidak menguji panggilan jaringan Gemini — itu butuh API key asli dan tidak
reproduktif di CI. Yang diuji: factory memilih branch yang benar, fallback
aman ke mock, dan mock deterministik + memantulkan konteks (dipakai test tutor).
"""

from basa.config import Settings
from basa.llm import get_llm_client
from basa.llm.mock_adapter import MockLLMClient


def test_get_llm_client_default_mock():
    settings = Settings(llm_provider="mock")
    client = get_llm_client(settings)
    assert isinstance(client, MockLLMClient)
    assert client.name == "mock"


def test_get_llm_client_gemini_without_key_falls_back_to_mock():
    """gemini TANPA key → fallback mock (bukan crash)."""
    settings = Settings(llm_provider="gemini", llm_api_key="")
    client = get_llm_client(settings)
    assert isinstance(client, MockLLMClient)


def test_get_llm_client_unknown_provider_falls_back_to_mock():
    settings = Settings(llm_provider="nonexistent")
    client = get_llm_client(settings)
    assert isinstance(client, MockLLMClient)


def test_mock_client_chat_deterministic():
    """Input sama → output sama; input beda → output beda."""
    client = MockLLMClient()
    a = client.chat("sys", "payload-123")
    b = client.chat("sys", "payload-123")
    assert a == b
    c = client.chat("sys", "payload-999")
    assert c != a


def test_mock_client_chat_reflects_context():
    """Mock memantulkan prompt user → konteks terlihat di output."""
    client = MockLLMClient()
    out = client.chat("system", "CONTEXT: kata = horas")
    assert "kata = horas" in out
    assert "Mode mock" in out
