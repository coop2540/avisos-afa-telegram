"""Tests de la lògica de publicació del menú (tasques 5.1–5.3, 6.2)."""

from datetime import date, datetime

import src.menu_service as menu_mod
from src.config import (
    CartaConfig,
    Config,
    FirstRunConfig,
    MenuConfig,
    MenuVariant,
    PollConfig,
    RssConfig,
    SiteConfig,
    TelegramConfig,
)
from src.menu_calendar import SchoolCalendar
from src.menu_service import maybe_publish_menu, menu_target_date, should_post_menu
from src.state import State
from src.telegram_out import SendResult


class FakeClient:
    def __init__(self, ok=True, ok_map=None):
        self.sent = []
        self.pins = []
        self.ok = ok
        self.ok_map = ok_map or {}

    def send_message(self, text, thread_id=None, disable_preview=True):
        self.sent.append((text, thread_id))
        ok = self.ok_map.get(thread_id, self.ok)
        return SendResult(ok=ok, status=200 if ok else 400, message_id=len(self.sent))

    def pin_message(self, message_id, thread_id=None):
        self.pins.append((message_id, thread_id))
        return SendResult(ok=True, status=200, message_id=message_id)


def _menu(**kw):
    base = dict(
        enabled=True,
        hora=(19, 0),
        page_url="https://x.test/menjador/",
        variants=[
            MenuVariant(id="basal", page=0, topic="menu_basal"),
            MenuVariant(id="sense_porc", page=1, topic="menu_sense_porc"),
        ],
    )
    base.update(kw)
    return MenuConfig(**base)


def _cfg(**menu_kw):
    return Config(
        site=SiteConfig(
            base_url="https://x.test",
            homepage="https://x.test/",
            feed="https://x.test/feed/",
            calendari_page="https://x.test/cal/",
        ),
        rss=RssConfig(),
        carta=CartaConfig(),
        poll=PollConfig(),
        telegram=TelegramConfig(
            chat_id="123",
            token="tok",
            dry_run=True,
            topics={"default": 1, "menu_basal": 24, "menu_sense_porc": 27},
        ),
        first_run=FirstRunConfig(),
        menu=_menu(**menu_kw),
        timezone="UTC",
    )


SCHOOL_CAL = SchoolCalendar(start=date(2026, 9, 8), end=date(2027, 6, 21))


# --- 5.1 should_post_menu ---------------------------------------------------


def test_should_post_before_slot_is_false():
    now = datetime(2026, 9, 23, 18, 30)
    assert should_post_menu(now, _menu(), date(2026, 9, 24), {}, "basal") is False


def test_should_post_at_slot_pending_is_true():
    now = datetime(2026, 9, 23, 19, 0)
    assert should_post_menu(now, _menu(), date(2026, 9, 24), {}, "basal") is True


def test_should_post_already_posted_is_false():
    now = datetime(2026, 9, 23, 19, 5)
    posted = {"basal": "2026-09-24"}
    assert should_post_menu(now, _menu(), date(2026, 9, 24), posted, "basal") is False


def test_should_post_no_target_is_false():
    now = datetime(2026, 9, 25, 19, 30)
    assert should_post_menu(now, _menu(), None, {}, "basal") is False


# --- 5.2 menu_target_date ---------------------------------------------------


def test_target_tomorrow_when_school_day():
    now = datetime(2026, 9, 23, 19, 0)  # dimecres
    assert menu_target_date(now, SCHOOL_CAL) == date(2026, 9, 24)


def test_target_friday_evening_is_none():
    now = datetime(2026, 9, 25, 19, 0)  # divendres -> dema dissabte
    assert menu_target_date(now, SCHOOL_CAL) is None


def test_target_monday_evening_is_tuesday():
    now = datetime(2026, 9, 28, 19, 0)  # dilluns -> dema dimarts
    assert menu_target_date(now, SCHOOL_CAL) == date(2026, 9, 29)


def test_target_holiday_evening_is_none():
    cal = SchoolCalendar(non_school_days={date(2026, 11, 2)})
    now = datetime(2026, 11, 1, 19, 0)  # diumenge 1 -> dema 2 festiu
    assert menu_target_date(now, cal) is None


# --- 5.3 / 6.2 maybe_publish_menu -------------------------------------------


def _run(cfg, state, client, now, **kw):
    kw.setdefault("menu_url", "https://x.test/Basal.pdf")
    kw.setdefault("calendar", SCHOOL_CAL)
    return maybe_publish_menu(cfg, state, client, now, **kw)


def test_publishes_both_variants_and_pin(monkeypatch):
    cfg = _cfg()
    state = State()
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)

    assert res.published == 2
    assert state.menu_posted == {"basal": "2026-09-24", "sense_porc": "2026-09-24"}
    threads = [t for _txt, t in client.sent]
    assert 24 in threads and 27 in threads
    assert res.pin_refreshed is True
    assert state.menu_pdf_url == "https://x.test/Basal.pdf"


def test_no_duplicate_on_rerun(monkeypatch):
    cfg = _cfg()
    state = State(menu_posted={"basal": "2026-09-24", "sense_porc": "2026-09-24"})
    state.menu_pdf_url = "https://x.test/Basal.pdf"
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)

    assert res.published == 0
    assert client.sent == []


def test_partial_failure_retries_only_failed(monkeypatch):
    cfg = _cfg()
    state = State()
    client = FakeClient(ok_map={27: False})
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)

    assert res.published == 1
    # el topic 27 falla el pin i el missatge diari (2 operacions fallides)
    assert res.failed == 2
    assert state.menu_posted["basal"] == "2026-09-24"
    assert "sense_porc" not in state.menu_posted  # es reintentara


def test_no_cell_means_no_message(monkeypatch):
    cfg = _cfg()
    state = State()
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: None)
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)
    assert res.published == 0
    assert state.menu_posted == {}


def test_pin_not_refreshed_if_url_unchanged(monkeypatch):
    cfg = _cfg()
    state = State(
        menu_pdf_url="https://x.test/Basal.pdf",
        menu_posted={"basal": "2026-09-24", "sense_porc": "2026-09-24"},
    )
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)
    assert res.pin_refreshed is False
    assert client.sent == []
    assert client.pins == []


def test_pin_refresh_when_url_changes(monkeypatch):
    cfg = _cfg()
    state = State(menu_pdf_url="https://x.test/Basal-antic.pdf",
                  menu_posted={"basal": "2026-09-24", "sense_porc": "2026-09-24"})
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)
    res = _run(cfg, state, client, now)
    assert res.pin_refreshed is True
    assert state.menu_pdf_url == "https://x.test/Basal.pdf"
    # un missatge de pin per cada variant + pin fixat
    assert len([t for _txt, t in client.sent]) == 2
    assert len(client.pins) == 2


def test_disabled_menu_does_nothing():
    cfg = _cfg(enabled=False)
    state = State()
    client = FakeClient()
    now = datetime(2026, 9, 23, 19, 0)
    res = maybe_publish_menu(cfg, state, client, now, menu_url="https://x.test/Basal.pdf")
    assert res.published == 0
    assert client.sent == []


# --- Estalvi de peticions a la web del centre --------------------------------


def test_before_slot_checks_url_only_once_per_day(monkeypatch):
    """Abans de l'slot: 1a revisió d'URL al dia; després, 0 peticions."""
    cfg = _cfg()
    state = State()
    client = FakeClient()
    calls = {"n": 0}

    def fake_fetch(**_k):
        calls["n"] += 1
        return "https://x.test/Basal.pdf"

    monkeypatch.setattr(menu_mod, "fetch_menu_url", fake_fetch)
    now = datetime(2026, 9, 23, 10, 0)  # abans de les 19:00

    res1 = maybe_publish_menu(cfg, state, client, now)
    assert calls["n"] == 1
    assert state.menu_url_checked_on == "2026-09-23"
    assert res1.published == 0  # no publica abans de l'slot

    res2 = maybe_publish_menu(cfg, state, client, now)
    assert calls["n"] == 1  # cap petició nova
    assert res2.published == 0


def test_after_slot_full_cycle_once_then_skips(monkeypatch):
    """A l'slot: cicle complet un cop; després, 0 peticions fins l'endemà."""
    cfg = _cfg()
    state = State()
    client = FakeClient()
    calls = {"n": 0}

    def fake_fetch(**_k):
        calls["n"] += 1
        return "https://x.test/Basal.pdf"

    monkeypatch.setattr(menu_mod, "fetch_menu_url", fake_fetch)
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)

    res1 = maybe_publish_menu(
        cfg, state, client, now, calendar=SCHOOL_CAL
    )
    assert calls["n"] == 1
    assert res1.published == 2
    assert state.menu_slot_done_on == "2026-09-23"

    res2 = maybe_publish_menu(
        cfg, state, client, now, calendar=SCHOOL_CAL
    )
    assert calls["n"] == 1  # cap petició nova
    assert res2.published == 0
    assert client.sent[0][0]  # només els missatges del primer cicle


def test_slot_not_marked_done_if_send_falls(monkeypatch):
    """Si Telegram falla, el slot NO es marca i es reintentarà."""
    cfg = _cfg()
    state = State()
    client = FakeClient(ok_map={27: False})
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: ["PLAT"])
    now = datetime(2026, 9, 23, 19, 0)

    maybe_publish_menu(cfg, state, client, now, calendar=SCHOOL_CAL,
                       menu_url="https://x.test/Basal.pdf")
    assert state.menu_slot_done_on is None  # pendent de reintent
    assert "sense_porc" not in state.menu_posted


def test_slot_marked_done_when_no_cell(monkeypatch):
    """Sense cel·la al PDF: compta com a resolt (no es reintentarà)."""
    cfg = _cfg()
    state = State()
    client = FakeClient()
    monkeypatch.setattr(menu_mod, "load_menu", lambda *a, **k: None)
    now = datetime(2026, 9, 23, 19, 0)

    res = maybe_publish_menu(cfg, state, client, now, calendar=SCHOOL_CAL,
                             menu_url="https://x.test/Basal.pdf")
    assert res.published == 0
    assert state.menu_slot_done_on == "2026-09-23"


def test_slot_done_for_non_school_day(monkeypatch):
    """Divendres al vespre (demà dissabte): es marca resolt sense publicar."""
    cfg = _cfg()
    state = State()
    client = FakeClient()
    now = datetime(2026, 9, 25, 19, 0)  # divendres

    res = maybe_publish_menu(cfg, state, client, now, calendar=SCHOOL_CAL,
                             menu_url="https://x.test/Basal.pdf")
    assert res.published == 0
    assert state.menu_slot_done_on == "2026-09-25"
