"""Adapter LLM Gemini — Google AI Studio (free tier) via REST API.

Memakai endpoint Generative Language (v1beta) langsung lewat httpx — tanpa
dependency SDK ``google-generativeai``, sehingga tidak ada risiko versi/
migrasi SDK. Endpoint ini diverifikasi kompatibel dengan API key Google AI
Studio (termasuk format key baru ``AQ...``).

Penanganan 429 (rate limit free tier): retry dengan backoff eksponensial
singkat (1s, 2s, 4s). Bila backoff habis, error dilempar (jangan karangan
teks) supaya caller tahu — konsisten dengan filosofi "jangan halusinasi".
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from basa.core.llm import LLMClient

log = logging.getLogger(__name__)

#: Endpoint Generative Language v1beta.
_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

#: Backoff detik untuk retry 429 (rate limit Gemini free tier).
_RETRY_BACKOFFS = (1.0, 2.0, 4.0)


class GeminiLLMClient(LLMClient):
    """Klien LLM Google Gemini (AI Studio free tier) via REST."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError(
                "LLM_API_KEY kosong — dapatkan key gratis di https://aistudio.google.com."
            )
        self._api_key = api_key
        self.model = model
        self._client = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Kirim prompt ke Gemini, kembalikan teks balasan (dengan retry 429)."""
        url = f"{_API_BASE}/models/{self.model}:generateContent"
        params = {"key": self._api_key}
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}

        last_err: Exception | None = None
        for attempt, delay in enumerate(_RETRY_BACKOFFS):
            try:
                resp = self._client.post(url, params=params, json=payload)
            except httpx.HTTPError as exc:  # gangguan jaringan transient → retry
                last_err = exc
                log.warning(
                    "Gemini error jaringan — retry dalam %.0fs (percobaan %d/%d).",
                    delay,
                    attempt + 1,
                    len(_RETRY_BACKOFFS),
                )
                time.sleep(delay)
                continue

            if resp.status_code == 429:
                last_err = RuntimeError(f"Gemini 429 rate-limit (percobaan {attempt + 1})")
                log.warning(
                    "Gemini rate-limit (429) — retry dalam %.0fs (percobaan %d/%d).",
                    delay,
                    attempt + 1,
                    len(_RETRY_BACKOFFS),
                )
                time.sleep(delay)
                continue

            if resp.status_code >= 400:
                # Error lain (mis. key invalid, model tidak ada, safety block) → jangan ditelan.
                raise RuntimeError(
                    f"Gemini API error {resp.status_code}: {resp.text[:300]}"
                )

            return _extract_text(resp.json())

        raise RuntimeError(
            f"Gemini rate-limit terus-menerus setelah retry: {last_err}"
        ) from last_err


def _extract_text(data: dict[str, Any]) -> str:
    """Ambil teks dari response generateContent; tangani block/error field."""
    candidates = data.get("candidates") or []
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        for part in parts:
            text = part.get("text")
            if text:
                return text.strip()
        # Candidate ada tapi tidak ada teks (mis. finishReason=SAFETY).
        finish_reason = candidates[0].get("finishReason")
        if finish_reason:
            raise RuntimeError(
                f"Gemini tidak mengembalikan teks (finishReason={finish_reason})."
            )
    prompt_feedback = data.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        raise RuntimeError(
            f"Gemini prompt diblokir (blockReason={prompt_feedback['blockReason']})."
        )
    raise RuntimeError(f"Respon Gemini tak terduga: {str(data)[:300]}")
