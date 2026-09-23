"""Filtratge d'esdeveniments i lògica de l'agenda setmanal.

Vegeu design.md D13 i specs/carta-agenda.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .config import AgendaConfig
from .parse_carta import CartaEvent


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def filter_events(events: list[CartaEvent], cursos: list[str]) -> list[CartaEvent]:
    """Filtra els esdeveniments pels cursos configurats (i etiquetes compartides).

    Un curs coincideix si és igual o comença pel valor buscat (p. ex. `I4`
    inclou `I4B`).
    """
    wanted = [_norm(c) for c in cursos if c and c.strip()]
    if not wanted:
        return list(events)
    selected = []
    for event in events:
        curs = _norm(event.curs)
        if any(curs == w or curs.startswith(w) for w in wanted):
            selected.append(event)
    return selected


def week_bounds(ref: date) -> tuple[date, date]:
    """Dilluns i diumenge de la setmana que conté `ref`."""
    monday = ref - timedelta(days=ref.weekday())
    return monday, monday + timedelta(days=6)


def events_in_week(events: list[CartaEvent], ref: date) -> list[CartaEvent]:
    """Esdeveniments dins la setmana de `ref`, ordenats per data."""
    start, end = week_bounds(ref)
    return sorted((e for e in events if start <= e.date <= end), key=lambda e: e.date)


def weekly_slot(now: datetime, cfg: AgendaConfig) -> datetime | None:
    """Moment programat de l'agenda d'aquesta setmana, o None si no s'aplica."""
    if not (cfg.enabled and cfg.weekly_enabled):
        return None
    monday = now.date() - timedelta(days=now.weekday())
    target = monday + timedelta(days=cfg.weekly_day - 1)  # 1=dilluns … 7=diumenge
    hour, minute = cfg.weekly_time
    return datetime.combine(target, time(hour, minute, tzinfo=now.tzinfo))


def should_post_weekly(now: datetime, cfg: AgendaConfig, last_post_iso: str | None) -> bool:
    """True si toca publicar l'agenda d'aquesta setmana i encara no s'ha fet."""
    slot = weekly_slot(now, cfg)
    if slot is None or now < slot:
        return False
    if last_post_iso:
        try:
            last = datetime.fromisoformat(last_post_iso)
        except ValueError:
            return True
        if last.tzinfo is None:
            last = last.replace(tzinfo=now.tzinfo)
        if last >= slot:
            return False
    return True
