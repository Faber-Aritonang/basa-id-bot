"""Utilitas bahasa — alias user → kode ISO 639-3.

Dipakai bersama oleh semua service (vocabulary, conversation, dll.) supaya
pemetaan alias (mis. 'batak' → 'bbc') tidak diduplikasi di beberapa tempat.
"""

from __future__ import annotations

#: Alias yang user ketik → kode bahasa (ISO 639-3)
LANG_ALIASES: dict[str, str] = {
    "batak": "bbc",
    "batak toba": "bbc",
    "toba": "bbc",
    "jawa": "jv",
    "javanese": "jv",
    "sunda": "su",
    "sundanese": "su",
    "indonesia": "id",
    "indonesian": "id",
}


def resolve_code(alias: str) -> str:
    """Ubah alias (mis. 'batak') → kode ISO. Fallback: alias apa adanya."""
    normalized = alias.strip().lower()
    return LANG_ALIASES.get(normalized, normalized)
