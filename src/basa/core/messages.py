"""Tipe pesan abstrak — jembatan antara platform dan logika inti.

Adapter platform (Telegram/WhatsApp/console) mengubah pesan platform menjadi
`UserMessage`, lalu menampilkan `BotReply` yang dihasilkan core. Core TIDAK
pernah mengenal SDK platform — hanya tipe-tipe ini.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Button:
    """Tombol aksi yang bisa dirender sebagai inline keyboard platform."""

    text: str
    callback_data: str


@dataclass
class UserMessage:
    """Pesan masuk dari user, sudah dinormalisasi oleh adapter."""

    user_id: str
    text: str
    platform: str = "console"


@dataclass
class BotReply:
    """Balasan bot: teks utama + tombol opsional (dipakai fitur interaktif)."""

    text: str
    buttons: list[Button] = field(default_factory=list)
