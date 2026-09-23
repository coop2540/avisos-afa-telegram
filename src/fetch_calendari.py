"""Fetcher del calendari del curs (pàgina HTML amb seccions de dates)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .http_util import fetch_text
from .logging_setup import get_logger

log = get_logger(__name__)

_CONTENT_SELECTORS = [".entry-content", "main", "article", "#content", "body"]
_HEADING_TAGS = ["h2", "h3", "h4", "h5"]
_WS_RE = re.compile(r"\s+")


@dataclass
class CalendariContent:
    normalized_text: str
    sections: list[str] = field(default_factory=list)


def _select_container(soup: BeautifulSoup):
    for selector in _CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return soup


def normalize_text(text: str) -> str:
    """Normalitza espais i línies buides per a una comparació estable."""
    lines = [_WS_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_calendari(html: str) -> CalendariContent:
    """Extreu el text normalitzat i els títols de secció del calendari."""
    soup = BeautifulSoup(html, "html.parser")
    container = _select_container(soup)
    sections = [
        _WS_RE.sub(" ", h.get_text(" ", strip=True)).strip()
        for h in container.find_all(_HEADING_TAGS)
        if h.get_text(strip=True)
    ]
    normalized = normalize_text(container.get_text("\n", strip=True))
    return CalendariContent(normalized_text=normalized, sections=sections)


def hash_content(normalized_text: str) -> str:
    """Hash estable del contingut normalitzat (prefix sha256:)."""
    digest = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def fetch_calendari(*, url: str, user_agent: str) -> CalendariContent:
    """Descarrega i extreu el contingut del calendari."""
    html = fetch_text(url, user_agent=user_agent)
    return extract_calendari(html)
