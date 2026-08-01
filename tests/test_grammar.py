"""Test layanan grammar (Langkah 8, fitur #3) dengan database in-memory."""

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.messages import UserMessage
from basa.core.router import Router
from basa.core.services.grammar import GrammarService
from basa.db.engine import Base
from basa.db.models import GrammarRule
from basa.db.repositories import LanguageRepository


@pytest.fixture()
def router() -> Router:
    """Router dengan DB in-memory: bahasa batak (2 aturan) & jawa (1 aturan)."""
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
                GrammarRule(language_id=bbc.id, title="Partikel 'do'", explanation="Menegaskan kata sebelumnya.", example="Au do.", example_translation="Sayalah.", level=1),
                GrammarRule(language_id=bbc.id, title="Kata ganti", explanation="au, ho, ibana.", level=1),
                GrammarRule(language_id=jv.id, title="Unggah-ungguh", explanation="ngoko vs krama.", level=1),
            ]
        )
        session.commit()
    return Router(session_factory=factory)


def test_random_rule_returns_one_rule(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/grammar batak"))
    assert "Partikel 'do'" in reply.text or "Kata ganti" in reply.text
    assert "Menegaskan" in reply.text or "au, ho" in reply.text


def test_random_rule_default_jawa(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/grammar"))
    assert "Unggah-ungguh" in reply.text


def test_random_rule_includes_level(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/grammar batak"))
    assert "Level: 1" in reply.text


def test_random_rule_unknown_language(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/grammar klingon"))
    assert "klingon" in reply.text
    assert "belum tersedia" in reply.text


def test_random_rule_empty_language():
    """Bahasa tanpa aturan grammar → pesan jelas (bukan crash)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        LanguageRepository(session).get_or_create("su", "Sundanese")
        session.commit()

    service = GrammarService(session=factory())
    reply = service.random_rule("sunda")
    assert "masih kosong" in reply.text


def test_help_lists_grammar_command(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/help"))
    assert "/grammar" in reply.text
