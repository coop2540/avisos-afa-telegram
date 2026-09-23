"""Plantilles de missatge (format avís + enllaç, HTML).

Els textos surten dels catàlegs d'idioma (`src/i18n/*.json`); aquí només es
composa el format HTML. Vegeu specs/telegram-publish i specs/service-i18n.
"""

from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

from .i18n import DEFAULT_LANG, translate

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


def carta_message(url: str, lang: str = DEFAULT_LANG) -> str:
    return (
        f"📚 <b>{_esc(translate('carta.title', lang))}</b>\n"
        f"{_esc(translate('carta.body', lang))}\n"
        f'<a href="{_esc(url)}">{_esc(translate("carta.link", lang))}</a>'
    )


def noticia_message(title: str, summary: str, link: str, lang: str = DEFAULT_LANG) -> str:
    lines = [f"📣 <b>{_esc(title)}</b>"]
    clean = plain_summary(summary)
    if clean:
        lines.append(_esc(clean))
    if link:
        lines.append(
            f'<a href="{_esc(link)}">{_esc(translate("noticia.read_more", lang))}</a>'
        )
    return "\n".join(lines)


def calendari_message(url: str, lang: str = DEFAULT_LANG) -> str:
    return (
        f"📅 <b>{_esc(translate('calendari.title', lang))}</b>\n"
        f"{_esc(translate('calendari.body', lang))}\n"
        f'<a href="{_esc(url)}">{_esc(translate("calendari.link", lang))}</a>'
    )


def welcome_message(lang: str = DEFAULT_LANG) -> str:
    return (
        f"🐝 <b>{_esc(translate('welcome.title', lang))}</b>\n"
        f"{_esc(translate('welcome.body', lang))}\n"
        f"{_esc(translate('welcome.start', lang))}"
    )
