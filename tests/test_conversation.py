"""Test layanan percakapan (Langkah 8, fitur #2) dengan database in-memory."""

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.messages import UserMessage
from basa.core.router import Router
from basa.core.services.conversation import ConversationService
from basa.db.engine import Base
from basa.db.models import Phrase
from basa.db.repositories import LanguageRepository


@pytest.fixture()
def router() -> Router:
    """Router dengan DB in-memory: bahasa batak (2 frasa) & jawa (1 frasa)."""
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
                Phrase(language_id=bbc.id, phrase="Horas!", translation="Halo", context="greeting"),
                Phrase(language_id=bbc.id, phrase="Mauliate.", translation="Terima kasih", context="politeness"),
                Phrase(language_id=jv.id, phrase="Piye kabare?", translation="Apa kabar?", context="greeting"),
            ]
        )
        session.commit()
    return Router(session_factory=factory)


def test_random_phrase_returns_one_phrase(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/frase batak"))
    assert "Horas!" in reply.text or "Mauliate." in reply.text
    assert "→" in reply.text  # ada terjemahan


def test_random_phrase_default_jawa(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/frase"))
    assert "Piye kabare?" in reply.text


def test_random_phrase_includes_context(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/frase batak"))
    assert "Konteks:" in reply.text


def test_random_phrase_unknown_language(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/frase klingon"))
    assert "klingon" in reply.text
    assert "belum tersedia" in reply.text


def test_random_phrase_empty_language():
    """Bahasa tanpa frasa → pesan jelas (bukan crash)."""
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

    service = ConversationService(session=factory())
    reply = service.random_phrase("sunda")
    assert "masih kosong" in reply.text


def test_help_lists_frase_command(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/help"))
    assert "/frase" in reply.text
