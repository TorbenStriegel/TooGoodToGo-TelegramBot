import configparser
import json
import logging
import time
from datetime import datetime, timezone
from threading import Thread

from telebot import TeleBot, types
from tgtg import TgtgClient
from tgtg.exceptions import TgtgLoginError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Notification status keys used in user settings
NOTIFICATION_TYPES = ("sold_out", "new_stock", "stock_reduced", "stock_increased")

# Human-readable labels for notification status types
STATUS_LABELS = {
    "sold_out": "❌ Sold out",
    "new_stock": "✅ New bags available!",
    "stock_reduced": "📉 Stock reduced",
    "stock_increased": "📈 Stock increased",
}

# Default polling interval in seconds
POLL_INTERVAL = 60

# Load optional proxy from config
_config = configparser.ConfigParser()
_config.read("config.ini")
TGTG_PROXY = _config.get("TGTG", "proxy", fallback="").strip() or None


class TooGoodToGo:
    """Core class that manages TGTG API interaction and Telegram notifications."""

    def __init__(self, bot_token: str):
        self.bot = TeleBot(bot_token)
        self.users_login_data: dict = {}
        self.users_settings_data: dict = {}
        self.available_items_favorites: dict = {}
        self.connected_clients: dict = {}
        self._pending_logins: dict = {}  # telegram_user_id -> {client, polling_id, email}

        self._load_all_data()

        # Start background polling thread
        self._poll_thread = Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        self.bot.set_my_commands([
            types.BotCommand("/info", "favorite bags that currently available"),
            types.BotCommand("/login", "log in with your mail"),
            types.BotCommand("/pin", "enter PIN from email to complete login"),
            types.BotCommand("/settings", "set when you want to be notified"),
            types.BotCommand("/help", "short explanation"),
        ])

    # ------------------------------------------------------------------
    # Data persistence
    # ------------------------------------------------------------------

    def _load_all_data(self):
        """Load all persisted data from disk."""
        self.users_login_data = self._read_json("users_login_data.txt")
        self.users_settings_data = self._read_json("users_settings_data.txt")
        self.available_items_favorites = self._read_json("available_items_favorites.txt")

    @staticmethod
    def _read_json(path: str) -> dict:
        """Read a JSON file and return its content as dict."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.loads(f.read())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write_json(path: str, data: dict):
        """Write a dict to a JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def save_users_login_data_to_txt(self):
        self._write_json("users_login_data.txt", self.users_login_data)

    def save_users_settings_data_to_txt(self):
        self._write_json("users_settings_data.txt", self.users_settings_data)

    def save_available_items_favorites_to_txt(self):
        self._write_json("available_items_favorites.txt", self.available_items_favorites)

    # ------------------------------------------------------------------
    # Messaging helpers
    # ------------------------------------------------------------------

    def send_message(self, telegram_user_id: str, message: str, parse_mode: str = None):
        self.bot.send_message(telegram_user_id, text=message, parse_mode=parse_mode)

    def send_message_with_link(self, telegram_user_id: str, message: str, item_id: str):
        """Send a message with an inline button linking to the TGTG app."""
        markup = types.InlineKeyboardMarkup(keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Open in app 📱",
                    callback_data="open_app",
                    url=f"https://share.toogoodtogo.com/item/{item_id}"
                )
            ]
        ])
        self.bot.send_message(telegram_user_id, text=message, reply_markup=markup)

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def add_user(self, telegram_user_id: str, credentials: dict):
        """Register a new user with their TGTG credentials and default settings."""
        self.users_login_data[telegram_user_id] = credentials
        self.save_users_login_data_to_txt()
        self.users_settings_data[telegram_user_id] = {key: 1 if key == "new_stock" else 0 for key in NOTIFICATION_TYPES}
        self.save_users_settings_data_to_txt()

    def _get_proxy_dict(self) -> dict | None:
        """Return proxy dict for requests if configured, else None."""
        if TGTG_PROXY:
            return {"http": TGTG_PROXY, "https": TGTG_PROXY}
        return None


    def new_user(self, telegram_user_id: str, email: str):
        """Start the TGTG login flow (blocking – run in a thread).

        After sending the auth email, TGTG returns a polling_id. The patched
        library now uses PIN-based auth, so we intercept before input() is
        called and ask the user for the PIN via Telegram.
        """
        try:
            client = TgtgClient(email=email, proxies=self._get_proxy_dict())

            # Call login() manually to intercept polling_id before input() is hit
            from tgtg import AUTH_BY_EMAIL_ENDPOINT
            response = client._post(
                client._get_url(AUTH_BY_EMAIL_ENDPOINT),
                json={"device_type": client.device_type, "email": client.email},
            )

            if response.status_code == 200:
                login_resp = response.json()
                if login_resp.get("state") == "WAIT":
                    polling_id = login_resp["polling_id"]
                    # Store for later PIN completion
                    self._pending_logins[telegram_user_id] = {
                        "client": client,
                        "polling_id": polling_id,
                        "email": email,
                    }
                    logger.info("Login initiated for %s – waiting for PIN", email)
                    self.send_message(
                        telegram_user_id,
                        "📩 Check your email for a *login PIN code* from Too Good To Go.\n\n"
                        "Then send it here:\n"
                        "/pin 12345",
                        parse_mode="Markdown",
                    )
                elif login_resp.get("state") == "TERMS":
                    self.send_message(
                        telegram_user_id,
                        "❌ This email is not linked to a TGTG account.\n"
                        "Please sign up in the TGTG app first."
                    )
                else:
                    self.send_message(telegram_user_id, f"❌ Unexpected response: {login_resp.get('state')}")
            else:
                raise TgtgLoginError(response.status_code, response.content)

        except TgtgLoginError as e:
            captcha_url = self._extract_captcha_url(e)
            if captcha_url:
                logger.warning("Captcha challenge for %s – Datadome block", email)
                self.send_message(
                    telegram_user_id,
                    "🔒 *Login blocked by TGTG (Datadome captcha).*\n\n"
                    "💡 Try again later or use a VPN/mobile hotspot.",
                    parse_mode="Markdown",
                )
            else:
                logger.error("Login failed for %s: %s", email, e)
                self.send_message(telegram_user_id, "❌ Login failed. Please try again later.")
        except Exception as e:
            logger.exception("Unexpected error during login for %s", email)
            self.send_message(telegram_user_id, f"❌ Login failed: {e}")

    def complete_login_with_pin(self, telegram_user_id: str, pin: str):
        """Complete a pending login with the PIN from the user's email."""
        pending = self._pending_logins.pop(telegram_user_id, None)
        if not pending:
            self.send_message(
                telegram_user_id,
                "⚠️ No pending login found. Please start with /login first."
            )
            return

        try:
            client: TgtgClient = pending["client"]
            client._auth_by_pin(pending["polling_id"], pin)
            credentials = {
                "access_token": client.access_token,
                "refresh_token": client.refresh_token,
                "cookie": client.cookie,
            }
            self.add_user(telegram_user_id, credentials)
            self.send_message(telegram_user_id, "✅ You are now logged in!")
            logger.info("Login completed for %s", pending["email"])
        except TgtgLoginError as e:
            logger.error("PIN auth failed for %s: %s", pending["email"], e)
            # Put it back so user can retry
            self._pending_logins[telegram_user_id] = pending
            self.send_message(
                telegram_user_id,
                "❌ Invalid PIN. Please check your email and try again:\n/pin 12345"
            )
        except Exception as e:
            logger.exception("Error completing login for %s", pending["email"])
            self.send_message(telegram_user_id, f"❌ Login failed: {e}")


    @staticmethod
    def _extract_captcha_url(error: TgtgLoginError) -> str | None:
        """Try to extract the captcha URL from a TgtgLoginError response."""
        try:
            # error.args is (status_code, body_bytes)
            body = error.args[1]
            if isinstance(body, bytes):
                body = body.decode("utf-8")
            data = json.loads(body)
            return data.get("url")
        except Exception:
            return None

    def find_credentials_by_telegramUserID(self, user_id: str) -> dict | None:
        """Return stored TGTG credentials for a Telegram user, or None."""
        return self.users_login_data.get(user_id)

    # ------------------------------------------------------------------
    # TGTG API connection
    # ------------------------------------------------------------------

    def connect(self, user_id: str):
        """Ensure a TgtgClient is available for the given user."""
        if user_id in self.connected_clients:
            self.client = self.connected_clients[user_id]
        else:
            creds = self.find_credentials_by_telegramUserID(user_id)
            self.client = TgtgClient(
                access_token=creds["access_token"],
                refresh_token=creds["refresh_token"],
                cookie=creds["cookie"],
                proxies=self._get_proxy_dict(),
            )
            self.connected_clients[user_id] = self.client
            time.sleep(3)

    def get_favourite_items(self) -> list:
        """Fetch the current user's favourite items from the TGTG API."""
        return self.client.get_items()

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_pickup_time(iso_string: str) -> str:
        """Convert an ISO-8601 timestamp to a human-readable string."""
        dt = datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%a %d.%m at %H:%M")

    @staticmethod
    def _build_item_text(item: dict, include_pickup: bool = True) -> str:
        """Build a formatted notification string for one item."""
        # Price field: try new API format first, fall back to legacy
        price_data = item["item"].get("item_price") or item["item"].get("price_including_taxes", {})
        price = int(price_data.get("minor_units", 0)) / 100
        lines = [
            "🍽 " + str(item["store"]["store_name"]),
            "🧭 " + str(item["store"]["store_location"]["address"]["address_line"]),
            f"💰 {price:.2f} €",
            "🥡 " + str(item["items_available"]) + " available",
        ]
        if include_pickup and "pickup_interval" in item:
            start = TooGoodToGo._format_pickup_time(item["pickup_interval"]["start"])
            end = TooGoodToGo._format_pickup_time(item["pickup_interval"]["end"])
            lines.append(f"⏰ {start} - {end}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # /info command – one-time query for a single user
    # ------------------------------------------------------------------

    def send_available_favourite_items_for_one_user(self, user_id: str):
        """Fetch and send all currently available favourites for one user."""
        try:
            self.connect(user_id)
            favourite_items = self.get_favourite_items()
            found = False
            for item in favourite_items:
                if item["items_available"] > 0:
                    found = True
                    item_id = item["item"]["item_id"]
                    text = self._build_item_text(item)
                    self.send_message_with_link(user_id, text, item_id)
            if not found:
                self.send_message(user_id, "Currently all your favorites are sold out 😕")
        except Exception as e:
            logger.exception("Error fetching items for user %s", user_id)
            self.send_message(user_id, f"❌ Could not fetch your favorites: {e}")

    # ------------------------------------------------------------------
    # Background polling – only query API when notifications are wanted
    # ------------------------------------------------------------------

    def _user_needs_notifications(self, user_id: str) -> bool:
        """Check if the user has at least one notification type enabled."""
        settings = self.users_settings_data.get(user_id, {})
        return any(settings.get(key, 0) for key in NOTIFICATION_TYPES)

    def _determine_status(self, old_count: int, new_count: int) -> str | None:
        """Compare old and new item counts and return the status change type."""
        if new_count == 0 and old_count > 0:
            return "sold_out"
        if old_count == 0 and new_count > 0:
            return "new_stock"
        if old_count > new_count:
            return "stock_reduced"
        if old_count < new_count:
            return "stock_increased"
        return None

    def _poll_loop(self):
        """Main polling loop – skips TGTG API calls when no user needs notifications."""
        while True:
            try:
                # Collect users that actually want notifications
                active_users = [
                    uid for uid in self.users_login_data
                    if self._user_needs_notifications(uid)
                ]

                if not active_users:
                    logger.info("No users with active notifications – skipping API poll.")
                    time.sleep(POLL_INTERVAL)
                    continue

                logger.info("Polling TGTG API for %d active user(s).", len(active_users))
                temp_status: dict[str, str] = {}

                for user_id in active_users:
                    try:
                        self.connect(user_id)
                        time.sleep(1)
                        items = self.get_favourite_items()
                    except Exception:
                        logger.exception("Error fetching items for user %s – resetting connection", user_id)
                        self.connected_clients.pop(user_id, None)
                        continue

                    for item in items:
                        item_id = item["item"]["item_id"]

                        # Determine status change (only first occurrence per item)
                        if item_id in self.available_items_favorites and item_id not in temp_status:
                            old_count = int(self.available_items_favorites[item_id]["items_available"])
                            new_count = int(item["items_available"])
                            status = self._determine_status(old_count, new_count)
                            if status:
                                temp_status[item_id] = status

                        # Update cached state
                        self.available_items_favorites[item_id] = item

                        # Send notification if the user has this status type enabled
                        if item_id in temp_status:
                            status = temp_status[item_id]
                            user_settings = self.users_settings_data.get(user_id, {})
                            if user_settings.get(status, 0):
                                include_pickup = status != "sold_out"
                                text = self._build_item_text(item, include_pickup=include_pickup)
                                text += f"\n{STATUS_LABELS.get(status, status)}"
                                logger.info("%s – Telegram user %s\n%s", status, user_id, text)
                                self.send_message_with_link(user_id, text, item_id)

                self.save_available_items_favorites_to_txt()

            except Exception:
                logger.exception("Error during polling loop")

            time.sleep(POLL_INTERVAL)
