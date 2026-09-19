"""Adapter Telegram — python-telegram-bot v21+ (async, polling).

Adaptasi dari console ke Telegram sangat tipis: semua command tetap
diproses oleh core `Router` (DRY antar platform). Adapter hanya:
  1. menerima pesan teks / callback → `UserMessage`
  2. mengirim `BotReply` → pesan Telegram (parse_mode MARKDOWN + inline keyboard)

Catatan: `handle_text()` (core) bersifat sinkron dan dipanggil di dalam
callback async — beban DB lokal ringan, jadi aman untuk skala proyek ini.
"""

from __future__ import annotations

import logging

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from basa.core.messages import BotReply
from basa.core.router import Router
from basa.platforms.base import PlatformAdapter

log = logging.getLogger(__name__)


class TelegramAdapter(PlatformAdapter):
    """Adapter Telegram: polling + inline keyboard + fallback markdown."""

    platform_name = "telegram"

    _MENU_COMMANDS = [
        BotCommand("start", "Mulai belajar"),
        BotCommand("kata", "Kata acak bahasa daerah"),
        BotCommand("kuis", "Kuis interaktif 5 soal"),
        BotCommand("bahasa", "Daftar bahasa tersedia"),
        BotCommand("frase", "Frasa percakapan harian"),
        BotCommand("grammar", "Aturan grammar dasar"),
        BotCommand("obrolan", "Latihan percakapan dengan tutor AI"),
        BotCommand("percakapan", "Dialog tanya-jawab 2 orang"),
        BotCommand("review", "Review kata yang jatuh tempo"),
        BotCommand("tantangan", "Tantangan belajar hari ini"),
        BotCommand("progres", "Statistik belajarmu"),
        BotCommand("help", "Bantuan & daftar perintah"),
    ]

    # Menu utama yang selalu ditampilkan di setiap balasan
    _MAIN_MENU = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("📚 /kata", callback_data="/kata")],
            [InlineKeyboardButton("📝 /kuis", callback_data="/kuis")],
            [InlineKeyboardButton("🌐 /bahasa", callback_data="/bahasa")],
            [InlineKeyboardButton("📖 /grammar", callback_data="/grammar")],
            [InlineKeyboardButton("🗣️ /percakapan", callback_data="/percakapan")],
            [InlineKeyboardButton("📊 /progres", callback_data="/progres")],
            [InlineKeyboardButton("❓ /help", callback_data="/help")],
        ]
    )

    def __init__(self, token: str, router: Router | None = None) -> None:
        super().__init__(router=router)
        if not token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN kosong. Dapatkan token dari @BotFather "
                "lalu isi di file .env (contoh: lihat .env.example)."
            )
        self.token = token

    # --- pembangunan aplikasi ---

    def _build_app(self) -> Application:
        app = (
            Application.builder()
            .token(self.token)
            .post_init(self._post_init)
            .build()
        )
        # Semua teks (termasuk /command) diteruskan ke Router inti — tidak ada
        # logika command terpisah di adapter.
        app.add_handler(MessageHandler(filters.TEXT, self._on_message))
        app.add_handler(CallbackQueryHandler(self._on_callback))
        return app

    @staticmethod
    async def _post_init(app: Application) -> None:
        """Dijalankan sekali setelah Application terinisialisasi."""
        await app.bot.set_my_commands(TelegramAdapter._MENU_COMMANDS)

    # --- handler ---

    async def _on_message(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message
        if message is None or message.text is None:
            return
        user_id = str(update.effective_user.id)
        reply = self.handle_text(message.text, user_id)  # panggilan sinkron ke core
        await self._send(message, reply)

    async def _on_callback(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if query is None or query.data is None:
            return
        await query.answer()
        user_id = str(update.effective_user.id)
        # Callback diproses seperti pesan teks — callback_data kuis berupa angka
        # jawaban ("1"/"2"/"3") yang diteruskan ke core Router seperti biasa.
        reply = self.handle_text(query.data, user_id)

        # Bangun keyboard sesuai reply
        keyboard = self._build_keyboard(reply.buttons)

        try:
            await query.edit_message_text(
                reply.text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        except TelegramError:
            # Jika gagal edit, kirim pesan baru
            if query.message is not None:
                await query.message.reply_text(
                    reply.text,
                    reply_markup=keyboard,
                )

    # --- kirim balasan ---

    async def _send(self, message: Message, reply: BotReply) -> None:
        """Kirim balasan dengan inline keyboard menu utama."""
        keyboard = self._build_keyboard(reply.buttons)
        try:
            await message.reply_text(
                reply.text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )
        except TelegramError:
            # Markdown ditolak Telegram (mis. asterisk tak seimbang) → teks polos.
            await message.reply_text(
                reply.text,
                disable_web_page_preview=True,
                reply_markup=keyboard,
            )

    def _build_keyboard(self, buttons: list) -> InlineKeyboardMarkup:
        """Bangun inline keyboard: button khusus di atas, menu utama di bawah."""
        # Menu utama selalu ada di bagian bawah
        if not buttons:
            return self._MAIN_MENU

        # Buat baris pertama untuk button khusus (kuis pilihan ganda)
        custom_row = [InlineKeyboardButton(b.text, callback_data=b.callback_data) for b in buttons]

        # Gabungkan: button khusus + menu utama
        # Konversi tuple ke list untuk operasi penjumlahan
        main_keyboard = list(self._MAIN_MENU.inline_keyboard)
        return InlineKeyboardMarkup(inline_keyboard=[custom_row] + main_keyboard)

    # --- lifecycle ---

    def start(self) -> None:
        """Jalankan polling Telegram (blocking sampai dihentikan)."""
        app = self._build_app()
        log.info("Bot Telegram Basa.id mulai polling... Tekan Ctrl+C untuk berhenti.")
        app.run_polling()