"""Model SQLAlchemy Basa.id — 8 tabel inti.

    users               — user dari berbagai platform (telegram/whatsapp)
    languages           — bahasa yang diajarkan (batak/jawa/sunda/dll.)
    words               — kosakata per bahasa
    phrases             — percakapan sehari-hari per bahasa (Langkah 8)
    grammar_rules       — aturan grammar dasar per bahasa (Langkah 8)
    user_word_progress  — pelacakan penguasaan kosakata per user
    quiz_results        — riwayat skor kuis per user
    quiz_sessions       — sesi kuis interaktif yang sedang berjalan (Langkah 8)

Kolom disimpan sebagai String (bukan enum native) supaya portabel antara
SQLite dan PostgreSQL tanpa migrasi khusus.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basa.db.engine import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Platform(StrEnum):
    """Platform tempat user berinteraksi dengan bot."""

    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    CONSOLE = "console"  # simulator lokal untuk development/testing


class ProgressStatus(StrEnum):
    """Status penguasaan kosakata oleh user."""

    NEW = "new"
    LEARNING = "learning"
    MASTERED = "mastered"


class User(Base):
    """Satu baris per (platform, platform_user_id)."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("platform", "platform_user_id", name="uq_users_platform_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), index=True)
    platform_user_id: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    progress: Mapped[list["UserWordProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    quiz_results: Mapped[list["QuizResult"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    quiz_sessions: Mapped[list["QuizSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Language(Base):
    """Bahasa daerah yang diajarkan (kode ISO 639-3: bbc, jv, su)."""

    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))

    words: Mapped[list["Word"]] = relationship(back_populates="language", cascade="all, delete-orphan")
    phrases: Mapped[list["Phrase"]] = relationship(back_populates="language", cascade="all, delete-orphan")
    grammar_rules: Mapped[list["GrammarRule"]] = relationship(
        back_populates="language", cascade="all, delete-orphan"
    )


class Word(Base):
    """Kosakata milik satu bahasa."""

    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("language_id", "term", "part_of_speech", name="uq_words_lang_term_pos"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    term: Mapped[str] = mapped_column(String(255), index=True)
    translation: Mapped[str] = mapped_column(Text)
    part_of_speech: Mapped[str] = mapped_column(String(50))
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    language: Mapped["Language"] = relationship(back_populates="words")
    progress: Mapped[list["UserWordProgress"]] = relationship(back_populates="word", cascade="all, delete-orphan")


class Phrase(Base):
    """Frasa percakapan sehari-hari milik satu bahasa."""

    __tablename__ = "phrases"
    __table_args__ = (
        UniqueConstraint("language_id", "phrase", "context", name="uq_phrases_lang_phrase_context"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    phrase: Mapped[str] = mapped_column(Text, index=True)
    translation: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(String(50), default="")  # greeting/food/travel/dll.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    language: Mapped["Language"] = relationship(back_populates="phrases")


class GrammarRule(Base):
    """Aturan grammar dasar milik satu bahasa."""

    __tablename__ = "grammar_rules"
    __table_args__ = (
        UniqueConstraint("language_id", "title", name="uq_grammar_lang_title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    language: Mapped["Language"] = relationship(back_populates="grammar_rules")


class UserWordProgress(Base):
    """Status penguasaan satu kosakata oleh satu user."""

    __tablename__ = "user_word_progress"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_progress_user_word"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=ProgressStatus.NEW.value, index=True)
    review_count: Mapped[int] = mapped_column(default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="progress")
    word: Mapped["Word"] = relationship(back_populates="progress")


class QuizSession(Base):
    """Satu sesi kuis interaktif yang sedang berjalan.

    Pertanyaan disimpan sebagai JSON (list dict) supaya soal yang sama
    ditampilkan ulang sampai user menjawab — portabel ke PostgreSQL
    (kolom Text, bukan tipe JSON native).
    """

    __tablename__ = "quiz_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    quiz_type: Mapped[str] = mapped_column(String(50), default="vocabulary")
    current_index: Mapped[int] = mapped_column(default=0)
    score: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=5)
    questions_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | finished
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="quiz_sessions")
    language: Mapped["Language"] = relationship()


class QuizResult(Base):
    """Satu riwayat kuis (skor + total soal) per user."""

    __tablename__ = "quiz_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    quiz_type: Mapped[str] = mapped_column(String(50))  # vocabulary | conversation | grammar
    score: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="quiz_results")
    language: Mapped["Language"] = relationship()
