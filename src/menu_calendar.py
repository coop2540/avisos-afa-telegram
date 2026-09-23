"""Dies no lectius a partir del text del calendari del curs.

El calendari del centre (pàgina HTML i/o PDF) conté rangs de vacances, festes de
lliure disposició, festes locals i els límits d'inici/fi de curs. Aquest mòdul
els converteix en un `set[date]` de dies no lectius perquè el servei de menú no
publiqui en dies sense escola.

La jornada intensiva SÍ és lectiva (no entra al set). Vegeu design.md D5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from .logging_setup import get_logger

log = get_logger(__name__)

MONTHS = {
    "gener": 1, "febrer": 2, "març": 3, "abril": 4, "maig": 5, "juny": 6,
    "juliol": 7, "agost": 8, "setembre": 9, "octubre": 10, "novembre": 11,
    "desembre": 12,
}
_MONTH_ALT = "|".join(MONTHS)

# Seccions les dates de les quals són dies no lectius.
_NON_SCHOOL_HEADINGS = [
    "vacances",
    "dies festius de lliure disposició",
    "festes de lliure disposició",
    "festes de lliure elecció",
    "festa local",
    "festes locals",
    "festa de lliure disposició del centre",
    "festa de lliure elecció del centre",
]
# "NADAL: del ... ", "SETMANA SANTA: del ..." i similars: rangs amb data pròpia.
_NON_SCHOOL_LABELS = ["nadal", "setmana santa", "vacances"]

_RANGE_RE = re.compile(
    rf"del\s+(\d{{1,2}})\s+de?\s+({_MONTH_ALT})"
    rf"(?:\s+de\s+(\d{{4}}))?"
    rf"\s+al\s+(\d{{1,2}})\s+de?\s+({_MONTH_ALT})"
    rf"(?:\s+de\s+(\d{{4}}))?",
    re.I,
)
# Rang dins el mateix mes: "Del 22 al 29 de març de 2027".
_RANGE_SAME_MONTH_RE = re.compile(
    rf"del\s+(\d{{1,2}})\s+al\s+(\d{{1,2}})\s+de?\s+({_MONTH_ALT})"
    rf"(?:\s+de\s+(\d{{4}}))?",
    re.I,
)
_SINGLE_RE = re.compile(
    rf"(\d{{1,2}})\s+de?\s+({_MONTH_ALT})\s+de\s+(\d{{4}})",
    re.I,
)


@dataclass
class SchoolCalendar:
    """Dies no lectius i límit d'inici/fi de curs."""

    non_school_days: set[date] = field(default_factory=set)
    start: date | None = None
    end: date | None = None


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_range(start_day: int, start_month: int, start_year: int | None,
                 end_day: int, end_month: int, end_year: int | None) -> set[date]:
    """Dates del rang [inici, fi] (ambdós inclosos), tolerant a l'any creuat.

    Regla: si l'any de fi no s'indica o bé `end < start`, l'any de fi és
    `start.year + 1` (tolera l'errata de la font: «al 7 de gener de 2026»
    després de «21 de desembre de 2026»). Vegeu design.md D5.
    """
    if start_year is None:
        start_year = date.today().year
    try:
        begin = date(start_year, start_month, start_day)
    except ValueError:
        return set()
    ey = end_year if end_year is not None else start_year
    try:
        finish = date(ey, end_month, end_day)
    except ValueError:
        return set()
    if finish < begin:
        try:
            finish = date(ey + 1, end_month, end_day)
        except ValueError:
            return set()
    days: set[date] = set()
    cursor = begin
    while cursor <= finish:
        days.add(cursor)
        cursor += timedelta(days=1)
    return days


def _section_spans(text: str) -> list[tuple[str, str]]:
    """Divideix el text en (etiqueta, cos) per a les seccions no lectives.

    L'etiqueta és el text abans dels dos punts (p. ex. «Vacances:»,
    «Dies festius de lliure disposició:»). El cos arriba fins a la propera
    etiqueta o el final.
    """
    spans: list[tuple[str, str]] = []
    matches = list(re.finditer(r"([^\n:]{3,60}?):", text))
    for i, match in enumerate(matches):
        label = _norm(match.group(1)).lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        spans.append((label, text[start:end]))
    return spans


def parse_calendar_text(text: str) -> SchoolCalendar:
    """Extreu els dies no lectius i els límits de curs del text del calendari."""
    cal = SchoolCalendar()
    flat = _norm(text)

    # Inici i fi de curs: frases explícites.
    m_inici = re.search(
        rf"comen[çc]ar[aà]\s+\w*\s*(\d{{1,2}})\s+de\s+({_MONTH_ALT})\s+de\s+(\d{{4}})", flat, re.I
    )
    m_fi = re.search(
        rf"acabar[aà]\s+\w*\s*(\d{{1,2}})\s+de\s+({_MONTH_ALT})\s+de\s+(\d{{4}})", flat, re.I
    )
    if m_inici:
        cal.start = date(int(m_inici.group(3)), MONTHS[m_inici.group(2).lower()], int(m_inici.group(1)))
    if m_fi:
        cal.end = date(int(m_fi.group(3)), MONTHS[m_fi.group(2).lower()], int(m_fi.group(1)))

    for label, body in _section_spans(text):
        is_non_school = any(h in label for h in _NON_SCHOOL_HEADINGS) or any(
            l in label for l in _NON_SCHOOL_LABELS
        )
        if not is_non_school:
            continue
        for rm in _RANGE_RE.finditer(_norm(body)):
            cal.non_school_days |= _parse_range(
                int(rm.group(1)), MONTHS[rm.group(2).lower()],
                int(rm.group(3)) if rm.group(3) else None,
                int(rm.group(4)), MONTHS[rm.group(5).lower()],
                int(rm.group(6)) if rm.group(6) else None,
            )
        for rm in _RANGE_SAME_MONTH_RE.finditer(_norm(body)):
            month = MONTHS[rm.group(3).lower()]
            year = int(rm.group(4)) if rm.group(4) else None
            cal.non_school_days |= _parse_range(
                int(rm.group(1)), month, year, int(rm.group(2)), month, year
            )
        for sm in _SINGLE_RE.finditer(_norm(body)):
            try:
                cal.non_school_days.add(
                    date(int(sm.group(3)), MONTHS[sm.group(2).lower()], int(sm.group(1)))
                )
            except ValueError:
                continue

    return cal


def is_school_day(d: date, calendar: SchoolCalendar | None, *, weekend: bool = True) -> bool:
    """True si `d` és dia lectiu (fora de cap de setmana i de dies no lectius)."""
    if weekend and d.weekday() >= 5:
        return False
    if calendar is None:
        return True
    if calendar.start and d < calendar.start:
        return False
    if calendar.end and d > calendar.end:
        return False
    return d not in calendar.non_school_days


def fetch_school_calendar(*, url: str, user_agent: str) -> SchoolCalendar:
    """Descarrega la pàgina del calendari i n'extreu els dies no lectius."""
    from .fetch_calendari import fetch_calendari

    content = fetch_calendari(url=url, user_agent=user_agent)
    return parse_calendar_text(content.normalized_text)
