"""Adapter LLM Gemini — Google AI Studio (free tier) via google-generativeai.

SDK `google-generativeai` di-import secara lazy di __init__ agar instalasi
tanpa extra `llm` (lihat pyproject.toml) tetap berjalan — error jelas muncul
hanya saat user benar-benar memilih LLM_PROVIDER=gemini tanpa menginstal SDK.

Penanganan 429 (rate limit free tier): retry dengan backoff eksponensial
singkat (1s, 2s, 4s) — cukup untuk transient, tidak memblokir lama. Bila
backoff habis, error dilempar (jangan karangan teks) supaya caller tahu.
"""

from __future__ import annotations

import logging
import time

from basa.core.llm import LLMClient

log = logging.getLogger(__name__)

#: Backoff detik untuk retry 429 (rate limit Gemini free tier).
_RETRY_BACKOFFS = (1.0, 2.0, 4.0)


class GeminiLLMClient(LLMClient):
    """Klien LLM Google Gemini (AI Studio free tier)."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        if not api_key:
            raise ValueError(
                "LLM_API_KEY kosong — dapatkan key gratis di https://aistudio.google.com."
            )
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - jalankan hanya saat extra llm terpasang
            raise ImportError(
                "Package 'google-generativeai' belum terpasang. "
                "Install dengan: pip install -e '.[llm]'"
            ) from exc
        genai.configure(api_key=api_key)
        self._genai = genai
        self.model = model

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Kirim prompt ke Gemini, kembalikan teks balasan (dengan retry 429)."""
        model = self._genai.GenerativeModel(
            self.model,
            system_instruction=system,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        last_err: Exception | None = None
        for attempt, delay in enumerate(_RETRY_BACKOFFS):
            try:
                resp = model.generate_content(user)
                return (resp.text or "").strip()
            except Exception as exc:  # pragma: no cover - tergantung jaringan
                last_err = exc
                text = str(exc)
                # 429 / Resource exhausted = rate-limit free tier → retry.
                if "429" in text or "Resource exhausted" in text or "RESOURCE_EXHAUSTED" in text:
                    log.warning(
                        "Gemini rate-limit (429) — retry dalam %.0fs (percobaan %d/%d).",
                        delay,
                        attempt + 1,
                        len(_RETRY_BACKOFFS),
                    )
                    time.sleep(delay)
                    continue
                # Error lain (mis. key invalid, safety block) → jangan ditelan.
                raise
        raise RuntimeError(f"Gemini rate-limit terus-menerus setelah retry: {last_err}") from last_err
