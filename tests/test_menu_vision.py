"""Tests del mòdul de visió del menú (canvi menu-vision, tasques 2.x/4.x/5.1).

Cap test depèn d'un Ollama real: el client es prova amb `httpx.MockTransport`
i l'extracció amb un motor fals (design D9).
"""

from datetime import date
from io import BytesIO

import httpx
import pytest

from src.menu_vision import (
    P_CELL,
    P_PILL,
    OllamaClient,
    OllamaVision,
    VisionError,
    _anchor_row_candidates,
    coerce_blocks,
    coerce_day,
    expected_days,
    page_geometry,
    parse_json_obj,
    render_page,
    validate_blocks,
)
from src.parse_menu import parse_menu_pdf
from tests.conftest import FIXTURES

OCT = FIXTURES / "menu_octubre_2026.pdf"
SET = FIXTURES / "menu_setembre_2026.pdf"

CELL_OCT8 = {
    "dia": 8,
    "blocs": [
        ["CIGRONS AMB HORTALISSES"],
        ["WOK DE POLLASTRE AMB VERDURES"],
        ["PA BLANC"],
        ["FRUITA ÀCIDA"],
    ],
}


class FakeEngine:
    """Motor fals: respon amb una llista guionitzada de càrregues."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # prompts, en ordre

    def ask_json(self, prompt, image, *, num_predict):
        self.calls.append(prompt)
        if not self.responses:
            raise AssertionError(f"crida inesperada: {prompt[:40]!r}")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    @property
    def cell_calls(self) -> int:
        return sum(1 for p in self.calls if p == P_CELL)

    @property
    def pill_calls(self) -> int:
        return sum(1 for p in self.calls if p == P_PILL)


# --- 2.1 geometria i renderitzat ---------------------------------------------


def test_geometry_set_p0_has_five_columns_and_pill():
    geo = page_geometry(SET.read_bytes(), 0)
    assert geo is not None
    assert geo.has_grid
    assert len(geo.cols) == 5
    assert len(geo.rows) == 4
    assert geo.pill is not None


def test_geometry_oct_calendar_pages_have_pill_others_are_skipped():
    data = OCT.read_bytes()
    p0 = page_geometry(data, 0)
    assert p0.has_grid and p0.pill is not None
    # Pàgina 1 (infografia) i 2 (sopars): sense píndola / sense rejilla.
    assert page_geometry(data, 1).pill is None
    assert not page_geometry(data, 2).has_grid
    p3 = page_geometry(data, 3)
    assert p3.has_grid and p3.pill is not None
    p4 = page_geometry(data, 4)
    assert p4.has_grid and p4.pill is not None
    # La píndola de p4 (al·lèrgies) és més llarga que la de p0 (BASAL).
    assert p4.pill[2] - p4.pill[0] > p0.pill[2] - p0.pill[0]


def test_geometry_out_of_range_page_is_none():
    assert page_geometry(SET.read_bytes(), 99) is None


def test_render_and_crop_works():
    data = OCT.read_bytes()
    geo = page_geometry(data, 0)
    img, pts = render_page(data, 0)
    assert img.size[0] > 1000
    assert pts[0] > 500
    from src.menu_vision import crop_box

    crop = crop_box(img, pts, geo.pill, pad=1.0)
    assert crop.size[0] > 20 and crop.size[1] > 10


# --- 2.2 client d'Ollama ------------------------------------------------------


def _client(handler, retries=1):
    return OllamaClient(
        url="http://ollama.test/api/chat",
        model="qwen3-vl:2b",
        timeout_s=5.0,
        retries=retries,
        transport=httpx.MockTransport(handler),
    )


def _img():
    from PIL import Image

    return Image.new("RGB", (32, 32), "white")


def test_client_returns_json_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"message": {"content": '{"dia": 8, "blocs": []}'}, "done_reason": "stop"}
        )

    obj = _client(handler).ask_json("hola", _img(), num_predict=10)
    assert obj == {"dia": 8, "blocs": []}


def test_client_retries_and_raises_on_empty_content():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"message": {"content": ""}, "done_reason": "length"})

    with pytest.raises(VisionError, match="resposta buida"):
        _client(handler, retries=1).ask_json("hola", _img(), num_predict=10)
    assert len(calls) == 2  # intent inicial + 1 reintento


def test_client_raises_on_uninterpretable_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "no puc llegir-ho"}})

    with pytest.raises(VisionError, match="JSON"):
        _client(handler, retries=0).ask_json("hola", _img(), num_predict=10)


def test_client_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model carregant"})

    with pytest.raises(VisionError):
        _client(handler, retries=1).ask_json("hola", _img(), num_predict=10)


def test_client_raises_on_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timeout")

    with pytest.raises(VisionError, match="timeout"):
        _client(handler, retries=1).ask_json("hola", _img(), num_predict=10)


def test_parse_json_obj_tolerates_prose_and_fences():
    assert parse_json_obj('{"a": 1}') == {"a": 1}
    assert parse_json_obj("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert parse_json_obj("Resposta: {\"dia\": null} gràcies") == {"dia": None}
    assert parse_json_obj("sense json") is None


# --- 2.3 validació ------------------------------------------------------------


def test_coerce_day_accepts_int_float_and_text():
    assert coerce_day(8) == 8
    assert coerce_day(8.0) == 8
    assert coerce_day(" 8 ") == 8
    assert coerce_day(True) is None
    assert coerce_day("vuit") is None
    assert coerce_day(None) is None


def test_expected_days_tolerates_one_day_but_drops_invalid():
    assert expected_days(date(2026, 10, 8)) == {7, 8, 9}
    assert expected_days(date(2026, 10, 1)) == {1, 2}
    assert expected_days(date(2026, 9, 30)) == {29, 30}


def test_coerce_blocks_shapes():
    assert coerce_blocks([["A"], ["B", "C"]]) == [["A"], ["B", "C"]]
    assert coerce_blocks(["A", "B"]) == [["A"], ["B"]]  # llista plana acceptada
    assert coerce_blocks([]) == []
    assert coerce_blocks("no soc llista") is None
    assert coerce_blocks([[1, 2]]) is None
    assert coerce_blocks(None) is None


def test_validate_blocks_ok_and_rejections():
    assert validate_blocks([["CREMA", "PA"], ["POSTRE"]]) is None
    assert validate_blocks([]) is not None  # 0 blocs
    assert validate_blocks([["A"]] * 9) is not None  # 9 blocs
    assert validate_blocks([["A"] * 9]) is not None  # 9 línies
    assert validate_blocks([["X" * 200]]) is not None  # línia massa llarga
    assert validate_blocks([["!!! ???"]]) is not None  # res alfabètic
    assert validate_blocks([["\x07 ringing"]]) is not None  # caràcter de control
    assert validate_blocks([[]]) is not None  # bloc buit


def test_validate_blocks_counts_lines_across_blocks():
    # 4 blocs de 2 línies = 8 línies → ok; 5 blocs de 2 = 10 → rebutjat.
    assert validate_blocks([[f"L{i}a", f"L{i}b"] for i in range(4)]) is None
    assert validate_blocks([[f"L{i}a", f"L{i}b"] for i in range(5)]) is not None


# --- 2.4 candidats d'ancoratge -------------------------------------------------


def test_anchor_candidates_october_and_september():
    # Octubre: la fila 0 del PDF és la setmana 28/9-4/10 → dilluns 7 = fila 1.
    assert _anchor_row_candidates(date(2026, 10, 7), 5) == [1, 0]
    assert _anchor_row_candidates(date(2026, 10, 1), 5) == [0]
    # Setembre (rejilla que comença a la setmana 7): prova files de més amunt.
    assert _anchor_row_candidates(date(2026, 9, 24), 4) == [3, 2, 1, 0]


# --- 2.4/2.5 extracció amb motor fals -----------------------------------------


MARKERS = {"basal": ["BASAL"], "sense_porc": ["NO PORC", "SENSE PORC"]}


def _vision(responses, markers=None, **kw):
    return OllamaVision(
        url="http://x", model="m",
        markers={"basal": ["BASAL"]} if markers is None else markers,
        client=FakeEngine(responses), **kw,
    )


def test_extract_uses_correct_row_in_one_call():
    engine = _vision([CELL_OCT8])
    cache = {"basal": 0}  # pàgina ja coneguda: sense detecció de segell
    blocks = engine.extract_plates(
        OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache=cache
    )
    assert blocks == CELL_OCT8["blocs"]
    assert engine.client.cell_calls == 1


def test_extract_discards_wrong_row_then_accepts_next_candidate():
    wrong = {"dia": 14, "blocs": [["CONTINGUT DE LA FILTA EQUIVOCADA"]]}
    engine = _vision([wrong, CELL_OCT8])
    blocks = engine.extract_plates(
        OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache={"basal": 0}
    )
    assert blocks == CELL_OCT8["blocs"]
    assert engine.client.cell_calls == 2


def test_extract_raises_when_no_candidate_validates():
    wrong = {"dia": 14, "blocs": [["RES"]]}
    engine = _vision([wrong, wrong])
    with pytest.raises(VisionError, match="cap fila"):
        engine.extract_plates(
            OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache={"basal": 0}
        )


def test_extract_empty_cell_is_resolved_not_an_error():
    engine = _vision([{"dia": None, "blocs": []}])
    assert (
        engine.extract_plates(
            OCT.read_bytes(), date(2026, 10, 1), variant_id="basal", page_cache={"basal": 0}
        )
        is None
    )
    assert engine.client.cell_calls == 1


def test_extract_bad_structure_keeps_trying_and_fails():
    bad = {"dia": 8, "blocs": "no soc llista"}
    engine = _vision([bad, bad])
    with pytest.raises(VisionError):
        engine.extract_plates(
            OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache={"basal": 0}
        )


def test_extract_engine_failure_propagates_as_vision_error():
    engine = _vision([VisionError("Ollama caigut")])
    with pytest.raises(VisionError, match="Ollama caigut"):
        engine.extract_plates(
            OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache={"basal": 0}
        )


def test_extract_weekend_makes_no_calls():
    engine = _vision([])
    assert engine.extract_plates(OCT.read_bytes(), date(2026, 10, 11)) is None
    assert engine.client.calls == []


def test_extract_reads_the_detected_page_not_the_configured_one():
    # `sense_porc` configurada a la pàgina 1 (infografia); la real és la 3.
    engine = _vision([CELL_OCT8])
    cache = {"sense_porc": 3}
    blocks = engine.extract_plates(
        OCT.read_bytes(), date(2026, 10, 8), variant_id="sense_porc", page_cache=cache
    )
    assert blocks == CELL_OCT8["blocs"]


# --- 2.5 detecció de variant pel segell ---------------------------------------


def test_detect_pages_maps_seals_and_skips_non_calendar_pages():
    engine = _vision([{"text": "BASAL"}, {"text": "NO PORC"}], markers=MARKERS)
    found = engine.detect_pages(OCT.read_bytes())
    assert found == {"basal": 0, "sense_porc": 3}
    # p1 (sense píndola) i p2 (sense rejilla) no es van intentar; p4 es va
    # aturar aviat perquè totes les variants ja estaven trobades.
    assert engine.client.pill_calls == 2


def test_detect_pages_missing_variant_raises_and_ignores_configured_index():
    engine = _vision(
        [{"text": "BASAL"}, {"text": "NO PORC"}, {"text": "AL·LÈRGIA A L'OU"}],
        markers={"basal": ["BASAL"], "sense_porc": ["SENSE PORC"]},
    )
    with pytest.raises(VisionError, match="cap pàgina"):
        engine.extract_plates(
            OCT.read_bytes(), date(2026, 10, 8), variant_id="sense_porc", page_cache={}
        )


def test_detect_pages_fallback_to_configured_page_when_no_seals():
    # Sense marcadors no es llegeix cap segell → fallback a la pàgina `page:`
    # sempre que tingui rejilla (design D5).
    engine = _vision([CELL_OCT8], markers={})
    cache: dict[str, int] = {}
    blocks = engine.extract_plates(
        OCT.read_bytes(), date(2026, 10, 8), variant_id="basal",
        fallback_page=0, page_cache=cache,
    )
    assert blocks == CELL_OCT8["blocs"]
    assert cache == {"basal": 0}
    assert engine.client.pill_calls == 0


def test_page_cache_is_reused_so_the_seal_is_read_once():
    engine = _vision([{"text": "BASAL"}, {"text": "NO PORC"}, CELL_OCT8], markers=MARKERS)
    cache: dict[str, int] = {}
    engine.extract_plates(OCT.read_bytes(), date(2026, 10, 8), variant_id="basal", page_cache=cache)
    first = engine.client.pill_calls
    assert first == 2
    # Segona extracció amb la mateixa URL: memòria de la pàgina, 0 segells nous.
    engine.client.responses.append(CELL_OCT8)
    engine.extract_plates(OCT.read_bytes(), date(2026, 10, 7), variant_id="basal", page_cache=cache)
    assert engine.client.pill_calls == first
    assert cache == {"basal": 0, "sense_porc": 3}


# --- 4.1 integració amb parse_menu_pdf ----------------------------------------


def test_parse_october_pdf_without_vision_returns_none():
    assert (
        parse_menu_pdf(OCT.read_bytes(), date(2026, 10, 8), page=0, source_url="https://x/2026/10/m.pdf")
        is None
    )


def test_parse_october_pdf_with_fake_engine_returns_oct8_plates():
    engine = _vision([{"text": "BASAL"}, {"text": "NO PORC"}, CELL_OCT8], markers=MARKERS)
    blocks = parse_menu_pdf(
        OCT.read_bytes(),
        date(2026, 10, 8),
        page=0,  # índex configurat: la detecció ho hauria de corregir igual
        source_url="https://agora.xtec.cat/escolaelisabadia/wp-content/uploads/usu667/2026/10/x.pdf",
        vision=engine,
        variant_id="basal",
        page_cache={},
    )
    assert blocks == CELL_OCT8["blocs"]
    assert engine.client.cell_calls == 1


def test_parse_september_pdf_never_calls_the_engine():
    engine = _vision([])
    blocks = parse_menu_pdf(
        SET.read_bytes(),
        date(2026, 9, 24),
        page=0,
        source_url="https://x/2026/09/m.pdf",
        vision=engine,
        variant_id="basal",
        page_cache={},
    )
    assert blocks is not None
    assert engine.client.calls == []  # ruta de texte: cap crida al model


def test_parse_without_text_and_without_vision_is_resolved_empty():
    # Sense visió configurada: no es publica, però no és un error (None resolt).
    assert parse_menu_pdf(OCT.read_bytes(), date(2026, 10, 8), page=0) is None


def test_parse_engine_failure_raises_instead_of_returning_none():
    engine = _vision([VisionError("Ollama apagat")])
    with pytest.raises(VisionError):
        parse_menu_pdf(
            OCT.read_bytes(),
            date(2026, 10, 8),
            page=0,
            source_url="https://x/2026/10/m.pdf",
            vision=engine,
            variant_id="basal",
            page_cache={},
        )


def test_parse_falls_back_to_vision_when_text_has_no_headers():
    # Pàgina 1 (infografia): pot tenir paraules però no capçaleres de rejilla.
    engine = _vision([{"text": "BASAL"}, {"text": "NO PORC"}, CELL_OCT8], markers=MARKERS)
    blocks = parse_menu_pdf(
        OCT.read_bytes(),
        date(2026, 10, 8),
        page=1,
        source_url="https://x/2026/10/m.pdf",
        vision=engine,
        variant_id="basal",
        page_cache={},
    )
    assert blocks == CELL_OCT8["blocs"]
