"""Adapter WhatsApp — Meta WhatsApp Cloud API (webhook + Graph API).

Arsitektur sama dengan Telegram: adapter tipis, semua perintah diproses core
`Router` (DRY antar platform). Adapter hanya:
  1. menerima webhook (verifikasi handshake + pesan masuk) → `UserMessage`
  2. mengirim `BotReply` → Graph API (teks atau interactive buttons)

Catatan penting:
- WhatsApp TIDAK mendukung markdown — teks dikirim polos (asterisk dibersihkan).
- Tombol interaktif terbatas 3 per pesan, judul maks 20 karakter.
- Balasan tombol datang sebagai tipe pesan `interactive` dengan
  `button_reply.id` — diproses seperti callback (mirip Telegram).
- Untuk dev lokal, expose webhook ke internet dengan ngrok:
      ngrok http 8080
  lalu pasang URL https ke Meta App Dashboard (Webhook → Callback URL),
  dan isi verify token yang sama di .env.
"""

from __future__ import annotations

import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from basa.core.messages import BotReply
from basa.core.router import Router
from basa.platforms.base import PlatformAdapter

log = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v20.0"
_MAX_BUTTONS = 3          # batas WhatsApp untuk tombol interaktif
_MAX_BUTTON_TITLE = 20    # batas judul tombol WhatsApp
_MAX_INTERACTIVE_BODY = 1024  # batas teks body pesan interaktif WhatsApp

#: Asterisk markdown Telegram → teks polos (WhatsApp tidak punya markdown).
_MARKDOWN_RE = re.compile(r"\*{1,2}([^*]+?)\*{1,2}")


class WhatsAppAdapter(PlatformAdapter):
    """Adapter WhatsApp: webhook Meta Cloud API + kirim via Graph API."""

    platform_name = "whatsapp"

    def __init__(
        self,
        api_token: str,
        phone_number_id: str,
        verify_token: str,
        port: int = 8080,
        router: Router | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(router=router)
        if not api_token or not phone_number_id or not verify_token:
            raise ValueError(
                "Kredensial WhatsApp belum lengkap. Isi WHATSAPP_API_TOKEN, "
                "WHATSAPP_PHONE_NUMBER_ID, dan WHATSAPP_VERIFY_TOKEN di .env "
                "(lihat .env.example)."
            )
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.port = port
        # Client HTTP bisa di-inject untuk test (tanpa jaringan).
        self._client = client or httpx.Client()

    # --- verifikasi webhook (handshake Meta) ---

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verifikasi handshake Meta → kembalikan `challenge` jika cocok.

        Meta mengirim GET dengan `hub.mode=subscribe`, `hub.verify_token`,
        dan `hub.challenge`. Jawaban harus persis nilai challenge (plain text).
        """
        if mode == "subscribe" and token == self.verify_token and challenge:
            return challenge
        return None

    # --- proses pesan masuk ---

    def handle_webhook(self, payload: dict[str, Any]) -> int:
        """Proses payload webhook Meta → balas pesan user.

        Mengembalikan HTTP status yang harus dijawab ke Meta (200 = sukses,
        sehingga Meta tidak mengulang kirim). Payload status (delivered/read)
        hanya di-ack, tidak diproses.
        """
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    try:
                        self._handle_message(message)
                    except Exception:
                        log.exception("Gagal memproses pesan WhatsApp")
        return 200

    def _handle_message(self, message: dict[str, Any]) -> None:
        wa_id = message.get("from")
        if not wa_id:
            return
        text = self._extract_text(message)
        if text is None:
            return
        reply = self.handle_text(text, wa_id)  # panggilan sinkron ke core
        self._send(wa_id, reply)

    @staticmethod
    def _extract_text(message: dict[str, Any]) -> str | None:
        """Ambil teks dari pesan masuk (text biasa atau balasan tombol)."""
        msg_type = message.get("type")
        if msg_type == "text":
            return message.get("text", {}).get("body")
        if msg_type == "interactive":
            # Balasan tombol interaktif → `button_reply.id` = callback_data.
            button = message.get("interactive", {}).get("button_reply", {})
            return button.get("id")
        return None

    # --- kirim balasan via Graph API ---

    def _send(self, to: str, reply: BotReply) -> None:
        url = f"{_GRAPH_API_BASE}/{self.phone_number_id}/messages"
        payload = self._build_payload(to, reply)
        resp = self._client.post(
            url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            json=payload,
        )
        resp.raise_for_status()

    def _build_payload(self, to: str, reply: BotReply) -> dict[str, Any]:
        """Bangun body Graph API: teks polos atau interactive buttons.

        Jika balasan punya tombol TAPI teksnya melebihi batas body interactive
        (1024 karakter), kirim sebagai teks polos tanpa tombol — tombol rusak
        lebih buruk daripada tanpa tombol.
        """
        body = self._render_text(reply.text)
        if not reply.buttons:
            return self._text_payload(to, body)
        if len(body) > _MAX_INTERACTIVE_BODY:
            log.warning(
                "Balasan ber-tombol terlalu panjang (%d>%d) — kirim tanpa tombol.",
                len(body),
                _MAX_INTERACTIVE_BODY,
            )
            return self._text_payload(to, body)
        buttons = [
            {"type": "reply", "reply": {"id": b.callback_data, "title": b.text[:_MAX_BUTTON_TITLE]}}
            for b in reply.buttons[:_MAX_BUTTONS]
        ]
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": buttons},
            },
        }

    @staticmethod
    def _text_payload(to: str, body: str) -> dict[str, Any]:
        """Body Graph API untuk pesan teks polos."""
        return {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }

    @staticmethod
    def _render_text(text: str) -> str:
        """Bersihkan markdown asterisk — WhatsApp hanya mendukung teks polos."""
        return _MARKDOWN_RE.sub(r"\1", text)

    # --- lifecycle ---

    def start(self) -> None:
        """Jalankan webhook server (blocking). Expose dengan ngrok untuk live."""
        handler = _make_handler(self)
        httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        log.info(
            "Webhook WhatsApp Basa.id aktif di port %s. "
            "Expose ke Meta dengan: ngrok http %s",
            self.port,
            self.port,
        )
        httpd.serve_forever()


def _make_handler(adapter: WhatsAppAdapter) -> type[BaseHTTPRequestHandler]:
    """Factory handler webhook yang menangkap instance adapter."""

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            # Handshake verifikasi: balas hub.challenge jika token cocok.
            query = parse_qs(urlparse(self.path).query)
            challenge = adapter.verify_webhook(
                query.get("hub.mode", [""])[0],
                query.get("hub.verify_token", [""])[0],
                query.get("hub.challenge", [""])[0],
            )
            if challenge is None:
                self._respond(403, b"Verification failed")
                return
            self._respond(200, challenge.encode())

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                payload = {}
            try:
                status = adapter.handle_webhook(payload)
            except Exception:
                log.exception("Gagal memproses webhook")
                status = 500
            # Meta butuh ack cepat — selalu balas "EVENT_RECEIVED".
            self._respond(status, b"EVENT_RECEIVED")

        def _respond(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: Any) -> None:
            # Jangan membanjiri log dengan baris akses webhook.
            log.debug("webhook: " + fmt, *args)

    return WebhookHandler
