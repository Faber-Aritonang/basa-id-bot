"""Health server minimal untuk hosting (Render, Railway, dll.).

Bot Telegram memakai *long polling* — proses tidak membuka port HTTP apa pun.
Padahal platform hosting seperti Render mengharuskan Web Service bind ke
`$PORT` dan merespons health check (default path `/`), kalau tidak deploy
dianggap gagal (502/503).

Solusinya: server HTTP minimal di thread daemon yang menjawab 200 di `/` dan
`/healthz`, berjalan di samping polling bot. Sederhana, tanpa dependency baru
(murni stdlib `http.server`).
"""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)

_BODY = b"ok"


class _HealthHandler(BaseHTTPRequestHandler):
    """Jawab 200 + 'ok' untuk semua request GET (path bebas)."""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(_BODY)))
        self.end_headers()
        self.wfile.write(_BODY)

    def do_HEAD(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(_BODY)))
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        # Jangan membanjiri log dengan akses health check tiap menit.
        log.debug("health: " + fmt, *args)


def start_health_server(port: int) -> ThreadingHTTPServer:
    """Mulai health server di thread daemon pada `port`.

    Mengembalikan objek server (daemon thread berjalan di latar belakang),
    sehingga pemanggil bisa membaca port aktual (`server.server_address[1]`
    saat port=0) atau menutup server saat shutdown.
    """
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
    log.info("Health server aktif di port %s — / dan /healthz.", port)
    return server
