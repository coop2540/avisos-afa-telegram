"""Utilitats HTTP compartides (timeouts, User-Agent identificable)."""

from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 20.0


class FetchError(Exception):
    """Error en obtenir una font remota (es tracta com a error recuperable)."""


def fetch_bytes(
    url: str,
    *,
    user_agent: str,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> bytes:
    """Descarrega una URL i retorna el cos en bytes, o llança FetchError."""
    headers = {"User-Agent": user_agent, "Accept-Language": "ca,es;q=0.8"}
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPStatusError as exc:
        raise FetchError(
            f"HTTP {exc.response.status_code} en obtenir {url}"
        ) from exc
    except httpx.HTTPError as exc:
        raise FetchError(f"Error de xarxa en obtenir {url}: {exc}") from exc
    finally:
        if owns_client:
            client.close()


def fetch_text(
    url: str,
    *,
    user_agent: str,
    timeout: float = DEFAULT_TIMEOUT,
    client: httpx.Client | None = None,
) -> str:
    """Com `fetch_bytes`, però decodifica a text (UTF-8 tolerant)."""
    raw = fetch_bytes(url, user_agent=user_agent, timeout=timeout, client=client)
    return raw.decode("utf-8", errors="replace")
