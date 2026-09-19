"""Adapter LLM — tipis, satu per provider (mock, gemini, bynara, ...).

Tugas adapter: menerjemahkan pemanggilan abstrak `LLMClient` ke API provider
nyata. Semua logika bisnis (RAG, prompt) tetap di `basa.core.services`.

Gunakan `get_llm_client(settings)` untuk membuat klien dari konfigurasi.
Provider fallback bersifat opsional: bila key fallback kosong, hanya primary
yang dipakai.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from basa.core.llm import LLMClient

if TYPE_CHECKING:
    from basa.config import Settings


def _build_provider_client(
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
) -> LLMClient:
    """Bangun adapter provider konkret; key wajib sudah divalidasi caller."""
    if provider == "gemini":
        from basa.llm.gemini_adapter import GeminiLLMClient

        return GeminiLLMClient(api_key=api_key, model=model)
    if provider == "bynara":
        from basa.llm.bynara_adapter import BynaraLLMClient

        return BynaraLLMClient(api_key=api_key, model=model, base_url=base_url)
    from basa.llm.mock_adapter import MockLLMClient

    return MockLLMClient()


def get_llm_client(settings: "Settings") -> LLMClient:
    """Buat client primary dan fallback dari konfigurasi.

    Jika ``LLM_FALLBACK_API_KEY`` diisi, primary dicoba lebih dulu. Exception
    dari primary (termasuk quota/rate-limit 429 setelah retry adapter) memicu
    perpindahan ke provider fallback. Tanpa key, aplikasi tetap aman memakai
    mock seperti perilaku sebelumnya.
    """
    provider = (settings.llm_provider or "mock").strip().lower()
    if provider not in {"gemini", "bynara"} or not settings.llm_api_key:
        from basa.llm.mock_adapter import MockLLMClient

        return MockLLMClient()

    primary = _build_provider_client(
        provider,
        settings.llm_api_key,
        settings.llm_model,
        settings.llm_base_url,
    )

    fallback_provider = (settings.llm_fallback_provider or "").strip().lower()
    if fallback_provider not in {"gemini", "bynara"} or not settings.llm_fallback_api_key:
        return primary

    fallback = _build_provider_client(
        fallback_provider,
        settings.llm_fallback_api_key,
        settings.llm_fallback_model,
        settings.llm_fallback_base_url,
    )
    from basa.llm.fallback_adapter import FallbackLLMClient

    return FallbackLLMClient(primary, fallback)


__all__ = ["LLMClient", "get_llm_client"]
