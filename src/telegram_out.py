"""Sortida cap a Telegram (Bot API `sendMessage`), amb retry i backoff.

Fase A: només enviament; no hi ha webhook ni recepció de missatges.
El token mai no es registra als logs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from .logging_setup import get_logger
from .messages import PARSE_MODE

log = get_logger(__name__)

API_BASE = "https://api.telegram.org"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class SendResult:
    ok: bool
    status: int | None = None
    description: str | None = None
    dry_run: bool = False


class TelegramClient:
    """Client mínim de Telegram per publicar avisos en un xat/topic."""

    def __init__(
        self,
        token: str | None,
        chat_id: str | None,
        *,
        dry_run: bool = False,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        sleep=time.sleep,
        client: httpx.Client | None = None,
    ) -> None:
        self.token = token
        self.chat_id = chat_id
        self.dry_run = dry_run
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "TelegramClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def send_message(
        self,
        text: str,
        *,
        thread_id: int | None = None,
        disable_preview: bool = True,
    ) -> SendResult:
        """Envia un missatge. Reintenta en errors temporals; no llança excepcions."""
        if self.dry_run:
            log.info(
                "[DRY_RUN] missatge a xat=%s topic=%s:\n%s",
                self.chat_id,
                thread_id,
                text,
            )
            return SendResult(ok=True, dry_run=True)

        if not self.token or not self.chat_id:
            return SendResult(
                ok=False, description="Falta token o chat_id per enviar."
            )

        url = f"{API_BASE}/bot{self.token}/sendMessage"
        payload: dict[str, object] = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": PARSE_MODE,
            "disable_web_page_preview": disable_preview,
        }
        if thread_id is not None:
            payload["message_thread_id"] = thread_id

        last: SendResult | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.post(url, json=payload, timeout=self.timeout)
            except httpx.HTTPError as exc:
                last = SendResult(ok=False, description=f"error de xarxa: {exc}")
                log.warning("Enviament Telegram fallit (intent %d): %s", attempt + 1, exc)
                self._sleep(self.backoff_base * (attempt + 1))
                continue

            if resp.status_code == 200:
                body = _safe_json(resp)
                if body.get("ok"):
                    return SendResult(ok=True, status=200)
                last = SendResult(
                    ok=False, status=200, description=str(body.get("description"))
                )
                log.error("Telegram ha rebutjat el missatge: %s", last.description)
                return last

            if resp.status_code in RETRYABLE_STATUS:
                retry_after = _retry_after(resp)
                delay = retry_after if retry_after is not None else self.backoff_base * (attempt + 1)
                last = SendResult(ok=False, status=resp.status_code, description="reintentable")
                log.warning(
                    "Telegram %s (intent %d); reintent en %.1fs",
                    resp.status_code,
                    attempt + 1,
                    delay,
                )
                self._sleep(delay)
                continue

            body = _safe_json(resp)
            last = SendResult(
                ok=False, status=resp.status_code, description=str(body.get("description"))
            )
            log.error("Error Telegram %s no reintentable: %s", resp.status_code, last.description)
            return last

        return last or SendResult(ok=False, description="esgotats els reintents")


def _safe_json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _retry_after(resp: httpx.Response) -> float | None:
    body = _safe_json(resp)
    params = body.get("parameters")
    if isinstance(params, dict) and "retry_after" in params:
        try:
            return float(params["retry_after"])
        except (TypeError, ValueError):
            return None
    return None
