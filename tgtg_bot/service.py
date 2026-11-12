"""TGTG side of the bot: logins, fetching favorites and the polling loop."""

from __future__ import annotations

import datetime
import logging
import random
import threading
import time
from collections.abc import Callable
from http import HTTPStatus

import requests
from tgtg.exceptions import TgtgAPIError, TgtgLoginError

from .client import BotTgtgClient, is_protection_block, is_unauthorized
from .config import Config
from .formatting import determine_status, item_id, items_available
from .storage import Storage

logger = logging.getLogger(__name__)

PAGE_SIZE = 50
MAX_PAGES = 5
BLOCK_BACKOFF_START = 5 * 60
BLOCK_BACKOFF_MAX = 60 * 60
PENDING_LOGIN_TTL = 30 * 60
OFFLINE_NOTIFY_AFTER = 20 * 60  # tell users after 20 min without connection

# notify(chat_id, kind, payload)
#   kind "item": payload = (item, status, wanted) – wanted: the user enabled this notification type.
#                Unwanted changes are still reported so an earlier message can be updated in place.
#   kind "text": payload = i18n key
Notifier = Callable[[str, str, object], None]


class BlockedError(Exception):
    """TGTG/DataDome rejected the request (captcha). Usually IP-related."""


class SessionExpiredError(Exception):
    """The stored refresh token is no longer valid – the user must log in again."""


class LoginError(Exception):
    """User-facing login problem. ``key``/``params`` select the text from ``i18n``."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


def _status_and_body(exc: Exception) -> tuple[int | None, bytes | str | None]:
    args = getattr(exc, "args", ())
    status = args[0] if args and isinstance(args[0], int) else None
    body = args[1] if len(args) > 1 and isinstance(args[1], (bytes, str)) else None
    return status, body


class TgtgService:
    def __init__(
        self,
        config: Config,
        storage: Storage,
        notify: Notifier,
        client_factory: Callable[..., BotTgtgClient] = BotTgtgClient,
    ):
        self.config = config
        self.storage = storage
        self.notify = notify
        self.client_factory = client_factory
        self._clients: dict[str, BotTgtgClient] = {}
        self._user_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._pending: dict[str, dict] = {}
        self._blocked_until: dict[str, float] = {}
        self._block_delay: dict[str, int] = {}
        self._offline_since: dict[str, float] = {}
        self._offline_notified: set[str] = set()
        self._error_streak: dict[str, int] = {}
        self.last_success: dict[str, datetime.datetime] = {}
        self.last_poll: datetime.datetime | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _lock(self, chat_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._user_locks.setdefault(chat_id, threading.Lock())

    def _language(self, chat_id: str) -> str:
        """Accept-Language for TGTG (affects texts like 'Nothing today')."""
        return "de-DE" if self.storage.language(chat_id) == "de" else self.config.language

    def _new_client(self, **kwargs) -> BotTgtgClient:
        return self.client_factory(
            proxy=self.config.proxy,
            base_url=self.config.base_url,
            item_endpoint=self.config.item_endpoint,
            user_agent=self.config.user_agent,
            **kwargs,
        )

    def _client(self, chat_id: str) -> BotTgtgClient:
        client = self._clients.get(chat_id)
        if client is None:
            creds = self.storage.credentials(chat_id)
            if not creds:
                raise SessionExpiredError()
            last = creds.get("last_refresh")
            client = self._new_client(
                access_token=creds.get("access_token"),
                refresh_token=creds.get("refresh_token"),
                cookie=creds.get("cookie"),
                last_time_token_refreshed=datetime.datetime.fromisoformat(last) if last else None,
                device_index=creds.get("device"),
                language=self._language(chat_id),
            )
            self._clients[chat_id] = client
        return client

    def forget_client(self, chat_id: str) -> None:
        self._clients.pop(chat_id, None)

    def is_blocked(self, chat_id: str) -> bool:
        return self._blocked_until.get(chat_id, 0) > time.time()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def has_pending_login(self, chat_id: str) -> bool:
        pending = self._pending.get(chat_id)
        if pending and time.time() - pending["created"] > PENDING_LOGIN_TTL:
            self._pending.pop(chat_id, None)
            return False
        return pending is not None

    def pending_email(self, chat_id: str) -> str | None:
        pending = self._pending.get(chat_id)
        return pending["email"] if pending else None

    def start_login(self, chat_id: str, email: str, lang: str = "en") -> None:
        """Ask TGTG to send a login PIN to ``email``. Raises ``LoginError``."""
        client = self._new_client(email=email, language="de-DE" if lang == "de" else self.config.language)
        try:
            polling_id = client.start_login()
        except ValueError as exc:
            raise LoginError("login_unknown_email") from exc
        except TgtgLoginError as exc:
            status, body = _status_and_body(exc)
            if is_protection_block(status or 0, body):
                raise LoginError("login_blocked") from exc
            if status == HTTPStatus.TOO_MANY_REQUESTS:
                raise LoginError("login_rate_limited") from exc
            logger.error("authByEmail failed: HTTP %s", status)
            raise LoginError("login_failed", status=status) from exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("Login request failed: %s", exc)
            raise LoginError("login_unreachable") from exc
        self._pending[chat_id] = {
            "client": client,
            "polling_id": polling_id,
            "email": email,
            "lang": lang,
            "created": time.time(),
        }

    def finish_login(self, chat_id: str, pin: str) -> None:
        """Complete the pending login with the PIN. Raises ``LoginError``."""
        if not self.has_pending_login(chat_id):
            raise LoginError("no_login_in_progress")
        pending = self._pending[chat_id]
        client: BotTgtgClient = pending["client"]
        try:
            client.finish_login(pending["polling_id"], pin)
        except TgtgLoginError as exc:
            status, body = _status_and_body(exc)
            if is_protection_block(status or 0, body):
                raise LoginError("pin_blocked") from exc
            raise LoginError("pin_wrong") from exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("PIN login failed: %s", exc)
            raise LoginError("login_unreachable") from exc
        self._pending.pop(chat_id, None)
        self.storage.set_credentials(chat_id, client.credentials(), email=pending["email"], language=pending["lang"])
        self._clients[chat_id] = client
        self._blocked_until.pop(chat_id, None)
        self.storage.stock.pop(chat_id, None)
        logger.info("Chat %s logged in", chat_id)

    def record_baseline(self, chat_id: str, items: list[dict]) -> None:
        """Remember the current stock if there is none yet (first fetch after login),
        so the very next check can already notify about changes."""
        if chat_id not in self.storage.stock:
            self.storage.set_stock(chat_id, {item_id(i): items_available(i) for i in items if item_id(i)})

    def logout(self, chat_id: str) -> None:
        self._pending.pop(chat_id, None)
        self.forget_client(chat_id)
        self.storage.remove_user(chat_id)

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _get_all_favorites(self, client: BotTgtgClient) -> list[dict]:
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            batch = client.get_items(favorites_only=True, page_size=PAGE_SIZE, page=page)
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
        return items

    def _refresh(self, client: BotTgtgClient, force: bool = False) -> None:
        try:
            if force:
                client.force_token_refresh()
            else:
                client.login()
        except (TgtgAPIError, TgtgLoginError) as exc:
            status, body = _status_and_body(exc)
            if is_protection_block(status or 0, body):
                raise BlockedError() from exc
            if status == HTTPStatus.BAD_REQUEST or is_unauthorized(status or 0, body):
                raise SessionExpiredError() from exc
            raise

    def _fetch(self, client: BotTgtgClient) -> list[dict]:
        self._refresh(client)
        try:
            return self._get_all_favorites(client)
        except TgtgAPIError as exc:
            status, body = _status_and_body(exc)
            if is_protection_block(status or 0, body):
                raise BlockedError() from exc
            if not is_unauthorized(status or 0, body):
                raise
        # Access token rejected before its expected lifetime – refresh once and retry
        self._refresh(client, force=True)
        try:
            return self._get_all_favorites(client)
        except TgtgAPIError as exc:
            status, body = _status_and_body(exc)
            if is_protection_block(status or 0, body):
                raise BlockedError() from exc
            raise

    def fetch_favorites(self, chat_id: str) -> list[dict]:
        """Return all favorite items of a user.

        Raises ``BlockedError`` (captcha), ``SessionExpiredError`` (log in
        again) or other exceptions for temporary problems.
        """
        with self._lock(chat_id):
            client = self._client(chat_id)
            try:
                items = self._fetch(client)
                self.last_success[chat_id] = datetime.datetime.now(self.config.timezone)
                return items
            except SessionExpiredError:
                self.forget_client(chat_id)
                self.storage.mark_needs_login(chat_id)
                raise
            finally:
                if self.storage.is_logged_in(chat_id):
                    self.storage.update_credentials(chat_id, client.credentials())

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _on_blocked(self, chat_id: str) -> None:
        delay = min(self._block_delay.get(chat_id, BLOCK_BACKOFF_START // 2) * 2, BLOCK_BACKOFF_MAX)
        first = chat_id not in self._block_delay
        self._block_delay[chat_id] = delay
        self._blocked_until[chat_id] = time.time() + delay
        # Next try with a fresh client (new DataDome cookie)
        self.forget_client(chat_id)
        logger.warning("Chat %s: blocked by DataDome, pausing %d min", chat_id, delay // 60)
        if first:
            self.notify(chat_id, "text", "blocked_notice")

    def _on_network_error(self, chat_id: str, exc: Exception) -> None:
        since = self._offline_since.setdefault(chat_id, time.time())
        streak = self._error_streak[chat_id] = self._error_streak.get(chat_id, 0) + 1
        # one warning per outage, details only in debug mode
        log = logger.warning if streak == 1 else logger.debug
        log("Chat %s: TGTG not reachable (%s) – retrying quietly", chat_id, type(exc).__name__)
        logger.debug("Network error details: %s", exc)
        if time.time() - since >= OFFLINE_NOTIFY_AFTER and chat_id not in self._offline_notified:
            self._offline_notified.add(chat_id)
            self.notify(chat_id, "text", "offline_notice")

    def is_offline(self, chat_id: str) -> bool:
        return chat_id in self._offline_since

    def _on_success(self, chat_id: str) -> None:
        self.last_success[chat_id] = datetime.datetime.now(self.config.timezone)
        streak = self._error_streak.pop(chat_id, 0)
        if streak > 1:
            logger.info("Chat %s: TGTG reachable again after %d failed checks", chat_id, streak)
        self._blocked_until.pop(chat_id, None)
        self._offline_since.pop(chat_id, None)
        was_blocked = self._block_delay.pop(chat_id, None) is not None
        was_offline = chat_id in self._offline_notified
        self._offline_notified.discard(chat_id)
        if was_blocked or was_offline:
            self.notify(chat_id, "text", "restored")

    def poll_user(self, chat_id: str) -> None:
        if self.is_blocked(chat_id):
            return
        try:
            items = self.fetch_favorites(chat_id)
        except BlockedError:
            self._on_blocked(chat_id)
            return
        except SessionExpiredError:
            logger.warning("Chat %s: session expired", chat_id)
            self.notify(chat_id, "text", "session_expired")
            return
        except requests.exceptions.RequestException as exc:
            self._on_network_error(chat_id, exc)
            return
        except Exception:  # noqa: BLE001
            logger.exception("Chat %s: error while fetching favorites", chat_id)
            return
        self._on_success(chat_id)
        self._process_items(chat_id, items)

    def _process_items(self, chat_id: str, items: list[dict]) -> None:
        old = self.storage.last_stock(chat_id)
        has_baseline = chat_id in self.storage.stock
        settings = self.storage.settings(chat_id)
        muted = self.storage.muted(chat_id)
        new: dict[str, int] = {}
        for item in items:
            iid = item_id(item)
            if not iid:
                continue
            count = items_available(item)
            new[iid] = count
            if iid in old:
                status = determine_status(int(old[iid]), count)
            elif has_baseline and count > 0:
                status = "new_stock"  # newly added favorite that has bags
            else:
                status = None
            if not status or iid in muted:
                continue
            wanted = settings.get(status, False)
            if wanted:
                logger.info("Chat %s: %s – %s (%d)", chat_id, status, item.get("display_name", iid), count)
            if wanted or status != "new_stock":
                self.notify(chat_id, "item", (item, status, wanted))
        self.storage.set_stock(chat_id, new)

    def poll_once(self) -> None:
        users = self.storage.active_users()
        if not users:
            logger.debug("No users with active notifications – skipping TGTG API")
            return
        for index, chat_id in enumerate(users):
            if index:
                time.sleep(random.uniform(2, 5))  # do not burst requests
            self.poll_user(chat_id)
        self.last_poll = datetime.datetime.now(self.config.timezone)

    def run_forever(self, stop: threading.Event) -> None:
        logger.info("Polling every ~%ds", self.config.poll_interval)
        while not stop.is_set():
            try:
                self.poll_once()
            except Exception:  # noqa: BLE001
                logger.exception("Unexpected error in polling loop")
            jitter = self.config.poll_interval * random.uniform(-0.1, 0.15)
            stop.wait(max(30.0, self.config.poll_interval + jitter))
