"""Adapter komposit untuk fallback antar-provider LLM."""

from __future__ import annotations

import logging

from basa.core.llm import LLMClient

log = logging.getLogger(__name__)


class FallbackLLMClient(LLMClient):
    """Coba provider utama; jika gagal, teruskan request ke provider cadangan."""

    def __init__(self, primary: LLMClient, fallback: LLMClient) -> None:
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}->{fallback.name}"

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        try:
            return self.primary.chat(
                system,
                user,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as primary_error:
            log.warning(
                "LLM primary '%s' gagal (%s); beralih ke fallback '%s'.",
                self.primary.name,
                primary_error,
                self.fallback.name,
            )
            try:
                return self.fallback.chat(
                    system,
                    user,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as fallback_error:
                raise RuntimeError(
                    f"LLM primary '{self.primary.name}' dan fallback "
                    f"'{self.fallback.name}' sama-sama gagal."
                ) from fallback_error
