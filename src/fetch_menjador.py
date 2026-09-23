"""Fetcher de l'enllaç al PDF del menú del menjador (resolt dinàmicament).

La URL del PDF canvia cada mes, així que mai no s'ha d'hardcodar: es resol de
l'HTML de la pàgina del menjador. Les àncores del menú no tenen text (són
imatges), per tant cal cercar per fragment d'`href`. Vegeu design.md D1.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_util import fetch_text
from .logging_setup import get_logger

log = get_logger(__name__)


def resolve_menu_url(
    html: str,
    *,
    base_url: str,
    link_markers: list[str],
    fallback_href_excludes: list[str],
) -> str | None:
    """Troba l'URL actual del PDF del menú dins l'HTML de la pàgina del menjador.

    Estratègia: primer un `.pdf` l'href del qual contingui algun marcador i cap
    exclusió; si no, el primer `.pdf` no exclòs. Retorna l'URL absolut o None.
    """
    soup = BeautifulSoup(html, "html.parser")
    markers = [m.strip().lower() for m in link_markers if m.strip()]
    excludes = [e.strip().lower() for e in fallback_href_excludes if e.strip()]

    pdf_anchors: list[str] = []
    for anchor in soup.find_all("a", href=True):
        raw = str(anchor["href"]).strip()
        if not raw or not raw.lower().endswith(".pdf"):
            continue
        pdf_anchors.append(raw)

    def _excluded(href: str) -> bool:
        low = href.lower()
        return any(exc in low for exc in excludes)

    for raw in pdf_anchors:
        low = raw.lower()
        if any(marker in low for marker in markers) and not _excluded(raw):
            return urljoin(base_url + "/", raw)

    for raw in pdf_anchors:
        if not _excluded(raw):
            log.warning(
                "Cap enllaç de menú coincideix amb els marcadors %s; s'usa '%s'.",
                markers,
                raw,
            )
            return urljoin(base_url + "/", raw)

    log.warning("No s'ha trobat cap enllaç .pdf de menú a la pàgina del menjador.")
    return None


def fetch_menu_url(
    *,
    page_url: str,
    base_url: str,
    user_agent: str,
    link_markers: list[str],
    fallback_href_excludes: list[str],
) -> str | None:
    """Descarrega la pàgina del menjador i resol l'URL del PDF del menú."""
    html = fetch_text(page_url, user_agent=user_agent)
    return resolve_menu_url(
        html,
        base_url=base_url,
        link_markers=link_markers,
        fallback_href_excludes=fallback_href_excludes,
    )
