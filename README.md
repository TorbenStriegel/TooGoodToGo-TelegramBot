# Too Good To Go – Telegram Bot 🍽

A self-hosted Telegram bot that watches your [Too Good To Go](https://www.toogoodtogo.com/) **favorites** and
messages you as soon as bags become available – faster than waiting for the app's push notification.

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-GPLv3-green">
</p>

## Features

- 🔔 **Notifications** for your favorites: new bags, sold out, fewer bags, more bags – each switchable with one tap.
  Only *new bags* make a sound, everything else arrives silently.
- 🔄 **Live updates** – a *new bags* message keeps itself up to date while the bags sell (*3 → 1 available →
  ❌ Sold out*) instead of flooding the chat with new messages
- 🔕 **Mute single stores** right from a notification, and unmute them later in `/settings`
- 🌙 **Silent at night** – optional: notifications between 22:00 and 07:00 arrive without sound
- 🔑 **Login in 2 messages** – send your email, then the PIN from the TGTG email. No password, no commands to remember.
- 🛍 **Rich messages** – store, bag type, ⭐ rating, price vs. original value, pickup window (*Today 17:00–18:30*,
  in your time zone), address plus buttons **📱 Open in app** and **📍 Route**
- ℹ️ `/info` shows what's available right now – and which favorites have nothing today
- 🇩🇪 🇬🇧 **German and English** – picked automatically from the user's Telegram language
- 👥 **Multi-user** – everyone logs in with their own TGTG account; optionally restrict the bot to your own Telegram IDs
- 🛡 **Careful with the API** – only polls when someone wants notifications, adds jitter, and backs off automatically
  when TGTG's bot protection (DataDome) kicks in. Short network hiccups are handled silently; longer outages and
  blocks are reported once – and you get a message when it works again
- 🔄 **Stays logged in** – refreshed tokens and cookies are saved, so restarts don't require a new login
- 🐳 Runs with plain Python or **Docker**

## Quick start

You need **Python 3.11+** and a Telegram bot token.

1. **Create a bot**: open [@BotFather](https://t.me/BotFather) in Telegram → `/newbot` → copy the token (`123456789:ABC…`).
2. **Download and start**:

   ```bash
   git clone https://github.com/TorbenStriegel/TooGoodToGo-TelegramBot.git
   cd TooGoodToGo-TelegramBot
   python quickstart.py
   ```

   The script asks for the token, writes `config.ini`, installs the dependencies and starts the bot.
3. **Log in via Telegram**: open your bot, tap *Start* and
   1. send the **email address** of your TGTG account – TGTG emails you a **PIN**
   2. send the **PIN** (just the number) – *don't click the link in the email*
4. Done ✅ – the bot shows the favorites it now watches and notifies you about new bags.
   Tap *⚙️ Notifications* (or `/settings`) to get more notifications.

> 💡 Recommended: restrict the bot to yourself. Send `/start` from a second account or look at the bot log to
> get your chat ID, then set `allowed_users = <your id>` in `config.ini` (see [Configuration](#configuration)).

<details>
<summary><b>Manual installation (without quickstart.py)</b></summary>

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.ini.example config.ini # Windows: copy config.ini.example config.ini
# edit config.ini and set the token
python -m tgtg_bot               # or: python Telegram.py
```
</details>

## Running with Docker

```bash
cp .env.example .env     # set TELEGRAM_TOKEN (and optionally ALLOWED_USERS)
mkdir -p data && sudo chown 1000:1000 data   # the container runs as uid 1000
docker compose up -d --build
docker compose logs -f
```

User data is stored in `./data`. Every option of `config.ini` can be set as an environment variable (see below).

## Running permanently (systemd)

<details>
<summary>Example unit for a Linux server / Raspberry Pi</summary>

`/etc/systemd/system/tgtg-bot.service`:

```ini
[Unit]
Description=Too Good To Go Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/TooGoodToGo-TelegramBot
ExecStart=/home/pi/TooGoodToGo-TelegramBot/.venv/bin/python -m tgtg_bot
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now tgtg-bot
journalctl -u tgtg-bot -f
```
</details>

## Bot commands

| Command | Description |
|---|---|
| `/start`, `/help` | Introduction and menu |
| *your email address* or `/login your@email.com` | Start the login – TGTG emails you a PIN |
| *the PIN* or `/pin 123456` | Finish the login (a button lets you request a new PIN) |
| `/info` | What's available right now |
| `/settings` | Choose notifications: ✅ new bags · ❌ sold out · 📉 fewer bags · 📈 more bags · 🌙 silent at night · 🔕 muted stores |
| `/status` | Login, number of watched favorites, connection state and last successful check |

Every notification has the buttons **📱 Open in app**, **📍 Route** and **🔕 Mute this store**.
| `/logout` | Log out and delete all your data from the bot (with confirmation) |

## Configuration

`config.ini` (created from [`config.ini.example`](config.ini.example)). Environment variables override the file.

| Section / key | Env variable | Default | Description |
|---|---|---|---|
| `[Telegram] token` | `TELEGRAM_TOKEN` | – | Bot token from @BotFather (**required**) |
| `[Telegram] allowed_users` | `ALLOWED_USERS` | *(everyone)* | Comma-separated Telegram user/chat IDs allowed to use the bot. Others see their ID and are rejected. |
| `[TGTG] poll_interval` | `POLL_INTERVAL` | `60` | Seconds between checks (min. 30). Lower = higher risk of being blocked. |
| `[TGTG] proxy` | `TGTG_PROXY` | – | HTTP/SOCKS proxy for all TGTG requests, e.g. `http://user:pass@host:8080` |
| `[Bot] timezone` | `TIMEZONE` | `Europe/Berlin` | Time zone for pickup times |
| `[Bot] data_dir` | `DATA_DIR` | `data` | Where `users.json` and `stock.json` are stored |
| `[TGTG] base_url` | `TGTG_BASE_URL` | `https://api.toogoodtogo.com/api/` | Advanced: API host |
| `[TGTG] item_endpoint` | `TGTG_ITEM_ENDPOINT` | `item/v9/` | Advanced: item endpoint version |
| `[TGTG] user_agent` | `TGTG_USER_AGENT` | *(current app version, modern device)* | Advanced: fixed user agent |
| – | `LOG_LEVEL` | `INFO` | `DEBUG` for more details |

## Troubleshooting

**"Login was blocked by TGTG's bot protection (captcha)" / "Too Good To Go is currently blocking requests"**
TGTG uses [DataDome](https://datadome.co/) against bots. Whether you're blocked mainly depends on the **IP address**
of the machine running the bot and on how many requests it sends.

- Wait – a block usually disappears after a few hours. The bot pauses by itself (5 min, doubling up to 1 h) and tells you when it works again.
- Don't set `poll_interval` too low and don't run several bots/scripts against TGTG from the same IP.
- Restarting your router often gives you a new IP.
- Still blocked? Set a `proxy`. Residential/mobile proxies work best; VPN exits can work but are hit or miss.

The captcha can't be "forwarded" to you: the cookie it produces is bound to the IP and app fingerprint of the bot,
so solving it in your phone's browser wouldn't unblock the bot.

**"Your session has expired"** – the TGTG refresh token is no longer valid (e.g. you logged out everywhere in the app).
Simply `/login` again.

**No notifications although bags are available** – the bot notifies you about *changes*: when a favorite goes from
0 to ≥1 bags. Bags that were already available when you logged in are shown in the overview / `/info`.
Check `/settings` (is ✅ *New bags* 🟢?) and `/status`.

**"Could not obtain a DataDome cookie from the SDK endpoint" in the log** – harmless. DNS filters such as Pi-hole,
AdGuard or some routers block `datadome.co`; the TGTG API sets the cookie itself, so the bot works anyway.

**HTTP 409 "terminated by other getUpdates request" in the log** – the same bot token is used by a second running
instance. Stop the other one; the bot retries automatically.

**The login email contains a link instead of a PIN** – use the newest email; if TGTG only sends a link, try again later.

## Upgrading from 2.x

Version 3 stores its data in `data/` instead of the `*.txt` files in the project folder and migrates them
automatically on first start – **existing logins and settings are kept**. Because `config.ini` and the `*.txt` files
are no longer part of the repository, back them up before pulling:

```bash
mkdir -p ../tgtg-backup && cp config.ini *.txt ../tgtg-backup/
git checkout -- config.ini users_login_data.txt users_settings_data.txt available_items_favorites.txt
git pull
cp ../tgtg-backup/* .
pip install -r requirements.txt   # Python 3.11+ is now required
python -m tgtg_bot                # migrates *.txt → data/ (old files are renamed to *.migrated)
```

## How it works

- A background thread checks the favorites of every user who has at least one notification enabled (every
  `poll_interval` seconds ± jitter, a few seconds apart per user) and compares the number of available bags with the
  last check. If nobody wants notifications, TGTG isn't contacted at all.
- The TGTG API is accessed with the [`tgtg`](https://github.com/ahivert/tgtg-python) library from PyPI. The bot adds a
  thin layer on top ([`tgtg_bot/client.py`](tgtg_bot/client.py)): current app version and device fingerprint for the
  DataDome SDK, consistent cookie handling (fresh DataDome cookies actually get sent), proxy support for every request
  and robust token refresh.

```
tgtg_bot/
├── __main__.py    entry point (python -m tgtg_bot)
├── bot.py         Telegram commands and messages
├── service.py     login, fetching favorites, polling, back-off
├── client.py      TGTG API client (wraps the tgtg library)
├── storage.py     users.json / stock.json / messages.json, migration from 2.x
├── formatting.py  message layout
├── i18n.py        all texts in English and German
└── config.py      config.ini + environment variables
```

### Development

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest
```

## Disclaimer

This project is not affiliated with Too Good To Go. It uses an unofficial API that can change at any time. Use it for
your own account(s) and keep the polling interval reasonable.

## Credits

- [Too Good To Go](https://www.toogoodtogo.com/) – 🌍 let's fight food waste together
- [@ahivert/tgtg-python](https://github.com/ahivert/tgtg-python) – Python client for the TGTG API
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)
- All contributors – see the [changelog](CHANGELOG.md)

## License

[GPL-3.0](LICENSE)
