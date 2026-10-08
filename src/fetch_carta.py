"""Fetcher de l'enllaç de la carta del mes (resolt dinàmicament de la portada).

Mai s'ha d'hardcodar la URL del PDF: canvia cada mes. Vegeu design.md D4.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from .http_util import fetch_text
from .logging_setup import get_logger
from .parse_carta import MONTHS

log = get_logger(__name__)

# Data de pujada a l'URL de mitjans de WordPress: /uploads/.../YYYY/MM/...
_UPLOAD_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/")
# Mes i any al nom del fitxer: Carta-mes-Octubre-26.pdf → (2026, 10)
_FILENAME_DATE_RE = re.compile(r"carta-mes-([a-zà-ÿ]+)-(\d{2,4})", re.I)


def _carta_recency(url: str) -> tuple[int, int]:
    """Clau de recència (any, mes) de la carta, per triar la més nova.

    Prioritza el mes/any del nom del fitxer (és el mes que representa la
    carta); si no es pot llegir, cau a la data de pujada /YYYY/MM/.
    """
    path = unquote(url.split("?", 1)[0]).lower()

    match = _FILENAME_DATE_RE.search(path)
    if match:
        month = MONTHS.get(match.group(1))
        if month:
            yy = match.group(2)
            year = int(yy) if len(yy) == 4 else 2000 + int(yy)
            return (year, month)

    match = _UPLOAD_DATE_RE.search(path)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    return (0, 0)


def resolve_carta_url(
    html: str,
    *,
    base_url: str,
    link_text_markers: list[str],
    fallback_href_contains: list[str],
) -> str | None:
    """Troba l'URL actual de la carta del mes dins l'HTML de la portada.

    Estratègia: recull tots els enllaços candidats (per text de l'enllaç o pel
    fragment d'href + .pdf) i tria el **més recent**. La portada sol conservar
    enllaços de cartes antigues (botons no actualitzats, entrades), així que
    retornar la primera coincidència triaria una carta caducada (D4). En cas
    d'empat, guanya el primer en ordre d'aparició.
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a", href=True)

    markers = [m.strip().lower() for m in link_text_markers if m.strip()]
    fallbacks = [f.strip().lower() for f in fallback_href_contains if f.strip()]

    candidates: list[str] = []
    for anchor in anchors:
        raw_href = str(anchor["href"]).strip()
        if not raw_href:
            continue
        absolute = urljoin(base_url + "/", raw_href)
        href_lower = raw_href.lower()

        by_text = bool(markers) and any(
            marker in anchor.get_text(" ", strip=True).lower() for marker in markers
        )
        if by_text and (absolute.lower().endswith(".pdf") or "carta" in absolute.lower()):
            candidates.append(absolute)
        elif absolute.lower().endswith(".pdf") and any(frag in href_lower for frag in fallbacks):
            candidates.append(absolute)

    if not candidates:
        log.warning("No s'ha trobat cap enllaç de carta del mes a la portada.")
        return None

    # Deduplica conservant l'ordre d'aparició i tria la carta més recent.
    seen: set[str] = set()
    unique = [c for c in candidates if not (c in seen or seen.add(c))]
    return max(unique, key=_carta_recency)


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
