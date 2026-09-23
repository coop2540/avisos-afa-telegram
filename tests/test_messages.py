"""Tests de les plantilles de missatge en català (tasca 4.3, 11.3)."""

from datetime import date

from src.messages import (
    agenda_message,
    calendari_message,
    carta_filtrada_message,
    carta_message,
    menu_dema_message,
    menu_pin_message,
    noticia_message,
    plain_summary,
    welcome_message,
)
from src.parse_carta import CartaEvent


def test_carta_message_has_title_and_link():
    msg = carta_message("https://x.test/carta.pdf")
    assert "Carta del mes" in msg
    assert 'href="https://x.test/carta.pdf"' in msg


def test_noticia_message_strips_html_from_summary():
    msg = noticia_message(
        "Reunió d'I4",
        "<p>Reunió <b>important</b> el dia 15.</p>",
        "https://x.test/post",
    )
    assert "Reunió d&#x27;I4" in msg or "Reunió d'I4" in msg
    assert "<b>important</b>" not in msg
    assert "important" in msg
    assert 'href="https://x.test/post"' in msg


def test_noticia_escapes_html_in_title():
    msg = noticia_message("Títol <script>alert(1)</script>", "", "https://x.test")
    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg


def test_calendari_message_has_link():
    msg = calendari_message("https://x.test/cal")
    assert "Calendari del curs actualitzat" in msg
    assert 'href="https://x.test/cal"' in msg


def test_plain_summary_truncates():
    long = "paraula " * 100
    assert len(plain_summary(long, max_chars=50)) <= 50
    assert plain_summary(long, max_chars=50).endswith("…")


def test_plain_summary_preserves_list_lines():
    html = "<p>PREINSCRIPCIÓ</p><p>16.06 Llista d'espera</p><p>17.06 Llista d'admesos</p>"
    out = plain_summary(html)
    assert out.splitlines() == [
        "PREINSCRIPCIÓ",
        "16.06 Llista d'espera",
        "17.06 Llista d'admesos",
    ]


def test_plain_summary_keeps_inline_text_together():
    out = plain_summary("<p>Reunió <b>important</b> el dia 15</p>")
    assert out == "Reunió important el dia 15"


def test_plain_summary_truncates_on_line_boundary():
    html = "<p>" + "</p><p>".join(["Línia llarga " + str(i) for i in range(10)]) + "</p>"
    out = plain_summary(html, max_chars=60)
    assert out.endswith("…")
    # no ha de tallar a mitja línia si hi ha un salt de línia raonable
    assert not out.rstrip("…").endswith(" ")
    assert len(out) <= 60


def test_plain_summary_handles_br():
    out = plain_summary("a<br>b<br>c")
    assert out.splitlines() == ["a", "b", "c"]


def test_welcome_message_mentions_afa():
    assert "AFA" in welcome_message()


def test_carta_filtrada_message():
    events = [
        CartaEvent(date(2026, 9, 15), "I4", "Reunió de famílies (15h)"),
        CartaEvent(date(2026, 9, 21), "Famílies", "Reunió del menjador"),
    ]
    msg = carta_filtrada_message(events, "https://x.test/c.pdf")
    assert "El que toca al teu curs" in msg
    assert "15/09 · Reunió de famílies (15h)" in msg
    assert "21/09 · Reunió del menjador" in msg
    assert 'href="https://x.test/c.pdf"' in msg


def test_agenda_message_with_events():
    events = [CartaEvent(date(2026, 9, 21), "Famílies", "Reunió del menjador")]
    msg = agenda_message(events, date(2026, 9, 21), date(2026, 9, 27), "https://x.test/c.pdf")
    assert "Agenda de la setmana" in msg
    assert "21/09 – 27/09" in msg
    assert "21/09 · Reunió del menjador" in msg
    assert 'href="https://x.test/c.pdf"' in msg


def test_agenda_message_empty():
    msg = agenda_message([], date(2026, 9, 21), date(2026, 9, 27), "https://x.test/c.pdf")
    assert "no hi ha cap acte" in msg


def test_agenda_message_localized():
    msg = agenda_message([], date(2026, 9, 21), date(2026, 9, 27), None, "es")
    assert "Agenda de la semana" in msg


def test_menu_dema_message_has_date_plates_and_no_link():
    msg = menu_dema_message(
        ["CREMA DE CARBASSA", "MAGRA DE PORC", "PA INTEGRAL"],
        date(2026, 9, 24),
        "basal",
    )
    assert "Demà dinem 24/09" in msg
    assert "CREMA DE CARBASSA" in msg
    assert "PA INTEGRAL" in msg
    assert "href=" not in msg  # sense enllaç al PDF
    assert "Menú basal" in msg


def test_menu_dema_message_localized_es():
    msg = menu_dema_message(["PA"], date(2026, 9, 24), "sense_porc", "es")
    assert "Mañana comemos 24/09" in msg
    assert "Sin cerdo" in msg


def test_menu_dema_message_escapes_html():
    msg = menu_dema_message(["<script>alert(1)</script>"], date(2026, 9, 24), "basal")
    assert "<script>" not in msg
    assert "&lt;script&gt;" in msg


def test_menu_pin_message_has_link():
    msg = menu_pin_message("https://x.test/Basal-escolar_merged.pdf")
    assert "Menú del mes (PDF)" in msg
    assert 'href="https://x.test/Basal-escolar_merged.pdf"' in msg
