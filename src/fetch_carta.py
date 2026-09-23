"""Fetcher de l'enllaç de la carta del mes (resolt dinàmicament de la portada).

Mai s'ha d'hardcodar la URL del PDF: canvia cada mes. Vegeu design.md D4.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_util import fetch_text
from .logging_setup import get_logger

log = get_logger(__name__)


def resolve_carta_url(
    html: str,
    *,
    base_url: str,
    link_text_markers: list[str],
    fallback_href_contains: list[str],
) -> str | None:
    """Troba l'URL actual de la carta del mes dins l'HTML de la portada.

    Estratègia: primer per text de l'enllaç; si no, per fragment d'href + .pdf.
    Retorna l'URL absolut o None si no es troba.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a", href=True)

    markers = [m.strip().lower() for m in link_text_markers if m.strip()]
    for anchor in anchors:
        text = anchor.get_text(" ", strip=True).lower()
        href = str(anchor["href"]).strip()
        if not href or not markers:
            continue
        if any(marker in text for marker in markers):
            candidate = urljoin(base_url + "/", href)
            if candidate.lower().endswith(".pdf") or "carta" in candidate.lower():
                return candidate

    fallbacks = [f.strip().lower() for f in fallback_href_contains if f.strip()]
    for anchor in anchors:
        raw_href = str(anchor["href"]).strip()
        href = raw_href.lower()
        if not href:
            continue
        if href.endswith(".pdf") and any(frag in href for frag in fallbacks):
            return urljoin(base_url + "/", raw_href)

    log.warning("No s'ha trobat cap enllaç de carta del mes a la portada.")
    return None


def fetch_carta_url(
    *,
    homepage: str,
    base_url: str,
    user_agent: str,
    link_text_markers: list[str],
    fallback_href_contains: list[str],
) -> str | None:
    """Descarrega la portada i resol l'URL de la carta."""
    html = fetch_text(homepage, user_agent=user_agent)
    return resolve_carta_url(
        html,
        base_url=base_url,
        link_text_markers=link_text_markers,
        fallback_href_contains=fallback_href_contains,
    )
