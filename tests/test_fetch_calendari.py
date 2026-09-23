"""Tests d'extracció i hash del calendari (tasca 3.3)."""

from tests.conftest import FIXTURES

from src.fetch_calendari import extract_calendari, hash_content


def _html():
    return (FIXTURES / "calendari.html").read_text(encoding="utf-8")


def test_extract_sections():
    content = extract_calendari(_html())
    assert "Inici de curs:" in content.sections
    assert "Dies festius de lliure disposició:" in content.sections
    assert "Fi de curs:" in content.sections


def test_normalized_text_has_dates():
    content = extract_calendari(_html())
    assert "2 de novembre de 2026" in content.normalized_text
    assert "21 de juny de 2027" in content.normalized_text


def test_hash_is_stable_for_same_html():
    a = hash_content(extract_calendari(_html()).normalized_text)
    b = hash_content(extract_calendari(_html()).normalized_text)
    assert a == b
    assert a.startswith("sha256:")


def test_hash_changes_when_date_changes():
    original = hash_content(extract_calendari(_html()).normalized_text)
    modified_html = _html().replace("2 de novembre de 2026", "3 de novembre de 2026")
    modified = hash_content(extract_calendari(modified_html).normalized_text)
    assert original != modified


def test_hash_ignores_whitespace_noise():
    original = hash_content(extract_calendari(_html()).normalized_text)
    noisy = _html().replace("<h4>", "<h4>   \n   ")
    assert hash_content(extract_calendari(noisy).normalized_text) == original
