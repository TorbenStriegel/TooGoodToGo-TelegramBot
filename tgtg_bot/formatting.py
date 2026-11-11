"""Turning TGTG API items into Telegram messages (HTML parse mode)."""

from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from html import escape as _escape
from urllib.parse import quote

from .i18n import t


def escape(text: str) -> str:
    """HTML-escape for Telegram (quotes don't need escaping)."""
    return _escape(text, quote=False)


CURRENCY_SYMBOLS = {
    "EUR": "€",
    "GBP": "£",
    "USD": "$",
    "CHF": "CHF",
    "DKK": "kr",
    "SEK": "kr",
    "NOK": "kr",
    "PLN": "zł",
}


def determine_status(old_count: int, new_count: int) -> str | None:
    """Compare two stock counts and return the kind of change (or None)."""
    if old_count == new_count:
        return None
    if new_count == 0:
        return "sold_out"
    if old_count == 0:
        return "new_stock"
    return "stock_reduced" if new_count < old_count else "stock_increased"


def item_id(item: dict) -> str:
    return str(item.get("item", {}).get("item_id", ""))


def items_available(item: dict) -> int:
    try:
        return int(item.get("items_available") or 0)
    except (TypeError, ValueError):
        return 0


def _money(price: dict | None) -> str | None:
    if not price or "minor_units" not in price:
        return None
    decimals = int(price.get("decimals", 2))
    value = int(price["minor_units"]) / (10**decimals)
    code = price.get("code", "EUR")
    return f"{value:.{decimals}f} {CURRENCY_SYMBOLS.get(code, code)}"


def format_price(item: dict) -> str | None:
    info = item.get("item", {})
    return _money(info.get("item_price") or info.get("price_including_taxes"))


def format_value(item: dict) -> str | None:
    """Original value of the bag (what it would normally cost)."""
    return _money(item.get("item", {}).get("item_value"))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _day_label(day: datetime, now: datetime, lang: str) -> str:
    if day.date() == now.date():
        return t(lang, "today")
    if day.date() == (now + timedelta(days=1)).date():
        return t(lang, "tomorrow")
    weekday = t(lang, "weekdays").split()[day.weekday()]
    return f"{weekday} {day:%d.%m.}"


def format_pickup(item: dict, tz: tzinfo, now: datetime | None = None, lang: str = "en") -> str | None:
    interval = item.get("pickup_interval")
    if not interval:
        return None
    try:
        start = _parse_time(interval["start"]).astimezone(tz)
        end = _parse_time(interval["end"]).astimezone(tz)
    except (KeyError, ValueError):
        return None
    now = (now or datetime.now(tz)).astimezone(tz)
    if start.date() == end.date():
        return f"{_day_label(start, now, lang)} {start:%H:%M}–{end:%H:%M}"
    return f"{_day_label(start, now, lang)} {start:%H:%M} – {_day_label(end, now, lang)} {end:%H:%M}"


def store_name(item: dict, lang: str = "en") -> str:
    if item.get("display_name"):
        return item["display_name"]
    store = item.get("store", {})
    name = store.get("store_name") or t(lang, "unknown_store")
    branch = store.get("branch")
    return f"{name} – {branch}" if branch and branch not in name else name


def bag_name(item: dict) -> str | None:
    info = item.get("item", {})
    return info.get("name") or (info.get("item_sub_category_details") or {}).get("name")


def _location(item: dict) -> dict:
    return item.get("pickup_location") or item.get("store", {}).get("store_location") or {}


def address(item: dict) -> str | None:
    return (_location(item).get("address") or {}).get("address_line") or None


def rating(item: dict) -> str | None:
    data = item.get("item", {}).get("average_overall_rating") or {}
    value, count = data.get("average_overall_rating"), data.get("rating_count")
    if not value or not count:
        return None
    return f"{value:.1f} ({count})"


def status_tag(item: dict) -> str | None:
    """Short info from the app such as 'Nothing today' or 'Sold out'."""
    tags = item.get("item_tags") or []
    return tags[0].get("short_text") if tags and isinstance(tags[0], dict) else None


def build_item_text(
    item: dict, tz: tzinfo, status: str | None = None, now: datetime | None = None, lang: str = "en"
) -> str:
    lines = []
    if status:
        lines.append(f"<b>{escape(t(lang, 'status_' + status))}</b>")
    lines.append(f"🍽 <b>{escape(store_name(item, lang))}</b>")
    bag = bag_name(item)
    if bag:
        stars = rating(item)
        lines.append(f"🛍 {escape(bag)}" + (f" · ⭐ {stars}" if stars else ""))
    count = items_available(item)
    lines.append(f"🥡 <b>{count}</b> {t(lang, 'available')}" if count else f"🥡 {t(lang, 'none_left')}")
    price, value = format_price(item), format_value(item)
    if price:
        lines.append(f"💰 <b>{escape(price)}</b>" + (f" <s>{escape(value)}</s>" if value and value != price else ""))
    if status != "sold_out":
        pickup = format_pickup(item, tz, now, lang)
        if pickup:
            lines.append(f"⏰ {t(lang, 'pickup')} {escape(pickup)}")
    addr = address(item)
    if addr:
        lines.append(f"📍 {escape(addr)}")
    return "\n".join(lines)


def item_link(item: dict) -> str:
    return f"https://share.toogoodtogo.com/item/{item_id(item)}"


def maps_link(item: dict) -> str | None:
    loc = _location(item).get("location") or {}
    lat, lon = loc.get("latitude"), loc.get("longitude")
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    addr = address(item)
    return f"https://www.google.com/maps/search/?api=1&query={quote(addr)}" if addr else None


def favorites_overview(items: list[dict], limit: int = 15, lang: str = "en") -> str:
    """One line per favorite: name + availability (available ones first)."""
    lines = []
    for item in sorted(items, key=lambda i: (-items_available(i), store_name(i, lang)))[:limit]:
        count = items_available(item)
        name = escape(store_name(item, lang))
        if count:
            lines.append(f"🟢 {name} – <b>{count}</b> {t(lang, 'available')}")
        else:
            tag = status_tag(item)
            lines.append(f"⚪️ {name}" + (f" – <i>{escape(tag)}</i>" if tag else ""))
    if len(items) > limit:
        lines.append(t(lang, "and_more", count=len(items) - limit))
    return "\n".join(lines)
