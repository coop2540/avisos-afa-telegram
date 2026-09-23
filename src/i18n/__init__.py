"""Internacionalització (i18n): textos del servei separats del codi.

Els catàlegs són fitxers JSON a aquesta carpeta (`ca.json`, `es.json`,
`en.json`, …). Afegir un idioma = afegir un fitxer. Vegeu `docs/guia-telegram.md`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..logging_setup import get_logger

log = get_logger(__name__)

CATALOG_DIR = Path(__file__).parent
DEFAULT_LANG = "ca"


def _catalog_files() -> dict[str, Path]:
    return {p.stem: p for p in CATALOG_DIR.glob("*.json")}


@lru_cache(maxsize=None)
def available_languages() -> tuple[str, ...]:
    """Codis d'idioma disponibles (segons els fitxers de catàleg)."""
    langs = sorted(_catalog_files())
    return tuple(langs) if langs else (DEFAULT_LANG,)


@lru_cache(maxsize=None)
def _load(lang: str) -> dict[str, str]:
    path = _catalog_files().get(lang)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover
        log.error("Catàleg d'idioma '%s' il·legible: %s", lang, exc)
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def normalize_language(lang: str | None) -> str:
    """Retorna un idioma suportat; si no ho és, el per defecte."""
    if not lang:
        return DEFAULT_LANG
    code = lang.strip().lower().split("-")[0].split("_")[0]
    return code if code in available_languages() else DEFAULT_LANG


def translate(key: str, lang: str | None = None, **kwargs) -> str:
    """Tradueix una clau amb format opcional; cau al català i, si no, a la clau."""
    code = normalize_language(lang)
    template = _load(code).get(key)
    if template is None:
        template = _load(DEFAULT_LANG).get(key, key)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):  # pragma: no cover - plantilla mal formada
        return template


class Translator:
    """Traductor lligat a un idioma (per passar-lo còmodament)."""

    def __init__(self, lang: str | None = None) -> None:
        self.lang = normalize_language(lang)

    def __call__(self, key: str, **kwargs) -> str:
        return translate(key, self.lang, **kwargs)
