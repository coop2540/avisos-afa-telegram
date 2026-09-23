"""Tests del calendari de dies no lectius (tasques 4.1, 4.2)."""

from datetime import date

from src.menu_calendar import is_school_day, parse_calendar_text

from tests.conftest import FIXTURES


def _real_calendar():
    text = (FIXTURES / "calendari_text_real.txt").read_text(encoding="utf-8")
    return parse_calendar_text(text)


def test_start_and_end_of_school_year():
    cal = _real_calendar()
    assert cal.start == date(2026, 9, 8)
    assert cal.end == date(2027, 6, 21)


def test_nadal_range_with_year_erratum():
    """La font diu «al 7 de gener de 2026» (errata): ha de ser 2027."""
    cal = _real_calendar()
    assert date(2026, 12, 21) in cal.non_school_days
    assert date(2027, 1, 7) in cal.non_school_days
    assert date(2027, 1, 8) not in cal.non_school_days


def test_same_month_range_february_and_march():
    cal = _real_calendar()
    # Setmana Santa: del 22 al 29 de març de 2027
    assert date(2027, 3, 22) in cal.non_school_days
    assert date(2027, 3, 29) in cal.non_school_days
    assert date(2027, 3, 30) not in cal.non_school_days


def test_free_disposition_days_and_local_holidays():
    cal = _real_calendar()
    assert date(2026, 11, 2) in cal.non_school_days
    assert date(2026, 12, 7) in cal.non_school_days
    assert date(2027, 5, 17) in cal.non_school_days


def test_intensive_period_is_not_added_as_non_school():
    """La jornada intensiva (del 7 al 21 de juny de 2027) NO és dia no lectiu."""
    cal = _real_calendar()
    # 9 de juny de 2027: dins el període d'intensiva però no en cap rang de vacances.
    assert date(2027, 6, 9) not in cal.non_school_days
    assert is_school_day(date(2027, 6, 9), cal) is True


def test_is_school_day_weekends_and_holidays():
    cal = _real_calendar()
    assert is_school_day(date(2026, 9, 23), cal) is True      # dimecres lectiu
    assert is_school_day(date(2026, 9, 26), cal) is False     # dissabte
    assert is_school_day(date(2026, 11, 2), cal) is False     # festiu lliure disposició
    assert is_school_day(date(2026, 12, 24), cal) is False    # dins Nadal
    assert is_school_day(date(2026, 7, 15), cal) is False     # fora de curs (estiu)


def test_is_school_day_without_calendar_only_filters_weekend():
    assert is_school_day(date(2026, 9, 23), None) is True
    assert is_school_day(date(2026, 9, 26), None) is False


def test_parse_from_calendari_html_fixture():
    """El text normalitzat de la pàgina de calendari real s'ha de poder parsejar."""
    from src.fetch_calendari import extract_calendari

    html = (FIXTURES / "calendari.html").read_text(encoding="utf-8")
    cal = parse_calendar_text(extract_calendari(html).normalized_text)
    assert date(2026, 11, 2) in cal.non_school_days
    assert date(2027, 1, 7) in cal.non_school_days
    assert date(2027, 1, 8) not in cal.non_school_days
