"""Tests del filtratge i la planificació de l'agenda (tasca 11.2, 11.5)."""

from datetime import date, datetime, timezone

from src.agenda import events_in_week, filter_events, should_post_weekly, week_bounds, weekly_slot
from src.config import AgendaConfig
from src.parse_carta import CartaEvent


def _events():
    return [
        CartaEvent(date(2026, 9, 8), "Tothom", "Comença el curs"),
        CartaEvent(date(2026, 9, 11), "Tothom", "Festiu"),
        CartaEvent(date(2026, 9, 15), "I4", "Reunió de famílies (15h)"),
        CartaEvent(date(2026, 9, 16), "3r", "Reunió de famílies (15h)"),
        CartaEvent(date(2026, 9, 21), "Famílies", "Reunió del menjador"),
        CartaEvent(date(2026, 9, 22), "I4B", "Agermanament"),
    ]


def test_filter_by_curso_and_shared():
    selected = filter_events(_events(), ["I4", "Tothom", "Famílies"])
    assert {(e.curs, e.activitat) for e in selected} == {
        ("Tothom", "Comença el curs"),
        ("Tothom", "Festiu"),
        ("I4", "Reunió de famílies (15h)"),
        ("Famílies", "Reunió del menjador"),
        ("I4B", "Agermanament"),  # I4 inclou I4B
    }


def test_filter_single_curso_excludes_others():
    selected = filter_events(_events(), ["I4"])
    assert {e.curs for e in selected} == {"I4", "I4B"}


def test_filter_empty_cursos_returns_all():
    assert len(filter_events(_events(), [])) == len(_events())


def test_week_bounds():
    start, end = week_bounds(date(2026, 9, 23))  # dimecres
    assert start == date(2026, 9, 21)  # dilluns
    assert end == date(2026, 9, 27)  # diumenge


def test_events_in_week_filters_and_sorts():
    week = events_in_week(_events(), date(2026, 9, 23))
    assert [e.date.day for e in week] == [21, 22]


def test_weekly_slot_disabled():
    cfg = AgendaConfig(enabled=False, weekly_enabled=True)
    now = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    assert weekly_slot(now, cfg) is None
    assert should_post_weekly(now, cfg, None) is False


def test_should_post_before_and_after_slot():
    cfg = AgendaConfig(enabled=True, weekly_enabled=True, weekly_day=1, weekly_time=(8, 0))
    before = datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)  # dilluns 07:00
    after = datetime(2026, 9, 21, 9, 0, tzinfo=timezone.utc)  # dilluns 09:00
    assert should_post_weekly(before, cfg, None) is False
    assert should_post_weekly(after, cfg, None) is True


def test_should_not_post_twice_same_week():
    cfg = AgendaConfig(enabled=True, weekly_enabled=True, weekly_day=1, weekly_time=(8, 0))
    now = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    slot = weekly_slot(now, cfg)
    assert should_post_weekly(now, cfg, slot.isoformat()) is False
    # Un post de la setmana anterior sí que permet publicar
    previous = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)
    assert should_post_weekly(now, cfg, previous.isoformat()) is True
