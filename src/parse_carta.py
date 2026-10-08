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

# El títol pot ser «DE SETEMBRE» o «D'OCTUBRE» (apòstrof recte o tipogràfic).
_TITLE_RE = re.compile(r"CARTA DEL MES\s+D(?:E|['\u2018\u2019])?\s*(\w+)\s+(\d{4})", re.I)
_HEADER_RE = re.compile(r"dia\s+curs\s+activitat", re.I)
_ROW_RE = re.compile(r"^(\d{1,2})\s+(\S+)\s+(.+)$")
# Cel·la del dia amb rang: «5 al 9» → primer dia 5.
_DAY_LEAD_RE = re.compile(r"^(\d{1,2})\b")


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


def extract_tables_from_pdf(data: bytes) -> list[list[list[str | None]]]:
    """Extreu les taules del PDF (totes les pàgines, en ordre)."""
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables() or [])
    return tables


def _split_cell(cell: str | None) -> list[str]:
    """Separa una cel·la de taula en els valors apilats per salts de línia."""
    return [part.strip() for part in (cell or "").split("\n")]


def _leading_day(value: str) -> int | None:
    """Primer dia d'una cel·la («5», «5 al 9» → 5); None si no n'hi ha."""
    match = _DAY_LEAD_RE.match(value.strip())
    return int(match.group(1)) if match else None


def parse_carta_tables(
    tables: list[list[list[str | None]]],
) -> list[tuple[int, str, str]]:
    """Retorna (dia, curs, activitat) de la taula Dia | Curs | Activitat.

    Treballa amb l'estructura de `pdfplumber.extract_tables`: cada cel·la pot
    contenir diversos valors separats per salts de línia. Això conserva els
    cursos amb espais («CM i CS», «C. Escolar») i els rangs de dies («5 al 9»),
    que `extract_text` aplana i barreja. Per als rangs s'usa el primer dia.
    """
    for table in tables or []:
        if not table:
            continue
        header = " ".join((cell or "").strip().lower() for cell in table[0])
        if not ("dia" in header and "curs" in header and "activitat" in header):
            continue

        days: list[str] = []
        cursos: list[str] = []
        activitats: list[str] = []
        for row in table[1:]:
            if len(row) < 3:
                continue
            days += _split_cell(row[0])
            cursos += _split_cell(row[1])
            activitats += _split_cell(row[2])

        rows: list[tuple[int, str, str]] = []
        for day, curs, activitat in zip(days, cursos, activitats):
            day_num = _leading_day(day)
            if day_num is None or not curs or not activitat:
                continue
            rows.append((day_num, curs, activitat))
        if rows:
            return rows
    return []


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


def build_carta_data(
    text: str,
    *,
    source_url: str | None = None,
    tables: list[list[list[str | None]]] | None = None,
) -> CartaData:
    """Construeix les dades de la carta (mes, any i esdeveniments amb data).

    El mes/any surten del títol (text). Si es passen `tables`, les files
    s'extreuen de la taula estructurada (més fiable); si no, del text.
    """
    month, year, rows = parse_carta_text(text)
    if tables is not None:
        table_rows = parse_carta_tables(tables)
        if table_rows:
            rows = table_rows
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
    return build_carta_data(
        extract_text_from_pdf(data),
        source_url=url,
        tables=extract_tables_from_pdf(data),
    )
