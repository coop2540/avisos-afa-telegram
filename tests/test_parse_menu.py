"""Tests del parser del menú del menjador (tasques 3.2–3.5)."""

from datetime import date

from src.parse_menu import (
    build_grid,
    cell_blocks,
    cell_words,
    parse_menu_pdf,
    plates_for_date,
    words_to_lines,
)

from tests.conftest import FIXTURES

PDF = FIXTURES / "menu_setembre_2026.pdf"
URL = "https://agora.xtec.cat/escolaelisabadia/wp-content/uploads/usu667/2026/09/Basal-escolar_merged.pdf"


def _load_words(page: int = 0):
    import pdfplumber

    with pdfplumber.open(PDF) as pdf:
        return pdf.pages[page].extract_words()


def test_pdf_has_three_pages():
    import pdfplumber

    with pdfplumber.open(PDF) as pdf:
        assert len(pdf.pages) == 3


def test_grid_columns_and_rows():
    grid = build_grid(_load_words(0), source_url=URL)
    assert grid is not None
    assert len(grid.columns) == 6  # 5 columnes + fronteres
    assert grid.month == 9
    assert grid.year == 2026
    # 4 files de setmana al setembre 2026 (7, 14, 21, 28)
    mondays = [m for m, _, _ in grid.rows]
    assert mondays == [7, 14, 21, 28]


def test_cell_line_order():
    words = _load_words(0)
    blocks = plates_for_date(words, date(2026, 9, 23), source_url=URL)
    assert blocks is not None
    flat = [ln for block in blocks for ln in block]
    assert any("CREMA DE CARBASSA" in ln for ln in flat)


def test_erratum_24_printed_as_25_resolves_by_column():
    """El dijous 24/09 està imprès com a «25»; ha de resoldre la cel·la de dijous."""
    words = _load_words(0)
    thursday = plates_for_date(words, date(2026, 9, 24), source_url=URL)
    friday = plates_for_date(words, date(2026, 9, 25), source_url=URL)
    assert thursday is not None and friday is not None
    thursday_text = " ".join(ln for b in thursday for ln in b)
    friday_text = " ".join(ln for b in friday for ln in b)
    # El dijous ha de contenir el plat del dia 24, no el de divendres 25.
    assert "GALL DINDI" in thursday_text
    assert "OUS AL FORN" in friday_text
    assert thursday != friday


def test_sense_porc_variant_page():
    """La pàgina 1 (sense porc) ha de donar cel·la o None net, mai excepció."""
    words = _load_words(1)
    result = plates_for_date(words, date(2026, 9, 23), source_url=URL)
    assert result is None or isinstance(result, list)


def test_weekend_has_no_cell():
    assert plates_for_date(_load_words(0), date(2026, 9, 26), source_url=URL) is None


def test_date_outside_month_returns_none():
    assert plates_for_date(_load_words(0), date(2026, 10, 15), source_url=URL) is None


def test_parse_menu_pdf_page_out_of_range():
    assert parse_menu_pdf(PDF.read_bytes(), date(2026, 9, 23), page=9, source_url=URL) is None


def test_parse_menu_pdf_illegible():
    assert parse_menu_pdf(b"not a pdf", date(2026, 9, 23), source_url=URL) is None


def test_words_to_lines_groups_by_top():
    words = [
        {"top": 10.0, "x0": 50.0, "x1": 60.0, "text": "HOLA"},
        {"top": 10.5, "x0": 62.0, "x1": 70.0, "text": "MÓN"},
        {"top": 30.0, "x0": 50.0, "x1": 55.0, "text": "ADEU"},
    ]
    assert words_to_lines(words) == ["HOLA MÓN", "ADEU"]


def test_glued_letters_are_joined_sense_porc_page():
    """La pagina 2 parte algunas palabras letra a letra; s'han d'unir."""
    words = _load_words(1)
    blocks = plates_for_date(words, date(2026, 9, 24), source_url=URL)
    assert blocks is not None
    joined = " ".join(ln for b in blocks for ln in b)
    assert "PA BLANC" in joined
    assert "FRUITA" in joined
    assert "P A B L" not in joined


def test_cell_blocks_groups_by_vertical_gap():
    """Les línies dins un bloc s'aproximen; entre blocs salta >14px."""
    words = _load_words(0)
    g = build_grid(words, source_url=URL)
    cell = cell_words(g, date(2026, 9, 24))
    assert cell is not None
    blocks = cell_blocks(cell)
    assert isinstance(blocks, list)
    assert all(isinstance(b, list) for b in blocks)
    assert len(blocks) >= 2
    first = " ".join(blocks[0])
    assert "MONGETA TENDRA I" in first
    assert "PATATA" in first
