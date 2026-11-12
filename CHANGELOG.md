# Changelog

## 3.1.0 – 2026-11-12

Based on a night of real-world use. Live-tested against TGTG and Telegram.

### New
- **Live updates**: a *new bags* notification is edited in place while the bags sell (*3 → 1 available → ❌ Sold out*,
  with *Updated 08:15*) – no extra messages, no sound. Separate messages for sold out / fewer / more bags are still
  sent if you switched them on.
- **Mute single stores** with the 🔕 button under every notification (button turns into 🔔 to undo).
  `/settings` → *Muted stores* lists them for unmuting. Muted favorites are marked 🔕 in overviews.
- **Silent at night** (🌙 in `/settings`): notifications between 22:00 and 07:00 arrive without sound.

### Improved
- `/status` shows the last **successful** check for your account (instead of the last attempt) plus muted stores
  and night mode.
- Network problems are logged once per outage (plus one line when it works again) instead of every minute.
- The *DataDome SDK not reachable* warning (typical with Pi-hole/AdGuard) is logged only once and explained in
  the README – the bot works without it.
- Telegram long-polling timeouts are no longer logged as errors.

## 3.0.0 – 2026-11-11

Complete overhaul. Tested against the live TGTG API (login with PIN, favorites via `item/v9`, token refresh,
restart with stored credentials).

### Fixed
- **403 / captcha errors**: the bundled client sent the stored login cookie as a raw `Cookie` header, which made
  `requests` drop the session cookie jar – a fresh DataDome cookie was never sent, so a block could never recover.
  Cookies are now managed in one place and updated from every response.
- **Outdated fingerprint**: the old user agents (Android 9–12) are blocked by DataDome. The bot now uses the current
  app version with modern devices and sends a matching DataDome SDK fingerprint.
- **Logins lost after a restart**: TGTG rotates the refresh token on every refresh, but the new token was never
  saved. Refreshed tokens and cookies are now persisted.
- Captcha detection while polling never worked (a string was passed instead of the exception).
- One blocked user paused polling for everybody for 5 minutes and got a message every time; blocks are now handled
  per user with an increasing back-off (5 min → 1 h) and exactly one message, plus a message when it works again.
- A 403 *UNAUTHORIZED* answer (expired access token) was treated like a captcha; it now triggers a token refresh.
- `/info` and the background poller shared one client object across threads.
- Pickup times were shown in UTC; they are now shown in your time zone.
- Prices used a hard-coded € sign and ignored the currency's decimals.
- More than 20 favorites were ignored (pagination).
- The DataDome cookie is now fetched through the configured proxy as well.

### Changed
- Uses the official [`tgtg`](https://pypi.org/project/tgtg/) package from PyPI (≥ 0.19) instead of a bundled copy,
  with API host `api.toogoodtogo.com` and item endpoint `v9` (both configurable).
- Python **3.11+** required.
- Code moved into the `tgtg_bot` package; start with `python -m tgtg_bot` (`python Telegram.py` still works).
- Data is stored in `data/users.json` and `data/stock.json` (atomic writes). Data from 2.x is migrated automatically.
- `config.ini` and the data files are no longer tracked in git. `setup.py` was renamed to `quickstart.py`.
- Synchronous Telegram client – `aiohttp` is no longer needed.

### New
- Login without commands: send your email, then the PIN. A button requests a new PIN.
- After login the bot shows which favorites it is watching and records the current stock, so the next change is
  notified right away.
- Richer messages: bag type, rating, price vs. original value, "Today/Tomorrow" pickup window, address,
  **📍 Route** button. Only *new bags* make a sound; the other notifications arrive silently.
- `/info` lists favorites without bags along with the app's hint (e.g. *Nothing today*).
- `/status`, `/logout` (with confirmation), inline menu buttons and feedback when toggling settings.
- **German and English** texts, chosen automatically from the Telegram language (also used for TGTG's own
  hints such as *Heute kein Angebot*); bot command menu in both languages.
- Network problems (e.g. proxy/VPN down) are logged as one line instead of a traceback; users are told only after
  20 minutes without connection, and again when it works.
- `allowed_users` to make the bot private, configurable `poll_interval` (with jitter), `timezone`, `data_dir`.
- All options can be set via environment variables; `Dockerfile` and `docker-compose.yml` included.
- Clean shutdown on SIGTERM; clear log message if the same token is used by two instances.
- Test suite (pytest) and GitHub Actions CI.

## 2.0.2 – 2026-05-10
- Fix 403 on startup caused by a dropped Cookie header.

## 2.0.1 – 2026-05-07
- Security update for aiohttp, clearer captcha error messages.

## 2.0.0 – 2026-04-17
- PIN-based login, DataDome handling, polling only when notifications are enabled, bundled tgtg library.
