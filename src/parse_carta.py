"""Extracció d'esdeveniments de la carta mensual (PDF).

La taula d'activitats (Dia | Curs | Activitat) és text pla al PDF, així que
s'extreu sense OCR. Vegeu design.md D13 i specs/carta-agenda.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO

import pdfplumber

from .http_util import fetch_bytes
from .logging_setup import get_logger

log = get_logger(__name__)

MONTHS = {
    "gener": 1, "febrer": 2, "març": 3, "abril": 4, "maig": 5, "juny": 6,
    "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11,
    "desembre": 12,
}

_TITLE_RE = re.compile(r"CARTA DEL MES DE\s+(\w+)\s+(\d{4})", re.I)
_HEADER_RE = re.compile(r"dia\s+curs\s+activitat", re.I)
_ROW_RE = re.compile(r"^(\d{1,2})\s+(\S+)\s+(.+)$")


@dataclass(frozen=True)
class CartaEvent:
    date: date
    curs: str
    activitat: str


@dataclass
class CartaData:
    month: int | None = None
    year: int | None = None
    events: list[CartaEvent] = field(default_factory=list)
    source_url: str | None = None

    @property
    def has_events(self) -> bool:
        return bool(self.events)


def extract_text_from_pdf(data: bytes) -> str:
    """Extreu tot el text del PDF (totes les pàgines)."""
    with pdfplumber.open(BytesIO(data)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def parse_carta_text(text: str) -> tuple[int | None, int | None, list[tuple[int, str, str]]]:
    """Retorna (mes, any, files) a partir del text de la carta.

    Les files són tuples (dia, curs, activitat) en ordre d'aparició.
    """
    title = _TITLE_RE.search(text)
    month = MONTHS.get(title.group(1).lower()) if title else None
    year = int(title.group(2)) if title else None

    rows: list[tuple[int, str, str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if not in_table:
            if _HEADER_RE.search(stripped):
                in_table = True
            continue
        if not stripped:
            continue
        match = _ROW_RE.match(stripped)
        if match:
            rows.append((int(match.group(1)), match.group(2), match.group(3).strip()))
        else:
            break  # fi de la taula (p. ex. el peu de pàgina)
    return month, year, rows


def build_carta_data(text: str, *, source_url: str | None = None) -> CartaData:
    """Construeix les dades de la carta (mes, any i esdeveniments amb data)."""
    month, year, rows = parse_carta_text(text)
    events: list[CartaEvent] = []
    if month and year:
        for day, curs, activitat in rows:
            try:
                events.append(CartaEvent(date(year, month, day), curs, activitat))
            except ValueError:
                log.warning("Dia invàlid a la carta: %s/%s/%s", day, month, year)
    else:
        log.warning("No s'ha pogut determinar el mes/any de la carta.")
    return CartaData(month=month, year=year, events=events, source_url=source_url)


def load_carta(url: str, *, user_agent: str) -> CartaData:
    """Descarrega i parseja la carta indicada."""
    data = fetch_bytes(url, user_agent=user_agent)
    return build_carta_data(extract_text_from_pdf(data), source_url=url)
