"""Loader data materi — memuat file JSON bahasa ke database (seed).

Membaca folder `data/`, memvalidasi skema, lalu menulis kata-kata ke tabel
`words`, frasa ke tabel `phrases`, dan aturan grammar ke `grammar_rules`
lewat repository (idempoten: menjalankan ulang tidak menduplikasi).
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from basa.db.repositories import GrammarRepository, LanguageRepository, PhraseRepository, WordRepository


def load_language_file(path: Path) -> dict:
    """Baca & validasi satu file data bahasa sesuai skema di data/README.md.

    File boleh berisi `words`, `phrases`, dan/atau `grammar` — minimal salah
    satunya harus ada dan non-kosong.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))

    language = payload.get("language")
    if not isinstance(language, dict) or not language.get("code") or not language.get("name"):
        raise ValueError(f"{path}: field 'language' harus berisi code dan name")

    words = payload.get("words") or []
    phrases = payload.get("phrases") or []
    grammar = payload.get("grammar") or []
    if not words and not phrases and not grammar:
        raise ValueError(f"{path}: harus berisi 'words', 'phrases', atau 'grammar' non-kosong")
    if not isinstance(words, list) or not isinstance(phrases, list) or not isinstance(grammar, list):
        raise ValueError(f"{path}: 'words', 'phrases', dan 'grammar' harus berupa list")

    if words:
        for i, word in enumerate(words):
            for field in ("term", "translation", "part_of_speech"):
                if not word.get(field):
                    raise ValueError(f"{path}: kata ke-{i} tidak punya field '{field}'")

    if phrases:
        for i, phrase in enumerate(phrases):
            for field in ("phrase", "translation"):
                if not phrase.get(field):
                    raise ValueError(f"{path}: frasa ke-{i} tidak punya field '{field}'")

    if grammar:
        for i, rule in enumerate(grammar):
            for field in ("title", "explanation"):
                if not rule.get(field):
                    raise ValueError(f"{path}: aturan grammar ke-{i} tidak punya field '{field}'")

    return payload


def seed_language_file(session: Session, path: Path) -> dict[str, int]:
    """Seed satu file bahasa ke DB. Mengembalikan {jenis: jumlah_baru} (idempoten)."""
    payload = load_language_file(path)
    language = LanguageRepository(session).get_or_create(
        code=payload["language"]["code"], name=payload["language"]["name"]
    )
    added: dict[str, int] = {}
    if payload.get("words"):
        added["words"] = WordRepository(session).bulk_add(language.id, payload["words"])
    if payload.get("phrases"):
        added["phrases"] = PhraseRepository(session).bulk_add(language.id, payload["phrases"])
    if payload.get("grammar"):
        added["grammar"] = GrammarRepository(session).bulk_add(language.id, payload["grammar"])
    # Commit per file: operasi seed berdiri sendiri. Tanpa commit, perubahan
    # hanya di-flush dan hilang saat session ditutup (rollback antar-proses).
    session.commit()
    return added


def seed_data_dir(session: Session, data_dir: Path = Path("data")) -> dict[str, dict[str, int]]:
    """Seed semua file *.json di subfolder data/. Mengembalikan {path: {jenis: jumlah}}."""
    results: dict[str, dict[str, int]] = {}
    for folder in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        for path in sorted(folder.glob("*.json")):
            results[str(path)] = seed_language_file(session, path)
    return results
