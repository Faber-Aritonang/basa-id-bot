"""Test Router + VocabularyService dengan database in-memory."""

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from basa.core.messages import UserMessage
from basa.core.router import Router
from basa.db.engine import Base
from basa.db.models import Word
from basa.db.repositories import LanguageRepository, WordRepository


@pytest.fixture()
def router() -> Router:
    """Router dengan DB in-memory berisi bahasa jawa (2 kata) & batak (1 kata)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        lang = LanguageRepository(session).get_or_create("jv", "Javanese")
        session.add_all(
            [
                Word(language_id=lang.id, term="sun", translation="a kiss", part_of_speech="noun", example="Sun ati", example_translation="Ciuman sayang"),
                Word(language_id=lang.id, term="mangan", translation="to eat", part_of_speech="verb"),
            ]
        )
        bbc = LanguageRepository(session).get_or_create("bbc", "Batak Toba")
        session.add(Word(language_id=bbc.id, term="horas", translation="salam", part_of_speech="interjection"))
        session.commit()
    return Router(session_factory=factory)


def test_help(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/help"))
    assert "Basa.id" in reply.text
    assert "/kata" in reply.text


def test_start(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/start"))
    assert "Basa.id" in reply.text


def test_list_languages(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/bahasa"))
    assert "jv" in reply.text and "Javanese" in reply.text
    assert "bbc" in reply.text


def test_random_word_default_jawa(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kata"))
    assert "sun" in reply.text or "mangan" in reply.text


def test_random_word_specific_language(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kata batak"))
    assert "horas" in reply.text


def test_random_word_unknown_language(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kata klingon"))
    assert "klingon" in reply.text


def test_command_with_bot_username(router: Router):
    """Telegram menambahkan @BotName pada command → harus tetap dikenali."""
    reply = router.handle(UserMessage(user_id="u1", text="/kata@BasaIdBot batak"))
    assert "horas" in reply.text


def test_mark_mastered(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuasai mangan"))
    assert "mangan" in reply.text
    # verifikasi tersimpan di DB via progres
    reply2 = router.handle(UserMessage(user_id="u1", text="/progres"))
    assert "Dikuasai: 1" in reply2.text


def test_mark_mastered_unknown_word(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuasai zebra"))
    assert "tidak ditemukan" in reply.text


def test_progress_empty(router: Router):
    reply = router.handle(UserMessage(user_id="fresh-user", text="/progres"))
    assert "belum belajar" in reply.text


def test_quiz_not_enough_words(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuis batak"))
    assert "belum cukup" in reply.text


def test_unknown_command(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/xyz"))
    assert "belum dikenal" in reply.text


def test_non_command_message(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="halo apa kabar"))
    assert "/help" in reply.text


def test_empty_message(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="  "))
    assert "/help" in reply.text


def test_word_lookup_repository_language_scoped():
    """get_by_term dengan language_id membatasi pencarian."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        jv = LanguageRepository(session).get_or_create("jv", "Javanese")
        su = LanguageRepository(session).get_or_create("su", "Sundanese")
        session.add(Word(language_id=jv.id, term="mangan", translation="to eat", part_of_speech="verb"))
        session.add(Word(language_id=su.id, term="mangan", translation="to eat (sunda)", part_of_speech="verb"))
        session.commit()

        repo = WordRepository(session)
        jv_word = repo.get_by_term("MANGAN", language_id=jv.id)
        su_word = repo.get_by_term("mangan", language_id=su.id)
        assert jv_word is not None and jv_word.language_id == jv.id
        assert su_word is not None and su_word.language_id == su.id
        # tanpa language_id → mengembalikan yang pertama
        any_word = repo.get_by_term("mangan")
        assert any_word is not None
