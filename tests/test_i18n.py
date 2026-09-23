"""Tests d'internacionalització: catàlegs, fallback i missatges (service-i18n)."""

from src.i18n import (
    DEFAULT_LANG,
    Translator,
    available_languages,
    normalize_language,
    translate,
)
from src.messages import (
    calendari_message,
    carta_message,
    menu_dema_message,
    menu_pin_message,
    noticia_message,
    welcome_message,
)


def test_default_language_is_catalan():
    assert DEFAULT_LANG == "ca"


def test_available_languages_include_known():
    langs = available_languages()
    assert {"ca", "es", "en"}.issubset(set(langs))


def test_normalize_language_variants():
    assert normalize_language("ca") == "ca"
    assert normalize_language("ES") == "es"
    assert normalize_language("es-ES") == "es"
    assert normalize_language("en_GB") == "en"
    assert normalize_language(None) == "ca"
    assert normalize_language("") == "ca"


def test_unknown_language_falls_back_to_catalan():
    assert normalize_language("fr") == "ca"
    assert translate("carta.link", "fr") == translate("carta.link", "ca")


def test_translation_differs_between_languages():
    assert translate("noticia.read_more", "ca") == "Llegir més"
    assert translate("noticia.read_more", "es") == "Leer más"
    assert translate("noticia.read_more", "en") == "Read more"


def test_unknown_key_returns_key():
    assert translate("no.existeix", "ca") == "no.existeix"


def test_translator_is_bound_to_language():
    t = Translator("es")
    assert t("calendari.link") == "Ver el calendario"


def test_carta_message_localized():
    ca = carta_message("https://x.test/c.pdf", "ca")
    es = carta_message("https://x.test/c.pdf", "es")
    assert "Obrir la carta" in ca
    assert "Abrir la carta" in es
    assert "https://x.test/c.pdf" in es


def test_noticia_message_localized_read_more():
    ca = noticia_message("Títol", "resum", "https://x.test/p", "ca")
    es = noticia_message("Títol", "resum", "https://x.test/p", "es")
    assert "Llegir més" in ca
    assert "Leer más" in es


def test_welcome_message_localized():
    assert "Servei d'avisos" in welcome_message("ca")
    assert "Servicio de avisos" in welcome_message("es")
    assert "AFA alerts" in welcome_message("en")


def test_calendari_message_localized():
    assert "Veure el calendari" in calendari_message("https://x.test/cal", "ca")
    assert "Ver el calendario" in calendari_message("https://x.test/cal", "es")


def test_messages_default_to_catalan():
    assert "Llegir més" in noticia_message("T", "s", "https://x.test")


def test_menu_keys_present_and_localized():
    for lang, expected in (("ca", "Demà dinem"), ("es", "Mañana comemos"), ("en", "Tomorrow")):
        assert expected in translate("menu.title", lang, data="24/09")
    assert translate("menu.variant.sense_porc", "ca") == "Sense porc"
    assert translate("menu.variant.sense_porc", "es") == "Sin cerdo"
    assert translate("no.existeix", "en") == "no.existeix"  # fallback a la clau


def test_menu_messages_localized():
    from datetime import date

    ca = menu_dema_message(["CREMA DE CARBASSA", "PA"], date(2026, 9, 24), "basal", "ca")
    es = menu_dema_message(["CREMA DE CARBASSA", "PA"], date(2026, 9, 24), "basal", "es")
    assert "Demà dinem 24/09" in ca
    assert "Mañana comemos 24/09" in es
    assert "CREMA DE CARBASSA" in ca
    pin = menu_pin_message("https://x.test/Basal.pdf", "ca")
    assert "Menú del mes" in pin
    assert "https://x.test/Basal.pdf" in pin
