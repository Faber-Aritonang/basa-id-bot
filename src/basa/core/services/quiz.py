"""Layanan kuis interaktif — fitur #4 Basa.id.

Menggantikan placeholder `VocabularyService.quiz` yang dulu mencatat skor 0
sebelum user menjawab. Kuis sungguhan: satu sesi per user di tabel
`quiz_sessions`, pertanyaan diajukan satu per satu, jawaban diverifikasi,
dan skor asli tercatat ke `quiz_results` saat kuis tuntas.

Desain lintas-platform:
- 3 opsi jawaban per soal (batas tombol interaktif WhatsApp),
- jawaban dikirim sebagai teks angka (1-3) ATAU tombol (callback/reply id),
  jadi flow yang sama bekerja di Telegram, WhatsApp, dan console.
"""

from __future__ import annotations

import json
import random

from sqlalchemy.orm import Session

from basa.core.languages import resolve_code
from basa.core.messages import BotReply, Button
from basa.db.models import Platform, QuizSession
from basa.db.repositories import (
    LanguageRepository,
    QuizRepository,
    QuizSessionRepository,
    UserRepository,
    WordRepository,
)

#: Jumlah opsi jawaban per soal — sama dengan batas 3 tombol WhatsApp.
OPTION_COUNT = 3
#: Jumlah soal per kuis.
QUESTION_COUNT = 5
#: Kata kunci untuk membatalkan kuis yang sedang berjalan.
STOP_WORDS = {"stop", "berhenti", "batal", "selesai"}


class QuizService:
    """Kuis interaktif: mulai sesi, terima jawaban, laporkan skor akhir."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.languages = LanguageRepository(session)
        self.words = WordRepository(session)
        self.sessions = QuizSessionRepository(session)
        self.quizzes = QuizRepository(session)

    # --- perintah utama ---

    def start(self, alias: str = "jawa", user_id: str | None = None, platform: Platform | None = None) -> BotReply:
        """Mulai kuis baru: susun 5 soal dari kosakata acak bahasa tertentu."""
        language = self.languages.get_by_code(resolve_code(alias))
        if language is None:
            return BotReply(f"Bahasa '{alias}' belum tersedia. Coba /bahasa.")

        if self.words.count_by_language(language.id) < QUESTION_COUNT:
            return BotReply(
                f"Kosakata bahasa ini belum cukup untuk kuis (butuh ≥{QUESTION_COUNT} kata)."
            )

        if user_id is None or platform is None:
            return BotReply("Kuis butuh identitas user — coba lewat bot ya.")

        questions = self._build_questions(language.id)
        user = self.users.get_or_create(platform, user_id)
        session_row = self.sessions.create(user.id, language.id, "vocabulary", questions)
        return self._question_reply(session_row, questions)

    def answer(self, user_id: str, platform: Platform, text: str) -> BotReply | None:
        """Proses jawaban kuis aktif. None jika user tidak sedang kuis.

        Router memanggil method ini untuk setiap pesan NON-command; bila
        hasilnya None, pesan diperlakukan seperti biasa (hint bantuan).
        """
        user = self.users.find(platform, user_id)
        if user is None:
            return None
        session_row = self.sessions.get_active(user.id)
        if session_row is None:
            return None

        questions = json.loads(session_row.questions_json)
        raw = text.strip().lower()

        if raw in STOP_WORDS:
            self.sessions.close(session_row)
            return BotReply("Kuis dibatalkan. Ketik /kuis <bahasa> untuk mulai lagi ya! 👋")

        question = questions[session_row.current_index]
        # Rentang valid mengikuti jumlah opsi soal — sinkron dengan prompt.
        valid_answers = {str(i) for i in range(1, len(question["options"]) + 1)}
        if raw not in valid_answers:
            last = len(question["options"])
            return BotReply(
                f"Jawab dengan angka 1-{last} ya, atau ketik 'stop' untuk berhenti. 😊"
            )

        correct = int(raw) - 1 == question["correct"]
        if correct:
            session_row.score += 1
        session_row.current_index += 1

        feedback = self._feedback(question, correct)
        if session_row.current_index >= session_row.total:
            return self._finish(session_row, user.id, feedback)
        return self._next_reply(session_row, questions, feedback)

    # --- pembangun soal ---

    def _build_questions(self, language_id: int) -> list[dict]:
        """5 soal acak: 1 kata + 3 opsi terjemahan (1 benar, 2 pengecoh)."""
        pool = self.words.get_random(language_id, limit=20)

        questions: list[dict] = []
        for word in pool[:QUESTION_COUNT]:
            distractors = [
                other.translation
                for other in pool
                if other.id != word.id and other.translation != word.translation
            ]
            options = self._pick_options(word.translation, distractors)
            questions.append(
                {
                    "term": word.term,
                    "pos": word.part_of_speech,
                    "translation": word.translation,
                    "options": options,
                    "correct": options.index(word.translation),
                }
            )
        return questions

    @staticmethod
    def _pick_options(correct: str, distractors: list[str]) -> list[str]:
        """3 opsi unik: jawaban benar + 2 pengecoh (acak)."""
        uniq = list(dict.fromkeys(d for d in distractors if d != correct))
        random.shuffle(uniq)
        options = [correct] + uniq[: OPTION_COUNT - 1]
        random.shuffle(options)
        return options

    # --- rendering ---

    def _question_text(self, session_row: QuizSession, questions: list[dict]) -> str:
        question = questions[session_row.current_index]
        options = "\n".join(f"  {i}. {opt}" for i, opt in enumerate(question["options"], start=1))
        # Rentang angka mengikuti jumlah opsi sebenarnya (robust jika < 3 opsi).
        last = len(question["options"])
        return (
            f"🧠 *Kuis Basa.id* — soal {session_row.current_index + 1}/{session_row.total}\n"
            f"Apa arti dari *{question['term']}* ({question['pos']})?\n"
            f"{options}\n\n"
            f"Balas dengan angka 1-{last}, atau ketik 'stop' untuk berhenti."
        )

    def _question_reply(self, session_row: QuizSession, questions: list[dict]) -> BotReply:
        question = questions[session_row.current_index]
        buttons = [
            Button(f"{i}. {opt}", str(i))
            for i, opt in enumerate(question["options"], start=1)
        ]
        return BotReply(self._question_text(session_row, questions), buttons=buttons)

    def _next_reply(self, session_row: QuizSession, questions: list[dict], feedback: str) -> BotReply:
        """Feedback jawaban + pertanyaan berikutnya (dengan tombol)."""
        next_reply = self._question_reply(session_row, questions)
        return BotReply(f"{feedback}\n\n{next_reply.text}", buttons=next_reply.buttons)

    @staticmethod
    def _feedback(question: dict, correct: bool) -> str:
        if correct:
            return f"✅ Benar! *{question['term']}* = *{question['translation']}*"
        return f"❌ Belum tepat. *{question['term']}* = *{question['translation']}*"

    def _finish(self, session_row: QuizSession, user_id: int, feedback: str) -> BotReply:
        """Kuis tuntas: catat skor asli ke quiz_results + tampilkan ringkasan."""
        self.sessions.close(session_row)
        self.quizzes.record_result(
            user_id, session_row.language_id, session_row.quiz_type,
            score=session_row.score, total=session_row.total,
        )
        best = self.quizzes.best_score(user_id, session_row.language_id, session_row.quiz_type)
        best_line = f"\n🏆 Skor terbaik: {best.score}/{best.total}" if best else ""
        return BotReply(
            f"🎉 *Kuis selesai!*\n{feedback}\n\n"
            f"Skor kamu: *{session_row.score}/{session_row.total}*{best_line}\n\n"
            "Ketik /kuis <bahasa> untuk coba lagi!"
        )
