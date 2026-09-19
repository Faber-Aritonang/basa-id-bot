"""Adapter LLM Bynara/NaraRouter via endpoint OpenAI-compatible.

Bynara menyediakan endpoint chat-completions yang kompatibel dengan skema
OpenAI. Adapter ini sengaja memakai httpx langsung agar tidak menambah SDK baru
ke proyek; core tetap hanya bergantung pada port ``LLMClient``.
"""

from __future__ import annotations

from typing import Any

import httpx

from basa.core.llm import LLMClient


_DEFAULT_BASE_URL = "https://router.bynara.id/v1"


class BynaraLLMClient(LLMClient):
    """Klien Bynara/NaraRouter untuk model-model pay-as-you-go."""

    name = "bynara"

    def __init__(
        self,
        api_key: str,
        model: str = "agnes-2.5-flash",
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("LLM_API_KEY kosong — isi token Bynara di .env.")
        if not base_url.strip():
            raise ValueError("LLM_BASE_URL kosong — isi base URL API Bynara di .env.")
        self._api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Kirim prompt ke endpoint OpenAI-compatible Bynara."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["messages"].append({"role": "system", "content": system})
        payload["messages"].append({"role": "user", "content": user})

        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Bynara error jaringan: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(
                f"Bynara API error {response.status_code}: {response.text[:300]}"
            )

        return _extract_text(response.json())


def _extract_text(data: dict[str, Any]) -> str:
    """Ambil choices[0].message.content dari response Chat Completions."""
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

    if data.get("error"):
        raise RuntimeError(f"Bynara response error: {str(data['error'])[:300]}")
    raise RuntimeError(f"Respon Bynara tak terduga: {str(data)[:300]}")
