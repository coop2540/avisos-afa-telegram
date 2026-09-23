"""Tests d'aprovació de membres (specs/member-approval)."""

from src.approval import (
    JoinRequest,
    decision_keyboard,
    parse_join_request,
    should_auto_reject,
)
from src.config import AutoRejectConfig, ApprovalConfig


def _update(**user):
    base = {"id": 999, "first_name": "Maria", "username": "maria_p"}
    base.update(user)
    return {
        "update_id": 1,
        "chat_join_request": {
            "chat": {"id": -100123},
            "from": base,
            "date": 123,
        },
    }


def test_parse_join_request_basic():
    jr = parse_join_request(_update())
    assert jr is not None
    assert jr.user_id == 999
    assert jr.chat_id == -100123
    assert jr.display_name == "Maria"
    assert jr.handle == "@maria_p"


def test_parse_ignores_other_updates():
    assert parse_join_request({"update_id": 1, "message": {}}) is None


def test_parse_requires_ids():
    bad = {"chat_join_request": {"from": {}, "chat": {}}}
    assert parse_join_request(bad) is None


def test_display_name_without_name():
    jr = JoinRequest(user_id=1, chat_id=2, first_name="", last_name="")
    assert jr.display_name == "(sense nom)"
    assert jr.handle == "(sense usuari)"


def test_auto_reject_disabled_by_default():
    jr = JoinRequest(user_id=1, chat_id=2)
    assert should_auto_reject(jr, ApprovalConfig()) is None


def test_auto_reject_empty_name():
    cfg = ApprovalConfig(auto_reject=AutoRejectConfig(enabled=True))
    jr = JoinRequest(user_id=1, chat_id=2, first_name="")
    assert should_auto_reject(jr, cfg) is not None


def test_auto_reject_numeric_name():
    cfg = ApprovalConfig(auto_reject=AutoRejectConfig(enabled=True))
    jr = JoinRequest(user_id=1, chat_id=2, first_name="12345")
    assert should_auto_reject(jr, cfg) is not None


def test_auto_reject_spam_bio():
    cfg = ApprovalConfig(auto_reject=AutoRejectConfig(enabled=True))
    jr = JoinRequest(user_id=1, chat_id=2, first_name="Ana", bio="guany diners https://t.me/x")
    assert should_auto_reject(jr, cfg) is not None


def test_auto_reject_clean_user_passes():
    cfg = ApprovalConfig(auto_reject=AutoRejectConfig(enabled=True))
    jr = JoinRequest(user_id=1, chat_id=2, first_name="Anna", username="anna")
    assert should_auto_reject(jr, cfg) is None


def test_decision_keyboard_has_two_buttons():
    kb = decision_keyboard(42)
    row = kb["inline_keyboard"][0]
    assert row[0]["callback_data"] == "apr:42"
    assert row[1]["callback_data"] == "rej:42"
