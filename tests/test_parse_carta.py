"""Tests del parser de la carta (tasca 11.1)."""

from datetime import date

from tests.conftest import FIXTURES

from src.parse_carta import (
    build_carta_data,
    parse_carta_tables,
    parse_carta_text,
)


def _text():
    return (FIXTURES / "carta_text.txt").read_text(encoding="utf-8")


def test_parse_title_month_year():
    month, year, _rows = parse_carta_text(_text())
    assert month == 9
    assert year == 2026


def test_parse_rows():
    _m, _y, rows = parse_carta_text(_text())
    assert len(rows) == 12
    assert rows[0] == (8, "Tothom", "Comença el curs escolar 26-27")
    assert rows[2] == (15, "I4", "Reunió de famílies (15h)")
    assert rows[-1] == (29, "I3", "Reunió de famílies (15:30h)")


def test_build_events_with_dates():
    carta = build_carta_data(_text(), source_url="https://x.test/carta.pdf")
    assert carta.month == 9 and carta.year == 2026
    assert len(carta.events) == 12
    first = carta.events[0]
    assert first.date == date(2026, 9, 8)
    assert first.curs == "Tothom"
    assert "Comença el curs" in first.activitat


def test_parse_title_handles_apostrophe():
    # Alguns mesos venen amb «D'OCTUBRE» (apòstrof) en lloc de «DE OCTUBRE».
    for text in ("CARTA DEL MES D’OCTUBRE 2026", "CARTA DEL MES D'OCTUBRE 2026"):
        month, year, _rows = parse_carta_text(text)
        assert (month, year) == (10, 2026)


def test_parse_tables_handles_multiword_curs_and_day_ranges():
    tables = [
        [
            ["Dia", "Curs", "Activitat"],
            [
                "1\n5 al 9\n12",
                "2n - 6è\nCM i CS\nTothom",
                "Activitat d’agermanament\nSetmana d’apadrinaments\nFestiu",
            ],
        ]
    ]
    rows = parse_carta_tables(tables)
    assert rows == [
        (1, "2n - 6è", "Activitat d’agermanament"),
        (5, "CM i CS", "Setmana d’apadrinaments"),
        (12, "Tothom", "Festiu"),
    ]


def test_build_carta_data_prefers_structured_tables():
    text = "CARTA DEL MES D’OCTUBRE 2026\nDia Curs Activitat\n1 Tothom Festiu"
    tables = [
        [
            ["Dia", "Curs", "Activitat"],
            ["1\n2", "2n - 6è\nTothom", "Agermanament\nFestiu"],
        ]
    ]
    carta = build_carta_data(text, tables=tables)
    assert carta.month == 10 and carta.year == 2026
    assert [(e.date.day, e.curs) for e in carta.events] == [(1, "2n - 6è"), (2, "Tothom")]


def test_parse_tables_ignores_non_carta_tables():
    tables = [[["Nom", "Preu"], ["A", "1"]]]
    assert parse_carta_tables(tables) == []


def test_no_table_returns_no_events():
    carta = build_carta_data("CARTA DEL MES DE SETEMBRE 2026\nSense taula aquí.")
    assert carta.month == 9 and carta.year == 2026
    assert carta.events == []


def test_no_title_returns_no_events():
    carta = build_carta_data("Dia Curs Activitat\n8 Tothom Festiu")
    assert carta.month is None
    assert carta.events == []
