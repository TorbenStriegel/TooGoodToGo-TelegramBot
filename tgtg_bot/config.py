"""Configuration: ``config.ini`` with optional environment variable overrides."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import DEFAULT_BASE_URL, DEFAULT_ITEM_ENDPOINT

PLACEHOLDER_TOKEN = "<YOUR_TOKEN>"


class ConfigError(Exception):
    pass


@dataclass
class Config:
    telegram_token: str
    allowed_users: set[str] = field(default_factory=set)
    poll_interval: int = 60
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Europe/Berlin"))
    data_dir: Path = Path("data")
    proxy: str | None = None
    language: str = "en-GB"
    base_url: str = DEFAULT_BASE_URL
    item_endpoint: str = DEFAULT_ITEM_ENDPOINT
    user_agent: str | None = None


def _get(parser: configparser.ConfigParser, env: str, section: str, key: str, default: str = "") -> str:
    value = os.environ.get(env)
    if value is None:
        value = parser.get(section, key, fallback=default)
    return (value or "").strip()


def load_config(path: str | os.PathLike = "config.ini") -> Config:
    """Load ``config.ini`` (optional when env vars are used) and validate it."""
    parser = configparser.ConfigParser()
    path = Path(os.environ.get("TGTG_BOT_CONFIG", path))
    if path.exists():
        parser.read(path, encoding="utf-8")

    token = _get(parser, "TELEGRAM_TOKEN", "Telegram", "token")
    if not token or token == PLACEHOLDER_TOKEN:
        raise ConfigError(
            "No Telegram bot token configured.\n"
            "Copy config.ini.example to config.ini and set [Telegram] token, "
            "or set the TELEGRAM_TOKEN environment variable."
        )

    allowed = _get(parser, "ALLOWED_USERS", "Telegram", "allowed_users")
    allowed_users = {u.strip() for u in allowed.replace(";", ",").split(",") if u.strip()}

    try:
        poll_interval = int(_get(parser, "POLL_INTERVAL", "TGTG", "poll_interval", "60") or 60)
    except ValueError as exc:
        raise ConfigError("[TGTG] poll_interval must be a number of seconds") from exc
    if poll_interval < 30:
        raise ConfigError("[TGTG] poll_interval must be at least 30 seconds (risk of being blocked)")

    tz_name = _get(parser, "TIMEZONE", "Bot", "timezone", "Europe/Berlin") or "Europe/Berlin"
    try:
        timezone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"Unknown timezone '{tz_name}' (e.g. Europe/Berlin)") from exc

    return Config(
        telegram_token=token,
        allowed_users=allowed_users,
        poll_interval=poll_interval,
        timezone=timezone,
        data_dir=Path(_get(parser, "DATA_DIR", "Bot", "data_dir", "data") or "data"),
        proxy=_get(parser, "TGTG_PROXY", "TGTG", "proxy") or None,
        language=_get(parser, "TGTG_LANGUAGE", "TGTG", "language", "en-GB") or "en-GB",
        base_url=_get(parser, "TGTG_BASE_URL", "TGTG", "base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL,
        item_endpoint=_get(parser, "TGTG_ITEM_ENDPOINT", "TGTG", "item_endpoint", DEFAULT_ITEM_ENDPOINT)
        or DEFAULT_ITEM_ENDPOINT,
        user_agent=_get(parser, "TGTG_USER_AGENT", "TGTG", "user_agent") or None,
    )
