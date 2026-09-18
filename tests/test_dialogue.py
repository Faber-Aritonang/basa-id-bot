"""Test layanan percakapan (fitur /percakapan, LLM+RAG) dengan mock LLM + DB in-memory.

Memverifikasi: bahasa tak dikenal ditolak, balasan non-kosong, materi kosong
ditangani, dan konteks RAG benar-benar mengalir ke LLM (kata 'horas' yang
di-seed muncul di balasan mock yang memantulkan prompt user).
"""

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.services.dialogue import DialogueService
from basa.db.engine import Base
from basa.db.models import GrammarRule, Phrase, Word
from basa.db.repositories import LanguageRepository
from basa.llm.mock_adapter import MockLLMClient


@pytest.fixture()
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture()
def session_factory():
    """DB in-memory: batak (2 kata, 1 frasa, 1 grammar) & jawa (1 kata)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        bbc = LanguageRepository(session).get_or_create("bbc", "Batak Toba")
        jv = LanguageRepository(session).get_or_create("jv", "Javanese")
        session.add_all(
            [
                Word(
                    language_id=bbc.id,
                    term="horas",
                    translation="halo/salam",
                    part_of_speech="interjection",
                    example="Horas!",
                    example_translation="Halo!",
                ),
                Word(language_id=bbc.id, term="mangan", translation="makan", part_of_speech="verb"),
                Phrase(language_id=bbc.id, phrase="Horas!", translation="Halo", context="greeting"),
                GrammarRule(
                    language_id=bbc.id,
                    title="Sapaan",
                    explanation="Horas dipakai untuk menyapa.",
                    example="Horas!",
                    example_translation="Halo!",
                    level=1,
                ),
                Word(language_id=jv.id, term="mangan", translation="makan", part_of_speech="verb"),
            ]
        )
        session.commit()
    return factory


def test_percakapan_unknown_language(session_factory, mock_llm):
    with session_factory() as session:
        svc = DialogueService(session, mock_llm)
        reply = svc.generate(alias="klingon")
    assert "klingon" in reply.text
    assert "belum tersedia" in reply.text


def test_percakapan_returns_dialogue(session_factory, mock_llm):
    with session_factory() as session:
        svc = DialogueService(session, mock_llm)
        reply = svc.generate(alias="batak")
    assert reply.text  # non-kosong
    assert "Mode mock" in reply.text  # penanda mock terlihat


def test_percakapan_uses_rag_context(session_factory, mock_llm):
    """Konteks RAG (kata 'horas') harus mengalir ke prompt -> muncul di balasan mock."""
    with session_factory() as session:
        svc = DialogueService(session, mock_llm)
        reply = svc.generate(alias="batak")
    # Mock memantulkan prompt user; kata 'horas' ada di blok CONTEXT.
    assert "horas" in reply.text.lower()


def test_percakapan_empty_language_returns_hint():
    """Bahasa tanpa materi -> pesan jelas (bukan crash)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    mock_llm = MockLLMClient()
    with factory() as session:
        LanguageRepository(session).get_or_create("su", "Sundanese")
        session.commit()
        svc = DialogueService(session, mock_llm)
        reply = svc.generate(alias="sunda")
    assert "kosong" in reply.text
