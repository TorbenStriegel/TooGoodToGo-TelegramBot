"""Telegram front end (pyTelegramBotAPI, synchronous + threaded)."""

from __future__ import annotations

import logging
import re
import threading

import telebot
from telebot import TeleBot, types
from telebot.apihelper import ApiTelegramException

from . import __version__
from .config import Config
from .formatting import build_item_text, escape, favorites_overview, item_link, items_available, maps_link
from .i18n import COMMANDS, DEFAULT_LANGUAGE, language_for, t
from .service import BlockedError, LoginError, SessionExpiredError, TgtgService
from .storage import NOTIFICATION_TYPES, Storage

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^@\s/]+@[^@\s]+\.[^@\s]+$")
PIN_RE = re.compile(r"^\d{4,8}$")


class TelegramBot:
    def __init__(self, config: Config, storage: Storage):
        self.config = config
        self.storage = storage
        # pyTelegramBotAPI ships its own stderr handler → avoid duplicated log lines
        telebot.logger.handlers.clear()
        telebot.logger.propagate = True
        self.bot = TeleBot(config.telegram_token, parse_mode="HTML", threaded=True, num_threads=4)
        self.service = TgtgService(config, storage, self.notify)
        self._lang: dict[str, str] = {}
        self._stop = threading.Event()
        self._register_handlers()

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------

    def _remember_language(self, chat_id: str, user: types.User | None) -> None:
        if user is None or not user.language_code:
            return
        lang = language_for(user.language_code)
        self._lang[chat_id] = lang
        self.storage.set_language(chat_id, lang)

    def lang(self, chat_id: str) -> str:
        return self._lang.get(chat_id) or self.storage.users.get(chat_id, {}).get("language") or DEFAULT_LANGUAGE

    def _t(self, chat_id: str, key: str, **kwargs) -> str:
        return t(self.lang(chat_id), key, **kwargs)

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _send(self, chat_id: str, text: str, **kwargs) -> None:
        try:
            self.bot.send_message(chat_id, text, disable_web_page_preview=True, **kwargs)
        except ApiTelegramException as exc:
            if exc.error_code == 403:  # user blocked the bot
                logger.info("Chat %s blocked the bot – disabling its notifications", chat_id)
                for key in NOTIFICATION_TYPES:
                    self.storage.set_setting(chat_id, key, False)
            else:
                logger.error("Telegram send to %s failed: %s", chat_id, exc)
        except Exception as exc:  # noqa: BLE001
            logger.error("Telegram send to %s failed: %s", chat_id, exc)

    def _say(self, chat_id: str, key: str, /, reply_markup=None, **kwargs) -> None:
        self._send(chat_id, self._t(chat_id, key, **kwargs), reply_markup=reply_markup)

    def _typing(self, chat_id: str) -> None:
        try:
            self.bot.send_chat_action(chat_id, "typing")
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _buttons(*rows: list[tuple[str, str]]) -> types.InlineKeyboardMarkup:
        """rows of (label, callback_data or URL)"""
        markup = types.InlineKeyboardMarkup()
        for row in rows:
            markup.row(
                *[
                    types.InlineKeyboardButton(label, url=target)
                    if target.startswith("http")
                    else types.InlineKeyboardButton(label, callback_data=target)
                    for label, target in row
                ]
            )
        return markup

    def send_item(self, chat_id: str, item: dict, status: str | None = None) -> None:
        lang = self.lang(chat_id)
        row = [(t(lang, "btn_open_app"), item_link(item))]
        route = maps_link(item)
        if route:
            row.append((t(lang, "btn_route"), route))
        self._send(
            chat_id,
            build_item_text(item, self.config.timezone, status, lang=lang),
            reply_markup=self._buttons(row),
            # only "new bags" should make a sound – the rest arrives silently
            disable_notification=status not in (None, "new_stock"),
        )

    def notify(self, chat_id: str, kind: str, payload) -> None:
        """Callback used by the polling service."""
        if kind == "item":
            item, status = payload
            self.send_item(chat_id, item, status)
        else:
            self._say(chat_id, str(payload))

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _allowed(self, chat_id: int, user_id: int | None) -> bool:
        if not self.config.allowed_users:
            return True
        return str(chat_id) in self.config.allowed_users or str(user_id) in self.config.allowed_users

    def _gate_message(self, message: types.Message) -> bool:
        """First filter for every message: remembers the language, rejects unknown users."""
        chat_id = str(message.chat.id)
        self._remember_language(chat_id, message.from_user)
        if self._allowed(message.chat.id, message.from_user.id if message.from_user else None):
            return False
        logger.warning("Rejected chat %s (not in allowed_users)", chat_id)
        self._say(chat_id, "private", id=chat_id)
        return True

    def _gate_callback(self, call: types.CallbackQuery) -> bool:
        chat_id = str(call.message.chat.id)
        self._remember_language(chat_id, call.from_user)
        return not self._allowed(call.message.chat.id, call.from_user.id)

    def _require_login(self, chat_id: str) -> bool:
        if self.storage.is_logged_in(chat_id):
            return True
        self._say(chat_id, "need_login")
        return False

    @staticmethod
    def _argument(message: types.Message) -> str:
        parts = (message.text or "").split(maxsplit=1)
        return parts[1].strip() if len(parts) > 1 else ""

    def _register_handlers(self) -> None:
        bot = self.bot

        @bot.message_handler(func=self._gate_message)
        def _reject(message):
            pass

        @bot.callback_query_handler(func=self._gate_callback)
        def _reject_callback(call):
            self.bot.answer_callback_query(call.id, self._t(str(call.message.chat.id), "not_allowed"))

        @bot.message_handler(commands=["start"])
        def _start(message):
            chat_id = str(message.chat.id)
            if self.storage.is_logged_in(chat_id):
                self._say(chat_id, "help", reply_markup=self._main_menu(chat_id))
            else:
                self._say(chat_id, "welcome")

        @bot.message_handler(commands=["help"])
        def _help(message):
            chat_id = str(message.chat.id)
            self._say(chat_id, "help", reply_markup=self._main_menu(chat_id))

        @bot.message_handler(commands=["login"])
        def _login(message):
            chat_id = str(message.chat.id)
            email = self._argument(message)
            if self.storage.is_logged_in(chat_id):
                self._say(chat_id, "already_logged_in")
            elif not email:
                self._say(chat_id, "ask_email")
            elif not EMAIL_RE.match(email):
                self._say(chat_id, "invalid_email")
            else:
                self._start_login(chat_id, email)

        @bot.message_handler(commands=["pin"])
        def _pin(message):
            self._handle_pin(str(message.chat.id), self._argument(message))

        @bot.message_handler(commands=["info"])
        def _info(message):
            self._show_info(str(message.chat.id))

        @bot.message_handler(commands=["settings"])
        def _settings(message):
            self._show_settings(str(message.chat.id))

        @bot.message_handler(commands=["status"])
        def _status(message):
            self._show_status(str(message.chat.id))

        @bot.message_handler(commands=["logout"])
        def _logout(message):
            chat_id = str(message.chat.id)
            if not self.storage.is_logged_in(chat_id):
                self.service.logout(chat_id)
                self._say(chat_id, "not_logged_in")
                return
            self._say(
                chat_id,
                "logout_confirm",
                reply_markup=self._buttons(
                    [(self._t(chat_id, "btn_logout_yes"), "logout_yes"), (self._t(chat_id, "btn_cancel"), "logout_no")]
                ),
            )

        @bot.message_handler(func=lambda m: bool(m.text) and EMAIL_RE.match(m.text.strip()) is not None)
        def _bare_email(message):
            chat_id = str(message.chat.id)
            if self.storage.is_logged_in(chat_id):
                self._say(chat_id, "already_logged_in")
            else:
                self._start_login(chat_id, message.text.strip())

        @bot.message_handler(func=lambda m: bool(m.text) and PIN_RE.match(m.text.strip()) is not None)
        def _bare_pin(message):
            chat_id = str(message.chat.id)
            if self.service.has_pending_login(chat_id):
                self._handle_pin(chat_id, message.text.strip())
            else:
                self._fallback(chat_id)

        @bot.callback_query_handler(func=lambda c: True)
        def _callback(call: types.CallbackQuery):
            self._on_callback(call)

        @bot.message_handler(func=lambda m: True, content_types=["text", "photo", "sticker", "document", "voice"])
        def _fallback(message):
            self._fallback(str(message.chat.id))

    def _fallback(self, chat_id: str) -> None:
        if self.service.has_pending_login(chat_id):
            self._say(chat_id, "need_pin")
        elif not self.storage.is_logged_in(chat_id):
            self._say(chat_id, "need_email")
        else:
            self._say(chat_id, "unknown", reply_markup=self._main_menu(chat_id))

    def _main_menu(self, chat_id: str) -> types.InlineKeyboardMarkup:
        return self._buttons(
            [(self._t(chat_id, "btn_info"), "info"), (self._t(chat_id, "btn_settings"), "settings")],
            [(self._t(chat_id, "btn_status"), "status")],
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _new_pin_button(self, chat_id: str) -> types.InlineKeyboardMarkup:
        return self._buttons([(self._t(chat_id, "btn_new_pin"), "resend_pin")])

    def _start_login(self, chat_id: str, email: str) -> None:
        self._typing(chat_id)
        try:
            self.service.start_login(chat_id, email, lang=self.lang(chat_id))
        except LoginError as exc:
            self._say(chat_id, exc.key, **exc.params)
            return
        self._say(chat_id, "pin_sent", email=escape(email), reply_markup=self._new_pin_button(chat_id))

    def _handle_pin(self, chat_id: str, pin: str) -> None:
        if not self.service.has_pending_login(chat_id):
            self._say(
                chat_id, "already_logged_in_short" if self.storage.is_logged_in(chat_id) else "no_login_in_progress"
            )
            return
        pin = pin.strip()
        if not PIN_RE.match(pin):
            self._say(chat_id, "need_pin")
            return
        self._typing(chat_id)
        try:
            self.service.finish_login(chat_id, pin)
        except LoginError as exc:
            self._say(chat_id, exc.key, reply_markup=self._new_pin_button(chat_id), **exc.params)
            return
        self._after_login(chat_id)

    def _after_login(self, chat_id: str) -> None:
        lang = self.lang(chat_id)
        intro = t(lang, "logged_in") + "\n\n"
        try:
            items = self.service.fetch_favorites(chat_id)
        except Exception:  # noqa: BLE001
            logger.exception("Initial fetch after login failed for %s", chat_id)
            self._send(chat_id, intro + t(lang, "logged_in_generic"), reply_markup=self._main_menu(chat_id))
            return
        self.service.record_baseline(chat_id, items)
        if not items:
            text = intro + t(lang, "logged_in_no_favorites")
        else:
            overview = favorites_overview(items, lang=lang)
            text = intro + t(lang, "logged_in_watching", count=len(items), overview=overview)
        self._send(chat_id, text, reply_markup=self._main_menu(chat_id))

    # ------------------------------------------------------------------
    # Screens
    # ------------------------------------------------------------------

    def _show_info(self, chat_id: str) -> None:
        if not self._require_login(chat_id):
            return
        lang = self.lang(chat_id)
        self._typing(chat_id)
        try:
            items = self.service.fetch_favorites(chat_id)
        except BlockedError:
            self._say(chat_id, "blocked_now")
            return
        except SessionExpiredError:
            self._say(chat_id, "session_expired")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("/info failed for %s: %s", chat_id, exc)
            self._say(chat_id, "fetch_failed")
            return
        self.service.record_baseline(chat_id, items)
        available = [i for i in items if items_available(i) > 0]
        if not items:
            self._say(chat_id, "no_favorites")
            return
        if not available:
            hint = t(lang, "will_notify" if self.storage.settings(chat_id)["new_stock"] else "notify_off")
            overview = favorites_overview(items, lang=lang)
            self._send(chat_id, t(lang, "nothing_available", overview=overview) + "\n\n" + hint)
            return
        for item in sorted(available, key=lambda i: -items_available(i)):
            self.send_item(chat_id, item)
        others = len(items) - len(available)
        if others:
            self._say(chat_id, "others_empty", count=others)

    def _show_settings(self, chat_id: str) -> None:
        if not self._require_login(chat_id):
            return
        self._say(chat_id, "settings_title", reply_markup=self._settings_keyboard(chat_id))

    def _show_status(self, chat_id: str) -> None:
        if self.service.has_pending_login(chat_id):
            self._say(chat_id, "status_pending")
            return
        if not self.storage.is_logged_in(chat_id):
            self._say(chat_id, "status_logged_out")
            return
        lang = self.lang(chat_id)
        enabled = [t(lang, "setting_" + k) for k, v in self.storage.settings(chat_id).items() if v]
        last = self.service.last_poll
        if self.service.is_blocked(chat_id):
            connection = t(lang, "status_blocked")
        elif self.service.is_offline(chat_id):
            connection = t(lang, "status_offline")
        else:
            connection = t(lang, "status_ok")
        lines = [
            t(lang, "status_logged_in", email=escape(self.storage.email(chat_id) or "?")),
            t(lang, "status_watching", count=len(self.storage.last_stock(chat_id))),
            t(lang, "status_notifications", list=", ".join(enabled) if enabled else t(lang, "status_all_off")),
            connection,
            t(lang, "status_last_check", time=f"{last:%H:%M:%S}", interval=self.config.poll_interval)
            if last
            else t(lang, "status_never"),
            f"<i>v{__version__}</i>",
        ]
        self._send(chat_id, "\n".join(lines))

    def _settings_keyboard(self, chat_id: str) -> types.InlineKeyboardMarkup:
        lang = self.lang(chat_id)
        settings = self.storage.settings(chat_id)
        buttons = [(f"{'🟢' if settings[k] else '🔴'} {t(lang, 'setting_' + k)}", k) for k in NOTIFICATION_TYPES]
        return self._buttons(buttons[:2], buttons[2:], [(t(lang, "all_on"), "all_on"), (t(lang, "all_off"), "all_off")])

    # ------------------------------------------------------------------
    # Inline buttons
    # ------------------------------------------------------------------

    def _on_callback(self, call: types.CallbackQuery) -> None:
        chat_id = str(call.message.chat.id)
        lang = self.lang(chat_id)
        data = call.data or ""
        toast = None
        if data in NOTIFICATION_TYPES or data in ("all_on", "all_off"):
            if not self.storage.is_logged_in(chat_id):
                toast = t(lang, "need_login")
            else:
                if data in NOTIFICATION_TYPES:
                    value = not self.storage.settings(chat_id)[data]
                    self.storage.set_setting(chat_id, data, value)
                    toast = f"{t(lang, 'setting_' + data)}: {t(lang, 'on' if value else 'off')}"
                else:
                    for key in NOTIFICATION_TYPES:
                        self.storage.set_setting(chat_id, key, data == "all_on")
                    toast = t(lang, "all_toggled", state=t(lang, "on" if data == "all_on" else "off"))
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=self._settings_keyboard(chat_id),
                    )
                except ApiTelegramException:
                    pass  # "message is not modified"
        elif data in ("info", "settings", "status"):
            self.bot.answer_callback_query(call.id)
            {"info": self._show_info, "settings": self._show_settings, "status": self._show_status}[data](chat_id)
            return
        elif data == "resend_pin":
            email = self.service.pending_email(chat_id)
            if self.storage.is_logged_in(chat_id):
                toast = t(lang, "already_logged_in_short")
            elif not email:
                toast = t(lang, "send_email_again")
            else:
                self.bot.answer_callback_query(call.id, t(lang, "requesting_pin"))
                self._start_login(chat_id, email)
                return
        elif data in ("logout_yes", "logout_no"):
            self._clear_buttons(call)
            if data == "logout_yes":
                self.service.logout(chat_id)
                self._send(chat_id, t(lang, "logged_out"))
            else:
                toast = t(lang, "cancelled")
        self.bot.answer_callback_query(call.id, toast)

    def _clear_buttons(self, call: types.CallbackQuery) -> None:
        try:
            self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except ApiTelegramException:
            pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _set_commands(self) -> None:
        try:
            self.bot.set_my_commands([types.BotCommand(c, d) for c, d in COMMANDS["en"]])
            for lang, commands in COMMANDS.items():
                if lang != "en":
                    self.bot.set_my_commands([types.BotCommand(c, d) for c, d in commands], language_code=lang)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not set bot commands: %s", exc)

    def run(self) -> None:
        me = self.bot.get_me()
        logger.info("Started @%s (v%s), %d user(s) stored", me.username, __version__, len(self.storage.users))
        self._set_commands()
        poller = threading.Thread(target=self.service.run_forever, args=(self._stop,), daemon=True, name="tgtg-poll")
        poller.start()
        try:
            while not self._stop.is_set():
                try:
                    self.bot.infinity_polling(
                        skip_pending=True, timeout=20, long_polling_timeout=20, logger_level=logging.WARNING
                    )
                    break
                except ApiTelegramException as exc:
                    if exc.error_code != 409:
                        raise
                    logger.error(
                        "Another instance is polling with the same bot token (HTTP 409). "
                        "Stop the other instance – retrying in 30s."
                    )
                    self._stop.wait(30)
        finally:
            self._stop.set()
