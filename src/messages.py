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
_WS_RE = re.compile(r"[ \t\u00a0]+")

# Etiquetes de bloc: separen línies (no s'han de "enganxar" al text del costat).
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "td", "th", "table",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section", "article", "pre",
}

PARSE_MODE = "HTML"


def _esc(value: str) -> str:
    return html.escape(value or "", quote=False)


def _html_to_lines(raw: str) -> list[str]:
    """Converteix HTML en línies de text pla, respectant paràgrafs i llistes."""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(True):
        if tag.name in _BLOCK_TAGS:
            tag.insert_before("\n")
            tag.insert_after("\n")
    text = soup.get_text("")
    lines = [_WS_RE.sub(" ", ln).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def plain_summary(raw: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    """Converteix un resum HTML del feed en text pla curt, conservant línies.

    Els paràgrafs i els elements de llista es mantenen com a línies separades
    (útil per a resums que són llistes de dates o passos).
    """
    if not raw:
        return ""
    text = "\n".join(_html_to_lines(raw))
    if len(text) > max_chars:
        cut = text[: max_chars - 1]
        # Si podem, tallem en un salt de línia per no deixar mitja línia.
        last_nl = cut.rfind("\n")
        if last_nl >= max_chars * 0.5:
            cut = cut[:last_nl]
        text = cut.rstrip() + "…"
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


def _event_line(event) -> str:
    """Línia d'un esdeveniment (data dd/mm · activitat)."""
    return f"• {event.date.strftime('%d/%m')} · {_esc(event.activitat)}"


def carta_filtrada_message(events, carta_url: str, lang: str = DEFAULT_LANG) -> str:
    """Selecció d'activitats del curs amb enllaç a la carta completa."""
    lines = [
        f"📚 <b>{_esc(translate('carta.title', lang))}</b>",
        _esc(translate("carta.filtrada_intro", lang)),
    ]
    lines.extend(_event_line(e) for e in events)
    lines.append(
        f'<a href="{_esc(carta_url)}">{_esc(translate("carta.full_link", lang))}</a>'
    )
    return "\n".join(lines)


def agenda_message(events, week_start, week_end, carta_url: str | None, lang: str = DEFAULT_LANG) -> str:
    """Agenda setmanal amb els actes de la setmana."""
    lines = [
        f"📅 <b>{_esc(translate('agenda.title', lang))}</b>",
        _esc(f"{week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}"),
    ]
    if events:
        lines.extend(_event_line(e) for e in events)
    else:
        lines.append(_esc(translate("agenda.empty", lang)))
    if carta_url:
        lines.append(
            f'<a href="{_esc(carta_url)}">{_esc(translate("agenda.full_link", lang))}</a>'
        )
    return "\n".join(lines)


def menu_dema_message(plates, target, variant_id: str, lang: str = DEFAULT_LANG) -> str:
    """Missatge diari «Demà dinem …» amb la data i els plats (sense enllaç).

    `plates` és una llista de blocs (cada bloc, una llista de línies); els
    blocs se separen amb una línia en blanc per llegir-los com al PDF.
    """
    title = translate("menu.title", lang, data=target.strftime("%d/%m"))
    lines = [f"🍽️ <b>{_esc(title)}</b>"]
    label = translate(f"menu.variant.{variant_id}", lang)
    if label and label != f"menu.variant.{variant_id}":
        lines.append(f"<i>{_esc(label)}</i>")

    if plates and isinstance(plates[0], str):
        plates = [list(plates)]  # compatibilitat amb una llista de línies planes
    for i, block in enumerate(plates):
        if i:
            lines.append("")
        lines.extend(_esc(line) for line in block)
    return "\n".join(lines)


def menu_pin_message(pdf_url: str, lang: str = DEFAULT_LANG) -> str:
    """Missatge anunciat amb l'enllaç al PDF del menú del mes vigent."""
    return (
        f"📎 <b>{_esc(translate('menu.pin_title', lang))}</b>\n"
        f'<a href="{_esc(pdf_url)}">{_esc(translate("menu.pin_link", lang))}</a>'
    )
