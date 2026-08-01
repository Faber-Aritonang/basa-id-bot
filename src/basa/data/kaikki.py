"""Parser data Kaikki.org (Wiktionary machine-readable) → format proyek Basa.id.

Struktur JSONL Kaikki per baris (lihat https://kaikki.org):
    {
      "word": "sun",
      "lang_code": "jv",
      "pos": "noun",
      "senses": [ { "glosses": ["a kiss"], "tags": [...], "alt_of": [...] } ],
      ...
    }

Modul ini murni transformasi data — tanpa I/O jaringan — sehingga mudah diuji.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# pos yang bukan kata sungguhan (romanisasi aksara, dll.) → dilewati.
# Catatan: "particle" sengaja TIDAK dilewati — partikel (ta, lah) adalah kata nyata.
SKIP_POS: frozenset[str] = frozenset(
    {
        "romanization",
        "transliteration",
        "punctuation",
        "character",
    }
)

# Tag sense yang menandakan entri "alt-of"/romanisasi → dilewati
SKIP_SENSE_TAGS: frozenset[str] = frozenset({"alt-of", "romanization"})

# Normalisasi part-of-speech: kode singkat wiktextract → nama lengkap proyek.
# Nilai yang tidak ada di peta ini tetap dipakai apa adanya (lowercase).
POS_NORMALIZE: dict[str, str] = {
    "adj": "adjective",
    "adv": "adverb",
    "num": "numeral",
    "pron": "pronoun",
    "intj": "interjection",
    "conj": "conjunction",
    "prep": "preposition",
    "det": "determiner",
    "phr": "phrase",
    "proverb": "proverb",
    "root": "root",
    "name": "proper name",
}

# Link wiki: jaga teks tampilan. `[[kiss]]` → `kiss`, `[[kiss|to kiss]]` → `to kiss`.
_LINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")

# Template link Wiktionary: `{{l|jv|sapa}}`/`{{m|jv|sapa}}` → `sapa` (jaga kata).
# Argumen bernama opsional (mis. `{{l|jv|mangan|t=to eat}}`) ikut dibuang.
_TEMPLATE_LINK_RE = re.compile(r"\{\{(?:l|m|lang)\|[^}|]+\|([^}|]+)(?:\|[^}]*)?\}\}")

# Template lain → hapus seluruhnya.
_TEMPLATE_RE = re.compile(r"\{\{.*?\}\}")

# Markup HTML/teks lain yang kadang tersisa.
_MARKUP_RE = re.compile(r"<[^>]+>|'''")


@dataclass
class KaikkiEntry:
    """Satu entri kamus hasil parsing (belum dinormalisasi)."""

    term: str
    pos: str
    lang_code: str
    glosses: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    """Bersihkan markup wiki/HTML dan whitespace berlebih."""
    cleaned = _LINK_RE.sub(r"\1", text)
    cleaned = _TEMPLATE_LINK_RE.sub(r"\1", cleaned)
    cleaned = _TEMPLATE_RE.sub("", cleaned)
    cleaned = _MARKUP_RE.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_line(line: str) -> KaikkiEntry | None:
    """Parse satu baris JSONL Kaikki menjadi KaikkiEntry.

    Mengembalikan None untuk baris kosong, rusak, atau yang harus difilter
    (romanization, tanpa gloss, term kosong, dll.).
    """
    line = line.strip()
    if not line:
        return None
    try:
        raw = json.loads(line)
    except json.JSONDecodeError:
        return None

    pos = str(raw.get("pos", "")).strip().lower()
    if not pos or pos in SKIP_POS:
        return None

    term = _clean(str(raw.get("word", "")))
    if not term:
        return None

    senses = raw.get("senses") or []
    glosses: list[str] = []
    for sense in senses:
        tags = set(sense.get("tags") or [])
        if tags & SKIP_SENSE_TAGS:
            continue
        if sense.get("alt_of"):
            continue
        for g in sense.get("glosses") or []:
            cleaned = _clean(g)
            if cleaned:
                glosses.append(cleaned)

    if not glosses:
        return None

    return KaikkiEntry(
        term=term,
        pos=pos,
        lang_code=str(raw.get("lang_code", "")).strip(),
        glosses=glosses,
    )


def to_project_word(entry: KaikkiEntry) -> dict:
    """Normalisasi KaikkiEntry menjadi format words[] proyek.

    Gloss digabung dengan "; " (sering ada beberapa arti). Contoh kalimat
    tidak tersedia di data Kaikki → None (dipakai kurasi manual nanti).
    """
    return {
        "term": entry.term,
        "translation": "; ".join(entry.glosses),
        "part_of_speech": POS_NORMALIZE.get(entry.pos, entry.pos),
        "example": None,
        "example_translation": None,
    }


def dedupe_words(words: list[dict]) -> list[dict]:
    """Hapus duplikat berdasarkan (term, part_of_speech), pertahankan urutan."""
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for w in words:
        key = (w["term"], w["part_of_speech"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(w)
    return unique
