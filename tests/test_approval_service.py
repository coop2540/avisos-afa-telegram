"""Tests d'integració del servei d'aprovació amb API simulada."""

from src.approval import ApprovalService
from src.config import (
    ApprovalConfig,
    AutoRejectConfig,
    Config,
    FirstRunConfig,
    TelegramConfig,
)
from src.state import State


def _cfg(tmp_path, *, auto_reject=False, admin="-100999888"):
    return Config(
        site=None, rss=None, carta=None, poll=None,
        telegram=TelegramConfig(
            chat_id="-100123456", token="tok", dry_run=True, admin_chat_id=admin,
            approval=ApprovalConfig(enabled=True, auto_reject=AutoRejectConfig(enabled=auto_reject)),
        ),
        first_run=FirstRunConfig(),
        state_path=tmp_path / "state.json",
    )


class FakeService(ApprovalService):
    """Servei amb l'API interceptada (no xarxa)."""

    def __init__(self, cfg, state):
        super().__init__(cfg, state)
        self.calls = []

    def _api(self, method, **params):
        self.calls.append((method, params))
        return {"ok": True}

    def _notify(self, jr, extra=""):
        self.calls.append(("notify", {"user_id": jr.user_id, "extra": extra}))


def _join_update(uid=999, first_name="Maria", username="maria"):
    return {
        "update_id": 10,
        "chat_join_request": {
            "chat": {"id": "-100123456"},
            "from": {"id": uid, "first_name": first_name, "username": username},
        },
    }


def test_join_request_notifies_and_records(tmp_path):
    cfg = _cfg(tmp_path)
    state = State()
    svc = FakeService(cfg, state)
    svc.process_update(_join_update())

    assert ("notify", {"user_id": 999, "extra": ""}) in svc.calls
    assert state.join_status(999) == "notified"


def test_join_request_not_notified_twice(tmp_path):
    cfg = _cfg(tmp_path)
    state = State()
    svc = FakeService(cfg, state)
    svc.process_update(_join_update())
    n1 = len(svc.calls)
    svc.process_update(_join_update())
    assert len(svc.calls) == n1  # cap notificació nova


def test_join_without_admin_config_logs_only(tmp_path):
    cfg = _cfg(tmp_path, admin=None)
    state = State()
    svc = FakeService(cfg, state)
    svc.process_update(_join_update())
    assert state.join_status(999) is None  # no s'ha processat


def test_auto_reject_declines_and_notifies(tmp_path):
    cfg = _cfg(tmp_path, auto_reject=True)
    state = State()
    svc = FakeService(cfg, state)
    svc.process_update(_join_update(first_name=""))  # nom buit -> rebuig

    methods = [m for m, _ in svc.calls]
    assert "declineChatJoinRequest" in methods
    assert state.join_status(999) == "declined"
    assert any(m == "notify" and p.get("extra") for m, p in svc.calls)


def test_admin_approves_via_callback(tmp_path):
    cfg = _cfg(tmp_path)
    state = State()
    state.remember_join(999, "notified")
    svc = FakeService(cfg, state)

    update = {
        "update_id": 11,
        "callback_query": {
            "id": "cb1",
            "data": "apr:999",
            "message": {"message_id": 5, "chat": {"id": "-100999888"}},
        },
    }
    svc.process_update(update)

    methods = [m for m, _ in svc.calls]
    assert "approveChatJoinRequest" in methods
    assert "answerCallbackQuery" in methods
    assert state.join_status(999) == "approved"


def test_callback_from_other_chat_ignored(tmp_path):
    cfg = _cfg(tmp_path)
    state = State()
    state.remember_join(999, "notified")
    svc = FakeService(cfg, state)
    update = {
        "update_id": 12,
        "callback_query": {
            "id": "cb2", "data": "apr:999",
            "message": {"message_id": 6, "chat": {"id": "-100777000"}},
        },
    }
    svc.process_update(update)
    assert state.join_status(999) == "notified"
    assert "approveChatJoinRequest" not in [m for m, _ in svc.calls]


def test_double_decision_not_applied(tmp_path):
    cfg = _cfg(tmp_path)
    state = State()
    state.remember_join(999, "approved")
    svc = FakeService(cfg, state)
    update = {
        "update_id": 13,
        "callback_query": {
            "id": "cb3", "data": "rej:999",
            "message": {"message_id": 7, "chat": {"id": "-100999888"}},
        },
    }
    svc.process_update(update)
    assert "declineChatJoinRequest" not in [m for m, _ in svc.calls]
