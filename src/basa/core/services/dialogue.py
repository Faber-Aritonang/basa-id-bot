"""Layanan percakapan contoh — fitur dialog tanya-jawab 2 orang via LLM+RAG.

Mirip TutorService: men-generate SATU dialog singkat antara dua orang (A & B)
dalam bahasa daerah, GROUNDED di data kurasi DB (anti-halusinasi). Tiap
panggilan menghasilkan dialog baru yang bervariasi bergantung LLM — tidak
sama setiap kali, beda dari /frase yang membaca frasa statis.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.llm import LLMClient
from basa.core.messages import BotReply
from basa.db.repositories import (
    GrammarRepository,
    LanguageRepository,
    PhraseRepository,
    WordRepository,
)

#: Jumlah item RAG per kategori yang disuapkan ke LLM. Frasa diperbanyak
#: karena dialog bersifat percakapan — frasa harian paling relevan.
_RAG_WORD_COUNT = 6
_RAG_PHRASE_COUNT = 5
_RAG_GRAMMAR_COUNT = 1

#: Batas token output untuk dialog (cukup untuk 4-6 baris + rangkuman).
_MAX_TOKENS = 600
#: Temperature sedikit lebih tinggi dari tutor → dialog bervariasi antar panggilan.
_TEMPERATURE = 0.6

_SYSTEM_PROMPT_TEMPLATE = (
    "Kamu adalah penulis dialog bahasa daerah di bot Basa.id.\n"
    "Tugas: buatkan SATU dialog tanya-jawab singkat (4-6 baris) antara dua "
    "orang, A dan B, dalam bahasa {language_name}.\n"
    "Aturan MUTLAK:\n"
    "1. HANYA gunakan kosakata, frasa, dan aturan grammar dari blok CONTEXT. "
    "JANGAN mengarang kata/frasa bahasa daerah sendiri.\n"
    "2. Tiap baris pakai format: 'A: <kalimat bahasa daerah> "
    "(<terjemahan Indonesia>)' atau 'B: ...'.\n"
    "3. Susun alami: sapaan -> pertanyaan -> jawaban -> tanggapan.\n"
    "4. Gunakan minimal 2 frasa/kata dari CONTEXT.\n"
    "5. Jika CONTEXT tidak cukup untuk dialog, katakan jujur 'Maaf, materi "
    "belum cukup untuk dialog lengkap.' dan sarankan /kata atau /frase.\n"
    "6. Setelah dialog, tambahkan satu baris kosong lalu baris rangkuman: "
    "'Materi: <daftar kata/frasa yang dipakai>'.\n"
    "Konteks: user meminta contoh percakapan bahasa {language_name}."
)


class DialogueService:
    """Fitur percakapan: dialog 2 orang grounded (RAG) via LLM."""

    def __init__(self, session: Session, llm: LLMClient) -> None:
        self.session = session
        self.llm = llm
        self.languages = LanguageRepository(session)
        self.words = WordRepository(session)
        self.phrases = PhraseRepository(session)
        self.grammar = GrammarRepository(session)

    def generate(
        self,
        alias: str,
        user_id: str | None = None,
        platform: "Platform | None" = None,
    ) -> BotReply:
        """Satu panggilan: ambil konteks RAG -> susun prompt -> panggil LLM.

        ``user_id`` dan ``platform`` diterima untuk simetri signature dengan
        service lain; belum dipakai di Fase 1.
        """
        del user_id, platform

        language = self.languages.get_by_code(resolve_code(alias))
        if language is None:
            return BotReply(
                f"Bahasa '{alias}' belum tersedia. Coba: /bahasa untuk daftar, "
                "atau /percakapan batak, /percakapan jawa, /percakapan sunda."
            )

        context = self._build_context(language.id, language.name)
        if not context["has_any"]:
            return BotReply(
                f"Materi bahasa {language.name} masih kosong. "
                "Jalankan `basa db seed` dulu ya sebelum /percakapan."
            )

        system = _SYSTEM_PROMPT_TEMPLATE.format(language_name=language.name)
        user = self._build_user_prompt(context)
        try:
            reply_text = self.llm.chat(
                system, user, max_tokens=_MAX_TOKENS, temperature=_TEMPERATURE
            )
        except Exception as exc:  # pragma: no cover - jalankan saat adapter nyata gagal
            return BotReply(
                "Maaf, pembuatan percakapan sedang gagal. Coba lagi sebentar ya. "
                f"(Detail: {exc})"
            )
        if not reply_text.strip():
            return BotReply("Tidak ada dialog yang dihasilkan. Coba /percakapan lagi ya.")
        return BotReply(reply_text.strip())

    # --- RAG retrieval (mirror TutorService, tetap self-contained per service) ---

    def _build_context(self, language_id: int, language_name: str) -> dict:
        """Ambil kata/frasa/grammar acak dari DB -> struktur konteks untuk prompt."""
        words = self.words.get_random(language_id, limit=_RAG_WORD_COUNT)
        phrases = self.phrases.get_random(language_id, limit=_RAG_PHRASE_COUNT)
        grammar = self.grammar.get_random(language_id, limit=_RAG_GRAMMAR_COUNT)
        return {
            "language_name": language_name,
            "words": [
                f"{w.term} ({w.part_of_speech}) = {w.translation}"
                + (f" | contoh: {w.example} ({w.example_translation})" if w.example else "")
                for w in words
            ],
            "phrases": [
                f"{p.phrase} = {p.translation}"
                + (f" | konteks: {p.context}" if p.context else "")
                for p in phrases
            ],
            "grammar": [
                f"{g.title}: {g.explanation}"
                + (f" | contoh: {g.example}" if g.example else "")
                for g in grammar
            ],
            "has_any": bool(words or phrases or grammar),
        }

    @staticmethod
    def _build_user_prompt(context: dict) -> str:
        """Susun prompt user: blok CONTEXT + permintaan generate dialog."""
        lines: list[str] = ["=== CONTEXT (data resmi dari DB Basa.id) ==="]
        if context["words"]:
            lines.append("Kosakata:")
            lines.extend(f"  - {w}" for w in context["words"])
        if context["phrases"]:
            lines.append("Frasa percakapan:")
            lines.extend(f"  - {p}" for p in context["phrases"])
        if context["grammar"]:
            lines.append("Aturan grammar:")
            lines.extend(f"  - {g}" for g in context["grammar"])
        lines.append("=== END CONTEXT ===")
        lines.append("")
        lines.append(
            "Pesan user: buatkan satu contoh dialog tanya-jawab 2 orang "
            "(A & B) memakai CONTEXT di atas."
        )
        return "\n".join(lines)
