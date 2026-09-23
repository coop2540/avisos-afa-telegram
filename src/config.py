"""Carrega de configuració (YAML + variables d'entorn).

Els secrets (token del bot) viuen NOMÉS a variables d'entorn o `.env`;
la resta de paràmetres són a `config.yaml`. Vegeu `config.yaml.example`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .logging_setup import get_logger

log = get_logger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_STATE_PATH = "state/state.json"


class ConfigError(Exception):
    """Configuració absent, il·legible o invàlida."""


@dataclass
class SiteConfig:
    base_url: str
    homepage: str
    feed: str
    calendari_page: str
    user_agent: str = "afa-elisabadia-avisos/0.1"


@dataclass
class RssConfig:
    include_categories: list[str] = field(default_factory=list)
    max_items_per_cycle: int = 10


@dataclass
class CartaConfig:
    link_text_markers: list[str] = field(default_factory=lambda: ["carta del mes"])
    fallback_href_contains: list[str] = field(default_factory=lambda: ["carta-mes"])


@dataclass
class PollConfig:
    base_minutes: int = 60
    hot_minutes: int = 20
    hot_window_minutes: int = 180
    calm_minutes: int = 240
    quiet_after_days: int = 7


@dataclass
class TelegramConfig:
    chat_id: str | None = None
    token: str | None = None
    dry_run: bool = False
    topics: dict[str, int | None] = field(default_factory=dict)

    def thread_id_for(self, source: str) -> int | None:
        """Retorna el message_thread_id per a un origen, amb fallback a `default`."""
        value = self.topics.get(source)
        if value is None:
            value = self.topics.get("default")
        return value


@dataclass
class FirstRunConfig:
    publish_welcome: bool = False


@dataclass
class Config:
    site: SiteConfig
    rss: RssConfig
    carta: CartaConfig
    poll: PollConfig
    telegram: TelegramConfig
    first_run: FirstRunConfig
    state_path: Path = Path(DEFAULT_STATE_PATH)
    config_path: Path | None = None

    def validate_for_run(self) -> None:
        """Comprova els requisits mínims per executar un cicle real."""
        if not self.telegram.dry_run:
            if not self.telegram.token:
                raise ConfigError(
                    "Falta TELEGRAM_BOT_TOKEN. Defineix-lo a `.env` o activa DRY_RUN=1."
                )
            if not self.telegram.chat_id:
                raise ConfigError(
                    "Falta telegram.chat_id a config.yaml (o TELEGRAM_CHAT_ID)."
                )


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key) or {}
    if not isinstance(value, dict):
        raise ConfigError(f"La secció '{key}' de la configuració ha de ser un mapa.")
    return value


def load_config(config_path: str | Path | None = None) -> Config:
    """Carrega la configuració des de YAML i aplica overrides d'entorn."""
    path = Path(config_path or os.environ.get("CONFIG_PATH") or DEFAULT_CONFIG_PATH)
    if not path.exists():
        raise ConfigError(
            f"No s'ha trobat la configuració a '{path}'. Copia config.yaml.example."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - missatge d'error
        raise ConfigError(f"YAML invàlid a '{path}': {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"La configuració de '{path}' ha de ser un mapa.")

    site_raw = _section(raw, "site")
    for required in ("base_url", "homepage", "feed", "calendari_page"):
        if not site_raw.get(required):
            raise ConfigError(f"Falta 'site.{required}' a '{path}'.")

    site = SiteConfig(
        base_url=str(site_raw["base_url"]).rstrip("/"),
        homepage=str(site_raw["homepage"]),
        feed=str(site_raw["feed"]),
        calendari_page=str(site_raw["calendari_page"]),
        user_agent=str(site_raw.get("user_agent") or "afa-elisabadia-avisos/0.1"),
    )

    rss_raw = _section(raw, "rss")
    rss = RssConfig(
        include_categories=[str(c) for c in (rss_raw.get("include_categories") or [])],
        max_items_per_cycle=int(rss_raw.get("max_items_per_cycle", 10)),
    )

    carta_raw = _section(raw, "carta")
    carta = CartaConfig(
        link_text_markers=[
            str(m) for m in (carta_raw.get("link_text_markers") or ["carta del mes"])
        ],
        fallback_href_contains=[
            str(m) for m in (carta_raw.get("fallback_href_contains") or ["carta-mes"])
        ],
    )

    poll_raw = _section(raw, "poll")
    poll = PollConfig(
        base_minutes=int(poll_raw.get("base_minutes", 60)),
        hot_minutes=int(poll_raw.get("hot_minutes", 20)),
        hot_window_minutes=int(poll_raw.get("hot_window_minutes", 180)),
        calm_minutes=int(poll_raw.get("calm_minutes", 240)),
        quiet_after_days=int(poll_raw.get("quiet_after_days", 7)),
    )

    tg_raw = _section(raw, "telegram")
    topics_raw = tg_raw.get("topics") or {}
    if not isinstance(topics_raw, dict):
        raise ConfigError("'telegram.topics' ha de ser un mapa origen→thread_id.")
    telegram = TelegramConfig(
        chat_id=str(tg_raw["chat_id"]) if tg_raw.get("chat_id") else None,
        token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
        dry_run=_as_bool(os.environ.get("DRY_RUN"), default=False),
        topics={str(k): (int(v) if v is not None else None) for k, v in topics_raw.items()},
    )
    env_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if env_chat_id:
        telegram.chat_id = env_chat_id

    first_run = FirstRunConfig(
        publish_welcome=_as_bool(_section(raw, "first_run").get("publish_welcome"), False)
    )

    state_path = Path(os.environ.get("STATE_PATH") or DEFAULT_STATE_PATH)

    cfg = Config(
        site=site,
        rss=rss,
        carta=carta,
        poll=poll,
        telegram=telegram,
        first_run=first_run,
        state_path=state_path,
        config_path=path,
    )
    log.info(
        "Configuració carregada de %s (destí=%s, dry_run=%s)",
        path,
        cfg.telegram.chat_id or "<sense destí>",
        cfg.telegram.dry_run,
    )
    return cfg
