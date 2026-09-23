"""Tests del sondeig adaptatiu (tasca 3.5)."""

from datetime import datetime, timedelta, timezone

from src.config import PollConfig
from src.scheduler import next_interval_minutes
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
