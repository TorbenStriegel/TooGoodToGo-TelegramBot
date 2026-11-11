"""Thread-safe JSON persistence for users, settings and stock state."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = ("new_stock", "sold_out", "stock_reduced", "stock_increased")
DEFAULT_SETTINGS = {"new_stock": True, "sold_out": False, "stock_reduced": False, "stock_increased": False}

# Files written by bot versions < 3.0 (in the working directory)
LEGACY_FILES = ("users_login_data.txt", "users_settings_data.txt", "available_items_favorites.txt")


def _read_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Could not read %s: %s", path, exc)
        return {}


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Storage:
    """``users.json``: credentials + settings per Telegram chat.
    ``stock.json``: last seen ``items_available`` per chat and item."""

    def __init__(self, data_dir: Path, legacy_dir: Path | None = Path(".")):
        self.data_dir = Path(data_dir)
        self.users_path = self.data_dir / "users.json"
        self.stock_path = self.data_dir / "stock.json"
        self._lock = threading.RLock()
        self.users: dict[str, dict] = _read_json(self.users_path)
        self.stock: dict[str, dict[str, int]] = _read_json(self.stock_path)
        if not self.users and legacy_dir is not None:
            self._migrate_legacy(Path(legacy_dir))

    # ------------------------------------------------------------------
    def _migrate_legacy(self, legacy_dir: Path) -> None:
        logins = _read_json(legacy_dir / LEGACY_FILES[0])
        settings = _read_json(legacy_dir / LEGACY_FILES[1])
        if not logins:
            return
        for chat_id, creds in logins.items():
            if not isinstance(creds, dict) or not creds.get("refresh_token"):
                continue
            old = settings.get(chat_id, {})
            self.users[str(chat_id)] = {
                "credentials": {
                    "access_token": creds.get("access_token"),
                    "refresh_token": creds.get("refresh_token"),
                    "cookie": creds.get("cookie"),
                },
                "settings": {k: bool(old.get(k, DEFAULT_SETTINGS[k])) for k in NOTIFICATION_TYPES},
            }
        self.save_users()
        logger.info("Migrated %d user(s) from the old *.txt files to %s", len(self.users), self.users_path)
        for name in LEGACY_FILES:
            src = legacy_dir / name
            if src.exists():
                src.rename(src.with_name(src.name + ".migrated"))

    # ------------------------------------------------------------------
    def save_users(self) -> None:
        with self._lock:
            _write_json_atomic(self.users_path, self.users)

    def save_stock(self) -> None:
        with self._lock:
            _write_json_atomic(self.stock_path, self.stock)

    # ------------------------------------------------------------------
    def is_logged_in(self, chat_id: str) -> bool:
        return bool(self.users.get(chat_id, {}).get("credentials"))

    def credentials(self, chat_id: str) -> dict | None:
        return self.users.get(chat_id, {}).get("credentials")

    def set_credentials(
        self, chat_id: str, credentials: dict, email: str | None = None, language: str | None = None
    ) -> None:
        with self._lock:
            user = self.users.setdefault(chat_id, {"settings": dict(DEFAULT_SETTINGS)})
            user["credentials"] = credentials
            if email:
                user["email"] = email
            if language:
                user["language"] = language
            user.pop("needs_login", None)
            self.save_users()

    def update_credentials(self, chat_id: str, credentials: dict) -> None:
        """Persist refreshed tokens/cookies – only writes when something changed."""
        with self._lock:
            user = self.users.get(chat_id)
            if user is None or user.get("credentials") == credentials:
                return
            user["credentials"] = credentials
            self.save_users()

    def mark_needs_login(self, chat_id: str) -> None:
        with self._lock:
            if chat_id in self.users:
                self.users[chat_id]["credentials"] = None
                self.users[chat_id]["needs_login"] = True
                self.save_users()

    def remove_user(self, chat_id: str) -> None:
        with self._lock:
            self.users.pop(chat_id, None)
            self.stock.pop(chat_id, None)
            self.save_users()
            self.save_stock()

    def language(self, chat_id: str) -> str:
        return self.users.get(chat_id, {}).get("language", "en")

    def set_language(self, chat_id: str, language: str) -> None:
        """Remember the user's language (only for known users, only writes on change)."""
        with self._lock:
            user = self.users.get(chat_id)
            if user is not None and user.get("language") != language:
                user["language"] = language
                self.save_users()

    def email(self, chat_id: str) -> str | None:
        return self.users.get(chat_id, {}).get("email")

    # ------------------------------------------------------------------
    def settings(self, chat_id: str) -> dict[str, bool]:
        stored = self.users.get(chat_id, {}).get("settings", {})
        return {k: bool(stored.get(k, DEFAULT_SETTINGS[k])) for k in NOTIFICATION_TYPES}

    def set_setting(self, chat_id: str, key: str, value: bool) -> None:
        with self._lock:
            user = self.users.setdefault(chat_id, {})
            user.setdefault("settings", dict(DEFAULT_SETTINGS))[key] = bool(value)
            self.save_users()

    def wants_notifications(self, chat_id: str) -> bool:
        return self.is_logged_in(chat_id) and any(self.settings(chat_id).values())

    def active_users(self) -> list[str]:
        return [cid for cid in list(self.users) if self.wants_notifications(cid)]

    # ------------------------------------------------------------------
    def last_stock(self, chat_id: str) -> dict[str, int]:
        return self.stock.get(chat_id, {})

    def set_stock(self, chat_id: str, stock: dict[str, int]) -> None:
        with self._lock:
            self.stock[chat_id] = stock
            self.save_stock()
