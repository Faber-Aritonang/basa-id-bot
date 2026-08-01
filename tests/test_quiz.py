"""Test kuis interaktif (Langkah 8, fitur #4) dengan database in-memory.

Kuis berjalan multi-pesan: `/kuis <bahasa>` membuka sesi, jawaban (angka atau
tombol) diproses per pesan, skor asli tercatat di `quiz_results` saat tuntas.
"""

import json

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from basa.core.messages import UserMessage
from basa.core.router import Router
from basa.core.services.quiz import OPTION_COUNT, QUESTION_COUNT
from basa.db.engine import Base
from basa.db.models import Platform, Word
from basa.db.repositories import (
    LanguageRepository,
    QuizSessionRepository,
    UserRepository,
)

_WORDS = [
    ("sun", "a kiss", "noun"),
    ("mangan", "to eat", "verb"),
    ("ngombe", "to drink", "verb"),
    ("turu", "to sleep", "verb"),
    ("apik", "good", "adjective"),
]


@pytest.fixture()
def router() -> Router:
    """Router dengan DB in-memory: jawa (5 kata) & batak (1 kata)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        jv = LanguageRepository(session).get_or_create("jv", "Javanese")
        session.add_all(
            [Word(language_id=jv.id, term=t, translation=tr, part_of_speech=pos) for t, tr, pos in _WORDS]
        )
        bbc = LanguageRepository(session).get_or_create("bbc", "Batak Toba")
        session.add(Word(language_id=bbc.id, term="horas", translation="salam", part_of_speech="interjection"))
        session.commit()
    return Router(session_factory=factory)


def _active_session(router: Router) -> dict:
    """Baca sesi kuis aktif user 'u1' (console) → dict jawaban + soal sekarang."""
    with router._session_factory() as session:
        user = UserRepository(session).find(Platform.CONSOLE, "u1")
        row = QuizSessionRepository(session).get_active(user.id)
        questions = json.loads(row.questions_json)
        return {
            "row": row,
            "question": questions[row.current_index],
        }


def _answer_correct(router: Router, question: dict) -> str:
    """Angka jawaban yang benar untuk soal tertentu (1-based)."""
    return str(question["correct"] + 1)


def _answer_wrong(router: Router, question: dict) -> str:
    """Angka jawaban yang salah (bukan indeks benar)."""
    correct = question["correct"]
    return "1" if correct != 0 else "2"


# --- mulai kuis ---

def test_quiz_start_returns_first_question_with_buttons(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    assert "soal 1/5" in reply.text
    assert "Apa arti dari" in reply.text
    assert len(reply.buttons) == OPTION_COUNT  # 3 opsi (batas tombol WhatsApp)
    assert [b.callback_data for b in reply.buttons] == ["1", "2", "3"]


def test_quiz_start_default_jawa(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuis"))
    assert "soal 1/5" in reply.text


def test_quiz_start_unknown_language(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/kuis klingon"))
    assert "belum tersedia" in reply.text


def test_quiz_not_enough_words(router: Router):
    # batak hanya punya 1 kata → kuis tidak bisa dimulai
    reply = router.handle(UserMessage(user_id="u1", text="/kuis batak"))
    assert "belum cukup" in reply.text


# --- menjawab ---

def test_quiz_correct_answer_advances(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    question = _active_session(router)["question"]
    reply = router.handle(UserMessage(user_id="u1", text=_answer_correct(router, question)))
    assert "Benar" in reply.text
    assert "soal 2/5" in reply.text  # maju ke soal berikutnya


def test_quiz_wrong_answer_does_not_score(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    question = _active_session(router)["question"]
    reply = router.handle(UserMessage(user_id="u1", text=_answer_wrong(router, question)))
    assert "Belum tepat" in reply.text
    assert "soal 2/5" in reply.text


def test_quiz_invalid_answer_prompts_again(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    reply = router.handle(UserMessage(user_id="u1", text="halo"))
    assert "angka 1-3" in reply.text
    # soal belum berubah (index tetap 0, tidak maju)
    assert _active_session(router)["row"].current_index == 0


def test_quiz_stop_cancels_session(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    reply = router.handle(UserMessage(user_id="u1", text="stop"))
    assert "dibatalkan" in reply.text
    # sesi ditutup → jawaban berikutnya tidak lagi diproses sebagai kuis
    reply = router.handle(UserMessage(user_id="u1", text="1"))
    assert "/help" in reply.text


# --- selesai kuis ---

def test_quiz_complete_records_real_score(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    for _ in range(QUESTION_COUNT):
        question = _active_session(router)["question"]
        router.handle(UserMessage(user_id="u1", text=_answer_correct(router, question)))

    # Skor asli tersimpan — bukan lagi placeholder 0.
    with router._session_factory() as session:
        user = UserRepository(session).find(Platform.CONSOLE, "u1")
        from basa.db.models import QuizResult
        row = session.query(QuizResult).filter_by(user_id=user.id).first()
        assert row is not None
        assert row.score == QUESTION_COUNT  # semua dijawab benar
        assert row.total == QUESTION_COUNT
        assert row.quiz_type == "vocabulary"


def test_quiz_partial_score_recorded(router: Router):
    """Jawaban campuran benar/salah → skor sesuai jawaban sungguhan."""
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    for i in range(QUESTION_COUNT):
        question = _active_session(router)["question"]
        answer = _answer_correct(router, question) if i % 2 == 0 else _answer_wrong(router, question)
        router.handle(UserMessage(user_id="u1", text=answer))

    with router._session_factory() as session:
        user = UserRepository(session).find(Platform.CONSOLE, "u1")
        from basa.db.models import QuizResult
        row = session.query(QuizResult).filter_by(user_id=user.id).first()
        assert row is not None
        assert 0 < row.score < QUESTION_COUNT


def test_quiz_final_reply_shows_score(router: Router):
    router.handle(UserMessage(user_id="u1", text="/kuis jawa"))
    for _ in range(QUESTION_COUNT - 1):
        question = _active_session(router)["question"]
        router.handle(UserMessage(user_id="u1", text=_answer_correct(router, question)))
    question = _active_session(router)["question"]
    reply = router.handle(UserMessage(user_id="u1", text=_answer_correct(router, question)))
    assert "Kuis selesai" in reply.text
    assert f"{QUESTION_COUNT}/{QUESTION_COUNT}" in reply.text


def test_quiz_non_command_without_session_gets_help(router: Router):
    """Pesan bebas tanpa kuis aktif → hint bantuan (perilaku lama dipertahankan)."""
    reply = router.handle(UserMessage(user_id="u1", text="halo apa kabar"))
    assert "/help" in reply.text


def test_help_lists_kuis(router: Router):
    reply = router.handle(UserMessage(user_id="u1", text="/help"))
    assert "/kuis" in reply.text
