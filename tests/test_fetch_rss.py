"""Tests del fetcher RSS i del filtre per categories (tasca 3.1)."""

from tests.conftest import FIXTURES

from src.fetch_rss import parse_feed, select_items


def _items():
    return parse_feed((FIXTURES / "feed.xml").read_bytes())


def test_parse_feed_counts_and_fields():
    items = _items()
    assert len(items) == 5
    first = items[0]
    assert first.guid.endswith("p=9001")
    assert first.title == "Reunió de famílies d'I4"
    assert first.link.endswith("/reunio-families-i4/")
    assert "I4" in first.categories
    assert "Reunió" in first.summary  # el resum cru pot portar HTML


def test_filter_by_categories():
    items = _items()
    selected = select_items(items, ["I4", "Portada", "General"])
    guids = {i.guid.rsplit("=", 1)[-1] for i in selected}
    # I4, I4B (prefix), Portada i General; NO 3r ni 6è
    assert guids == {"9001", "9004", "9005"}


def test_filter_prefix_matches_subgroup():
    items = _items()
    selected = select_items(items, ["I4"])
    assert {i.guid.rsplit("=", 1)[-1] for i in selected} == {"9001", "9005"}


def test_no_filter_returns_all():
    assert len(select_items(_items(), [])) == 5


def test_filter_excludes_items_without_categories():
    items = _items()
    items[0].categories = []
    selected = select_items(items, ["I4"])
    assert items[0].guid not in {i.guid for i in selected}


def test_parse_invalid_feed_returns_empty():
    assert parse_feed(b"no soc rss") == []
