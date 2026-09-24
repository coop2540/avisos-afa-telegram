"""Tests del sondeig adaptatiu (tasca 3.5)."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.config import MenuConfig, PollConfig
from src.scheduler import SLOT_RETRY_MINUTES, next_interval_minutes, next_menu_deadline
from src.state import State

POLL = PollConfig(
    base_minutes=60, hot_minutes=20, hot_window_minutes=180, calm_minutes=240, quiet_after_days=7
)
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _state(minutes_ago: float | None) -> State:
    s = State()
    if minutes_ago is not None:
        s.ultima_novetat = (NOW - timedelta(minutes=minutes_ago)).isoformat()
    return s


def test_no_change_uses_base():
    assert next_interval_minutes(_state(None), POLL, now=NOW) == POLL.base_minutes


def test_recent_change_uses_hot():
    assert next_interval_minutes(_state(10), POLL, now=NOW) == POLL.hot_minutes


def test_after_hot_window_uses_base():
    assert next_interval_minutes(_state(240), POLL, now=NOW) == POLL.base_minutes


def test_long_quiet_uses_calm():
    assert next_interval_minutes(_state(60 * 24 * 10), POLL, now=NOW) == POLL.calm_minutes


def test_boundary_hot_window():
    assert next_interval_minutes(_state(POLL.hot_window_minutes), POLL, now=NOW) == POLL.hot_minutes


def test_invalid_timestamp_falls_back_to_base():
    s = State(ultima_novetat="not-a-date")
    assert next_interval_minutes(s, POLL, now=NOW) == POLL.base_minutes


# --- slot-aware sleep (D3: arribar a les 19:00) ---------------------------

MADRID = ZoneInfo("Europe/Madrid")
MENU = MenuConfig(enabled=True, hora=(19, 0))


def _at(h, m, *, menu=MENU, minutes_ago=None):
    """Crida el scheduler a les h:m d'hora de Madrid."""
    now = datetime(2026, 9, 24, h, m, tzinfo=MADRID)
    s = State()
    if minutes_ago is not None:
        s.ultima_novetat = (now - timedelta(minutes=minutes_ago)).isoformat()
    return next_interval_minutes(s, POLL, now=now, menu=menu, tz=MADRID)


def test_slot_pending_caps_interval_before_slot():
    # 18:41 → slot a les 19:00: falten 19 min (< base 60)
    assert _at(18, 41) == 19


def test_slot_far_away_keeps_base_interval():
    assert _at(10, 0) == POLL.base_minutes


def test_slot_done_today_no_cap():
    now = datetime(2026, 9, 24, 18, 41, tzinfo=MADRID)
    s = _state(None)
    s.menu_slot_done_on = "2026-09-24"
    assert next_interval_minutes(s, POLL, now=now, menu=MENU, tz=MADRID) == POLL.base_minutes


def test_slot_passed_pending_retries_soon():
    # 19:41 i slot d'avui pendent (web o Telegram caiguts) → reintent aviat
    assert _at(19, 41) == SLOT_RETRY_MINUTES


def test_menu_disabled_no_cap():
    disabled = MenuConfig(enabled=False, hora=(19, 0))
    assert _at(18, 41, menu=disabled) == POLL.base_minutes


def test_no_tz_no_cap():
    now = datetime(2026, 9, 24, 16, 41, tzinfo=timezone.utc)
    s = _state(None)
    assert next_interval_minutes(s, POLL, now=now, menu=MENU, tz=None) == POLL.base_minutes


def test_cap_also_applies_to_hot_interval():
    # Novetat recent (hot=20) però falten 10 min per al slot → 10
    assert _at(18, 50, minutes_ago=10) == 10


def test_cap_also_applies_to_calm_interval():
    # Calma (240 min) i falten 120 min per al slot → 120
    assert _at(17, 0, minutes_ago=60 * 24 * 10) == 120


def test_exact_slot_with_pending_slot_retries():
    # Exactament a les 19:00 amb el slot pendent (cicle anterior ha fallat)
    assert _at(19, 0) == SLOT_RETRY_MINUTES


def test_after_midnight_targets_todays_slot():
    # 00:30 del dia 25 amb slot del 24 resolt → interval normal (base)
    now = datetime(2026, 9, 25, 0, 30, tzinfo=MADRID)
    s = _state(None)
    s.menu_slot_done_on = "2026-09-24"
    assert next_interval_minutes(s, POLL, now=now, menu=MENU, tz=MADRID) == POLL.base_minutes


def test_deadline_helper_shapes():
    now = datetime(2026, 9, 24, 18, 41, tzinfo=MADRID)
    # pendent abans de slot → hora del slot local
    assert next_menu_deadline(MENU, MADRID, _state(None), now) == datetime(
        2026, 9, 24, 19, 0, tzinfo=MADRID
    )
    # ja resolt → None
    s = _state(None)
    s.menu_slot_done_on = "2026-09-24"
    assert next_menu_deadline(MENU, MADRID, s, now) is None
    # menú deshabilitat → None
    assert next_menu_deadline(MenuConfig(enabled=False), MADRID, _state(None), now) is None
    # slot passat pendent → now (reintent)
    late = datetime(2026, 9, 24, 19, 41, tzinfo=MADRID)
    assert next_menu_deadline(MENU, MADRID, _state(None), late) == late
