"""Test factory & adapter LLM (mock fallback, determinisme).

Tidak menguji panggilan jaringan Gemini — itu butuh API key asli dan tidak
reproduktif di CI. Yang diuji: factory memilih branch yang benar, fallback
aman ke mock, dan mock deterministik + memantulkan konteks (dipakai test tutor).
"""

from basa.config import Settings
from basa.llm import get_llm_client
from basa.llm.bynara_adapter import BynaraLLMClient
from basa.llm.fallback_adapter import FallbackLLMClient
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


def test_get_llm_client_bynara_with_key():
    settings = Settings(
        llm_provider="bynara",
        llm_api_key="test-token",
        llm_model="agnes-2.5-flash",
        llm_base_url="https://example.test/v1",
    )
    client = get_llm_client(settings)
    assert isinstance(client, BynaraLLMClient)
    assert client.name == "bynara"
    assert client.model == "agnes-2.5-flash"
    assert client.base_url == "https://example.test/v1"


def test_get_llm_client_bynara_without_key_falls_back_to_mock():
    settings = Settings(llm_provider="bynara", llm_api_key="")
    client = get_llm_client(settings)
    assert isinstance(client, MockLLMClient)


def test_get_llm_client_builds_gemini_to_bynara_fallback():
    settings = Settings(
        llm_provider="gemini",
        llm_api_key="gemini-token",
        llm_model="gemini-model",
        llm_fallback_provider="bynara",
        llm_fallback_api_key="bynara-token",
        llm_fallback_model="agnes-2.5-flash",
        llm_fallback_base_url="https://example.test/v1",
    )
    client = get_llm_client(settings)
    assert isinstance(client, FallbackLLMClient)
    assert client.name == "gemini->bynara"
    assert client.primary.name == "gemini"
    assert client.fallback.name == "bynara"
    assert client.fallback.model == "agnes-2.5-flash"


def test_fallback_client_uses_backup_after_primary_error():
    class FakeClient:
        def __init__(self, name, result=None, error=None):
            self.name = name
            self.result = result
            self.error = error
            self.calls = 0

        def chat(self, system, user, *, max_tokens=512, temperature=0.7):
            del system, user, max_tokens, temperature
            self.calls += 1
            if self.error:
                raise self.error
            return self.result

    primary = FakeClient("gemini", error=RuntimeError("quota exhausted"))
    fallback = FakeClient("bynara", result="response dari Agnes")
    client = FallbackLLMClient(primary, fallback)

    assert client.chat("system", "user") == "response dari Agnes"
    assert primary.calls == 1
    assert fallback.calls == 1


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


def test_bynara_client_chat_uses_openai_compatible_payload():
    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {"choices": [{"message": {"content": "  jawaban Bynara  "}}]}

    class FakeHTTPClient:
        def __init__(self):
            self.request = None

        def post(self, url, *, headers, json):
            self.request = (url, headers, json)
            return FakeResponse()

    client = BynaraLLMClient(
        api_key="secret",
        model="agnes-2.5-flash",
        base_url="https://router.example/v1/",
    )
    fake = FakeHTTPClient()
    client._client = fake

    result = client.chat("system prompt", "user prompt", max_tokens=100, temperature=0.6)

    assert result == "jawaban Bynara"
    url, headers, payload = fake.request
    assert url == "https://router.example/v1/chat/completions"
    assert headers["Authorization"] == "Bearer secret"
    assert payload["model"] == "agnes-2.5-flash"
    assert payload["max_tokens"] == 100
    assert payload["temperature"] == 0.6
    assert payload["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]


def test_mock_client_chat_reflects_context():
    """Mock memantulkan prompt user → konteks terlihat di output."""
    client = MockLLMClient()
    out = client.chat("system", "CONTEXT: kata = horas")
    assert "kata = horas" in out
    assert "Mode mock" in out
