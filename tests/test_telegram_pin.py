"""Tests del client de Telegram: send_message i pin_message (tasca 6.1)."""

import httpx
import respx

from src.telegram_out import API_BASE, TelegramClient

TOKEN = "tok-test"


def _client(**kw):
    return TelegramClient(TOKEN, "-100123", timeout=1.0, sleep=lambda _s: None, **kw)


@respx.mock
def test_send_message_returns_message_id():
    route = respx.post(f"{API_BASE}/bot{TOKEN}/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 555}})
    )
    client = _client()
    res = client.send_message("hola", thread_id=24)
    assert res.ok is True
    assert res.message_id == 555
    assert route.called


@respx.mock
def test_pin_message_calls_endpoint():
    route = respx.post(f"{API_BASE}/bot{TOKEN}/pinChatMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": True})
    )
    client = _client()
    res = client.pin_message(555, thread_id=24)
    assert res.ok is True
    assert route.called
    body = route.calls.last.request.content.decode()
    assert '"message_id":555' in body
    assert '"message_thread_id":24' in body


def test_pin_message_dry_run_does_not_raise():
    client = TelegramClient(TOKEN, "-100123", dry_run=True, sleep=lambda _s: None)
    res = client.pin_message(42, thread_id=24)
    assert res.ok is True
    assert res.dry_run is True


@respx.mock
def test_pin_message_handles_rejection():
    respx.post(f"{API_BASE}/bot{TOKEN}/pinChatMessage").mock(
        return_value=httpx.Response(400, json={"ok": False, "description": "not enough rights"})
    )
    res = _client().pin_message(1)
    assert res.ok is False
    assert res.status == 400
