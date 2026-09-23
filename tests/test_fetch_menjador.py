"""Tests del fetcher de l'enllaç del menú del menjador (tasques 2.1, 2.2)."""

from src.fetch_menjador import resolve_menu_url

from tests.conftest import FIXTURES

BASE = "https://agora.xtec.cat/escolaelisabadia"
MARKERS = ["basal", "menu"]
EXCLUDES = ["carta", "calendari", "funcionament", "preus", "que-cal-portar"]


def _resolve(html: str) -> str | None:
    return resolve_menu_url(
        html, base_url=BASE, link_markers=MARKERS, fallback_href_excludes=EXCLUDES
    )


def test_resolves_real_page_fixture():
    html = (FIXTURES / "menjador.html").read_text(encoding="utf-8")
    url = _resolve(html)
    assert url is not None
    assert url.endswith("Basal-escolar_merged.pdf")
    assert "/2026/09/" in url


def test_marker_match_ignores_carta_and_calendari():
    html = """
    <a href="/uploads/2026/09/Carta-mes-Setembre-26.pdf">CARTA DEL MES</a>
    <a href="/uploads/2026/07/26-27-Calendari-1.pdf">CALENDARI ESCOLAR</a>
    <a href="/uploads/2026/09/Basal-escolar_merged.pdf"></a>
    """
    url = _resolve(html)
    assert url is not None
    assert url.endswith("Basal-escolar_merged.pdf")


def test_fallback_first_non_excluded_when_no_marker():
    html = """
    <a href="/uploads/preus.pdf">Preus</a>
    <a href="/uploads/menjador.pdf">Menjador</a>
    """
    # cap marcador coincideix amb cap href (preus i menjador) → fallback primer no exclòs
    url = resolve_menu_url(
        html, base_url=BASE, link_markers=["zzz"], fallback_href_excludes=EXCLUDES
    )
    assert url.endswith("/uploads/menjador.pdf")


def test_no_pdf_returns_none():
    assert _resolve("<p>Sense enllaços</p>") is None


def test_relative_url_resolved_against_base():
    html = '<a href="wp-content/uploads/x/Menu-octubre.pdf"></a>'
    url = _resolve(html)
    assert url == f"{BASE}/wp-content/uploads/x/Menu-octubre.pdf"
