"""Extracció del menú per visió local (Ollama) quan el PDF no té capa de texte.

El PDF del menjador és una imatge escanejada alguns mesos: no hi ha paraules
extraïbles, però sí la geometria de les caixes de cel·la (curves ~98x108 pt).
Aquest mòdul localitza les cel·les per geometria, retalla la cel·la del dia i
demana al model de visió **una sola cosa**: transcriure literalment el que s'hi
llegeix, amb el número de dia imprès per validar que som a la fila correcta.

Condicions (design.md D2): IA exclusivament local i privada, exclusivament
transcripció (el model no calcula dates ni inventa) i, si el motor falla, no es
publica i es reintenta. Cap crida surt del servidor. Vegeu també D4 (candidats
de dilluns), D5 (variant pel segell) i D8 (semàntica d'error).
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange
from io import BytesIO

import httpx
import pdfplumber
import pypdfium2 as pdfium
from PIL import Image

from .logging_setup import get_logger

log = get_logger(__name__)

# --- Geometria (pdfplumber: `curves` de les caixes del calendari) ------------
CELL_W = (90.0, 112.0)
CELL_H = (100.0, 116.0)
PILL_W = (25.0, 140.0)
PILL_H = (6.0, 40.0)
PILL_TOP_MAX = 150.0
EXPECTED_COLS = 5
RENDER_SCALE = 5.0

# --- Límits de validació (spec: 1..8 línies de ≤80 caràcters) ---------------
MAX_BLOCKS = 8
MAX_LINES = 8
MAX_LINE_LEN = 80
MAX_CELL_CALLS = 4  # candidats de dilluns provats per extracció
# Sostre de generació. `qwen3-vl:2b` raona (thinking) abans de respondre i
# `think:false` no el desactiva: amb 900 el pensament s'emportava tot el
# pressupost i el JSON sortia truncat (`done_reason=length`). El sostre alt
# només és un límit: si el model acaba abans, no costaria més.
NUM_PREDICT_CELL = 2400
NUM_PREDICT_PILL = 1600

_WS_RE = re.compile(r"\s+")

P_CELL = (
    "Imatge d'una cel·la del calendari mensual del menjador escolar. "
    'Retorna NOMÉS un JSON {"dia": <enter o null>, "blocs": [[<text literal>], ...]}. '
    '"dia" és el número imprès al cercle de la cantonada (null si no n\'hi ha). '
    '"blocs" agrupa les línies de la cel·la tal com es veuen separades per espai en blanc '
    "(una llista de llistes: cada llista és un bloc de línies juntes). "
    "Text literal, de dalt a baix, sense traduir, sense comentaris. "
    "Si no hi ha text, blocs buida."
)
P_PILL = (
    "Imatge de la pastilla (etiqueta) del capçalera d'una pàgina del menú del menjador escolar. "
    'Retorna NOMÉS un JSON {"text": "<text literal de la pastilla>"}. '
    "Text literal, sense traduir, sense comentaris."
)


class VisionError(RuntimeError):
    """Fallada del motor de visió o del PDF: no es publica; es reintentarà."""


# --- Geometria i renderitzat -------------------------------------------------
@dataclass
class PageGeometry:
    """Caixes de cel·la (i píndola de variant) d'una pàgina, en punts PDF."""

    cols: list[tuple[float, float]]  # (x0, x1) per columna, esquerra→dreta
    rows: list[tuple[float, float]]  # (top, bottom) per fila, dalt→abaix
    pill: tuple[float, float, float, float] | None = None

    @property
    def has_grid(self) -> bool:
        return len(self.cols) == EXPECTED_COLS and bool(self.rows)


def _cluster(values: list[float], tol: float) -> list[float]:
    groups: list[list[float]] = []
    for v in sorted(values):
        if groups and abs(v - groups[-1][-1]) <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [sum(g) / len(g) for g in groups]


def _pill_box(page) -> tuple[float, float, float, float] | None:
    """Píndola farcida del capçalera (segell de variant), si n'hi ha."""
    candidates = []
    for c in page.curves:
        w = c["x1"] - c["x0"]
        h = c["bottom"] - c["top"]
        if c["top"] < PILL_TOP_MAX and PILL_W[0] <= w <= PILL_W[1] and PILL_H[0] <= h <= PILL_H[1]:
            candidates.append((c["top"], c["x0"], c["x1"], c["bottom"]))
    if not candidates:
        return None
    top, x0, x1, bottom = sorted(candidates)[0]
    return (x0, top, x1, bottom)


def page_geometry(data: bytes, page_idx: int) -> PageGeometry | None:
    """Columnes, files i píndola de la pàgina; None si la pàgina no existeix."""
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if not 0 <= page_idx < len(pdf.pages):
                return None
            page = pdf.pages[page_idx]
            pill = _pill_box(page)
            boxes = []
            for c in page.curves:
                w = c["x1"] - c["x0"]
                h = c["bottom"] - c["top"]
                if CELL_W[0] <= w <= CELL_W[1] and CELL_H[0] <= h <= CELL_H[1]:
                    boxes.append((c["x0"], c["top"], c["x1"], c["bottom"]))
    except VisionError:
        raise
    except Exception as exc:
        raise VisionError(f"no s'ha pogut analitzar la pàgina {page_idx}: {exc}") from exc

    if not boxes:
        return PageGeometry(cols=[], rows=[], pill=pill)

    centers = _cluster([(b[0] + b[2]) / 2 for b in boxes], 15)
    tops = _cluster([b[1] for b in boxes], 12)
    bots = _cluster([b[3] for b in boxes], 12)
    cols: list[tuple[float, float]] = []
    for cx in centers:
        sel = [b for b in boxes if abs((b[0] + b[2]) / 2 - cx) <= 15]
        cols.append((min(b[0] for b in sel), max(b[2] for b in sel)))
    cols.sort()
    rows = [(tops[i], bots[i] if i < len(bots) else tops[i] + 108.0) for i in range(len(tops))]
    return PageGeometry(cols=cols, rows=rows, pill=pill)


def render_page(
    data: bytes, page_idx: int, *, scale: float = RENDER_SCALE
) -> tuple[Image.Image, tuple[float, float]]:
    """Renderitza la pàgina a una imatge PIL. Retorna (imatge, ample, alt) en punts."""
    try:
        doc = pdfium.PdfDocument(data)
        try:
            if not 0 <= page_idx < len(doc):
                raise VisionError(f"pàgina {page_idx} inexistent al PDF")
            page = doc[page_idx]
            pts = page.get_size()
            img = page.render(scale=scale).to_pil().convert("RGB")
        finally:
            doc.close()
    except VisionError:
        raise
    except Exception as exc:
        raise VisionError(f"no s'ha pogut renderitzar la pàgina {page_idx}: {exc}") from exc
    return img, (float(pts[0]), float(pts[1]))


def crop_box(
    img: Image.Image,
    page_pts: tuple[float, float],
    box: tuple[float, float, float, float],
    *,
    pad: float = 2.0,
) -> Image.Image:
    """Retalla una caixa (en punts PDF) de la pàgina renderitzada."""
    pw, ph = page_pts
    width, height = img.size
    x0, top, x1, bottom = box

    def px_x(v: float) -> int:
        return min(width, max(0, int((v - pad) / pw * width)))

    def px_y(v: float) -> int:
        return min(height, max(0, int((v - pad) / ph * height)))

    left, upper = px_x(x0), px_y(top)
    right, lower = px_x(x1), px_y(bottom)
    if right - left < 8 or lower - upper < 8:
        raise VisionError(f"retall buit per a la caixa {box}")
    return img.crop((left, upper, right, lower))


# --- Client d'Ollama ---------------------------------------------------------
def parse_json_obj(text: str) -> dict | None:
    """Primer objecte JSON del text (el model de vegades envolta la resposta)."""
    stripped = _WS_RE.sub(" ", text.strip().strip("`").strip())
    if stripped.lower().startswith("json"):
        stripped = stripped[4:].lstrip()
    start = stripped.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(stripped[start:])
    except ValueError:
        end = stripped.rfind("}")
        if end <= start:
            return None
        try:
            obj, _ = json.JSONDecoder().raw_decode(stripped[start : end + 1])
        except ValueError:
            return None
    return obj if isinstance(obj, dict) else None


class OllamaClient:
    """Client HTTP d'Ollama (`/api/chat` amb imatge), `temperature: 0`.

    Un `content` buit o no interpretable es considera fallada del motor: es
    reintenta un cop i, si persisteix, es llança `VisionError` (design D6/D8).
    """

    def __init__(
        self,
        *,
        url: str,
        model: str,
        timeout_s: float = 60.0,
        retries: int = 1,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.url = url
        self.model = model
        self.retries = retries
        self._http = httpx.Client(timeout=timeout_s, transport=transport)

    def ask_json(
        self, prompt: str, image: Image.Image, *, num_predict: int
    ) -> dict:
        buf = BytesIO()
        image.save(buf, format="PNG")
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(buf.getvalue()).decode()],
                }
            ],
            "options": {"temperature": 0, "num_predict": num_predict},
        }
        last = "sense resposta"
        for attempt in range(self.retries + 1):
            try:
                resp = self._http.post(self.url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                message = data.get("message") if isinstance(data, dict) else None
                content = str((message or {}).get("content") or "").strip()
                if not content:
                    last = f"resposta buida (done_reason={data.get('done_reason')})"
                else:
                    obj = parse_json_obj(content)
                    if obj is not None:
                        return obj
                    last = f"JSON no interpretable: {content[:120]!r}"
            except httpx.HTTPError as exc:
                last = str(exc)
            except ValueError as exc:
                last = f"resposta no JSON: {exc}"
            if attempt < self.retries:
                log.warning("Crida a Ollama fallida (%s); reintento.", last)
        raise VisionError(f"Ollama ({self.model}): {last}")


# --- Validació ----------------------------------------------------------------
def coerce_day(value) -> int | None:
    """Número de dia imprès tal com el torna el model (enter, float o text)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d{1,2})\s*", value)
        if match:
            return int(match.group(1))
    return None


def expected_days(target: date) -> set[int]:
    """Dies admesos a la cel·la: el real i els veïns (tolera l'errata d'origen)."""
    last = monthrange(target.year, target.month)[1]
    return {d for d in (target.day - 1, target.day, target.day + 1) if 1 <= d <= last}


def coerce_blocks(value) -> list[list[str]] | None:
    """Normalitza `blocs` del model. `[]` = cel·la buida; None = estructura dolenta."""
    if not isinstance(value, list):
        return None
    blocks: list[list[str]] = []
    for item in value:
        if isinstance(item, str):
            raw_lines = [item]
        elif isinstance(item, list):
            if not all(isinstance(line, str) for line in item):
                return None
            raw_lines = list(item)
        else:
            return None
        lines = [_WS_RE.sub(" ", line).strip() for line in raw_lines]
        blocks.append([line for line in lines if line])
    return blocks


def validate_blocks(blocks: list[list[str]]) -> str | None:
    """None si l'estructura és publicable; sinó, el motiu del descart."""
    if not 1 <= len(blocks) <= MAX_BLOCKS:
        return f"{len(blocks)} blocs (cal 1..{MAX_BLOCKS})"
    total = 0
    for block in blocks:
        if not block:
            return "bloc buit"
        for line in block:
            total += 1
            if len(line) > MAX_LINE_LEN:
                return f"línia de {len(line)} caràcters (màxim {MAX_LINE_LEN})"
            if any(ord(ch) < 32 for ch in line):
                return "caràcter de control"
    if not 1 <= total <= MAX_LINES:
        return f"{total} línies (cal 1..{MAX_LINES})"
    if not any(ch.isalnum() for block in blocks for line in block for ch in line):
        return "cap caràcter alfabètic ni numèric"
    return None


def _anchor_row_candidates(target: date, n_rows: int) -> list[int]:
    """Files a provar, en ordre: candidats de dilluns de fila 0 (design D4).

    Es generen els dilluns de les setmanes que toquen el mes de `target` (de
    l'1 del mes cap endavant són els primers: la hipòtesi més probable és que
    la fila 0 sigui la setmana de l'1) i es tradueixen a índex de fila.
    """
    first = date(target.year, target.month, 1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    monday0 = first - timedelta(days=first.weekday())
    target_monday = target - timedelta(days=target.weekday())
    out: list[int] = []
    anchor = monday0
    while anchor <= last:  # el mes toca com a màxim 6 setmanes
        delta = (target_monday - anchor).days
        if delta % 7 == 0 and 0 <= delta // 7 < n_rows:
            out.append(delta // 7)
        anchor += timedelta(days=7)
    return out


# --- Motor de visió ----------------------------------------------------------
class OllamaVision:
    """Localitza la cel·la del dia (i la pàgina de la variant) i la llegeix.

    `ask_json` és substituïble per tests (design D9): qualsevol objecte amb
    `ask_json(prompt, image, num_predict=...) -> dict`.
    """

    def __init__(
        self,
        *,
        url: str,
        model: str,
        timeout_s: float = 60.0,
        markers: dict[str, list[str]] | None = None,
        client: object | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.client = client or OllamaClient(
            url=url, model=model, timeout_s=timeout_s, transport=transport
        )
        self.markers = {
            str(vid): [_WS_RE.sub(" ", str(m)).strip().upper() for m in mlist]
            for vid, mlist in (markers or {}).items()
            if mlist
        }

    # --- variant → pàgina ---------------------------------------------------
    def detect_pages(self, data: bytes) -> dict[str, int]:
        """Mapa variant → pàgina llegint el segell de cada pàgina amb rejilla.

        Les pàgines sense rejilla (infografia, propostes de sopars) es descarten
        sense cap crida al model. Les variants no configurades amb marcadors
        no es busquen aquí.
        """
        if not self.markers:
            return {}
        try:
            with pdfplumber.open(BytesIO(data)) as pdf:
                n_pages = len(pdf.pages)
        except Exception as exc:
            raise VisionError(f"PDF il·legible: {exc}") from exc

        found: dict[str, int] = {}
        for idx in range(n_pages):
            if all(vid in found for vid in self.markers):
                break
            geo = page_geometry(data, idx)
            if geo is None or not geo.has_grid or geo.pill is None:
                continue  # pàgina que no és calendari: es descarta (spec)
            img, page_pts = render_page(data, idx)
            crop = crop_box(img, page_pts, geo.pill, pad=1.0)
            try:
                payload = self.client.ask_json(P_PILL, crop, num_predict=NUM_PREDICT_PILL)
            except VisionError as exc:
                raise VisionError(f"segell de la pàgina {idx}: {exc}") from exc
            text = _WS_RE.sub(" ", str(payload.get("text") or "")).upper().strip()
            if not text:
                continue
            for vid, markers in self.markers.items():
                if vid in found:
                    continue
                if any(marker in text for marker in markers):
                    found[vid] = idx
                    log.info("Variant %s detectada a la pàgina %d (segell %r).", vid, idx, text)
        return found

    def _page_for(
        self, data: bytes, *, variant_id: str | None, fallback_page: int, cache: dict[str, int]
    ) -> int:
        if variant_id and variant_id in cache:
            return int(cache[variant_id])
        found = self.detect_pages(data)
        if variant_id:
            cache.update(found)
            if variant_id in cache:
                return int(cache[variant_id])
            if found:
                raise VisionError(f"cap pàgina del PDF correspon a la variant {variant_id!r}")
        # Cap segell llegible: ús de la pàgina configurada si té rejilla i
        # no l'ha reclamada una altra variant (design D5).
        if 0 <= fallback_page and fallback_page not in found.values():
            geo = page_geometry(data, fallback_page)
            if geo is not None and geo.has_grid:
                log.warning(
                    "Segell de variant llegible; s'usa la pàgina configurada %d per a %s.",
                    fallback_page,
                    variant_id,
                )
                if variant_id:
                    cache[variant_id] = fallback_page
                return fallback_page
        raise VisionError(f"cap pàgina amb rejilla per a la variant {variant_id!r}")

    # --- cel·la del dia -----------------------------------------------------
    def extract_plates(
        self,
        data: bytes,
        target: date,
        *,
        variant_id: str | None = None,
        fallback_page: int = 0,
        page_cache: dict[str, int] | None = None,
    ) -> list[list[str]] | None:
        """Plats de `target` llegits per visió; None si la cel·la és buida.

        Llança `VisionError` davant una fallada del motor o si cap candidat de
        fila valida el dia imprès (mai retorna contingut no validat).
        """
        if target.weekday() > 4:
            return None
        cache: dict[str, int] = page_cache if page_cache is not None else {}
        page = self._page_for(
            data, variant_id=variant_id, fallback_page=fallback_page, cache=cache
        )
        geo = page_geometry(data, page)
        if geo is None:
            raise VisionError(f"pàgina {page} inexistent al PDF")
        if not geo.has_grid:
            raise VisionError(f"la pàgina {page} no té rejilla de cel·les")

        img, page_pts = render_page(data, page)
        lo, hi = geo.cols[target.weekday()]
        allowed = expected_days(target)
        saw_empty = False

        for row_idx in _anchor_row_candidates(target, len(geo.rows))[:MAX_CELL_CALLS]:
            top, bottom = geo.rows[row_idx]
            crop = crop_box(img, page_pts, (lo, top, hi, bottom))
            payload = self.client.ask_json(P_CELL, crop, num_predict=NUM_PREDICT_CELL)
            day = coerce_day(payload.get("dia"))
            blocks = coerce_blocks(payload.get("blocs"))
            if blocks is None:
                log.warning("Estructura inesperada del model a la fila %d.", row_idx)
                continue
            if day is None or day not in allowed:
                if day is None and not blocks:
                    saw_empty = True
                log.info(
                    "Fila %d descartada: dia imprès %r, s'esperava %s.",
                    row_idx,
                    day,
                    sorted(allowed),
                )
                continue
            if not blocks:
                log.info("Cel·la de %s buida (fila %d).", target, row_idx)
                return None
            reason = validate_blocks(blocks)
            if reason:
                log.warning("Estructura invàlida (%s) a la fila %d.", reason, row_idx)
                continue
            return blocks

        if saw_empty:
            log.warning("Cel·la buida a la fila de %s; no es publica cap menú.", target)
            return None
        raise VisionError(
            f"cap fila del calendari valida el dia imprès per al {target.isoformat()}"
        )
