"""Layanan tutor percakapan — fitur #5 Basa.id (integrasi LLM).

Berbeda dari service lain yang membaca data statis, TutorService memakai LLM
(ports & adapters) untuk merangkai percakapan bebas — TAPI tetap grounded
di data kurasi via RAG: kata/frasa/aturan diambil dari DB dan disuapkan ke
LLM sebagai blok CONTEXT. LLM dilarang mengarang kosakata bahasa daerah
sendiri (anti-halusinasi — krusial untuk Batak Toba yang nyaris tidak ada
di memori parametrik model umum).

Stateless per Fase 1: tiap ``/obrolan`` = satu turn tutor tanpa memori
percakapan sebelumnya. Memori multi-turn (tabel ``conversation_sessions``)
menjadi Fase 2.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.llm import LLMClient
from basa.core.messages import BotReply
from basa.db.models import Platform
from basa.db.repositories import (
    GrammarRepository,
    LanguageRepository,
    PhraseRepository,
    WordRepository,
)

#: Jumlah item RAG per kategori yang disuapkan ke LLM.
_RAG_WORD_COUNT = 8
_RAG_PHRASE_COUNT = 3
_RAG_GRAMMAR_COUNT = 1

#: Batas token output untuk balasan tutor (singkat & ramah).
_MAX_TOKENS = 512
#: Temperature rendah → jawaban faktual, minim halusinasi.
_TEMPERATURE = 0.4

_SYSTEM_PROMPT_TEMPLATE = (
    "Kamu adalah tutor bahasa daerah Indonesia di bot Basa.id.\n"
    "Aturan MUTLAK:\n"
    "1. HANYA gunakan kosakata, frasa, dan aturan grammar yang ada di blok CONTEXT "
    "yang disediakan user. JANGAN pernah mengarang kata/frasa bahasa daerah sendiri.\n"
    "2. Jika CONTEXT tidak cukup menjawab, katakan dengan jujur 'belum tahu' dan "
    "arahkan user ke /kata, /frase, atau /grammar untuk materi lain.\n"
    "3. Balas SINGKAT (2-4 kalimat), ramah, dalam bahasa Indonesia.\n"
    "4. Saat memakai kata/frasa bahasa daerah, sertakan terjemahan Indonesia dalam "
    "kurung, mis: horas (halo).\n"
    "5. Jangan mengklaim lancar bahasa yang tidak ada di CONTEXT.\n"
    "Konteks: user sedang belajar bahasa {language_name}."
)


class TutorService:
    """Fitur tutor: percakapan bebas grounded (RAG) via LLM."""

    def __init__(self, session: Session, llm: LLMClient) -> None:
        self.session = session
        self.llm = llm
        self.languages = LanguageRepository(session)
        self.words = WordRepository(session)
        self.phrases = PhraseRepository(session)
        self.grammar = GrammarRepository(session)

    def converse(
        self,
        alias: str,
        user_message: str,
        user_id: str | None = None,
        platform: Platform | None = None,
    ) -> BotReply:
        """Satu turn tutor: ambil konteks RAG → susun prompt → panggil LLM.

        ``user_id`` dan ``platform`` diterima untuk simetri signature dengan
        service lain (dan bekal Fase 2 multi-turn); Fase 1 stateless belum
        memakainya.
        """
        del user_id, platform  # belum dipakai Fase 1 — simetri signature.

        language = self.languages.get_by_code(resolve_code(alias))
        if language is None:
            return BotReply(
                f"Bahasa '{alias}' belum tersedia. Coba: /bahasa untuk daftar, "
                "atau /obrolan batak, /obrolan jawa, /obrolan sunda."
            )

        context = self._build_context(language.id, language.name)
        if not context["has_any"]:
            return BotReply(
                f"Materi bahasa {language.name} masih kosong. "
                "Jalankan `basa db seed` dulu ya sebelum /obrolan."
            )

        system = _SYSTEM_PROMPT_TEMPLATE.format(language_name=language.name)
        user = self._build_user_prompt(user_message, context)
        try:
            reply_text = self.llm.chat(
                system, user, max_tokens=_MAX_TOKENS, temperature=_TEMPERATURE
            )
        except Exception as exc:  # pragma: no cover - jalankan saat adapter nyata gagal
            # Gagal panggil LLM → jangan crash bot; beri pesan + petunjuk.
            return BotReply(
                "Maaf, tutor AI sedang gagal merespons. Coba lagi sebentar ya. "
                f"(Detail: {exc})"
            )
        if not reply_text.strip():
            return BotReply("Tutor tidak memberikan balasan. Coba /obrolan lagi ya.")
        return BotReply(reply_text.strip())

    # --- RAG retrieval ---

    def _build_context(self, language_id: int, language_name: str) -> dict:
        """Ambil kata/frasa/grammar acak dari DB → struktur konteks untuk prompt."""
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

    # --- prompt user ---

    @staticmethod
    def _build_user_prompt(user_message: str, context: dict) -> str:
        """Susun prompt user: blok CONTEXT + pesan user (atau permintaan awal)."""
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
        msg = (user_message or "").strip()
        if msg:
            lines.append(f"Pesan user: {msg}")
        else:
            # Tanpa pesan → minta tutor memulai latihan dari CONTEXT.
            lines.append(
                "Pesan user: (user baru saja memulai sesi tanpa pesan khusus — "
                "sapa mereka dan ajak latihan dengan satu frasa dari CONTEXT di atas.)"
            )
        return "\n".join(lines)
