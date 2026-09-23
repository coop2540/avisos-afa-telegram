"""Extracció del menú diari del PDF mensual del menjador.

El PDF és una rejilla de calendari Dilluns–Divendres amb una fila per setmana i
una pàgina per variant (0=basal, 1=sense porc). `extract_text()` barreja les
columnes i `extract_tables()` no detecta taules, així que es reconstrueix la
rejilla per coordenades amb `extract_words()`.

La data objectiu NO es resol pel número imprès a la cel·la (pot contenir
errates: ex. el dijous 24 imprès com a «25»), sinó pel **dilluns de la fila +
índex de columna**. Vegeu design.md D2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
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

_HEADERS = ["DILLUNS", "DIMARTS", "DIMECRES", "DIJOUS", "DIVENDRES"]
_DAY_ABBRS = {
    "DILLUNS": 0, "DIMARTS": 1, "DIMECRES": 2, "DIJOUS": 3, "DIVENDRES": 4,
    "DILLUNS.": 0, "DIMARTS.": 1, "DIMECRES.": 2, "DIJOUS.": 3, "DIVENDRES.": 4,
}
_WS_RE = re.compile(r"\s+")
_DATE_ROW_TOL = 6  # px: agrupació de dates d'una mateixa fila
_LINE_TOL = 5  # px: agrupació de paraules d'una mateixa línia de cel·la
_BLOCK_TOL = 14  # px: salt vertical que separa blocs dins una cel·la


@dataclass
class MenuGrid:
    """Rejilla de dates d'una pàgina del PDF."""

    columns: list[float] = field(default_factory=list)
    # rows: (dia del mes del dilluns de la fila, top_inici, top_fi)
    rows: list[tuple[int, float, float]] = field(default_factory=list)
    words: list[dict] = field(default_factory=list)
    month: int | None = None
    year: int | None = None

    def column_of(self, word: dict) -> int | None:
        center = (word["x0"] + word["x1"]) / 2
        for i in range(len(self.columns) - 1):
            if self.columns[i] <= center < self.columns[i + 1]:
                return i
        return None


def _column_bounds(headers: list[dict]) -> list[float]:
    """Fronteres de columna a partir de la capçalera DILLUNS…DIVENDRES."""
    ordered = sorted(headers, key=lambda w: w["x0"])
    bounds = [ordered[0]["x0"] - 20.0]
    for a, b in zip(ordered, ordered[1:]):
        bounds.append((a["x1"] + b["x0"]) / 2)
    bounds.append(ordered[-1]["x1"] + 60.0)
    return bounds


def _monday_day(entries: list[tuple[int, int]]) -> int | None:
    """Dia del dilluns implicat per les dates d'una fila: `day - col_idx`, moda.

    Ignora les errates (col·loca la data pel seu índex de columna, no pel seu
    valor imprès); per tant la moda dels dilluns implicats és fiable.
    """
    counts: dict[int, int] = {}
    for col, day in entries:
        if 1 <= day <= 31 and 1 <= col <= 4:
            monday = day - col
            counts[monday] = counts.get(monday, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda d: (counts[d], -d))


def _extract_month_year(words: list[dict], source_url: str | None) -> tuple[int | None, int | None]:
    """Mes pel títol (p. ex. 'SETEMBRE') i any de la ruta de l'URL (/YYYY/)."""
    month = None
    for w in sorted(words, key=lambda w: w["top"]):
        if w["top"] > 80:
            break
        name = w["text"].strip().lower()
        if name in MONTHS:
            month = MONTHS[name]
            break
    year = None
    if source_url:
        match = re.search(r"/(\d{4})/(\d{2})/", source_url)
        if match:
            year = int(match.group(1))
            if month is None:
                month = int(match.group(2))
    return month, year


def build_grid(
    words: list[dict], *, source_url: str | None = None
) -> MenuGrid | None:
    """Reconstrueix la rejilla (columnes + files) a partir de les paraules."""
    headers = [w for w in words if w["text"].strip().upper() in _HEADERS]
    if len(headers) < 5:
        if headers:
            log.warning("Capçalera incompleta (%d/5 dies); no es reconstrueix la rejilla.", len(headers))
        return None

    columns = _column_bounds(headers)
    grid = MenuGrid(columns=columns, words=words)
    grid.month, grid.year = _extract_month_year(words, source_url)

    # Dates: tokens d'1-2 dígits dins la rejilla (fora de la capçalera i del peu).
    header_top = min(w["top"] for w in headers)
    date_entries: list[tuple[float, int, int]] = []
    for w in words:
        t = w["text"].strip()
        if not t.isdigit() or len(t) > 2:
            continue
        if w["top"] <= header_top + 5 or w["top"] > 780:
            continue
        col = grid.column_of(w)
        if col is None or col == 0:  # la col. 0 és el marge (dilluns decoratiu)
            continue
        date_entries.append((w["top"], col, int(t)))

    date_entries.sort()
    clusters: list[list[tuple[float, int, int]]] = []
    for top, col, day in date_entries:
        if clusters and abs(top - clusters[-1][-1][0]) <= _DATE_ROW_TOL:
            clusters[-1].append((top, col, day))
        else:
            clusters.append([(top, col, day)])

    if not clusters:
        log.warning("No s'han trobat dates al PDF del menú.")
        return None

    tops_per_row = [min(top for top, _, _ in cl) for cl in clusters]
    for i, cl in enumerate(clusters):
        entries = [(col, day) for _, col, day in cl]
        monday_day = _monday_day(entries)
        if monday_day is None:
            continue
        row_top = tops_per_row[i]
        row_bottom = tops_per_row[i + 1] if i + 1 < len(tops_per_row) else 760.0
        grid.rows.append((monday_day, row_top, row_bottom))

    return grid


def _resolve_monday(day: int, month: int | None, year: int | None) -> date | None:
    if month is None or year is None:
        return None
    for m, y in ((month, year), (month - 1, year), (month + 1, year)):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    return None


def cell_words(grid: MenuGrid, target: date) -> list[dict] | None:
    """Paraules de la cel·la de `target` (o None si no hi ha fila/columna)."""
    if target.weekday() > 4:
        return None
    for monday_day, top, bottom in grid.rows:
        monday = _resolve_monday(monday_day, grid.month, grid.year)
        if monday is None:
            continue
        # La fila del dilluns pot creuar de mes; reconstrueix el dilluns real.
        # Si la data objectiu cau dins d'aquesta setmana, és la fila correcta.
        if monday.isocalendar()[:2] != (target - timedelta(days=target.weekday())).isocalendar()[:2]:
            continue
        col = target.weekday()
        lo, hi = grid.columns[col], grid.columns[col + 1]
        words = [
            w
            for w in grid.words
            if top - 4 <= w["top"] < bottom and lo <= (w["x0"] + w["x1"]) / 2 < hi
        ]
        # Descarta el número de dia imprès (token solt d'1-2 dígits a la capçalera de la cel·la).
        cell_top = min((w["top"] for w in words), default=None)
        cleaned = []
        for w in words:
            t = w["text"].strip()
            if t.isdigit() and len(t) <= 2 and cell_top is not None and w["top"] <= cell_top + 3:
                continue
            cleaned.append(w)
        return cleaned
    return None


def words_to_lines(words: list[dict]) -> list[str]:
    """Agrupa paraules en línies per `top` i ordena per `x0`.

    Uneix sense espai les paraules pegades horitzontalment (pdfplumber parteix
    algunes paraules lletra a lletra, p. ex. «PA B L A N C» a la pàgina 2).
    """
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][-1]["top"]) <= _LINE_TOL:
            lines[-1].append(w)
        else:
            lines.append([w])
    result = []
    for line in lines:
        ordered = sorted(line, key=lambda w: w["x0"])
        pieces: list[str] = []
        prev_end: float | None = None
        for w in ordered:
            text = w["text"]
            if prev_end is not None:
                gap = w["x0"] - prev_end
                joiner = "" if gap < 0.8 else " "
                pieces.append(joiner + text)
            else:
                pieces.append(text)
            prev_end = w["x1"]
        text = _WS_RE.sub(" ", "".join(pieces)).strip()
        if text:
            result.append(text)
    return result


def _line_entries(words: list[dict]) -> list[tuple[float, str]]:
    """Retorna (top, text) de cada línia, ordenades verticalment."""
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][-1]["top"]) <= _LINE_TOL:
            lines[-1].append(w)
        else:
            lines.append([w])
    entries: list[tuple[float, str]] = []
    for line in lines:
        top = min(w["top"] for w in line)
        text = words_to_lines(line)[0] if line else ""
        if text:
            entries.append((top, text))
    return entries


def cell_blocks(words: list[dict]) -> list[list[str]]:
    """Agrupa les línies de la cel·la en blocs pel salt vertical.

    Dins un bloc (p. ex. el primer plat en dues línies) el salt és petit
    (~9-10px); entre blocs (primer/segons/pa/postre) és gran (~19px). No
    s'inventen categories: només se separen els grups.
    """
    entries = _line_entries(words)
    blocks: list[list[str]] = []
    prev_top: float | None = None
    for top, text in entries:
        if prev_top is None or (top - prev_top) > _BLOCK_TOL:
            blocks.append([text])
        else:
            blocks[-1].append(text)
        prev_top = top
    # Estructura desada: 1r plat | 2n plat (guarnició inclosa) | pa+postre.
    # Un bloc d'una sola línia al mig (p. ex. «ENCIAM I OLIVES») s'uneix al
    # bloc anterior; el primer i l'últim (pa/postre) es respecten.
    merged: list[list[str]] = []
    for i, block in enumerate(blocks):
        is_middle = 0 < i < len(blocks) - 1
        if is_middle and len(block) == 1 and merged:
            merged[-1].extend(block)
        else:
            merged.append(block)
    return merged


def plates_for_date(
    words: list[dict],
    target: date,
    *,
    source_url: str | None = None,
) -> list[str] | None:
    """Retorna els plats de `target` o None si no hi ha cel·la amb contingut."""
    grid = build_grid(words, source_url=source_url)
    if grid is None:
        return None
    cell = cell_words(grid, target)
    if cell is None:
        return None
    blocks = cell_blocks(cell)
    return blocks or None


def parse_menu_pdf(
    data: bytes,
    target: date,
    *,
    page: int = 0,
    source_url: str | None = None,
) -> list[str] | None:
    """Interpreta el PDF del menú i retorna els plats de `target` (o None)."""
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if page < 0 or page >= len(pdf.pages):
                log.warning("Pàgina %d fora del PDF del menú (%d pàgines).", page, len(pdf.pages))
                return None
            words = pdf.pages[page].extract_words()
    except Exception as exc:  # PDF il·legible o estructura desconeguda
        log.error("No s'ha pogut llegir el PDF del menú: %s", exc)
        return None
    return plates_for_date(words, target, source_url=source_url)


def load_menu(
    url: str,
    target: date,
    *,
    page: int = 0,
    user_agent: str,
) -> list[str] | None:
    """Descarrega el PDF del menú i retorna els plats de `target` (o None)."""
    data = fetch_bytes(url, user_agent=user_agent)
    return parse_menu_pdf(data, target, page=page, source_url=url)
