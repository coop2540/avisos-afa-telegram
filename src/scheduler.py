"""Sondeig adaptatiu: decideix l'interval fins al proper cicle.

Base → calenta (just després d'una novetat) → calma (dies sense res).
Vegeu design.md D2.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import PollConfig
from .state import State


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


def next_interval_minutes(
    state: State,
    poll: PollConfig,
    *,
    now: datetime | None = None,
) -> int:
    """Retorna els minuts a esperar abans del proper cicle."""
    now = now or datetime.now(timezone.utc)
    last = _parse_iso(state.ultima_novetat)

    if last is None:
        return poll.base_minutes

    elapsed = now - last
    if elapsed <= timedelta(minutes=poll.hot_window_minutes):
        return poll.hot_minutes
    if elapsed >= timedelta(days=poll.quiet_after_days):
        return poll.calm_minutes
    return poll.base_minutes
