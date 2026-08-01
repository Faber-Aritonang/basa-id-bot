"""Test parser Kaikki: parsing, filtering, normalisasi, dedupe."""

import json

from basa.data.kaikki import dedupe_words, parse_line, to_project_word


def _line(word: str, pos: str, glosses: list[str], tags: list[str] | None = None, alt_of=None) -> str:
    sense: dict = {"glosses": glosses}
    if tags:
        sense["tags"] = tags
    if alt_of is not None:
        sense["alt_of"] = alt_of
    return json.dumps({"word": word, "pos": pos, "lang_code": "jv", "senses": [sense]})


def test_parse_simple_noun():
    entry = parse_line(_line("sun", "noun", ["a kiss"]))
    assert entry is not None
    assert entry.term == "sun"
    assert entry.pos == "noun"
    assert entry.glosses == ["a kiss"]


def test_skip_romanization():
    assert parse_line(_line("bot", "romanization", ["romanization of ꦧꦺꦴꦠ꧀"], ["alt-of", "romanization"])) is None
    # aman juga: pos romanization tapi tanpa tags
    assert parse_line(_line("bot", "romanization", ["x"])) is None


def test_skip_entry_without_glosses():
    line = json.dumps({"word": "x", "pos": "noun", "lang_code": "jv", "senses": [{"tags": ["no-gloss"]}]})
    assert parse_line(line) is None


def test_skip_alt_of_sense():
    entry = parse_line(_line("bot", "noun", ["x"], alt_of=[{"word": "asal"}]))
    assert entry is None


def test_skip_empty_term():
    assert parse_line(_line("  ", "noun", ["a kiss"])) is None
    assert parse_line(_line("[[ ]]", "noun", ["a kiss"])) is None


def test_clean_markup_from_term_and_gloss():
    entry = parse_line(_line("{{l|jv|sapa}}", "noun", ["to greet [[someone]] <i>politely</i>"]))
    assert entry is not None
    assert entry.term == "sapa"
    assert entry.glosses == ["to greet someone politely"]


def test_keep_word_inside_wiktionary_link_template():
    # {{l|jv|mangan}} di gloss adalah link → kata "mangan" harus dipertahankan
    entry = parse_line(_line("mangan", "verb", ["{{l|jv|mangan}} means to eat"]))
    assert entry is not None
    assert entry.glosses == ["mangan means to eat"]


def test_remove_other_templates_but_keep_surrounding_text():
    entry = parse_line(_line("ora", "adv", ["not; {{rfv-sense}} really"]))
    assert entry is not None
    assert entry.glosses == ["not; really"]


def test_keep_word_in_template_with_named_args():
    # {{l|jv|mangan|t=to eat}} — argumen bernama tidak boleh menghilangkan kata
    entry = parse_line(_line("mangan", "verb", ["{{l|jv|mangan|t=to eat}} is the verb"]))
    assert entry is not None
    assert entry.glosses == ["mangan is the verb"]


def test_pos_abbreviation_normalized():
    entry = parse_line(_line("lama", "adj", ["old"]))
    assert entry is not None
    word = to_project_word(entry)
    assert word["part_of_speech"] == "adjective"


def test_particle_is_kept():
    entry = parse_line(_line("ta", "particle", ["question particle"]))
    assert entry is not None
    assert entry.term == "ta"


def test_skip_empty_or_broken_lines():
    assert parse_line("") is None
    assert parse_line("  ") is None
    assert parse_line("not-json{") is None


def test_to_project_word_joins_multiple_glosses():
    entry = parse_line(_line("mangan", "verb", ["to eat", "to consume"]))
    assert entry is not None
    word = to_project_word(entry)
    assert word["term"] == "mangan"
    assert word["translation"] == "to eat; to consume"
    assert word["part_of_speech"] == "verb"
    assert word["example"] is None


def test_dedupe_words_keeps_first():
    words = [
        {"term": "a", "part_of_speech": "noun", "translation": "1"},
        {"term": "a", "part_of_speech": "noun", "translation": "2"},  # duplikat
        {"term": "a", "part_of_speech": "verb", "translation": "3"},  # beda pos → bukan duplikat
    ]
    result = dedupe_words(words)
    assert len(result) == 2
    assert result[0]["translation"] == "1"
