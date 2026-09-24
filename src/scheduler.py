"""Sondeig adaptatiu: decideix l'interval fins al proper cicle.

Base → calenta (just després d'una novetat) → calma (dies sense res), amb
"slot-aware sleep": si el slot de menú del dia encara no s'ha resolt, el proper
cicle s'acosta al slot (o reintentarà aviat si ja ha passat). Vegeu design.md D2/D3.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .config import MenuConfig, PollConfig
from .state import State

# Reintent quan el slot de menú ha passat i encara no s'ha resolt (web o
# Telegram caiguts): prou curt per arribar a temps, prou llarg per no
# col·lapsar la web del centre.
SLOT_RETRY_MINUTES = 10


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def next_menu_deadline(
    menu: MenuConfig | None,
    tz,
    state: State,
    now: datetime,
) -> datetime | None:
    """Proper deadline del slot de menú, o None si no cal acostar-s'hi.

    - Slot d'avui pendent i encara no ha arribat → l'hora del slot (avui).
    - Slot d'avui pendent i ja ha passat → `now` (reintent immediat).
    - Slot d'avui ja resolt (o menú deshabilitat) → None (interval normal).
    """
    if menu is None or not menu.enabled or tz is None:
        return None
    local = now.astimezone(tz)
    if state.menu_slot_done_on == local.date().isoformat():
        return None
    slot_h, slot_m = menu.hora
    slot = local.replace(hour=slot_h, minute=slot_m, second=0, microsecond=0)
    return slot if local < slot else now


def next_interval_minutes(
    state: State,
    poll: PollConfig,
    *,
    now: datetime | None = None,
    menu: MenuConfig | None = None,
    tz=None,
) -> int:
    """Retorna els minuts a esperar abans del proper cicle."""
    now = now or datetime.now(timezone.utc)
    last = _parse_iso(state.ultima_novetat)

    if last is None:
        interval = poll.base_minutes
    else:
        elapsed = now - last
        if elapsed <= timedelta(minutes=poll.hot_window_minutes):
            interval = poll.hot_minutes
        elif elapsed >= timedelta(days=poll.quiet_after_days):
            interval = poll.calm_minutes
        else:
            interval = poll.base_minutes

    # Slot-aware sleep: no deixar que el slot de menú quedi fora de l'interval.
    deadline = next_menu_deadline(menu, tz, state, now)
    if deadline is None:
        return interval
    if deadline <= now:
        return min(interval, SLOT_RETRY_MINUTES)
    minutes_to_slot = max(1, math.ceil((deadline - now).total_seconds() / 60))
    return min(interval, minutes_to_slot)
