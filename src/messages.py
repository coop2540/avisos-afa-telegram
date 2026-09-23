"""Plantilles de missatge en català (format avís + enllaç, HTML).

Vegeu specs/telegram-publish: missatges breus, en català, sense IA.
"""

from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

MAX_SUMMARY_CHARS = 300
_WS_RE = re.compile(r"\s+")

PARSE_MODE = "HTML"


def _esc(value: str) -> str:
    return html.escape(value or "", quote=False)


def plain_summary(raw: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    """Converteix un resum HTML del feed en text pla curt."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def carta_message(url: str) -> str:
    return (
        "📚 <b>Carta del mes</b>\n"
        "Ja està publicada la carta del mes del centre.\n"
        f'<a href="{_esc(url)}">Obrir la carta</a>'
    )


def noticia_message(title: str, summary: str, link: str) -> str:
    lines = [f"📣 <b>{_esc(title)}</b>"]
    clean = plain_summary(summary)
    if clean:
        lines.append(_esc(clean))
    if link:
        lines.append(f'<a href="{_esc(link)}">Llegir més</a>')
    return "\n".join(lines)


def calendari_message(url: str) -> str:
    return (
        "📅 <b>Calendari del curs actualitzat</b>\n"
        "Hi ha canvis al calendari escolar del centre.\n"
        f'<a href="{_esc(url)}">Veure el calendari</a>'
    )


def welcome_message() -> str:
    return (
        "🐝 <b>Servei d'avisos de l'AFA</b>\n"
        "Aquest canal publica avisos del centre a partir de la seva web pública.\n"
        "Comença ara."
    )
