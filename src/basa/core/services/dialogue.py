"""Layanan percakapan contoh — fitur dialog tanya-jawab 2 orang via LLM+RAG.

Mirip TutorService: men-generate SATU dialog singkat antara dua orang (A & B)
dalam bahasa daerah, GROUNDED di data kurasi DB (anti-halusinasi). Tiap
panggilan menghasilkan dialog baru yang bervariasi bergantung LLM — tidak
sama setiap kali, beda dari /frase yang membaca frasa statis.
"""

from __future__ import annotations

import random

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

#: Batas token output untuk dialog. 3-5 tanya-jawab (6-10 baris) + terjemahan
#: + baris Tema + baris Materi butuh ruang lebih besar dari tutor singkat.
_MAX_TOKENS = 1000
#: Temperature moderat — cukup variasi antar panggilan, tapi cukup patuh
#: aturan struktur (jumlah baris, format).
_TEMPERATURE = 0.6

#: Daftar tema percakapan sehari-hari. Dipilih acak tiap panggilan supaya
#: tiap /percakapan menghasilkan dialog yang berbeda konteksnya, bukan cuma
#: beda kalimat. Tema juga diteruskan ke LLM lewat system + user prompt.
_THEMES: tuple[str, ...] = (
    "Sapaan & perkenalan dua orang yang baru bertemu",
    "Bertemu teman lama di jalan",
    "Membeli buah di pasar",
    "Memesan makanan di warung",
    "Bertanya arah jalan ke penduduk lokal",
    "Mengundang teman makan bareng",
    "Berbincang tentang keluarga (berapa anak, dari mana)",
    "Menyampaikan undangan pesta pernikahan",
    "Bertanya kabar orang sakit",
    "Bicara tentang cuaca & musim panen",
    "Menanyakan jadwal bus/kereta ke kota sebelah",
    "Memuji hidangan tuan rumah saat berkunjung",
)

_SYSTEM_PROMPT_TEMPLATE = (
    "Kamu adalah penulis dialog bahasa daerah di bot Basa.id.\n"
    "Tugas: buatkan SATU dialog tanya-jawab antara dua orang, A dan B, dalam "
    "bahasa {language_name}, dengan TEMA: {theme}.\n"
    "Aturan MUTLAK:\n"
    "1. Dialog HARUS terdiri dari MINIMAL 3 dan MAKSIMAL 5 kali tanya-jawab. "
    "Satu tanya-jawab = 1 baris A + 1 baris B (sepasang). Jadi total HARUS "
    "GENAP: 6, 8, atau 10 baris A/B. JANGAN berhenti di 5 atau 7 baris. "
    "Contoh struktur yang BENAR (3 tanya-jawab = 6 baris):\n"
    "   A: ... (...)\n"
    "   B: ... (...)\n"
    "   A: ... (...)\n"
    "   B: ... (...)\n"
    "   A: ... (...)\n"
    "   B: ... (...)\n"
    "   -> berakhir pada baris B.\n"
    "2. HANYA gunakan kosakata, frasa, dan aturan grammar dari blok CONTEXT. "
    "JANGAN mengarang kata/frasa bahasa daerah sendiri.\n"
    "3. Tiap baris pakai format: 'A: <kalimat bahasa daerah> "
    "(<terjemahan Indonesia>)' atau 'B: ...'.\n"
    "4. TEMA adalah SETTING/RANGKA saja, BUKAN syarat kosakata. Susun dialog "
    "mengikuti tema selama mungkin, tapi prioritas UTAMA adalah memakai kata/"
    "frasa dari CONTEXT. Bila kata spesifik untuk tema tidak ada di CONTEXT, "
    "SEDERHANAKAN temanya agar cocok dengan kosakata yang tersedia (mis. tema "
    "'membeli buah di pasar' -> cukup dialog sapaan + tanya kabar + sebut "
    "makanan/harga memakai kata yang ADA) — JANGAN menolak membuat dialog.\n"
    "5. Gunakan minimal 2 frasa/kata dari CONTEXT.\n"
    "6. Susun alami: sapaan -> inti percakapan -> penutup/salam.\n"
    "7. HANYA boleh menolak ('Maaf, materi belum cukup...') jika CONTEXT "
    "berisi kurang dari 2 item total. Selama CONTEXT ada >= 2 item, WAJIB "
    "produksi dialog penuh sesuai aturan di atas.\n"
    "8. Baris PALING ATAS wajib: 'Tema: <ringkasan singkat temanya, boleh "
    "disesuaikan ke versi yang cocok dengan CONTEXT>'. Setelah itu baris "
    "kosong, lalu dialog A/B.\n"
    "9. Setelah dialog selesai, tambahkan satu baris kosong lalu baris "
    "rangkuman: 'Materi: <daftar kata/frasa dari CONTEXT yang dipakai>'.\n"
    "Konteks: user meminta contoh percakapan bahasa {language_name} dengan "
    "tema '{theme}'."
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

        theme = random.choice(_THEMES)
        system = _SYSTEM_PROMPT_TEMPLATE.format(
            language_name=language.name, theme=theme
        )
        user = self._build_user_prompt(context, theme)
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
    def _build_user_prompt(context: dict, theme: str) -> str:
        """Susun prompt user: blok CONTEXT + tema + permintaan generate dialog."""
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
        lines.append(f"Tema percakapan yang harus diangkat: {theme}")
        lines.append("")
        lines.append(
            "Pesan user: buatkan satu contoh dialog tanya-jawab (MIN 3, MAKS 5 "
            "kali tanya-jawab) antara 2 orang (A & B) memakai CONTEXT di atas "
            "dan sesuai tema. Baris pertama wajib 'Tema: ...', baris terakhir "
            "wajib 'Materi: ...'."
        )
        return "\n".join(lines)
