# Too Good To Go – Telegram Bot 🍽

A self-hosted Telegram bot that watches your [Too Good To Go](https://www.toogoodtogo.com/) **favorites** and messages
you as soon as Surprise Bags become available – often faster than the app.

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="Docker" src="https://img.shields.io/badge/docker-amd64%20%7C%20arm64%20%7C%20armv7-blue">
  <img alt="License" src="https://img.shields.io/badge/license-GPLv3-green">
</p>

## Features

- 🔔 **Instant notifications** when a favorite has bags – optionally also when it sells out or stock changes
- 🔄 **Live messages** – a notification updates itself while the bags sell (*3 → 1 → ❌ sold out*)
- 🛍 Store, bag type, ⭐ rating, price, pickup window and address, with **📱 Open in app** and **📍 Route** buttons
- 🔕 **Mute single stores** with one tap, 🌙 optional **silent nights** (22–7)
- 🔑 **Easy login** – send your email, then the PIN from the TGTG email. No password needed.
- 🇩🇪 🇬🇧 German and English, 👥 multiple users, 🔒 optionally private
- 🛡 Gentle on the TGTG API and recovers automatically from blocks and network problems

## Setup

### 1. Create your Telegram bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram and send `/newbot`.
2. Choose a name and a username ending in `bot`.
3. Copy the **token** – it looks like `123456789:ABC-DEF…`. Keep it secret.

### 2. Start the bot

Choose **one** option. The bot only sends notifications while it is running, so a computer that is always on
(Raspberry Pi, NAS, server) is ideal.

#### Option A – Start script *(Windows · macOS · Linux · Raspberry Pi)*

Requires [Python 3.11+](https://www.python.org/downloads/) (Windows: tick *Add python.exe to PATH* during setup).

1. Download the [latest release](https://github.com/TorbenStriegel/TooGoodToGo-TelegramBot/releases/latest)
   (*Source code (zip)*) and unpack it – or `git clone` the repository.
2. Start it:
   - **Windows:** double-click `start.bat`
   - **macOS / Linux:** run `sh start.sh` in the folder
3. Paste the bot token when asked.

The script installs everything into a local `.venv` folder and starts the bot. Use the same script to start it
again later.

#### Option B – Docker *(server · NAS · Raspberry Pi)*

```bash
docker run -d --name tgtg-bot \
  --restart unless-stopped \
  -e TELEGRAM_TOKEN=123456789:ABC... \
  -v tgtg-data:/data \
  ghcr.io/torbenstriegel/toogoodtogo-telegrambot
```

Show the logs with `docker logs -f tgtg-bot`.

**Or with Docker Compose:** put [`docker-compose.yml`](docker-compose.yml) and [`.env.example`](.env.example) into a
folder, rename `.env.example` to `.env`, enter the token and run:

```bash
docker compose up -d
```

#### Option C – Manual installation

<details>
<summary>Show commands</summary>

```bash
git clone https://github.com/TorbenStriegel/TooGoodToGo-TelegramBot.git
cd TooGoodToGo-TelegramBot
python3 -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.ini.example config.ini                   # then enter the token in config.ini
python -m tgtg_bot
```
</details>

### 3. Log in

Open your bot in Telegram and tap **Start**:

1. Send the **email address** of your Too Good To Go account.
2. TGTG emails you a **PIN** – send just the number. *Don't click the link in the email.*

Done ✅ – the bot shows which favorites it watches and notifies you about new bags. Stores you mark with ❤️ in the
TGTG app are picked up automatically.

> 🔒 **Make it private (recommended):** anyone who finds your bot could use it. Send `/status` to see your chat ID and
> enter it as `allowed_users` in `config.ini` (Docker: `ALLOWED_USERS`), then restart the bot.

## Using the bot

| Command | |
|---|---|
| `/info` | What's available right now |
| `/settings` | Choose notifications: ✅ new bags · ❌ sold out · 📉 fewer · 📈 more · 🌙 silent at night · 🔕 muted stores |
| `/status` | Login, connection, last check and your chat ID |
| `/login`, `/logout` | Log in (or just send your email) / log out and delete your data |
| `/help` | Short help |

Every notification has the buttons **📱 Open in app**, **📍 Route** and **🔕 Mute this store**. Only *new bags* make
a sound; everything else arrives silently.

## Configuration

Settings live in `config.ini` (start script) or are passed as environment variables (Docker, `.env`).
Only the token is required.

| `config.ini` | Environment | Default | |
|---|---|---|---|
| `[Telegram] token` | `TELEGRAM_TOKEN` | – | Bot token (**required**) |
| `[Telegram] allowed_users` | `ALLOWED_USERS` | everyone | Comma-separated chat IDs allowed to use the bot |
| `[Bot] timezone` | `TIMEZONE` | `Europe/Berlin` | Time zone for pickup times |
| `[TGTG] poll_interval` | `POLL_INTERVAL` | `60` | Seconds between checks (min. 30) |
| `[TGTG] proxy` | `TGTG_PROXY` | – | Proxy for TGTG requests, e.g. `http://user:pass@host:8080` |
| `[Bot] data_dir` | `DATA_DIR` | `data` | Where logins and state are stored |
| – | `LOG_LEVEL` | `INFO` | `DEBUG` for details |

<details>
<summary>Advanced (only if TGTG changes its API)</summary>

`[TGTG] base_url` / `TGTG_BASE_URL` (default `https://api.toogoodtogo.com/api/`),
`[TGTG] item_endpoint` / `TGTG_ITEM_ENDPOINT` (default `item/v9/`),
`[TGTG] user_agent` / `TGTG_USER_AGENT`, `[TGTG] language` / `TGTG_LANGUAGE`.
</details>

## Updating

- **Start script:** download the new release into the same folder (or `git pull`) and start again –
  dependencies are updated automatically, logins are kept.
- **Docker:** `docker pull ghcr.io/torbenstriegel/toogoodtogo-telegrambot`, then recreate the container
  (Compose: `docker compose pull && docker compose up -d`).

<details>
<summary>Upgrading from version 2.x</summary>

Logins and settings are migrated automatically. Back up your files before pulling, because `config.ini` and the
`*.txt` files are no longer part of the repository:

```bash
mkdir -p ../tgtg-backup && cp config.ini *.txt ../tgtg-backup/
git checkout -- config.ini users_login_data.txt users_settings_data.txt available_items_favorites.txt
git pull
cp ../tgtg-backup/* .
sh start.sh          # Windows: start.bat
```
</details>

## Troubleshooting

**"Blocked by TGTG's bot protection (captcha)"** – TGTG blocks IP addresses that look automated. The bot pauses,
retries on its own and tells you when it works again – usually within a few hours. A router restart (new IP) often
helps right away. If it keeps happening, set a residential `proxy`. Don't lower `poll_interval` and don't run other
TGTG tools from the same IP.

**"Your session has expired"** – send your email address again to log in.

**No notification although bags are available** – the bot reports *changes*. Bags that were already there when you
logged in are listed in the login message and under `/info`. Check that *✅ New bags* is 🟢 in `/settings`.

**No PIN email** – check your spam folder and use the newest email. *🔁 Send a new PIN* requests another one.

**"Could not obtain a DataDome cookie" in the log** – harmless; DNS filters like Pi-hole or AdGuard block that
address and the bot works without it.

**HTTP 409 in the log** – the same token is used by a second running bot. Stop the other one.

## How it works

The bot checks the favorites of every user with notifications enabled about once a minute and compares the number of
available bags with the previous check. TGTG is accessed with the [`tgtg`](https://github.com/ahivert/tgtg-python)
library; [`tgtg_bot/client.py`](tgtg_bot/client.py) adds a current app fingerprint, consistent cookie handling,
proxy support and token refresh.

<details>
<summary>Project structure and development</summary>

```
tgtg_bot/
├── __main__.py    entry point (python -m tgtg_bot)
├── bot.py         Telegram commands, buttons and messages
├── service.py     login, fetching favorites, polling, back-off
├── client.py      TGTG API client (wraps the tgtg library)
├── storage.py     users.json, stock.json, messages.json
├── formatting.py  message layout
├── i18n.py        texts in English and German
└── config.py      config.ini + environment variables
```

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && pytest
```
</details>

## Disclaimer

Not affiliated with Too Good To Go. The bot uses an unofficial API that can change at any time. Use it for your own
account(s) and keep the polling interval reasonable.

## Credits

[Too Good To Go](https://www.toogoodtogo.com/) – 🌍 let's fight food waste together ·
[tgtg-python](https://github.com/ahivert/tgtg-python) by @ahivert ·
[pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) · all contributors ([changelog](CHANGELOG.md))

## License

[GPL-3.0](LICENSE)
