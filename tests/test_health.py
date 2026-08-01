"""Test health server (`basa.health`) — dipakai hosting Render/Railway.

Health server harus menjawab 200 di `/` dan `/healthz` (dan HEAD), sehingga
Render menganggap Web Service sehat meski bot memakai long polling tanpa HTTP.
"""

from __future__ import annotations

import http.client

from basa.health import start_health_server


def _request(server_port: int, method: str, path: str) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", server_port, timeout=5)
    conn.request(method, path)
    resp = conn.getresponse()
    body = resp.read()
    status = resp.status
    conn.close()
    return status, body


def test_health_get_serves_ok_on_all_paths() -> None:
    """GET /, /healthz, dan path lain membalas 200 'ok'."""
    server = start_health_server(0)
    port = server.server_address[1]
    try:
        assert _request(port, "GET", "/") == (200, b"ok")
        assert _request(port, "GET", "/healthz") == (200, b"ok")
        assert _request(port, "GET", "/random/path") == (200, b"ok")
    finally:
        server.shutdown()
        server.server_close()


def test_health_head_returns_200_without_body() -> None:
    """HEAD membalas 200 tanpa body (kontrak health check standar)."""
    server = start_health_server(0)
    port = server.server_address[1]
    try:
        status, body = _request(port, "HEAD", "/healthz")
        assert status == 200
        assert body == b""
    finally:
        server.shutdown()
        server.server_close()


def test_start_health_server_binds_0_0_0_0() -> None:
    """Server bind ke 0.0.0.0 (agar terjangkau health check platform hosting)."""
    server = start_health_server(0)
    try:
        assert server.server_address[0] == "0.0.0.0"
    finally:
        server.shutdown()
        server.server_close()
