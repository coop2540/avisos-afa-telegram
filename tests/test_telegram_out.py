"""Tests de la sortida Telegram: èxit, retry i errors (tasques 4.1, 4.2)."""

import httpx
import pytest

from src.telegram_out import TelegramClient

TOKEN = "123456:TESTTOKEN"
CHAT = "-100123"


def _client(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return TelegramClient(TOKEN, CHAT, client=http, sleep=lambda _s: None, **kwargs)


def test_dry_run_does_not_call_network():
    calls = []

    def handler(request):  # pragma: no cover - no s'ha de cridar
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    client = TelegramClient(None, None, dry_run=True, client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.send_message("hola")
    assert result.ok is True and result.dry_run is True
    assert calls == []


def test_success_sends_to_correct_topic():
    seen = {}

    def handler(request):
        seen["payload"] = request.read()
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    client = _client(handler)
    result = client.send_message("hola", thread_id=42)
    assert result.ok is True
    assert b'"message_thread_id":42' in seen["payload"].replace(b" ", b"")


def test_retry_on_429_then_success():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, json={"ok": False, "parameters": {"retry_after": 0}})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    result = client.send_message("hola")
    assert result.ok is True
    assert attempts["n"] == 2


def test_retry_on_5xx_then_success():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(503, text="bad gateway")
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    assert client.send_message("hola").ok is True
    assert attempts["n"] == 3


def test_non_retryable_4xx_fails_without_retry():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        return httpx.Response(400, json={"ok": False, "description": "chat not found"})

    client = _client(handler)
    result = client.send_message("hola")
    assert result.ok is False
    assert result.status == 400
    assert attempts["n"] == 1


def test_network_error_retries_then_fails():
    attempts = {"n": 0}

    def handler(request):
        attempts["n"] += 1
        raise httpx.ConnectError("boom")

    client = _client(handler, max_retries=2)
    result = client.send_message("hola")
    assert result.ok is False
    assert attempts["n"] == 3  # 1 + 2 reintents


def test_missing_token_fails_gracefully():
    client = TelegramClient(None, CHAT)
    result = client.send_message("hola")
    assert result.ok is False
