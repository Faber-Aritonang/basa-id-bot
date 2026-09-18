"""Port LLM — kontrak abstrak untuk klien bahasa model.

Sama seperti `PlatformAdapter`, `LLMClient` adalah PORT: core hanya mengenal
interface ini, tidak pernah menyentuh SDK provider (Google Gemini, dst.).
Adapter konkret (mock, gemini) ada di `basa.llm` dan di-inject ke service
lewat constructor — sehingga service tetap mudah diuji tanpa panggilan jaringan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Kontrak minimal klien LLM: prompt sistem + prompt user → teks balasan.

    Method tunggal `chat()` sengaja disederhanakan agar mudah ditiru oleh
    adapter mock (untuk test) maupun adapter provider nyata. Provider
    mana pun yang dipakai, service inti tidak berubah — itu inti pola
    ports & adapters yang sudah dipakai project ini.
    """

    #: Nama provider untuk log/diagnostik (mis. "mock", "gemini").
    name: str = "llm"

    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> str:
        """Kirim prompt sistem + user → kembalikan teks balasan LLM.

        Args:
            system: instruksi peran/batasan (prompt sistem).
            user: pesan user beserta konteks RAG (prompt user).
            max_tokens: batas kasar token output.
            temperature: kreativitas (0=kaku, 1=liar).

        Returns:
            Teks balasan (sudah dipangkas whitespace). Tidak pernah None.
        """
        raise NotImplementedError
