"""Fetcher del RSS del blog del centre (`/feed/`)."""

from __future__ import annotations

from dataclasses import dataclass, field

import feedparser

from .http_util import fetch_bytes
from .logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class RssItem:
    guid: str
    title: str
    link: str
    summary: str = ""
    categories: list[str] = field(default_factory=list)
    published: str | None = None


def parse_feed(data: bytes) -> list[RssItem]:
    """Parseja el contingut RSS/Atom i retorna els elements en ordre d'aparició."""
    parsed = feedparser.parse(data)
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        log.warning("RSS il·legible o buit: %s", getattr(parsed, "bozo_exception", "?"))
        return []

    items: list[RssItem] = []
    for entry in parsed.entries:
        link = str(entry.get("link") or "")
        guid = str(entry.get("id") or link)
        if not guid:
            continue
        categories = [
            str(tag.get("term", "")).strip()
            for tag in (entry.get("tags") or [])
            if tag.get("term")
        ]
        # Preferim el contingut complet (content:encoded) perquè conserva
        # l'estructura (paràgrafs, llistes); el `description` sovint ve pla.
        summary = ""
        content = entry.get("content")
        if content:
            try:
                summary = str(content[0].get("value") or "")
            except (IndexError, AttributeError, TypeError):
                summary = ""
        if not summary:
            summary = str(entry.get("summary") or "")
        items.append(
            RssItem(
                guid=guid,
                title=str(entry.get("title") or "(sense títol)").strip(),
                link=link,
                summary=summary.strip(),
                categories=categories,
                published=entry.get("published"),
            )
        )
    return items


def _matches_category(item: RssItem, markers: list[str]) -> bool:
    normalized_markers = [m.strip().lower() for m in markers if m.strip()]
    if not normalized_markers:
        return True
    for category in item.categories:
        cat = category.strip().lower()
        for marker in normalized_markers:
            if cat == marker or cat.startswith(marker):
                return True
    return False


def select_items(items: list[RssItem], include_categories: list[str]) -> list[RssItem]:
    """Filtra elements per categories configurades (sense distingir majúscules).

    Un element sense categories no es publica si hi ha filtres actius.
    """
    if not include_categories:
        return list(items)
    return [item for item in items if _matches_category(item, include_categories)]


def fetch_rss(
    url: str,
    *,
    user_agent: str,
    include_categories: list[str],
    max_items: int = 10,
) -> list[RssItem]:
    """Descarrega, parseja i filtra el RSS. Retorna com a màxim `max_items`."""
    data = fetch_bytes(url, user_agent=user_agent)
    items = select_items(parse_feed(data), include_categories)
    return items[:max_items]
