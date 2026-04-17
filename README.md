# Too Good To Go – Telegram Bot 🍽

A Telegram bot that monitors your [Too Good To Go](https://www.toogoodtogo.com/) favorites and notifies you when stock changes occur (new bags, sold out, etc.).

## Features

- 🔑 **Login** – Authenticate with your TGTG account via email + PIN
- ℹ️ **Info** – Show currently available bags from your favorites
- ⚙️ **Settings** – Choose which notifications you want (new stock, sold out, stock reduced, stock increased)
- 🚀 **Smart Polling** – The TGTG API is **only queried when at least one user has notifications enabled**, preventing unnecessary requests and 403 bans

## Getting Started

1. Clone this repository
2. Create a Telegram bot and obtain a token ([guide](https://core.telegram.org/bots/tutorial#getting-ready))
3. Run the setup script – it will guide you through everything:

```bash
python setup.py
```

<details>
<summary>Manual setup (alternative)</summary>

1. Copy `config.ini.example` to `config.ini` and replace `<YOUR_TOKEN>` with your bot token
2. Install dependencies and start the bot:

```bash
pip install -r requirements.txt
python Telegram.py
```

</details>

### Requirements

- Python 3.10+
- A Telegram bot token

### Configuration

The `config.ini` file supports the following options:

```ini
[Telegram]
token = <YOUR_TOKEN>

[TGTG]
; Optional – only needed if your IP is blocked by TGTG
proxy =
```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` / `/help` | Show welcome message |
| `/login email@example.com` | Start login – sends a PIN to your email |
| `/pin 12345` | Complete login with the PIN from your email |
| `/info` | Show currently available favorite bags |
| `/settings` | Configure notification preferences |

### Login Flow

1. Send `/login your@email.com` to the bot
2. Check your email for a **PIN code** from Too Good To Go
3. Send `/pin 12345` (with your actual PIN) to complete the login
4. Done! The bot will now monitor your favorites.

## How It Works

The bot runs a background polling loop that checks the TGTG API every 60 seconds. **Crucially, it first checks whether any user has at least one notification type enabled.** If all users have disabled all notifications, the API is not queried at all — this minimizes the risk of being rate-limited or banned (HTTP 403) by TGTG.

### TGTG Library

This project includes a **bundled version** of [tgtg-python](https://github.com/ahivert/tgtg-python) in the `tgtg/` directory with patches for Datadome bypass and PIN-based authentication ([PR #378](https://github.com/ahivert/tgtg-python/pull/378)).

## Credits

- [@TGTG](https://www.toogoodtogo.com/)
- [@ahivert](https://github.com/ahivert/tgtg-python) – Python client for the TGTG API
- [@jalaliamirreza](https://github.com/ahivert/tgtg-python/pull/378) – Datadome bypass & PIN auth patch

## License

See [LICENSE](LICENSE) for details.
