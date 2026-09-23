"""Lògica de publicació del menú diari: slot horari, data objectiu i cicle.

Separat de `main.py` per poder testar-ho amb rellotge simulat sense xarxa ni
Telegram. Vegeu specs/daily-menu i design.md D3/D4/D5.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .config import Config, MenuConfig
from .fetch_menjador import fetch_menu_url
from .logging_setup import get_logger
from .menu_calendar import SchoolCalendar, fetch_school_calendar, is_school_day
from .messages import menu_dema_message, menu_pin_message
from .parse_menu import load_menu
from .state import State
from .telegram_out import TelegramClient

log = get_logger(__name__)


def menu_target_date(now_local: datetime, calendar: SchoolCalendar | None) -> date | None:
    """Data objectiu del menú: demà si és dia lectiu, si no None.

    El contracte és publicar el menú de *demà* (no del proper dia lectiu): el
    divendres al vespre, demà = dissabte → None. Vegeu design.md D3/D5.
    """
    target = now_local.date() + timedelta(days=1)
    if not is_school_day(target, calendar):
        return None
    return target


def should_post_menu(
    now_local: datetime,
    cfg_menu: MenuConfig,
    target_date: date | None,
    menu_posted: dict[str, str],
    variant: str,
) -> bool:
    """True si toca publicar la variant per a `target_date` en aquest moment."""
    if target_date is None:
        return False
    slot_h, slot_m = cfg_menu.hora
    if (now_local.hour, now_local.minute) < (slot_h, slot_m):
        return False
    return menu_posted.get(variant) != target_date.isoformat()


@dataclass
class MenuCycleResult:
    published: int = 0
    failed: int = 0
    pin_refreshed: bool = False
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def resolve_calendar(cfg: Config) -> SchoolCalendar | None:
    """Obté el calendari del centre; si falla, retorna None amb warning.

    Decisió D5 (open question b): una caiguda puntual de la pàgina de calendari
    no bloqueja la publicació; es cau a «només cel·la al PDF» amb warning.
    """
    try:
        return fetch_school_calendar(url=cfg.site.calendari_page, user_agent=cfg.site.user_agent)
    except Exception as exc:
        log.warning("No s'ha pogut obtenir el calendari del centre (%s); es continua sense.", exc)
        return None


def _refresh_pin(
    cfg: Config,
    state: State,
    client: TelegramClient,
    pdf_url: str,
    result: MenuCycleResult,
) -> None:
    """Publica i fixa el missatge amb l'enllaç del PDF si l'URL ha canviat."""
    if pdf_url == state.menu_pdf_url:
        return
    text = menu_pin_message(pdf_url, cfg.language)
    for variant in cfg.menu.active_variants():
        thread = cfg.telegram.thread_id_for(variant.topic or "default")
        res = client.send_message(text, thread_id=thread)
        if not res.ok:
            log.error("No s'ha pogut publicar el pin del menú (variant %s).", variant.id)
            result.failed += 1
            continue
        msg_id = getattr(res, "message_id", None)
        if msg_id is not None:
            state.menu_pin_ids[variant.id] = msg_id
            client.pin_message(msg_id, thread_id=thread)
    state.menu_pdf_url = pdf_url
    result.pin_refreshed = True


def maybe_publish_menu(
    cfg: Config,
    state: State,
    client: TelegramClient,
    now: datetime,
    *,
    menu_url: str | None = None,
    calendar: SchoolCalendar | None = None,
    target: date | None = None,
) -> MenuCycleResult:
    """Resol el PDF, fa el pin si cal i publica el menú de demà per variant.

    Estalvi de peticions a la web del centre (no sabem quan publiquen el PDF
    nou del mes): abans de l'slot només es toca la web un cop al dia (per
    actualitzar el pin si l'URL canvia); a l'slot es fa el cicle complet;
    un cop resolt el slot del dia, no es torna a tocar res fins l'endemà.
    """
    result = MenuCycleResult()
    if not cfg.menu.enabled:
        return result

    slot_h, slot_m = cfg.menu.hora
    after_slot = (now.hour, now.minute) >= (slot_h, slot_m)
    today = now.date().isoformat()

    # --- Abans de l'slot: com a molt, una revisió d'URL al dia (pin) -------
    if not after_slot:
        if state.menu_url_checked_on == today:
            return result  # ja s'ha comprovat avui: 0 peticions
        pdf_url = menu_url
        if pdf_url is None:
            try:
                pdf_url = fetch_menu_url(
                    page_url=cfg.menu.page_url or cfg.site.homepage,
                    base_url=cfg.site.base_url,
                    user_agent=cfg.site.user_agent,
                    link_markers=cfg.menu.link_markers,
                    fallback_href_excludes=cfg.menu.fallback_href_excludes,
                )
            except Exception as exc:
                result.errors.append(f"menu-url: {exc}")
                log.error("No s'ha pogut resoldre l'URL del PDF del menú: %s", exc)
                return result
        if pdf_url:
            _refresh_pin(cfg, state, client, pdf_url, result)
            state.menu_url_checked_on = today
        return result

    # --- A l'slot (o després): cicle complet, un sol cop al dia -----------
    if state.menu_slot_done_on == today:
        return result  # slot d'avui ja resolt: 0 peticions

    pdf_url = menu_url
    if pdf_url is None:
        try:
            pdf_url = fetch_menu_url(
                page_url=cfg.menu.page_url or cfg.site.homepage,
                base_url=cfg.site.base_url,
                user_agent=cfg.site.user_agent,
                link_markers=cfg.menu.link_markers,
                fallback_href_excludes=cfg.menu.fallback_href_excludes,
            )
        except Exception as exc:
            result.errors.append(f"menu-url: {exc}")
            log.error("No s'ha pogut resoldre l'URL del PDF del menú: %s", exc)
            return result

    if not pdf_url:
        log.warning("Sense URL de PDF del menú; s'omet el menú.")
        state.menu_slot_done_on = today
        return result

    if calendar is None:
        calendar = resolve_calendar(cfg)

    if target is None:
        target = menu_target_date(now, calendar)

    # Pin amb l'enllaç vigent (sempre que canviï l'URL).
    _refresh_pin(cfg, state, client, pdf_url, result)
    state.menu_url_checked_on = today

    if target is None:
        log.info("Demà no és dia lectiu; no es publica menú.")
        state.menu_slot_done_on = today
        return result

    no_cell: set[str] = set()
    for variant in cfg.menu.active_variants():
        if not should_post_menu(now, cfg.menu, target, state.menu_posted, variant.id):
            continue
        try:
            plates = load_menu(
                pdf_url, target, page=variant.page, user_agent=cfg.site.user_agent
            )
        except Exception as exc:
            result.errors.append(f"menu-{variant.id}: {exc}")
            log.error("Error obtenint el menú de la variant %s: %s", variant.id, exc)
            continue
        if not plates:
            # La cel·la no existeix al PDF: reintentar-ho no la farà aparèixer
            # (el PDF del mes és estàtic). Compta com a resolt per avui.
            log.info("Sense cel·la de menú per a %s (variant %s).", target, variant.id)
            no_cell.add(variant.id)
            continue
        text = menu_dema_message(plates, target, variant.id, cfg.language)
        thread = cfg.telegram.thread_id_for(variant.topic or "default")
        res = client.send_message(text, thread_id=thread)
        if res.ok:
            state.menu_posted[variant.id] = target.isoformat()
            result.published += 1
            log.info("Publicat menú %s (%s).", target, variant.id)
        else:
            result.failed += 1
            log.error("No s'ha pogut publicar el menú (variant %s).", variant.id)

    # Slot resolt quan no queda res pendent: totes les variants publicades o
    # sense cel·la. Si Telegram ha fallat, NO es marca i es reintentarà al
    # proper cicle (la dedup de `menu_posted` evita duplicats).
    pending = [
        v.id
        for v in cfg.menu.active_variants()
        if state.menu_posted.get(v.id) != target.isoformat() and v.id not in no_cell
    ]
    if not pending:
        state.menu_slot_done_on = today
    else:
        log.warning("Menú pendent de reintentar (variants: %s).", ", ".join(pending))
    return result
