"""Orquestrador del servei: cicle fetch → diff → publicar → estat → dormir."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .agenda import events_in_week, filter_events, should_post_weekly, week_bounds
from .config import Config, load_config
from .fetch_calendari import fetch_calendari, hash_content
from .fetch_carta import fetch_carta_url
from .fetch_rss import fetch_rss
from .http_util import FetchError
from .logging_setup import get_logger, setup_logging
from .messages import (
    agenda_message,
    calendari_message,
    carta_filtrada_message,
    carta_message,
    noticia_message,
    welcome_message,
)
from .parse_carta import load_carta
from .scheduler import next_interval_minutes
from .state import State
from .telegram_out import TelegramClient

log = get_logger(__name__)


def _local_tz(cfg: Config):
    try:
        return ZoneInfo(cfg.timezone)
    except Exception:
        log.warning("Zona horària '%s' no vàlida; s'usa UTC.", cfg.timezone)
        return timezone.utc


def _carta_text(cfg: Config, carta_url: str) -> str:
    """Missatge de carta: selecció del curs si l'agenda ho permet, si no enllaç."""
    if cfg.agenda.enabled and cfg.agenda.carta_filtrada:
        try:
            carta = load_carta(carta_url, user_agent=cfg.site.user_agent)
            events = filter_events(carta.events, cfg.agenda.cursos)
            if events:
                return carta_filtrada_message(events, carta_url, cfg.language)
            log.info("Carta sense activitats del curs; s'envia només l'enllaç.")
        except Exception as exc:  # xarxa o parseig del PDF
            log.error("No s'ha pogut processar la carta per a l'agenda: %s", exc)
    return carta_message(carta_url, cfg.language)


def maybe_publish_weekly(cfg: Config, state: State, client: TelegramClient, now: datetime) -> int:
    """Publica l'agenda setmanal si toca. Retorna 1 si s'ha publicat, 0 si no."""
    if not (cfg.agenda.enabled and cfg.agenda.weekly_enabled):
        return 0
    local = now.astimezone(_local_tz(cfg))
    if not should_post_weekly(local, cfg.agenda, state.last_weekly_post):
        return 0
    carta_url = state.carta_url
    if not carta_url:
        return 0
    try:
        carta = load_carta(carta_url, user_agent=cfg.site.user_agent)
    except Exception as exc:
        log.error("Agenda: no s'ha pogut llegir la carta (%s); es reintentarà.", exc)
        return 0
    events = events_in_week(filter_events(carta.events, cfg.agenda.cursos), local.date())
    if not events:
        log.info("Agenda setmanal: cap acte aquesta setmana; s'omet.")
        state.last_weekly_post = local.isoformat()
        return 0
    start, end = week_bounds(local.date())
    text = agenda_message(events, start, end, carta_url, cfg.language)
    res = client.send_message(text, thread_id=cfg.telegram.thread_id_for("agenda"))
    if res.ok:
        state.last_weekly_post = local.isoformat()
        log.info("Publicada agenda setmanal (%d actes).", len(events))
        return 1
    log.error("No s'ha pogut publicar l'agenda setmanal; es reintentarà.")
    return 0


@dataclass
class CycleResult:
    published: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    baseline: bool = False


def seed_baseline(cfg: Config, state: State, client: TelegramClient) -> CycleResult:
    """Primera execució: desa la línia base sense abocar l'històric.

    Només es marca com a feta si totes les fonts responen; si alguna falla,
    es reintenta al proper cicle (les fonts que sí responen són idempotents).
    """
    result = CycleResult(baseline=True)
    all_ok = True

    try:
        items = fetch_rss(
            cfg.site.feed,
            user_agent=cfg.site.user_agent,
            include_categories=cfg.rss.include_categories,
            max_items=cfg.rss.max_items_per_cycle,
        )
        for item in items:
            state.remember_rss(item.guid)
        state.clear_error("rss")
        log.info("Línia base RSS: %d elements recordats (sense publicar).", len(items))
    except FetchError as exc:
        all_ok = False
        result.errors.append(f"rss: {exc}")
        state.bump_error("rss")
        log.error("Línia base RSS fallida: %s", exc)

    try:
        url = fetch_carta_url(
            homepage=cfg.site.homepage,
            base_url=cfg.site.base_url,
            user_agent=cfg.site.user_agent,
            link_text_markers=cfg.carta.link_text_markers,
            fallback_href_contains=cfg.carta.fallback_href_contains,
        )
        if url:
            state.carta_url = url
        state.clear_error("carta")
        log.info("Línia base carta: %s", url or "<no trobada>")
    except FetchError as exc:
        all_ok = False
        result.errors.append(f"carta: {exc}")
        state.bump_error("carta")
        log.error("Línia base carta fallida: %s", exc)

    try:
        content = fetch_calendari(url=cfg.site.calendari_page, user_agent=cfg.site.user_agent)
        state.cal_hash = hash_content(content.normalized_text)
        state.clear_error("calendari")
        log.info("Línia base calendari: %s", state.cal_hash)
    except FetchError as exc:
        all_ok = False
        result.errors.append(f"calendari: {exc}")
        state.bump_error("calendari")
        log.error("Línia base calendari fallida: %s", exc)

    if all_ok:
        state.baseline_done = True
    else:
        log.warning("Línia base incompleta; es reintentarà al proper cicle.")
    state.save(cfg.state_path)

    if all_ok and cfg.first_run.publish_welcome:
        res = client.send_message(
            welcome_message(cfg.language), thread_id=cfg.telegram.thread_id_for("default")
        )
        if res.ok:
            result.published += 1
        else:
            result.failed += 1

    return result


def run_cycle(
    cfg: Config,
    state: State,
    client: TelegramClient,
    *,
    now: datetime | None = None,
) -> CycleResult:
    """Un cicle complet de sondeig i publicació."""
    now = now or datetime.now(timezone.utc)
    result = CycleResult()
    changed = False

    # --- RSS ---
    try:
        items = fetch_rss(
            cfg.site.feed,
            user_agent=cfg.site.user_agent,
            include_categories=cfg.rss.include_categories,
            max_items=cfg.rss.max_items_per_cycle,
        )
        state.clear_error("rss")
        for item in items:
            if state.knows_rss(item.guid):
                continue
            res = client.send_message(
                noticia_message(item.title, item.summary, item.link, cfg.language),
                thread_id=cfg.telegram.thread_id_for("rss"),
            )
            if res.ok:
                state.remember_rss(item.guid)
                result.published += 1
                changed = True
                log.info("Publicada notícia: %s", item.title)
            else:
                result.failed += 1
                state.bump_error("rss")
                log.error("No s'ha pogut publicar la notícia '%s'; es reintentarà.", item.title)
                break  # no inundar si Telegram falla
    except FetchError as exc:
        result.errors.append(f"rss: {exc}")
        state.bump_error("rss")
        log.error("Error obtenint RSS: %s", exc)

    # --- Carta ---
    try:
        carta_url = fetch_carta_url(
            homepage=cfg.site.homepage,
            base_url=cfg.site.base_url,
            user_agent=cfg.site.user_agent,
            link_text_markers=cfg.carta.link_text_markers,
            fallback_href_contains=cfg.carta.fallback_href_contains,
        )
        state.clear_error("carta")
        if carta_url:
            if state.carta_url is None:
                state.carta_url = carta_url  # línia base tardana
                log.info("Línia base carta fixada: %s", carta_url)
            elif carta_url != state.carta_url:
                res = client.send_message(
                    _carta_text(cfg, carta_url),
                    thread_id=cfg.telegram.thread_id_for("carta"),
                )
                if res.ok:
                    state.carta_url = carta_url
                    result.published += 1
                    changed = True
                    log.info("Publicada carta nova: %s", carta_url)
                else:
                    result.failed += 1
                    state.bump_error("carta")
    except FetchError as exc:
        result.errors.append(f"carta: {exc}")
        state.bump_error("carta")
        log.error("Error obtenint la carta: %s", exc)

    # --- Calendari ---
    try:
        content = fetch_calendari(url=cfg.site.calendari_page, user_agent=cfg.site.user_agent)
        state.clear_error("calendari")
        new_hash = hash_content(content.normalized_text)
        if state.cal_hash is None:
            state.cal_hash = new_hash  # línia base tardana
            log.info("Línia base calendari fixada: %s", new_hash)
        elif new_hash != state.cal_hash:
            res = client.send_message(
                calendari_message(cfg.site.calendari_page, cfg.language),
                thread_id=cfg.telegram.thread_id_for("calendari"),
            )
            if res.ok:
                state.cal_hash = new_hash
                result.published += 1
                changed = True
                log.info("Publicat canvi de calendari: %s", new_hash)
            else:
                result.failed += 1
                state.bump_error("calendari")
    except FetchError as exc:
        result.errors.append(f"calendari: {exc}")
        state.bump_error("calendari")
        log.error("Error obtenint el calendari: %s", exc)

    # --- Agenda setmanal (si toca) ---
    weekly = maybe_publish_weekly(cfg, state, client, now)
    if weekly:
        result.published += weekly
        changed = True

    if changed:
        state.mark_change()
    state.save(cfg.state_path)
    return result


def run_once(
    cfg: Config,
    *,
    state: State | None = None,
    client: TelegramClient | None = None,
) -> CycleResult:
    """Executa un únic cicle (útil per a cron o proves)."""
    cfg.validate_for_run()
    state = state or State.load(cfg.state_path)
    owns_client = client is None
    client = client or TelegramClient(
        cfg.telegram.token, cfg.telegram.chat_id, dry_run=cfg.telegram.dry_run
    )
    try:
        if not state.baseline_done:
            return seed_baseline(cfg, state, client)
        return run_cycle(cfg, state, client)
    finally:
        if owns_client:
            client.close()


def run_forever(cfg: Config) -> None:
    """Bucle principal amb sondeig adaptatiu."""
    cfg.validate_for_run()
    state = State.load(cfg.state_path)
    with TelegramClient(
        cfg.telegram.token, cfg.telegram.chat_id, dry_run=cfg.telegram.dry_run
    ) as client:
        if not state.baseline_done:
            res = seed_baseline(cfg, state, client)
            log.info(
                "Línia base: publicats=%d fallits=%d errors=%s",
                res.published,
                res.failed,
                res.errors or "-",
            )
        while True:
            res = run_cycle(cfg, state, client)
            log.info(
                "Cicle: publicats=%d fallits=%d errors=%s",
                res.published,
                res.failed,
                res.errors or "-",
            )
            minutes = next_interval_minutes(state, cfg.poll)
            log.info("Proper sondeig en %d minuts.", minutes)
            time.sleep(minutes * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Servei d'avisos AFA Escola Elisa Badia")
    parser.add_argument("--config", default=None, help="Ruta a config.yaml")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa un sol cicle i surt (per a cron o proves).",
    )
    args = parser.parse_args(argv)

    # Carrega `.env` (si existeix) sense sobreescriure variables ja definides.
    load_dotenv()
    setup_logging()
    try:
        cfg = load_config(args.config)
    except Exception as exc:  # ConfigError i similars
        log.error("No s'ha pogut carregar la configuració: %s", exc)
        return 2

    if args.once:
        res = run_once(cfg)
        log.info(
            "Cicle únic: publicats=%d fallits=%d errors=%s",
            res.published,
            res.failed,
            res.errors or "-",
        )
        return 0 if not res.errors else 1

    try:
        run_forever(cfg)
    except KeyboardInterrupt:
        log.info("Aturat per l'usuari.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
