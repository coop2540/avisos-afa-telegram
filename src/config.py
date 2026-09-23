"""Carrega de configuració (YAML + variables d'entorn).

Els secrets (token del bot) viuen NOMÉS a variables d'entorn o `.env`;
la resta de paràmetres són a `config.yaml`. Vegeu `config.yaml.example`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .i18n import DEFAULT_LANG, normalize_language
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
    user_agent: str = "avisos-afa-telegram/0.1"


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
class AutoRejectConfig:
    enabled: bool = False
    block_empty_name: bool = True
    block_spam_bio: bool = True


@dataclass
class ApprovalConfig:
    enabled: bool = False
    receive: str = "polling"  # polling | webhook
    webhook_url: str | None = None
    webhook_secret: str | None = None
    auto_reject: AutoRejectConfig = field(default_factory=AutoRejectConfig)

    def validate(self) -> None:
        if self.enabled and self.receive not in {"polling", "webhook"}:
            raise ConfigError(
                f"telegram.approval.receive ha de ser 'polling' o 'webhook' (és '{self.receive}')."
            )
        if self.enabled and self.receive == "webhook" and not self.webhook_url:
            raise ConfigError(
                "telegram.approval.receive=webhook requereix telegram.approval.webhook.url."
            )


@dataclass
class TelegramConfig:
    chat_id: str | None = None
    token: str | None = None
    dry_run: bool = False
    topics: dict[str, int | None] = field(default_factory=dict)
    admin_chat_id: str | None = None
    approval: ApprovalConfig = field(default_factory=ApprovalConfig)

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
class AgendaConfig:
    enabled: bool = False
    cursos: list[str] = field(default_factory=list)
    carta_filtrada: bool = True
    weekly_enabled: bool = False
    weekly_day: int = 1  # 1=dilluns … 7=diumenge
    weekly_time: tuple[int, int] = (8, 0)


@dataclass
class Config:
    site: SiteConfig
    rss: RssConfig
    carta: CartaConfig
    poll: PollConfig
    telegram: TelegramConfig
    first_run: FirstRunConfig
    agenda: AgendaConfig = field(default_factory=AgendaConfig)
    language: str = DEFAULT_LANG
    timezone: str = "Europe/Madrid"
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


def _parse_hhmm(value: Any, default: tuple[int, int] = (8, 0)) -> tuple[int, int]:
    """Converteix 'HH:MM' en (hora, minut); si no és vàlid, retorna el defecte."""
    if not value:
        return default
    match = re.match(r"^(\d{1,2}):(\d{2})$", str(value).strip())
    if not match:
        return default
    hour, minute = int(match.group(1)), int(match.group(2))
    if 0 <= hour < 24 and 0 <= minute < 60:
        return (hour, minute)
    return default


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
        user_agent=str(site_raw.get("user_agent") or "avisos-afa-telegram/0.1"),
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

    approval_raw = _section(tg_raw, "approval")
    ar_raw = _section(approval_raw, "auto_reject")
    webhook_raw = _section(approval_raw, "webhook")
    approval = ApprovalConfig(
        enabled=_as_bool(approval_raw.get("enabled"), False),
        receive=str(approval_raw.get("receive") or "polling").strip().lower(),
        webhook_url=(str(webhook_raw["url"]) if webhook_raw.get("url") else None),
        webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET") or None,
        auto_reject=AutoRejectConfig(
            enabled=_as_bool(ar_raw.get("enabled"), False),
            block_empty_name=_as_bool(ar_raw.get("block_empty_name"), True),
            block_spam_bio=_as_bool(ar_raw.get("block_spam_bio"), True),
        ),
    )
    approval.validate()

    telegram = TelegramConfig(
        chat_id=str(tg_raw["chat_id"]) if tg_raw.get("chat_id") else None,
        token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
        dry_run=_as_bool(os.environ.get("DRY_RUN"), default=False),
        topics={str(k): (int(v) if v is not None else None) for k, v in topics_raw.items()},
        admin_chat_id=(str(tg_raw["admin_chat_id"]) if tg_raw.get("admin_chat_id") else None),
        approval=approval,
    )
    env_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if env_chat_id:
        telegram.chat_id = env_chat_id
    env_admin = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    if env_admin:
        telegram.admin_chat_id = env_admin

    first_run = FirstRunConfig(
        publish_welcome=_as_bool(_section(raw, "first_run").get("publish_welcome"), False)
    )

    agenda_raw = _section(raw, "agenda")
    setmanal_raw = _section(agenda_raw, "setmanal")
    weekly_day = int(setmanal_raw.get("dia", 1))
    if not 1 <= weekly_day <= 7:
        weekly_day = 1
    agenda = AgendaConfig(
        enabled=_as_bool(agenda_raw.get("enabled"), False),
        cursos=[str(c) for c in (agenda_raw.get("cursos") or [])],
        carta_filtrada=_as_bool(agenda_raw.get("carta_filtrada"), True),
        weekly_enabled=_as_bool(setmanal_raw.get("enabled"), False),
        weekly_day=weekly_day,
        weekly_time=_parse_hhmm(setmanal_raw.get("hora")),
    )

    language = normalize_language(os.environ.get("LANGUAGE") or raw.get("language"))

    tz_name = str(raw.get("timezone") or os.environ.get("TZ") or "Europe/Madrid")

    state_path = Path(os.environ.get("STATE_PATH") or DEFAULT_STATE_PATH)

    cfg = Config(
        site=site,
        rss=rss,
        carta=carta,
        poll=poll,
        telegram=telegram,
        first_run=first_run,
        agenda=agenda,
        language=language,
        timezone=tz_name,
        state_path=state_path,
        config_path=path,
    )
    log.info(
        "Configuració carregada de %s (destí=%s, idioma=%s, dry_run=%s)",
        path,
        cfg.telegram.chat_id or "<sense destí>",
        cfg.language,
        cfg.telegram.dry_run,
    )
    return cfg
