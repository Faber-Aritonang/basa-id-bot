"""Test layer database: engine, model, repository, tracking progres."""

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from basa.db import models  # noqa: F401  # daftarkan model
from basa.db.engine import Base, _normalize_postgres_url, create_db_engine
from basa.db.models import Language, Platform, ProgressStatus, Word
from basa.db.repositories import (
    LanguageRepository,
    ProgressRepository,
    QuizRepository,
    UserRepository,
    WordRepository,
)


@pytest.fixture()
def session() -> Session:
    """Session SQLite in-memory yang bersih per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)( ) as s:
        yield s
    engine.dispose()


@pytest.fixture()
def seeded(session: Session) -> int:
    """Seed 1 bahasa + 2 kata; mengembalikan language_id."""
    language = LanguageRepository(session).get_or_create("jv", "Javanese")
    session.add_all(
        [
            Word(language_id=language.id, term="sun", translation="a kiss", part_of_speech="noun"),
            Word(language_id=language.id, term="mangan", translation="to eat", part_of_speech="verb"),
        ]
    )
    session.commit()
    return language.id


def test_engine_from_settings_default():
    engine = create_db_engine()
    assert engine.dialect.name == "sqlite"


def test_normalize_postgres_url_adds_psycopg_driver():
    """URL Postgres tanpa driver (gaya Render) dinormalisasi ke psycopg3."""
    assert (
        _normalize_postgres_url("postgres://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    assert (
        _normalize_postgres_url("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )


def test_normalize_postgres_url_keeps_existing_driver_and_sqlite():
    """URL yang sudah ber-driver dan SQLite tidak diubah."""
    assert (
        _normalize_postgres_url("postgresql+psycopg://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    assert (
        _normalize_postgres_url("sqlite:///data/basa.db")
        == "sqlite:///data/basa.db"
    )


def test_get_or_create_user(session: Session):
    repo = UserRepository(session)
    first = repo.get_or_create(Platform.TELEGRAM, "12345", display_name="Budi")
    session.commit()
    again = repo.get_or_create(Platform.TELEGRAM, "12345")
    assert first.id == again.id
    # Platform berbeda → user berbeda
    other = repo.get_or_create(Platform.WHATSAPP, "12345")
    assert other.id != first.id


def test_language_repository(session: Session):
    repo = LanguageRepository(session)
    lang = repo.get_or_create("bbc", "Batak Toba")
    session.commit()
    assert repo.get_by_code("bbc") is lang
    assert len(repo.list_all()) == 1
    # idempoten
    assert repo.get_or_create("bbc", "Batak Toba").id == lang.id


def test_word_repository_random(session: Session, seeded: int):
    repo = WordRepository(session)
    words = repo.get_random(seeded, limit=2)
    assert len(words) == 2
    assert all(w.language_id == seeded for w in words)
    assert repo.count_by_language(seeded) == 2


def test_progress_tracking_flow(session: Session, seeded: int):
    user = UserRepository(session).get_or_create(Platform.TELEGRAM, "u1")
    word = WordRepository(session).get_random(seeded, limit=1)[0]
    session.commit()

    repo = ProgressRepository(session)
    progress = repo.record_review(user.id, word.id, ProgressStatus.LEARNING)
    session.commit()
    assert progress.review_count == 1
    assert progress.last_reviewed_at is not None

    # Review kedua → status naik, review_count bertambah
    repo.record_review(user.id, word.id, ProgressStatus.MASTERED)
    session.commit()
    stats = repo.stats(user.id)
    assert stats[ProgressStatus.LEARNING.value] == 0
    assert stats[ProgressStatus.MASTERED.value] == 1


def test_progress_stats_zero_for_new_user(session: Session, seeded: int):
    user = UserRepository(session).get_or_create(Platform.WHATSAPP, "u2")
    session.commit()
    stats = ProgressRepository(session).stats(user.id)
    assert stats == {status.value: 0 for status in ProgressStatus}


def test_quiz_repository(session: Session, seeded: int):
    user = UserRepository(session).get_or_create(Platform.TELEGRAM, "u3")
    repo = QuizRepository(session)
    repo.record_result(user.id, seeded, "vocabulary", score=8, total=10)
    repo.record_result(user.id, seeded, "vocabulary", score=10, total=10)
    session.commit()
    best = repo.best_score(user.id, seeded, "vocabulary")
    assert best is not None
    assert best.score == 10


def test_unique_user_platform(session: Session):
    from sqlalchemy.exc import IntegrityError

    repo = UserRepository(session)
    repo.get_or_create(Platform.TELEGRAM, "dup")
    session.commit()
    # insert langsung duplikat harus ditolak oleh constraint
    session.add(models.User(platform="telegram", platform_user_id="dup"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_alembic_migration_creates_all_tables(tmp_path):
    """Gate Langkah 3: jalankan migrasi Alembic ke SQLite kosong.

    Memverifikasi `basa db upgrade` (alembic upgrade head) membuat kelima
    tabel + berfungsi untuk database baru — simulasikan ganti DB ke Postgres.
    """
    import os
    import subprocess
    import sys
    from pathlib import Path as P

    db_file = tmp_path / "test_migrate.db"
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{db_file}")
    root = P(__file__).resolve().parents[1]
    # Jalankan lewat CLI aplikasi (`basa db upgrade`) supaya path migrations di
    # cli.py ikut teruji, bukan hanya mekanisme alembic-nya.
    result = subprocess.run(
        [sys.executable, "-m", "basa", "db", "upgrade"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    from sqlalchemy import create_engine, inspect

    inspector = inspect(create_engine(f"sqlite:///{db_file}"))
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "languages",
        "words",
        "user_word_progress",
        "quiz_results",
        "quiz_sessions",
        "phrases",
        "grammar_rules",
    } <= tables


def test_language_is_seeded_from_data_files():
    """Sanity: data hasil impor Kaikki memuat setidaknya 1 bahasa."""
    import json
    from pathlib import Path

    data_dir = Path(__file__).resolve().parents[1] / "data"
    jawa = json.loads((data_dir / "jawa" / "jawa.json").read_text(encoding="utf-8"))
    assert jawa["language"]["code"] == "jv"
    assert len(jawa["words"]) > 3000
