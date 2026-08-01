"""Test loader data: validasi skema & seed idempoten."""

import json
from pathlib import Path

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from basa.db.engine import Base
from basa.db.models import Language
from basa.db.repositories import LanguageRepository, WordRepository
from basa.data.loaders import load_language_file, seed_data_dir, seed_language_file


@pytest.fixture()
def session() -> Session:
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
def sample_file(tmp_path: Path) -> Path:
    """File data valid sederhana untuk test."""
    payload = {
        "language": {"code": "bbc", "name": "Batak Toba"},
        "license": "public domain",
        "words": [
            {"term": "horas", "translation": "salam", "part_of_speech": "interjection"},
            {"term": "mangan", "translation": "makan", "part_of_speech": "verb", "example": "Mangan ma hita."},
        ],
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_language_file_valid(sample_file: Path):
    payload = load_language_file(sample_file)
    assert payload["language"]["code"] == "bbc"
    assert len(payload["words"]) == 2


def test_load_language_file_missing_language(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"words": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_language_file(path)


def test_load_language_file_missing_word_field(tmp_path: Path):
    path = tmp_path / "bad2.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "words": [{"term": "horas"}],  # tanpa translation & part_of_speech
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_language_file(path)


def test_seed_language_file_is_idempotent(session: Session, sample_file: Path):
    first = seed_language_file(session, sample_file)
    second = seed_language_file(session, sample_file)  # dijalankan ulang
    assert first == {"words": 2}
    assert second == {"words": 0}  # tidak menduplikasi
    assert WordRepository(session).count_by_language(1) == 2


def test_seed_data_dir(session: Session, tmp_path: Path):
    # buat folder data/latihan_tes/ dengan 1 file
    folder = tmp_path / "latihan_tes"
    folder.mkdir()
    (folder / "x.json").write_text(
        json.dumps(
            {
                "language": {"code": "xx", "name": "Tes"},
                "words": [{"term": "a", "translation": "b", "part_of_speech": "noun"}],
            }
        ),
        encoding="utf-8",
    )
    results = seed_data_dir(session, tmp_path)
    assert len(results) == 1
    assert LanguageRepository(session).get_by_code("xx") is not None


def test_load_language_file_phrases_only(tmp_path: Path):
    """File boleh hanya berisi frasa (tanpa words)."""
    path = tmp_path / "phrases.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "phrases": [{"phrase": "Horas!", "translation": "Halo", "context": "greeting"}],
            }
        ),
        encoding="utf-8",
    )
    payload = load_language_file(path)
    assert payload["phrases"][0]["phrase"] == "Horas!"


def test_load_language_file_missing_both(tmp_path: Path):
    """File tanpa words DAN tanpa phrases → error."""
    path = tmp_path / "bad3.json"
    path.write_text(
        json.dumps({"language": {"code": "bbc", "name": "Batak Toba"}, "words": [], "phrases": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_language_file(path)


def test_load_language_file_missing_phrase_field(tmp_path: Path):
    """Frasa tanpa field translation → error."""
    path = tmp_path / "bad4.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "phrases": [{"phrase": "Horas!"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_language_file(path)


def test_seed_phrases_idempotent(session: Session, tmp_path: Path):
    """Seed frasa idempoten: dijalankan ulang tidak menduplikasi."""
    from basa.db.repositories import PhraseRepository

    path = tmp_path / "phrases.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "phrases": [
                    {"phrase": "Horas!", "translation": "Halo", "context": "greeting"},
                    {"phrase": "Mauliate.", "translation": "Terima kasih"},
                ],
            }
        ),
        encoding="utf-8",
    )
    first = seed_language_file(session, path)
    second = seed_language_file(session, path)
    assert first == {"phrases": 2}
    assert second == {"phrases": 0}
    language = LanguageRepository(session).get_by_code("bbc")
    assert PhraseRepository(session).count_by_language(language.id) == 2


def test_load_language_file_grammar_only(tmp_path: Path):
    """File boleh hanya berisi grammar (tanpa words/phrases)."""
    path = tmp_path / "grammar.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "grammar": [{"title": "Partikel do", "explanation": "Menegaskan."}],
            }
        ),
        encoding="utf-8",
    )
    payload = load_language_file(path)
    assert payload["grammar"][0]["title"] == "Partikel do"


def test_load_language_file_missing_grammar_field(tmp_path: Path):
    """Aturan grammar tanpa explanation → error."""
    path = tmp_path / "bad5.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "grammar": [{"title": "Partikel do"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_language_file(path)


def test_seed_grammar_idempotent(session: Session, tmp_path: Path):
    """Seed grammar idempoten: dijalankan ulang tidak menduplikasi."""
    from basa.db.repositories import GrammarRepository

    path = tmp_path / "grammar.json"
    path.write_text(
        json.dumps(
            {
                "language": {"code": "bbc", "name": "Batak Toba"},
                "grammar": [
                    {"title": "Partikel do", "explanation": "Menegaskan."},
                    {"title": "Kata ganti", "explanation": "au, ho, ibana."},
                ],
            }
        ),
        encoding="utf-8",
    )
    first = seed_language_file(session, path)
    second = seed_language_file(session, path)
    assert first == {"grammar": 2}
    assert second == {"grammar": 0}
    language = LanguageRepository(session).get_by_code("bbc")
    assert GrammarRepository(session).count_by_language(language.id) == 2
