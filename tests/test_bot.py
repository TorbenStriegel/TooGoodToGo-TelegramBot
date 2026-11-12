"""Telegram flows end to end – Telegram API calls are recorded instead of sent."""

import time

import pytest
from telebot import types
from test_service import FakeClient, LoginClient, item

from tgtg_bot.bot import TelegramBot
from tgtg_bot.config import Config
from tgtg_bot.storage import Storage

CHAT = 4711


class Recorder:
    def __init__(self, tb):
        self.calls = []
        bot = tb.bot
        bot.threaded = False
        bot.send_message = lambda chat_id, text, **kw: self.calls.append(("send", str(chat_id), text, kw))
        bot.send_chat_action = lambda *a, **kw: None
        bot.edit_message_reply_markup = lambda *a, **kw: self.calls.append(("edit", a, kw))
        bot.edit_message_text = lambda text, **kw: self.calls.append(("edit_text", text, kw))
        self.next_id = 100

        def send_message(chat_id, text, **kw):
            self.next_id += 1
            self.calls.append(("send", str(chat_id), text, kw))
            return types.Message.de_json(
                {"message_id": self.next_id, "date": 0, "chat": {"id": int(chat_id), "type": "private"}, "text": text}
            )

        bot.send_message = send_message
        bot.answer_callback_query = lambda cid, text=None, **kw: self.calls.append(("answer", text))

    def texts(self, chat=str(CHAT)):
        return [c[2] for c in self.calls if c[0] == "send" and c[1] == chat]

    def last_markup(self):
        return [c[3].get("reply_markup") for c in self.calls if c[0] == "send"][-1]


_uid = [0]


def message(text, chat=CHAT, lang=None):
    _uid[0] += 1
    sender = {"id": chat, "is_bot": False, "first_name": "T"}
    if lang:
        sender["language_code"] = lang
    entities = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}] if text.startswith("/") else []
    return types.Update.de_json(
        {
            "update_id": _uid[0],
            "message": {
                "message_id": _uid[0],
                "date": int(time.time()),
                "text": text,
                "chat": {"id": chat, "type": "private"},
                "from": sender,
                "entities": entities,
            },
        }
    )


def callback(data, chat=CHAT, text="x", markup=None):
    _uid[0] += 1
    return types.Update.de_json(
        {
            "update_id": _uid[0],
            "callback_query": {
                "id": str(_uid[0]),
                "chat_instance": "x",
                "data": data,
                "from": {"id": chat, "is_bot": False, "first_name": "T"},
                "message": {
                    "message_id": 1,
                    "date": 1,
                    "chat": {"id": chat, "type": "private"},
                    "text": text,
                    **({"reply_markup": markup} if markup else {}),
                },
            },
        }
    )


@pytest.fixture
def setup(tmp_path):
    FakeClient.script = []
    FakeClient.refresh_error = None
    tb = TelegramBot(Config(telegram_token="1:x"), Storage(tmp_path, legacy_dir=None))
    tb.service.client_factory = LoginClient
    rec = Recorder(tb)

    def send(*updates):
        tb.bot.process_new_updates(list(updates))

    return tb, rec, send


def test_login_by_plain_email_and_pin_shows_watched_favorites(setup):
    tb, rec, send = setup
    send(message("/start"))
    assert "send me the <b>email address</b>" in rec.texts()[-1]
    send(message("me@x.de"))
    assert "PIN" in rec.texts()[-1] and "me@x.de" in rec.texts()[-1]
    send(message("000000"))
    assert "didn't work" in rec.texts()[-1]
    FakeClient.script = [[item("a", 2), item("b", 0)]]
    send(message("123456"))
    text = rec.texts()[-1]
    assert "logged in" in text and "<b>2</b> favorite(s)" in text and "Store a" in text
    # baseline recorded right away → the next poll can notify immediately
    assert tb.storage.last_stock(str(CHAT)) == {"a": 2, "b": 0}
    FakeClient.script = [[item("a", 2), item("b", 4)]]
    tb.service.poll_once()
    assert rec.texts()[-1].startswith("<b>✅ New bags available!</b>")
    assert [c[3] for c in rec.calls if c[0] == "send"][-1]["disable_notification"] is False


def test_unknown_input_guides_the_user(setup):
    tb, rec, send = setup
    send(message("hello"))
    assert "email address" in rec.texts()[-1]
    send(message("/login"))
    assert "email address" in rec.texts()[-1]
    send(message("me@x.de"))
    send(message("hello"))
    assert "PIN" in rec.texts()[-1]


def test_info_settings_and_logout(setup):
    tb, rec, send = setup
    tb.storage.set_credentials(str(CHAT), {"access_token": "a", "refresh_token": "r"}, email="me@x.de")
    FakeClient.script = [[item("a", 0), item("b", 0)]]
    send(message("/info"))
    assert "Nothing available right now" in rec.texts()[-1]
    FakeClient.script = [[item("a", 1), item("b", 0)]]
    send(callback("info"))
    assert "Store a" in rec.texts()[-2] and "1 other favorite" in rec.texts()[-1]

    send(message("/settings"))
    send(callback("sold_out"))
    assert tb.storage.settings(str(CHAT))["sold_out"] is True
    assert ("answer", "❌ Sold out: on") in rec.calls
    send(callback("all_off"))
    assert not any(tb.storage.settings(str(CHAT)).values())

    send(message("/logout"))
    assert tb.storage.is_logged_in(str(CHAT))  # confirmation first
    send(callback("logout_yes"))
    assert not tb.storage.is_logged_in(str(CHAT))


def test_allowed_users(tmp_path):
    tb = TelegramBot(Config(telegram_token="1:x", allowed_users={"1"}), Storage(tmp_path, legacy_dir=None))
    rec = Recorder(tb)
    tb.bot.process_new_updates([message("me@x.de", chat=999)])
    assert rec.texts("999") == ["⛔ This bot is private.\nYour chat ID: <code>999</code>"]
    assert not tb.service.has_pending_login("999")


def test_german_user_gets_german_texts(setup):
    tb, rec, send = setup
    send(message("/start", lang="de-DE"))
    assert "Willkommen" in rec.texts()[-1]
    send(message("me@x.de", lang="de"))
    assert "Schick mir einfach die Zahl" in rec.texts()[-1]
    FakeClient.script = [[item("a", 0)]]
    send(message("123456", lang="de"))
    assert "Du bist angemeldet" in rec.texts()[-1] and "Ich beobachte jetzt deine <b>1</b> Favoriten" in rec.texts()[-1]
    assert tb.storage.language(str(CHAT)) == "de"
    # background notification (no incoming message) uses the stored language
    tb._lang.clear()
    FakeClient.script = [[item("a", 3)]]
    tb.service.poll_once()
    assert rec.texts()[-1].startswith("<b>✅ Neue Tüten verfügbar!</b>")
    assert "<b>3</b> verfügbar" in rec.texts()[-1]
    markup = rec.last_markup().to_dict()["inline_keyboard"][0]
    assert markup[0]["text"] == "📱 In der App öffnen"
    send(message("/settings", lang="de"))
    send(callback("sold_out"))
    assert ("answer", "❌ Ausverkauft: an") in rec.calls


def logged_in(tb):
    tb.storage.set_credentials(str(CHAT), {"access_token": "a", "refresh_token": "r"}, email="me@x.de")
    tb.storage.set_stock(str(CHAT), {"a": 0})


def test_new_bags_message_is_updated_in_place_until_sold_out(setup):
    tb, rec, send = setup
    logged_in(tb)
    FakeClient.script = [[item("a", 3)], [item("a", 1)], [item("a", 0)], [item("a", 0)]]
    tb.service.poll_once()
    assert rec.texts()[-1].startswith("<b>✅ New bags available!</b>")
    live_id = rec.next_id
    assert tb.storage.live_message(str(CHAT), "a") == live_id
    tb.service.poll_once()  # 3 -> 1: silent edit, no new message
    edits = [c for c in rec.calls if c[0] == "edit_text"]
    assert len(edits) == 1 and edits[0][2]["message_id"] == live_id
    assert "<b>1</b> available" in edits[0][1] and "Updated" in edits[0][1]
    assert len(rec.texts()) == 1
    tb.service.poll_once()  # 1 -> 0: message turns into "sold out", live tracking ends
    assert "Sold out" in [c for c in rec.calls if c[0] == "edit_text"][-1][1]
    assert tb.storage.live_message(str(CHAT), "a") is None
    assert len(rec.texts()) == 1


def test_mute_store_from_notification_and_unmute_from_settings(setup):
    tb, rec, send = setup
    logged_in(tb)
    FakeClient.script = [[item("a", 2)]]
    tb.service.poll_once()
    markup = rec.last_markup().to_dict()
    assert markup["inline_keyboard"][1][0]["callback_data"] == "mute:a"
    send(callback("mute:a", text="✅ New bags available!\n🍽 Store a\n🥡 2 available", markup=markup))
    assert tb.storage.muted(str(CHAT)) == {"a": "Store a"}
    assert ("answer", "🔕 Store a: no more notifications") in rec.calls
    swapped = [c for c in rec.calls if c[0] == "edit"][-1][2]["reply_markup"].to_dict()
    assert swapped["inline_keyboard"][1][0]["callback_data"] == "unmute:a"
    assert swapped["inline_keyboard"][0][0]["text"] == "📱 Open in app"  # other buttons kept
    FakeClient.script = [[item("a", 0)], [item("a", 5)]]
    tb.service.poll_once()
    tb.service.poll_once()
    assert len(rec.texts()) == 1  # muted: no new notification
    send(message("/settings"))
    rows = rec.last_markup().to_dict()["inline_keyboard"]
    assert rows[-1][0]["callback_data"] == "muted_list"
    send(callback("muted_list"))
    assert rec.last_markup().to_dict()["inline_keyboard"] == [[{"text": "🔔 Store a", "callback_data": "unmute_l:a"}]]
    send(callback("unmute_l:a"))
    assert tb.storage.muted(str(CHAT)) == {}


def test_quiet_night_and_status(setup, monkeypatch):
    import tgtg_bot.bot as botmod

    tb, rec, send = setup
    logged_in(tb)
    send(message("/settings"))
    send(callback("quiet"))
    assert tb.storage.quiet_night(str(CHAT)) is True

    class Night(botmod.datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return botmod.datetime.datetime(2026, 11, 11, 23, 30, tzinfo=tz)

    monkeypatch.setattr(botmod.datetime, "datetime", Night)
    FakeClient.script = [[item("a", 2)]]
    tb.service.poll_once()
    sent = [c for c in rec.calls if c[0] == "send"][-1]
    assert sent[2].startswith("<b>✅ New bags available!</b>") and sent[3]["disable_notification"] is True
    send(message("/status"))
    status = rec.texts()[-1]
    assert "Silent at night" in status and "Last successful check" in status
    assert f"<code>{CHAT}</code>" in status
