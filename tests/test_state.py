"""Tests de l'estat persistent i la deduplicació (tasques 2.1, 2.2)."""

from src.state import State, now_iso


def test_load_missing_is_new(tmp_path):
    state = State.load(tmp_path / "state.json")
    assert state.is_new is True
    assert state.baseline_done is False


def test_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = State()
    state.remember_rss("guid-1")
    state.carta_url = "https://example.test/carta.pdf"
    state.cal_hash = "sha256:abc"
    state.mark_change()
    state.baseline_done = True
    state.save(path)

    loaded = State.load(path)
    assert loaded.rss_guids == ["guid-1"]
    assert loaded.carta_url == "https://example.test/carta.pdf"
    assert loaded.cal_hash == "sha256:abc"
    assert loaded.ultima_novetat is not None
    assert loaded.baseline_done is True
    assert loaded.is_new is False


def test_atomic_save_leaves_no_temp(tmp_path):
    path = tmp_path / "state.json"
    State(rss_guids=["a"]).save(path)
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".state-")]
    assert leftovers == []
    assert path.exists()


def test_mark_change_sets_timestamp():
    state = State()
    assert state.ultima_novetat is None
    state.mark_change()
    assert state.ultima_novetat is not None
    assert state.ultima_novetat >= now_iso()[:10]  # almenys la data d'avui


def test_remember_rss_is_idempotent():
    state = State()
    state.remember_rss("g1")
    state.remember_rss("g1")
    assert state.rss_guids == ["g1"]
    assert state.knows_rss("g1") is True
    assert state.knows_rss("g2") is False


def test_error_counters():
    state = State()
    state.bump_error("rss")
    state.bump_error("rss")
    assert state.intent_errors["rss"] == 2
    state.clear_error("rss")
    assert "rss" not in state.intent_errors


def test_corrupt_state_starts_fresh(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{ not json", encoding="utf-8")
    state = State.load(path)
    assert state.is_new is True


def test_menu_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = State()
    state.menu_pdf_url = "https://x.test/Basal.pdf"
    state.menu_posted = {"basal": "2026-09-24", "sense_porc": "2026-09-24"}
    state.menu_pin_ids = {"basal": 111, "sense_porc": 222}
    state.menu_url_checked_on = "2026-09-23"
    state.menu_slot_done_on = "2026-09-23"
    state.save(path)

    loaded = State.load(path)
    assert loaded.menu_pdf_url == "https://x.test/Basal.pdf"
    assert loaded.menu_posted == {"basal": "2026-09-24", "sense_porc": "2026-09-24"}
    assert loaded.menu_pin_ids == {"basal": 111, "sense_porc": 222}
    assert loaded.menu_url_checked_on == "2026-09-23"
    assert loaded.menu_slot_done_on == "2026-09-23"


def test_old_state_without_menu_keys(tmp_path):
    path = tmp_path / "state.json"
    path.write_text('{"version": 1, "rss_guids": ["a"]}', encoding="utf-8")
    state = State.load(path)
    assert state.menu_pdf_url is None
    assert state.menu_url_checked_on is None
    assert state.menu_slot_done_on is None
    assert state.menu_posted == {}
    assert state.menu_pin_ids == {}
