"""Tests de resolució de l'enllaç de la carta del mes (tasca 3.2)."""

from tests.conftest import FIXTURES

from src.fetch_carta import resolve_carta_url

BASE = "https://agora.xtec.cat/escolaelisabadia"
MARKERS = ["carta del mes", "consulteu la carta"]
FALLBACK = ["carta-mes"]


def _resolve(html: str):
    return resolve_carta_url(
        html, base_url=BASE, link_text_markers=MARKERS, fallback_href_contains=FALLBACK
    )


def test_resolves_from_homepage_fixture():
    html = (FIXTURES / "homepage.html").read_text(encoding="utf-8")
    url = _resolve(html)
    assert url == f"{BASE}/wp-content/uploads/usu667/2026/09/Carta-mes-Setembre-26.pdf"


def test_fallback_by_href_when_text_does_not_match():
    html = '<a href="wp-content/uploads/usu667/2026/09/Carta-mes-Octubre-26.pdf">Mira això</a>'
    assert _resolve(html).endswith("/Carta-mes-Octubre-26.pdf")


def test_relative_href_is_absolutized():
    html = '<a href="wp-content/uploads/usu667/2026/09/Carta-mes-Novembre-26.pdf">Consulteu la carta del mes</a>'
    assert _resolve(html) == f"{BASE}/wp-content/uploads/usu667/2026/09/Carta-mes-Novembre-26.pdf"


def test_returns_none_when_absent():
    assert _resolve("<html><body><a href='/algo.pdf'>Res</a></body></html>") is None


def test_ignores_non_pdf_marker_link():
    html = '<a href="/categoria/afa/">La carta del mes</a>'
    # No acaba en .pdf ni conté "carta" a l'URL -> no hauria de retornar res
    assert _resolve(html) is None
