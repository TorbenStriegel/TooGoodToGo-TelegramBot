# Changelog

## 3.1.0 – 2026-11-12

- **Live messages:** a *new bags* notification updates itself while the bags sell (count, sold out) instead of
  sending new messages.
- **Mute stores** with the 🔕 button under a notification; unmute them in `/settings`.
- **Silent nights** (optional): no notification sound from 22:00 to 07:00.
- **Easier setup:** `start.bat` (Windows) and `start.sh` (macOS/Linux) install everything and start the bot.
  Ready-made Docker image `ghcr.io/torbenstriegel/toogoodtogo-telegrambot` for amd64, arm64 and armv7.
- `/status` shows the last successful check and your chat ID (for `allowed_users`).
- Fewer log messages during network problems.
- Docker Compose uses a named volume – fixes missing write permissions for `./data`.

## 3.0.0 – 2026-11-11

Complete rewrite – works with the current TGTG API again.

- **Fixed:** 403/captcha errors caused by an outdated app fingerprint and broken cookie handling, and logins that
  were lost after a restart.
- Login by simply sending your email and the PIN; German and English texts.
- Richer notifications: price, rating, pickup time in your time zone, *Open in app* and *Route* buttons.
- New `/status` and `/logout`; automatic pause and recovery when TGTG blocks requests.
- `allowed_users`, configuration via environment variables, Docker support.
- **Requires Python 3.11+.** Data moved to `data/` – data from 2.x is migrated automatically (see README).

## 2.0.2 – 2026-05-10
- Fix 403 on startup caused by a dropped Cookie header.

## 2.0.1 – 2026-05-07
- Security update for aiohttp, clearer captcha error messages.

## 2.0.0 – 2026-04-17
- PIN-based login, DataDome handling, polling only when notifications are enabled, bundled tgtg library.
