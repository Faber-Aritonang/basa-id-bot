"""Adapter LLM tiruan — untuk test & demo tanpa API key.

`MockLLMClient` tidak memanggil jaringan apa pun. Balasannya deterministik
dan **merefleksikan konteks RAG** yang disuapi lewat prompt user — sehingga:

- demo `basa run` tanpa `LLM_API_KEY` tetap memperlihatkan apa yang diambil
  dari DB (konteks retrieval terlihat), dan
- test bisa menegaskan bahwa konteks benar-benar mengalir ke LLM (lihat
  `tests/test_tutor.py`).

Saat `LLM_API_KEY` terisi + `LLM_PROVIDER=gemini`, factory otomatis beralih
ke `GeminiLLMClient` — mock tidak dipakai lagi.
"""

from __future__ import annotations

from basa.core.llm import LLMClient

#: Batas cuplikan konteks yang ditampilkan balasan mock (cukup untuk demo & test).
_PREVIEW_LIMIT = 1200


class MockLLMClient(LLMClient):
    """Klien LLM tiruan: balasan deterministik dari konteks prompt user."""

    name = "mock"

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        # Parameter `system`/`max_tokens`/`temperature` sengaja tidak dipakai —
        # mock hanya merangkum `user` (yang berisi blok CONTEXT RAG) supaya
        # alur retrieval terlihat. Abaikan warning "unused" lewaat decorator.
        del system, max_tokens, temperature
        preview = user.strip()
        if len(preview) > _PREVIEW_LIMIT:
            preview = preview[:_PREVIEW_LIMIT].rstrip() + " …"
        return (
            "🤖 [Mode mock — tanpa API key]\n"
            "Tutor tiruan membalas berdasarkan konteks yang diambil dari DB:\n"
            f"---\n{preview}\n---\n"
            "Untuk respons tutor nyata, isi LLM_PROVIDER=gemini + LLM_API_KEY "
            "di .env (dapat key gratis di https://aistudio.google.com)."
        )
