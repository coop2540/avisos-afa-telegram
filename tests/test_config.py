"""Tests de càrrega de configuració (tasca 1.2)."""

import pytest

from src.config import ConfigError, load_config


def test_load_example_without_secrets():
    cfg = load_config("config.yaml.example")
    assert cfg.site.base_url.endswith("escolaelisabadia")
    assert cfg.rss.include_categories == ["I4", "Portada", "General"]
    assert cfg.poll.base_minutes == 60
    assert cfg.poll.hot_minutes == 20
    assert cfg.telegram.chat_id is None
    assert cfg.telegram.token is None
    assert cfg.language == "ca"  # per defecte català


def test_language_env_override(monkeypatch):
    monkeypatch.setenv("LANGUAGE", "es")
    cfg = load_config("config.yaml.example")
    assert cfg.language == "es"


def test_language_unknown_falls_back(monkeypatch):
    monkeypatch.setenv("LANGUAGE", "fr")
    cfg = load_config("config.yaml.example")
    assert cfg.language == "ca"


def test_agenda_config_from_example():
    cfg = load_config("config.yaml.example")
    assert cfg.agenda.enabled is True
    assert cfg.agenda.cursos == ["I4", "Tothom", "Famílies"]
    assert cfg.agenda.carta_filtrada is True
    assert cfg.agenda.weekly_enabled is True
    assert cfg.agenda.weekly_day == 1
    assert cfg.agenda.weekly_time == (8, 0)


def test_timezone_default():
    cfg = load_config("config.yaml.example")
    assert cfg.timezone == "Europe/Madrid"


def test_agenda_invalid_day_falls_back(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "site:\n  base_url: 'https://x.test'\n  homepage: 'https://x.test/'\n"
        "  feed: 'https://x.test/feed/'\n  calendari_page: 'https://x.test/cal/'\n"
        "agenda:\n  enabled: true\n  setmanal:\n    enabled: true\n    dia: 9\n    hora: '25:99'\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.agenda.weekly_day == 1
    assert cfg.agenda.weekly_time == (8, 0)


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100999")
    monkeypatch.setenv("DRY_RUN", "1")
    cfg = load_config("config.yaml.example")
    assert cfg.telegram.token == "tok-123"
    assert cfg.telegram.chat_id == "-100999"
    assert cfg.telegram.dry_run is True


def test_thread_id_fallback():
    cfg = load_config("config.yaml.example")
    cfg.telegram.topics = {"default": 7, "rss": 11}
    assert cfg.telegram.thread_id_for("rss") == 11
    assert cfg.telegram.thread_id_for("carta") == 7  # fallback a default


def test_menu_config_from_example():
    cfg = load_config("config.yaml.example")
    assert cfg.menu.enabled is False
    assert cfg.menu.hora == (19, 0)
    assert cfg.menu.page_url.endswith("menjador-escolar/")
    assert cfg.menu.link_markers == ["basal", "menu"]
    ids = [v.id for v in cfg.menu.variants]
    assert ids == ["basal", "sense_porc"]
    assert cfg.menu.variants[0].page == 0
    assert cfg.menu.variants[1].page == 1
    assert cfg.menu.variants[1].topic == "menu_sense_porc"
    assert [v.id for v in cfg.menu.active_variants()] == ["basal", "sense_porc"]


def test_menu_absent_is_disabled(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "site:\n  base_url: 'https://x.test'\n  homepage: 'https://x.test/'\n"
        "  feed: 'https://x.test/feed/'\n  calendari_page: 'https://x.test/cal/'\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.menu.enabled is False
    assert cfg.menu.variants  # defaults presents però inactives
    assert cfg.menu.active_variants()


def test_menu_variant_disabled_and_custom_page(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "site:\n  base_url: 'https://x.test'\n  homepage: 'https://x.test/'\n"
        "  feed: 'https://x.test/feed/'\n  calendari_page: 'https://x.test/cal/'\n"
        "menu:\n  enabled: true\n  hora: '18:30'\n  variants:\n"
        "    - id: basal\n      page: 0\n      topic: menu_basal\n      enabled: false\n"
        "    - id: sense_porc\n      page: 2\n      topic: menu_sense_porc\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.menu.enabled is True
    assert cfg.menu.hora == (18, 30)
    assert [v.id for v in cfg.menu.active_variants()] == ["sense_porc"]
    assert cfg.menu.variants[1].page == 2


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def test_missing_site_key_raises(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("site:\n  base_url: 'https://x.test'\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_validate_requires_token_unless_dry_run(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    cfg = load_config("config.yaml.example")
    with pytest.raises(ConfigError):
        cfg.validate_for_run()
    cfg.telegram.dry_run = True
    cfg.validate_for_run()  # no ha de llançar
