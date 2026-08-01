"""Repository pattern — akses data terpusat.

Services (di `basa.core`) memanggil repository ini, BUKAN query SQLAlchemy
langsung. Dengan begitu:
  - pemindahan SQLite → PostgreSQL tidak menyentuh logika bisnis
  - query mudah diuji dengan database in-memory
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from basa.db.models import (
    GrammarRule,
    Language,
    Phrase,
    Platform,
    ProgressStatus,
    QuizResult,
    QuizSession,
    User,
    UserWordProgress,
    Word,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRepository:
    """Akses tabel `users`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create(self, platform: Platform, platform_user_id: str, display_name: str | None = None) -> User:
        """Cari user; buat jika belum ada (commit dilakukan pemanggil)."""
        user = self.session.scalar(
            select(User).where(
                User.platform == platform.value,
                User.platform_user_id == platform_user_id,
            )
        )
        if user is None:
            user = User(
                platform=platform.value,
                platform_user_id=platform_user_id,
                display_name=display_name,
            )
            self.session.add(user)
            self.session.flush()
        return user

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def find(self, platform: Platform, platform_user_id: str) -> User | None:
        """Cari user tanpa membuat — None jika belum pernah terdaftar."""
        return self.session.scalar(
            select(User).where(
                User.platform == platform.value,
                User.platform_user_id == platform_user_id,
            )
        )


class LanguageRepository:
    """Akses tabel `languages`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_code(self, code: str) -> Language | None:
        return self.session.scalar(select(Language).where(Language.code == code))

    def get_or_create(self, code: str, name: str) -> Language:
        language = self.get_by_code(code)
        if language is None:
            language = Language(code=code, name=name)
            self.session.add(language)
            self.session.flush()
        return language

    def list_all(self) -> list[Language]:
        return list(self.session.scalars(select(Language).order_by(Language.code)))


class WordRepository:
    """Akses tabel `words`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, word_id: int) -> Word | None:
        return self.session.get(Word, word_id)

    def get_by_term(self, term: str, language_id: int | None = None) -> Word | None:
        """Cari kata berdasarkan term (case-insensitive).

        Jika `language_id` diberikan, pencarian dibatasi ke bahasa itu;
        jika None, kata pertama yang cocok dikembalikan.
        """
        query = select(Word).where(func.lower(Word.term) == term.strip().lower())
        if language_id is not None:
            query = query.where(Word.language_id == language_id)
        return self.session.scalar(query)

    def get_random(self, language_id: int, limit: int = 1) -> list[Word]:
        """Ambil N kata acak dari satu bahasa.

        `func.random()` tersedia di SQLite maupun PostgreSQL — portabel.
        """
        return list(
            self.session.scalars(
                select(Word)
                .where(Word.language_id == language_id)
                .order_by(func.random())
                .limit(limit)
            )
        )

    def count_by_language(self, language_id: int) -> int:
        return self.session.scalar(
            select(func.count(Word.id)).where(Word.language_id == language_id)
        ) or 0

    def bulk_add(self, language_id: int, words: list[dict]) -> int:
        """Tambah banyak kata sekaligus (seed data), idempoten.

        Kata yang sudah ada (term + part_of_speech yang sama untuk bahasa
        tersebut) dilewati. Mengembalikan jumlah kata yang benar-benar baru.
        """
        existing = set(
            self.session.execute(
                select(Word.term, Word.part_of_speech).where(Word.language_id == language_id)
            ).all()
        )
        to_add: list[Word] = []
        for w in words:
            key = (w["term"], w["part_of_speech"])
            if key in existing:
                continue
            existing.add(key)
            to_add.append(
                Word(
                    language_id=language_id,
                    term=w["term"],
                    translation=w["translation"],
                    part_of_speech=w["part_of_speech"],
                    example=w.get("example"),
                    example_translation=w.get("example_translation"),
                )
            )
        self.session.add_all(to_add)
        self.session.flush()
        return len(to_add)


class PhraseRepository:
    """Akses tabel `phrases` — percakapan sehari-hari per bahasa."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_random(self, language_id: int, limit: int = 1) -> list[Phrase]:
        """Ambil N frasa acak dari satu bahasa (portabel ke PostgreSQL)."""
        return list(
            self.session.scalars(
                select(Phrase)
                .where(Phrase.language_id == language_id)
                .order_by(func.random())
                .limit(limit)
            )
        )

    def count_by_language(self, language_id: int) -> int:
        return self.session.scalar(
            select(func.count(Phrase.id)).where(Phrase.language_id == language_id)
        ) or 0

    def bulk_add(self, language_id: int, phrases: list[dict]) -> int:
        """Tambah banyak frasa sekaligus (seed data), idempoten.

        Frasa yang sudah ada (phrase + context sama untuk bahasa tersebut)
        dilewati. Mengembalikan jumlah frasa yang benar-benar baru.
        """
        existing = set(
            self.session.execute(
                select(Phrase.phrase, Phrase.context).where(Phrase.language_id == language_id)
            ).all()
        )
        to_add: list[Phrase] = []
        for p in phrases:
            key = (p["phrase"], p.get("context", ""))
            if key in existing:
                continue
            existing.add(key)
            to_add.append(
                Phrase(
                    language_id=language_id,
                    phrase=p["phrase"],
                    translation=p["translation"],
                    context=p.get("context", ""),
                )
            )
        self.session.add_all(to_add)
        self.session.flush()
        return len(to_add)


class GrammarRepository:
    """Akses tabel `grammar_rules` — aturan grammar dasar per bahasa."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_random(self, language_id: int, limit: int = 1) -> list[GrammarRule]:
        """Ambil N aturan grammar acak dari satu bahasa (portabel ke PostgreSQL)."""
        return list(
            self.session.scalars(
                select(GrammarRule)
                .where(GrammarRule.language_id == language_id)
                .order_by(func.random())
                .limit(limit)
            )
        )

    def count_by_language(self, language_id: int) -> int:
        return self.session.scalar(
            select(func.count(GrammarRule.id)).where(GrammarRule.language_id == language_id)
        ) or 0

    def bulk_add(self, language_id: int, rules: list[dict]) -> int:
        """Tambah banyak aturan sekaligus (seed data), idempoten.

        Aturan dengan judul (title) sama untuk bahasa tersebut dilewati.
        Mengembalikan jumlah aturan yang benar-benar baru.
        """
        # `scalars()` mengembalikan nilai polos (bukan Row) — string dibandingkan
        # dengan string; pakai execute().all() akan menghasilkan set Row dan
        # pengecekan `title in existing` selalu False (duplikat di seed ulang).
        existing = set(
            self.session.scalars(
                select(GrammarRule.title).where(GrammarRule.language_id == language_id)
            )
        )
        to_add: list[GrammarRule] = []
        for r in rules:
            if r["title"] in existing:
                continue
            existing.add(r["title"])
            to_add.append(
                GrammarRule(
                    language_id=language_id,
                    title=r["title"],
                    explanation=r["explanation"],
                    example=r.get("example"),
                    example_translation=r.get("example_translation"),
                    level=r.get("level", 1),
                )
            )
        self.session.add_all(to_add)
        self.session.flush()
        return len(to_add)


class ProgressRepository:
    """Akses tabel `user_word_progress` — pelacakan penguasaan kosakata."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: int, word_id: int) -> UserWordProgress | None:
        return self.session.scalar(
            select(UserWordProgress).where(
                UserWordProgress.user_id == user_id,
                UserWordProgress.word_id == word_id,
            )
        )

    def record_review(self, user_id: int, word_id: int, status: ProgressStatus) -> UserWordProgress:
        """Catat review kosakata: buat baru / update status + hitung ulang."""
        progress = self.get(user_id, word_id)
        if progress is None:
            # review_count di-set eksplisit: default kolom baru berlaku saat INSERT,
            # sedangkan kita perlu nilainya sebelum flush untuk operasi += 1.
            progress = UserWordProgress(user_id=user_id, word_id=word_id, review_count=0)
            self.session.add(progress)
        progress.status = status.value
        progress.review_count += 1
        progress.last_reviewed_at = _utcnow()
        self.session.flush()
        return progress

    def stats(self, user_id: int) -> dict[str, int]:
        """Jumlah kosakata per status untuk satu user."""
        rows = self.session.execute(
            select(UserWordProgress.status, func.count(UserWordProgress.id))
            .where(UserWordProgress.user_id == user_id)
            .group_by(UserWordProgress.status)
        ).all()
        stats = {status.value: 0 for status in ProgressStatus}
        stats.update({status: count for status, count in rows})
        return stats


class QuizSessionRepository:
    """Akses tabel `quiz_sessions` — sesi kuis interaktif yang berjalan."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self, user_id: int) -> QuizSession | None:
        """Sesi kuis yang masih aktif untuk satu user (status='active')."""
        return self.session.scalar(
            select(QuizSession).where(
                QuizSession.user_id == user_id,
                QuizSession.status == "active",
            )
        )

    def create(self, user_id: int, language_id: int, quiz_type: str, questions: list[dict]) -> QuizSession:
        """Mulai sesi baru; sesi aktif lama ditutup dulu (satu kuis per user)."""
        active = self.get_active(user_id)
        if active is not None:
            active.status = "finished"
        session_row = QuizSession(
            user_id=user_id,
            language_id=language_id,
            quiz_type=quiz_type,
            total=len(questions),  # konsisten dengan jumlah soal, bukan default kolom
            questions_json=json.dumps(questions, ensure_ascii=False),
        )
        self.session.add(session_row)
        self.session.flush()
        return session_row

    def close(self, session_row: QuizSession) -> None:
        """Tandai sesi selesai (kuis tuntas atau dibatalkan)."""
        session_row.status = "finished"


class QuizRepository:
    """Akses tabel `quiz_results`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record_result(self, user_id: int, language_id: int, quiz_type: str, score: int, total: int) -> QuizResult:
        result = QuizResult(
            user_id=user_id,
            language_id=language_id,
            quiz_type=quiz_type,
            score=score,
            total=total,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def best_score(self, user_id: int, language_id: int, quiz_type: str) -> QuizResult | None:
        """Skor terbaik user untuk jenis kuis tertentu."""
        return self.session.scalar(
            select(QuizResult)
            .where(
                QuizResult.user_id == user_id,
                QuizResult.language_id == language_id,
                QuizResult.quiz_type == quiz_type,
            )
            .order_by(QuizResult.score.desc())
            .limit(1)
        )
