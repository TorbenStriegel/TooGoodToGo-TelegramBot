from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tgtg_bot.formatting import (
    build_item_text,
    determine_status,
    favorites_overview,
    format_pickup,
    format_price,
    format_value,
    maps_link,
)

BERLIN = ZoneInfo("Europe/Berlin")
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=BERLIN)


@pytest.mark.parametrize(
    "old,new,expected",
    [
        (0, 0, None),
        (3, 3, None),
        (0, 2, "new_stock"),
        (2, 0, "sold_out"),
        (3, 1, "stock_reduced"),
        (1, 4, "stock_increased"),
    ],
)
def test_determine_status(old, new, expected):
    assert determine_status(old, new) == expected


def make_item(**overrides):
    """Shape taken from a real item/v9 response."""
    item = {
        "item": {
            "item_id": "42",
            "item_price": {"code": "EUR", "minor_units": 399, "decimals": 2},
            "item_value": {"code": "EUR", "minor_units": 1200, "decimals": 2},
            "name": "",
            "item_sub_category_details": {"name": "Bakery <Surprise> Bag"},
            "average_overall_rating": {"average_overall_rating": 4.7727, "rating_count": 22},
        },
        "store": {"store_name": "Bäckerei & Co", "branch": "Hauptstr."},
        "display_name": "Bäckerei & Co - Hauptstr.",
        "pickup_location": {
            "address": {"address_line": "Hauptstr. 1, 76133 Karlsruhe"},
            "location": {"latitude": 49.01, "longitude": 8.35},
        },
        "items_available": 3,
        "pickup_interval": {"start": "2026-11-11T16:00:00Z", "end": "2026-11-11T17:30:00Z"},
        "item_tags": [{"short_text": "Nothing today"}],
    }
    item.update(overrides)
    return item


def test_price_value_and_pickup_in_local_time():
    item = make_item()
    assert format_price(item) == "3.99 €"
    assert format_value(item) == "12.00 €"
    assert format_pickup(item, BERLIN, NOW) == "Today 17:00–18:30"
    tomorrow = make_item(pickup_interval={"start": "2026-11-12T07:00:00Z", "end": "2026-11-12T08:00:00Z"})
    assert format_pickup(tomorrow, BERLIN, NOW) == "Tomorrow 08:00–09:00"
    later = make_item(pickup_interval={"start": "2026-11-14T07:00:00Z", "end": "2026-11-14T08:00:00Z"})
    assert format_pickup(later, BERLIN, NOW) == "Sat 14.11. 08:00–09:00"


def test_legacy_price_field():
    item = make_item(item={"item_id": "1", "price_including_taxes": {"code": "GBP", "minor_units": 250, "decimals": 2}})
    assert format_price(item) == "2.50 £"


def test_item_text_is_html_escaped_and_complete():
    text = build_item_text(make_item(), BERLIN, "new_stock", NOW)
    assert text.startswith("<b>✅ New bags available!</b>")
    assert "Bäckerei &amp; Co - Hauptstr." in text
    assert "Bakery &lt;Surprise&gt; Bag · ⭐ 4.8 (22)" in text
    assert "<b>3.99 €</b> <s>12.00 €</s>" in text
    assert "⏰ Pickup Today 17:00–18:30" in text
    assert "📍 Hauptstr. 1, 76133 Karlsruhe" in text


def test_sold_out_has_no_pickup_and_missing_fields_are_tolerated():
    text = build_item_text(make_item(items_available=0), BERLIN, "sold_out")
    assert "⏰" not in text and "none left" in text
    assert "available" in build_item_text({"item": {"item_id": "1"}, "store": {}, "items_available": 1}, BERLIN)


def test_maps_link_and_overview():
    assert maps_link(make_item()) == "https://www.google.com/maps/search/?api=1&query=49.01,8.35"
    assert maps_link({"item": {}, "store": {}}) is None
    overview = favorites_overview([make_item(items_available=0), make_item(display_name="A & B", items_available=2)])
    assert overview.splitlines() == [
        "🟢 A &amp; B – <b>2</b> available",
        "⚪️ Bäckerei &amp; Co - Hauptstr. – <i>Nothing today</i>",
    ]


def test_german_formatting():
    text = build_item_text(make_item(), BERLIN, "sold_out", NOW, lang="de")
    assert text.startswith("<b>❌ Ausverkauft</b>") and "<b>3</b> verfügbar" in text
    assert format_pickup(make_item(), BERLIN, NOW, "de") == "Heute 17:00–18:30"
    later = make_item(pickup_interval={"start": "2026-11-14T07:00:00Z", "end": "2026-11-14T08:00:00Z"})
    assert format_pickup(later, BERLIN, NOW, "de") == "Sa 14.11. 08:00–09:00"


def test_every_text_has_both_languages():
    from tgtg_bot.i18n import TEXTS, language_for

    assert all(set(v) == {"en", "de"} for v in TEXTS.values())
    assert language_for("de-AT") == "de" and language_for("fr") == "en" and language_for(None) == "en"
