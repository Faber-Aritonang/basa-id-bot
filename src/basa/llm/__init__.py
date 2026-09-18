"""Adapter LLM — tipis, satu per provider (mock, gemini, ...).

Tugas adapter: menerjemahkan pemanggilan abstrak `LLMClient` ke API provider
nyata. Semua logika bisnis (RAG, prompt) tetap di `basa.core.services`.

Gunakan `get_llm_client(settings)` untuk membuat klien dari konfigurasi.
Pola ini mirip `platforms.get_adapter` — provider dipilih lewat env, dan
di-fallback ke `MockLLMClient` jika kredensial belum diisi, agar `basa run`
tetap jalan tanpa API key (konsisten dengan filosofi "demo tanpa token").
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from basa.core.llm import LLMClient

if TYPE_CHECKING:
    from basa.config import Settings


def get_llm_client(settings: "Settings") -> LLMClient:
    """Buat klien LLM dari konfigurasi (default: mock jika tanpa API key).

    Bila `LLM_PROVIDER=gemini` TAPI `LLM_API_KEY` kosong, fallback ke mock
    (bukan crash) — agar bot tetap berfungsi sambil user menunggu isi kredensial.
    """
    provider = (settings.llm_provider or "mock").strip().lower()
    if provider == "gemini":
        if not settings.llm_api_key:
            from basa.llm.mock_adapter import MockLLMClient

            return MockLLMClient()
        from basa.llm.gemini_adapter import GeminiLLMClient

        return GeminiLLMClient(api_key=settings.llm_api_key, model=settings.llm_model)
    from basa.llm.mock_adapter import MockLLMClient

    return MockLLMClient()


__all__ = ["LLMClient", "get_llm_client"]
