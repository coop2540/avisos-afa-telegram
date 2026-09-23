"""Tests de les plantilles de missatge en català (tasca 4.3)."""

from src.messages import (
    calendari_message,
    carta_message,
    noticia_message,
    plain_summary,
    welcome_message,
)


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


def test_welcome_message_mentions_afa():
    assert "AFA" in welcome_message()
