"""Tests del parser de la carta (tasca 11.1)."""

from datetime import date

from tests.conftest import FIXTURES

from src.parse_carta import build_carta_data, parse_carta_text


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


def test_no_table_returns_no_events():
    carta = build_carta_data("CARTA DEL MES DE SETEMBRE 2026\nSense taula aquí.")
    assert carta.month == 9 and carta.year == 2026
    assert carta.events == []


def test_no_title_returns_no_events():
    carta = build_carta_data("Dia Curs Activitat\n8 Tothom Festiu")
    assert carta.month is None
    assert carta.events == []
