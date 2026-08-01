"""Simulator konsol — uji & demo bot langsung di terminal, tanpa akun apa pun.

Menjalankan loop chat sederhana: baca baris dari stdin, teruskan ke core lewat
`PlatformAdapter.handle_text`, lalu tampilkan `BotReply` dengan gaya konsol.

Perintah khusus konsol (TIDAK diteruskan ke core):
    /quit, /exit, /keluar  → keluar dari simulator
"""

from __future__ import annotations

import os
import re
import sys

from basa.core.messages import BotReply
from basa.platforms.base import PlatformAdapter

#: User tetap untuk semua sesi konsol — progres tersimpan lintas sesi.
CONSOLE_USER_ID = "console-user"

#: Perintah yang diproses konsol sendiri (bukan diteruskan ke core).
EXIT_COMMANDS = {"/quit", "/exit", "/keluar"}

# ANSI minimal — hanya dipakai saat stdout benar-benar terminal (tty).
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"

#: Asterisk `*teks*` / `**teks**` (markdown Telegram) → teks polos/tebal di terminal.
_MARKDOWN_RE = re.compile(r"\*{1,2}([^*]+?)\*{1,2}")

#: Teks prefix tanpa kode ANSI — dipakai menghitung indent baris lanjutan
#: (len(prefix ber-ANSI) ≠ lebar yang terlihat di layar).
_PREFIX_TEXT = "basa › "


def _is_tty() -> bool:
    return sys.stdout.isatty()


def _style(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if _is_tty() else text


def _enable_ansi() -> None:
    # Windows 10+: aktifkan VT processing supaya kode ANSI berfungsi.
    if os.name == "nt":
        os.system("")


class ConsoleAdapter(PlatformAdapter):
    """Adapter terminal: dijalankan lewat `python -m basa run`."""

    platform_name = "console"

    def start(self) -> None:
        _enable_ansi()
        self._print_banner()
        while True:
            try:
                raw = input(_style("kamu › ", _CYAN + _BOLD))
            except (EOFError, KeyboardInterrupt):
                self._print_farewell()
                break

            text = raw.strip()
            if not text:
                continue
            if text.lower() in EXIT_COMMANDS:
                self._print_farewell()
                break

            self.render(self.handle_text(text, CONSOLE_USER_ID))

    # --- rendering ---

    def render(self, reply: BotReply) -> None:
        """Tampilkan `BotReply` ke terminal (indentasi baris lanjutan)."""
        prefix = _style(_PREFIX_TEXT, _GREEN + _BOLD)
        indent = " " * len(_PREFIX_TEXT)
        body = self._render_text(reply.text).replace("\n", "\n" + indent)
        print(prefix + body)
        for button in reply.buttons:
            print(indent + _style(f"[ {button.text} ]", _DIM))

    def _render_text(self, text: str) -> str:
        """Bersihkan markdown asterisk: tebal di tty, polos di luar tty."""
        if _is_tty():
            return _MARKDOWN_RE.sub(_BOLD + r"\1" + _RESET, text)
        return _MARKDOWN_RE.sub(r"\1", text)

    def _print_banner(self) -> None:
        print(
            _style(
                "╔══════════════════════════════════════════════════════╗\n"
                "║   Basa.id — belajar bahasa daerah Indonesia 🇮🇩      ║\n"
                "║   one conversation at a time                          ║\n"
                "╚══════════════════════════════════════════════════════╝",
                _BOLD,
            )
        )
        print(_style("Ketik /help untuk perintah · /quit untuk keluar", _DIM))
        print()

    def _print_farewell(self) -> None:
        print(_style("\nSampai jumpa! Horas! 👋", _GREEN + _BOLD))
