import os
import re
import configparser
import asyncio
from threading import Thread

from telebot import types
from telebot.async_telebot import AsyncTeleBot

from TooGoodToGo import TooGoodToGo, NOTIFICATION_TYPES

# Load configuration
if not os.path.exists("config.ini"):
    print("ERROR: config.ini not found!")
    print("Please copy config.ini.example to config.ini and add your Telegram bot token.")
    exit(1)

config = configparser.ConfigParser()
config.read("config.ini")

if config.get("Telegram", "token", fallback="<YOUR_TOKEN>") == "<YOUR_TOKEN>":
    print("ERROR: Please set your Telegram bot token in config.ini")
    exit(1)

token = config["Telegram"]["token"]
bot = AsyncTeleBot(token)
tooGoodToGo = TooGoodToGo(token)


# ------------------------------------------------------------------
# Helper: check if the user is logged in, send error if not
# ------------------------------------------------------------------

async def _require_login(chat_id: str) -> bool:
    """Return True if the user is logged in, otherwise send an error message."""
    if tooGoodToGo.find_credentials_by_telegramUserID(chat_id) is not None:
        return True
    await bot.send_message(
        chat_id=chat_id,
        text=(
            "🔑 You have to log in with your mail first!\n"
            "Please enter */login email@example.com*\n"
            "*❗️️This is necessary if you want to use the bot❗️*"
        ),
        parse_mode="Markdown",
    )
    return False


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

@bot.message_handler(commands=["help", "start"])
async def send_welcome(message):
    await bot.send_message(
        message.chat.id,
        """
*Hi welcome to the TGTG Bot:*

The bot will notify you as soon as new bags from your favorites are available.

*❗️️This is necessary if you want to use the bot❗️*
🔑 To login into your TooGoodToGo account enter 
*/login email@example.com*
_You will receive an email with a PIN code.
Then enter_ */pin 12345* _to complete the login._

⚙️ With */settings* you can set when you want to be notified. 

ℹ️ With */info* you can display all stores from your favorites where bags are currently available.

_🌐 You can find more information about Too Good To Go_ [here](https://www.toogoodtogo.com/).

*🌍 LET'S FIGHT food waste TOGETHER 🌎*
""",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["info"])
async def send_info(message):
    chat_id = str(message.chat.id)
    if not await _require_login(chat_id):
        return
    Thread(target=tooGoodToGo.send_available_favourite_items_for_one_user, args=(chat_id,), daemon=True).start()


@bot.message_handler(commands=["login"])
async def send_login(message):
    chat_id = str(message.chat.id)
    if tooGoodToGo.find_credentials_by_telegramUserID(chat_id) is not None:
        await bot.send_message(chat_id=chat_id, text="👍 You are already logged in!")
        return

    email = message.text.replace("/login", "").strip()
    if re.match(r"[^@]+@[^@]+\.[^@]+", email):
        Thread(target=tooGoodToGo.new_user, args=(chat_id, email), daemon=True).start()
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "*⚠️ No valid mail address ⚠️*\n"
                "Please enter */login email@example.com*"
            ),
            parse_mode="Markdown",
        )



@bot.message_handler(commands=["pin"])
async def send_pin(message):
    """Handle /pin <code> – complete login with the PIN from email."""
    chat_id = str(message.chat.id)

    # Check if there's a pending login for this user
    if chat_id not in tooGoodToGo._pending_logins:
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ No pending login. Please start with */login email@example.com* first.",
            parse_mode="Markdown",
        )
        return

    pin = message.text.replace("/pin", "").strip()
    if not pin:
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ Please provide the PIN from your email:\n*/pin 12345*",
            parse_mode="Markdown",
        )
        return
    await bot.send_message(chat_id=chat_id, text="⏳ Verifying PIN...")
    Thread(target=tooGoodToGo.complete_login_with_pin, args=(chat_id, pin), daemon=True).start()


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

def _build_settings_keyboard(chat_id: str) -> types.InlineKeyboardMarkup:
    """Build the inline keyboard reflecting current notification settings."""
    settings = tooGoodToGo.users_settings_data.get(chat_id, {})
    labels = {
        "sold_out": "❌ Sold out",
        "new_stock": "✅ New bags",
        "stock_reduced": "📉 Less bags",
        "stock_increased": "📈 More bags",
    }
    buttons = []
    for key in NOTIFICATION_TYPES:
        icon = "🟢" if settings.get(key, 0) else "🔴"
        buttons.append(types.InlineKeyboardButton(text=f"{icon} {labels[key]}", callback_data=key))

    return types.InlineKeyboardMarkup(keyboard=[
        buttons[0:2],
        buttons[2:4],
        [types.InlineKeyboardButton(text="✅ activate all ✅", callback_data="activate_all")],
        [types.InlineKeyboardButton(text="❌ disable all ❌", callback_data="disable_all")],
    ])


@bot.message_handler(commands=["settings"])
async def send_settings(message):
    chat_id = str(message.chat.id)
    if not await _require_login(chat_id):
        return
    await bot.send_message(
        chat_id,
        "🟢 = enabled | 🔴 = disabled\n*Notify me when:*",
        parse_mode="Markdown",
        reply_markup=_build_settings_keyboard(chat_id),
    )


# ------------------------------------------------------------------
# Callback handlers – single toggle handler for all notification types
# ------------------------------------------------------------------

@bot.callback_query_handler(func=lambda c: c.data in NOTIFICATION_TYPES)
async def toggle_setting(call: types.CallbackQuery):
    """Toggle a single notification setting on/off."""
    chat_id = str(call.message.chat.id)
    key = call.data
    current = tooGoodToGo.users_settings_data[chat_id].get(key, 0)
    tooGoodToGo.users_settings_data[chat_id][key] = 0 if current else 1
    tooGoodToGo.save_users_settings_data_to_txt()
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=_build_settings_keyboard(chat_id),
    )


@bot.callback_query_handler(func=lambda c: c.data in ("activate_all", "disable_all"))
async def bulk_toggle(call: types.CallbackQuery):
    """Activate or disable all notification settings at once."""
    chat_id = str(call.message.chat.id)
    value = 1 if call.data == "activate_all" else 0
    for key in NOTIFICATION_TYPES:
        tooGoodToGo.users_settings_data[chat_id][key] = value
    tooGoodToGo.save_users_settings_data_to_txt()
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=_build_settings_keyboard(chat_id),
    )


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(bot.polling())
