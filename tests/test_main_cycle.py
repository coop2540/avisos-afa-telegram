"""Test d'integració del cicle complet (tasques 3.4, 5.1, 8.1).

Simula: línia base sense publicar → novetat RSS/carta/calendari publicada al
topic correcte en català amb enllaç → estat actualitzat → reexecució sense
duplicats. També cobreix la tolerància a errors d'una font.
"""

import src.main as main_mod
import src.menu_service as menu_mod
from datetime import date, datetime, timezone

from src.config import (
    CartaConfig,
    Config,
    FirstRunConfig,
    PollConfig,
    RssConfig,
    SiteConfig,
    TelegramConfig,
)
from src.fetch_calendari import CalendariContent, hash_content
from src.fetch_rss import RssItem
from src.http_util import FetchError
from src.parse_carta import CartaData, CartaEvent
from src.state import State
from src.telegram_out import SendResult

TOPICS = {"default": 1, "rss": 11, "carta": 12, "calendari": 13, "agenda": 14}


class FakeClient:
    def __init__(self, ok=True):
        self.sent = []
        self.ok = ok

    def send_message(self, text, thread_id=None, disable_preview=True):
        self.sent.append((text, thread_id))
        return SendResult(ok=self.ok, status=200 if self.ok else 400)


def make_cfg(tmp_path):
    return Config(
        site=SiteConfig(
            base_url="https://x.test",
            homepage="https://x.test/",
            feed="https://x.test/feed/",
            calendari_page="https://x.test/cal/",
        ),
        rss=RssConfig(include_categories=["I4"], max_items_per_cycle=10),
        carta=CartaConfig(),
        poll=PollConfig(),
        telegram=TelegramConfig(
            chat_id="123", token="tok", dry_run=True, topics=dict(TOPICS)
        ),
        first_run=FirstRunConfig(publish_welcome=False),
        state_path=tmp_path / "state.json",
    )


def item(guid, title, link):
    return RssItem(guid=guid, title=title, link=link, summary="resum", categories=["I4"])


def patch_sources(monkeypatch, *, items=None, carta=None, cal="base", rss_error=None):
    def fake_rss(*_a, **_k):
        if rss_error:
            raise FetchError(rss_error)
        return list(items or [])

    monkeypatch.setattr(main_mod, "fetch_rss", fake_rss)
    monkeypatch.setattr(main_mod, "fetch_carta_url", lambda **_k: carta)
    monkeypatch.setattr(
        main_mod,
        "fetch_calendari",
        lambda **_k: CalendariContent(normalized_text=cal or "base"),
    )


def test_baseline_does_not_publish(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    patch_sources(
        monkeypatch,
        items=[item("g1", "Reunió I4", "https://x.test/p1")],
        carta="https://x.test/carta-1.pdf",
    )
    client = FakeClient()
    state = State()
    result = main_mod.seed_baseline(cfg, state, client)

    assert result.baseline is True
    assert result.published == 0
    assert client.sent == []
    assert state.baseline_done is True
    assert state.rss_guids == ["g1"]
    assert state.carta_url == "https://x.test/carta-1.pdf"
    assert state.cal_hash is not None


def test_new_rss_item_publishes_to_topic(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    client = FakeClient()

    patch_sources(monkeypatch, items=[item("g1", "Antiga", "https://x.test/p1")], carta="c1")
    main_mod.seed_baseline(cfg, state, client)
    assert client.sent == []

    patch_sources(
        monkeypatch,
        items=[
            item("g1", "Antiga", "https://x.test/p1"),
            item("g2", "Reunió de famílies d'I4", "https://x.test/p2"),
        ],
        carta="c1",
    )
    result = main_mod.run_cycle(cfg, state, client)

    assert result.published == 1
    assert len(client.sent) == 1
    text, thread = client.sent[0]
    assert thread == TOPICS["rss"]
    assert "Reunió de famílies d&#x27;I4" in text or "Reunió de famílies d'I4" in text
    assert "https://x.test/p2" in text
    assert "g2" in state.rss_guids
    assert state.ultima_novetat is not None


def test_no_duplicate_on_rerun(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    client = FakeClient()
    items = [item("g1", "A", "https://x.test/p1"), item("g2", "B", "https://x.test/p2")]

    patch_sources(monkeypatch, items=items, carta="c1")
    main_mod.seed_baseline(cfg, state, client)
    main_mod.run_cycle(cfg, state, client)
    first = len(client.sent)
    main_mod.run_cycle(cfg, state, client)
    assert len(client.sent) == first  # cap duplicat


def test_carta_and_calendari_changes_publish(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    client = FakeClient()

    patch_sources(monkeypatch, items=[], carta="c1", cal="base")
    main_mod.seed_baseline(cfg, state, client)

    patch_sources(monkeypatch, items=[], carta="c2", cal="base")
    main_mod.run_cycle(cfg, state, client)

    patch_sources(monkeypatch, items=[], carta="c2", cal="canviat")
    main_mod.run_cycle(cfg, state, client)

    threads = [thread for _text, thread in client.sent]
    assert threads == [TOPICS["carta"], TOPICS["calendari"]]
    assert "carta-2" not in client.sent[0][0]  # el text conté l'enllaç, no el nom intern
    assert "c2" in client.sent[0][0]


def test_failed_send_does_not_mark_dedup(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    patch_sources(monkeypatch, items=[], carta="c1", cal="base")
    main_mod.seed_baseline(cfg, state, FakeClient())

    patch_sources(
        monkeypatch, items=[item("g9", "Nova", "https://x.test/p9")], carta="c1"
    )
    result = main_mod.run_cycle(cfg, state, FakeClient(ok=False))

    assert result.failed == 1
    assert "g9" not in state.rss_guids  # es reintentarà


def test_rss_error_does_not_stop_other_sources(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    state.baseline_done = True
    state.carta_url = "c1"
    state.cal_hash = hash_content("base")

    patch_sources(monkeypatch, rss_error="timeout", carta="c2", cal="base")
    result = main_mod.run_cycle(cfg, state, FakeClient())

    assert any(e.startswith("rss:") for e in result.errors)
    # la carta sí que s'ha publicat malgrat l'error del RSS
    assert result.published == 1


def test_baseline_incomplete_retries_next_cycle(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    state = State()
    patch_sources(monkeypatch, items=[], carta="c1", cal="base", rss_error="down")
    result = main_mod.seed_baseline(cfg, state, FakeClient())
    assert result.baseline is True
    assert state.baseline_done is False  # es reintentarà
    assert any(e.startswith("rss:") for e in result.errors)


def _fake_carta(monkeypatch, events):
    monkeypatch.setattr(
        main_mod,
        "load_carta",
        lambda url, user_agent: CartaData(month=9, year=2026, events=list(events)),
    )


def test_carta_filtrada_on_new_carta(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.agenda.enabled = True
    cfg.agenda.carta_filtrada = True
    cfg.agenda.cursos = ["I4"]
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c2", cal="base")
    _fake_carta(monkeypatch, [CartaEvent(date(2026, 9, 15), "I4", "Reunió de famílies (15h)")])

    client = FakeClient()
    result = main_mod.run_cycle(cfg, state, client)

    assert result.published == 1
    text, thread = client.sent[0]
    assert thread == TOPICS["carta"]
    assert "Reunió de famílies" in text
    assert "15/09" in text


def test_carta_without_class_events_falls_back_to_link(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.agenda.enabled = True
    cfg.agenda.carta_filtrada = True
    cfg.agenda.cursos = ["I4"]
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c2", cal="base")
    _fake_carta(monkeypatch, [CartaEvent(date(2026, 9, 16), "3r", "Reunió de 3r")])

    client = FakeClient()
    main_mod.run_cycle(cfg, state, client)
    text, _thread = client.sent[0]
    assert "Carta del mes" in text  # avís+enllaç, sense llista buida
    assert "3r" not in text


def test_weekly_agenda_published_once(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.agenda.enabled = True
    cfg.agenda.weekly_enabled = True
    cfg.agenda.weekly_day = 1
    cfg.agenda.weekly_time = (8, 0)
    cfg.agenda.cursos = ["I4"]
    cfg.timezone = "UTC"
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c1", cal="base")
    _fake_carta(monkeypatch, [CartaEvent(date(2026, 9, 23), "I4", "Reunió de famílies")])

    client = FakeClient()
    now = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)  # dimecres; slot dilluns 08:00 passat
    result = main_mod.run_cycle(cfg, state, client, now=now)

    assert result.published == 1
    text, thread = client.sent[0]
    assert thread == TOPICS["agenda"]
    assert "Agenda de la setmana" in text
    assert "23/09 · Reunió de famílies" in text
    assert state.last_weekly_post is not None

    # Segona execució: no duplica
    result2 = main_mod.run_cycle(cfg, state, client, now=now)
    assert result2.published == 0


def test_weekly_agenda_disabled_does_nothing(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.agenda.enabled = False
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c1", cal="base")
    now = datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc)
    result = main_mod.run_cycle(cfg, state, FakeClient(), now=now)
    assert result.published == 0


def test_menu_publishes_in_cycle(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    from src.config import MenuConfig, MenuVariant

    cfg.menu = MenuConfig(
        enabled=True,
        hora=(19, 0),
        page_url="https://x.test/menjador/",
        variants=[MenuVariant(id="basal", page=0, topic="menu_basal")],
    )
    cfg.timezone = "UTC"
    cfg.telegram.topics["menu_basal"] = 24
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c1", cal="base")

    monkeypatch.setattr(
        menu_mod,
        "fetch_menu_url",
        lambda **_k: "https://x.test/Basal.pdf",
    )
    monkeypatch.setattr(
        menu_mod,
        "fetch_school_calendar",
        lambda **_k: __import__("src.menu_calendar", fromlist=["SchoolCalendar"]).SchoolCalendar(
            start=date(2026, 9, 8), end=date(2027, 6, 21)
        ),
    )
    monkeypatch.setattr(
        menu_mod, "load_menu", lambda url, target, page, user_agent: ["CREMA", "PA"]
    )
    client = FakeClient()
    now = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)
    result = main_mod.run_cycle(cfg, state, client, now=now)
    assert result.published >= 1
    assert state.menu_posted.get("basal") == "2026-09-24"
    assert any(t == 24 for _txt, t in client.sent)


def test_menu_fetch_error_does_not_crash_cycle(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    from src.config import MenuConfig, MenuVariant

    cfg.menu = MenuConfig(
        enabled=True,
        hora=(19, 0),
        page_url="https://x.test/menjador/",
        variants=[MenuVariant(id="basal", page=0, topic="menu_basal")],
    )
    state = State(baseline_done=True, carta_url="c1", cal_hash=hash_content("base"))
    patch_sources(monkeypatch, items=[], carta="c1", cal="base")

    def boom(**_k):
        raise FetchError("menjador down")

    monkeypatch.setattr(menu_mod, "fetch_menu_url", boom)
    now = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)
    result = main_mod.run_cycle(cfg, state, FakeClient(), now=now)
    assert any(e.startswith("menu-url:") for e in result.errors)
