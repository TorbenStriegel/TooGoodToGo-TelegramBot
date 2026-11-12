"""User-facing texts in English and German.

The language is picked from the Telegram app language of the user
(``language_code`` starting with ``de`` → German, everything else → English).
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"
LANGUAGES = ("en", "de")

TEXTS: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- general
    "welcome": {
        "en": "<b>🍽 Welcome to the Too Good To Go bot!</b>\n\n"
        "I watch your TGTG <b>favorites</b> and message you as soon as Surprise Bags become available – "
        "often faster than the app.\n\n"
        "<b>Let's start:</b> send me the <b>email address</b> of your Too Good To Go account.\n"
        "<i>You'll get a PIN by email – no password needed.</i>",
        "de": "<b>🍽 Willkommen beim Too-Good-To-Go-Bot!</b>\n\n"
        "Ich beobachte deine TGTG-<b>Favoriten</b> und schreibe dir, sobald Überraschungstüten verfügbar sind – "
        "oft schneller als die App.\n\n"
        "<b>Los geht's:</b> Schick mir die <b>E-Mail-Adresse</b> deines Too-Good-To-Go-Kontos.\n"
        "<i>Du bekommst dann eine PIN per E-Mail – kein Passwort nötig.</i>",
    },
    "help": {
        "en": "<b>🍽 Too Good To Go – Telegram Bot</b>\n\n"
        "I watch your TGTG <b>favorites</b> (❤️ in the app) and notify you when bags become available.\n\n"
        "<b>Commands</b>\n"
        "/info – what's available right now\n"
        "/settings – when you want to be notified\n"
        "/status – login and connection status\n"
        "/login – log in (or just send your email address)\n"
        "/logout – log out and delete your data\n\n"
        "<i>🌍 Let's fight food waste together!</i>",
        "de": "<b>🍽 Too Good To Go – Telegram-Bot</b>\n\n"
        "Ich beobachte deine TGTG-<b>Favoriten</b> (❤️ in der App) und melde mich, sobald es Tüten gibt.\n\n"
        "<b>Befehle</b>\n"
        "/info – was gibt es gerade?\n"
        "/settings – wann möchtest du benachrichtigt werden?\n"
        "/status – Login- und Verbindungsstatus\n"
        "/login – anmelden (oder einfach deine E-Mail-Adresse schicken)\n"
        "/logout – abmelden und Daten löschen\n\n"
        "<i>🌍 Gemeinsam gegen Lebensmittelverschwendung!</i>",
    },
    "private": {
        "en": "⛔ This bot is private.\nYour chat ID: <code>{id}</code>",
        "de": "⛔ Dieser Bot ist privat.\nDeine Chat-ID: <code>{id}</code>",
    },
    "not_allowed": {"en": "⛔ Not allowed", "de": "⛔ Nicht erlaubt"},
    "unknown": {
        "en": "🤔 I didn't get that. What do you want to do?",
        "de": "🤔 Das habe ich nicht verstanden. Was möchtest du tun?",
    },
    "need_email": {
        "en": "📧 To get started, send me the email address of your Too Good To Go account.",
        "de": "📧 Schick mir zum Start die E-Mail-Adresse deines Too-Good-To-Go-Kontos.",
    },
    "need_login": {
        "en": "🔑 Please log in first – just send me the email address of your TGTG account.",
        "de": "🔑 Bitte melde dich zuerst an – schick mir einfach die E-Mail-Adresse deines TGTG-Kontos.",
    },
    "btn_info": {"en": "🔍 Available now", "de": "🔍 Jetzt verfügbar"},
    "btn_settings": {"en": "⚙️ Notifications", "de": "⚙️ Benachrichtigungen"},
    "btn_status": {"en": "ℹ️ Status", "de": "ℹ️ Status"},
    "btn_open_app": {"en": "📱 Open in app", "de": "📱 In der App öffnen"},
    "btn_route": {"en": "📍 Route", "de": "📍 Route"},
    # ------------------------------------------------------------------ login
    "already_logged_in": {
        "en": "👍 You are already logged in. Use /logout first to switch accounts.",
        "de": "👍 Du bist schon angemeldet. Mit /logout kannst du das Konto wechseln.",
    },
    "ask_email": {
        "en": "📧 Send me the email address of your Too Good To Go account.",
        "de": "📧 Schick mir die E-Mail-Adresse deines Too-Good-To-Go-Kontos.",
    },
    "invalid_email": {
        "en": "⚠️ That doesn't look like an email address. Please try again.",
        "de": "⚠️ Das sieht nicht wie eine E-Mail-Adresse aus. Bitte versuch es nochmal.",
    },
    "pin_sent": {
        "en": "📩 I asked Too Good To Go to email a <b>PIN</b> to <b>{email}</b>.\n\n"
        "👉 Just send me the number from that email.\n"
        "<i>Don't click the link in the email – and check your spam folder if nothing arrives.</i>",
        "de": "📩 Too Good To Go schickt dir jetzt eine <b>PIN</b> an <b>{email}</b>.\n\n"
        "👉 Schick mir einfach die Zahl aus dieser E-Mail.\n"
        "<i>Bitte nicht auf den Link in der Mail klicken – und schau im Spam-Ordner nach, "
        "falls nichts ankommt.</i>",
    },
    "btn_new_pin": {"en": "🔁 Send a new PIN", "de": "🔁 Neue PIN anfordern"},
    "requesting_pin": {"en": "Requesting a new PIN …", "de": "Neue PIN wird angefordert …"},
    "send_email_again": {
        "en": "Please send your email address again",
        "de": "Bitte schick deine E-Mail-Adresse nochmal",
    },
    "need_pin": {
        "en": "🔢 Please send the PIN from the Too Good To Go email (just the number).",
        "de": "🔢 Bitte schick mir die PIN aus der Too-Good-To-Go-E-Mail (nur die Zahl).",
    },
    "no_login_in_progress": {
        "en": "⚠️ No login in progress – send me your email address first.",
        "de": "⚠️ Gerade läuft keine Anmeldung – schick mir zuerst deine E-Mail-Adresse.",
    },
    "already_logged_in_short": {"en": "👍 You are already logged in.", "de": "👍 Du bist schon angemeldet."},
    "login_unknown_email": {
        "en": "❌ This email is not linked to a Too Good To Go account.\n"
        "Please sign up in the Too Good To Go app first.",
        "de": "❌ Zu dieser E-Mail gibt es kein Too-Good-To-Go-Konto.\nBitte registriere dich zuerst in der App.",
    },
    "login_blocked": {
        "en": "🔒 Login was blocked by TGTG's bot protection (captcha).\n\n"
        "This depends on the IP address of the server the bot runs on. "
        "Wait a few hours and try again, or configure a (residential) proxy.",
        "de": "🔒 Die Anmeldung wurde vom Bot-Schutz von TGTG blockiert (Captcha).\n\n"
        "Das hängt von der IP-Adresse des Servers ab, auf dem der Bot läuft. "
        "Versuch es in ein paar Stunden nochmal oder richte einen Proxy ein.",
    },
    "login_rate_limited": {
        "en": "⏳ Too many login attempts. Please wait a while and try again.",
        "de": "⏳ Zu viele Anmeldeversuche. Bitte warte etwas und versuch es dann nochmal.",
    },
    "login_failed": {
        "en": "❌ Login failed (HTTP {status}). Please try again later.",
        "de": "❌ Anmeldung fehlgeschlagen (HTTP {status}). Bitte versuch es später nochmal.",
    },
    "login_unreachable": {
        "en": "❌ Could not reach Too Good To Go. Please try again later.",
        "de": "❌ Too Good To Go ist gerade nicht erreichbar. Bitte versuch es später nochmal.",
    },
    "pin_wrong": {
        "en": "❌ That PIN didn't work. Check the newest email from Too Good To Go and send the number again.",
        "de": "❌ Die PIN hat nicht funktioniert. Schau in die neueste Mail von Too Good To Go "
        "und schick mir die Zahl nochmal.",
    },
    "pin_blocked": {
        "en": "🔒 Blocked by TGTG's bot protection. Please try again later.",
        "de": "🔒 Vom Bot-Schutz von TGTG blockiert. Bitte versuch es später nochmal.",
    },
    "logged_in": {"en": "✅ <b>You're logged in!</b>", "de": "✅ <b>Du bist angemeldet!</b>"},
    "logged_in_generic": {
        "en": "I'll notify you as soon as bags from your favorites become available.",
        "de": "Ich melde mich, sobald es bei deinen Favoriten Tüten gibt.",
    },
    "logged_in_no_favorites": {
        "en": "You don't have any favorites yet. Tap ❤️ on stores in the Too Good To Go app – "
        "I'll pick them up automatically.",
        "de": "Du hast noch keine Favoriten. Tippe in der Too-Good-To-Go-App bei Läden auf ❤️ – "
        "ich übernehme sie automatisch.",
    },
    "logged_in_watching": {
        "en": "I'm now watching your <b>{count}</b> favorite(s):\n\n{overview}\n\n"
        "🔔 You'll get a message as soon as <b>new bags</b> are available. "
        "Want more (e.g. sold out)? → Notifications",
        "de": "Ich beobachte jetzt deine <b>{count}</b> Favoriten:\n\n{overview}\n\n"
        "🔔 Du bekommst eine Nachricht, sobald es <b>neue Tüten</b> gibt. "
        "Mehr Benachrichtigungen (z. B. ausverkauft)? → Benachrichtigungen",
    },
    # ------------------------------------------------------------------ info
    "blocked_now": {
        "en": "🚫 Too Good To Go is blocking requests right now (captcha). Please try again later.",
        "de": "🚫 Too Good To Go blockiert gerade Anfragen (Captcha). Bitte versuch es später nochmal.",
    },
    "session_expired": {
        "en": "🔑 Your Too Good To Go session has expired. Send me your email address to log in again.",
        "de": "🔑 Deine Too-Good-To-Go-Sitzung ist abgelaufen. Schick mir deine E-Mail-Adresse, "
        "um dich neu anzumelden.",
    },
    "fetch_failed": {
        "en": "❌ Could not load your favorites. Please try again later.",
        "de": "❌ Deine Favoriten konnten nicht geladen werden. Bitte versuch es später nochmal.",
    },
    "no_favorites": {
        "en": "You have no favorites yet. Tap ❤️ on stores in the Too Good To Go app.",
        "de": "Du hast noch keine Favoriten. Tippe in der Too-Good-To-Go-App bei Läden auf ❤️.",
    },
    "nothing_available": {
        "en": "😕 <b>Nothing available right now</b>\n\n{overview}",
        "de": "😕 <b>Gerade ist nichts verfügbar</b>\n\n{overview}",
    },
    "will_notify": {
        "en": "🔔 I'll message you as soon as something becomes available.",
        "de": "🔔 Ich schreibe dir, sobald etwas verfügbar ist.",
    },
    "notify_off": {
        "en": "🔕 Notifications for new bags are off – see /settings.",
        "de": "🔕 Benachrichtigungen für neue Tüten sind aus – siehe /settings.",
    },
    "others_empty": {
        "en": "<i>{count} other favorite(s) have nothing at the moment.</i>",
        "de": "<i>{count} weitere Favoriten haben gerade nichts.</i>",
    },
    # -------------------------------------------------------------- settings
    "settings_title": {
        "en": "🔔 <b>Notify me when …</b>\n"
        "<i>Tap to switch on 🟢 / off 🔴. Only “New bags” makes a sound, the rest arrives silently. "
        "A “New bags” message is updated automatically while the bags sell.</i>",
        "de": "🔔 <b>Benachrichtige mich, wenn …</b>\n"
        "<i>Tippen zum Ein- 🟢 / Ausschalten 🔴. Nur „Neue Tüten“ macht einen Ton, der Rest kommt lautlos. "
        "Eine „Neue Tüten“-Nachricht wird automatisch aktualisiert, solange verkauft wird.</i>",
    },
    "setting_new_stock": {"en": "✅ New bags", "de": "✅ Neue Tüten"},
    "setting_sold_out": {"en": "❌ Sold out", "de": "❌ Ausverkauft"},
    "setting_stock_reduced": {"en": "📉 Fewer bags", "de": "📉 Weniger Tüten"},
    "setting_stock_increased": {"en": "📈 More bags", "de": "📈 Mehr Tüten"},
    "all_on": {"en": "🟢 All on", "de": "🟢 Alle an"},
    "all_off": {"en": "🔴 All off", "de": "🔴 Alle aus"},
    "on": {"en": "on", "de": "an"},
    "off": {"en": "off", "de": "aus"},
    "all_toggled": {"en": "All notifications {state}", "de": "Alle Benachrichtigungen {state}"},
    # ------------------------------------------------------- mute / quiet
    "btn_mute": {"en": "🔕 Mute this store", "de": "🔕 Laden stummschalten"},
    "btn_unmute": {"en": "🔔 Notify me again", "de": "🔔 Wieder benachrichtigen"},
    "muted_toast": {
        "en": "🔕 {name}: no more notifications",
        "de": "🔕 {name}: keine Benachrichtigungen mehr",
    },
    "unmuted_toast": {"en": "🔔 {name}: notifications on again", "de": "🔔 {name}: Benachrichtigungen wieder an"},
    "btn_muted_list": {"en": "🔕 Muted stores ({count})", "de": "🔕 Stummgeschaltete Läden ({count})"},
    "muted_title": {
        "en": "🔕 <b>Muted stores</b>\n<i>Tap a store to get notifications for it again.</i>",
        "de": "🔕 <b>Stummgeschaltete Läden</b>\n<i>Tippe auf einen Laden, um wieder benachrichtigt zu werden.</i>",
    },
    "muted_empty": {"en": "No muted stores.", "de": "Keine stummgeschalteten Läden."},
    "setting_quiet": {"en": "🌙 Silent at night (22–7)", "de": "🌙 Nachts lautlos (22–7 Uhr)"},
    "status_muted": {"en": "🔕 {count} store(s) muted", "de": "🔕 {count} Laden/Läden stummgeschaltet"},
    "status_quiet": {"en": "🌙 Silent at night (22–7)", "de": "🌙 Nachts lautlos (22–7 Uhr)"},
    "updated": {"en": "🔄 Updated {time}", "de": "🔄 Aktualisiert {time}"},
    # ---------------------------------------------------------------- status
    "status_pending": {
        "en": "🟡 Login in progress – send me the PIN from the email.",
        "de": "🟡 Anmeldung läuft – schick mir die PIN aus der E-Mail.",
    },
    "status_logged_out": {
        "en": "🔴 Not logged in – send me the email address of your TGTG account.",
        "de": "🔴 Nicht angemeldet – schick mir die E-Mail-Adresse deines TGTG-Kontos.",
    },
    "your_id": {
        "en": "🆔 Your chat ID: <code>{id}</code> <i>(for allowed_users)</i>",
        "de": "🆔 Deine Chat-ID: <code>{id}</code> <i>(für allowed_users)</i>",
    },
    "status_logged_in": {"en": "🟢 Logged in as <b>{email}</b>", "de": "🟢 Angemeldet als <b>{email}</b>"},
    "status_watching": {"en": "❤️ Watching {count} favorite(s)", "de": "❤️ Beobachte {count} Favoriten"},
    "status_notifications": {"en": "🔔 Notifications: {list}", "de": "🔔 Benachrichtigungen: {list}"},
    "status_all_off": {"en": "all off – see /settings", "de": "alle aus – siehe /settings"},
    "status_blocked": {
        "en": "🚫 Blocked by TGTG right now – retrying automatically",
        "de": "🚫 Gerade von TGTG blockiert – neuer Versuch erfolgt automatisch",
    },
    "status_offline": {
        "en": "📡 TGTG not reachable right now – retrying automatically",
        "de": "📡 TGTG gerade nicht erreichbar – neuer Versuch erfolgt automatisch",
    },
    "status_ok": {"en": "✅ Connection to TGTG OK", "de": "✅ Verbindung zu TGTG OK"},
    "status_last_check": {
        "en": "🕒 Last successful check: {time} (every ~{interval}s)",
        "de": "🕒 Letzte erfolgreiche Prüfung: {time} (alle ~{interval}s)",
    },
    "status_never": {"en": "🕒 Last check: –", "de": "🕒 Letzte Prüfung: –"},
    # ---------------------------------------------------------------- logout
    "not_logged_in": {"en": "You are not logged in.", "de": "Du bist nicht angemeldet."},
    "logout_confirm": {
        "en": "Do you really want to log out? Your login and settings will be deleted from this bot.",
        "de": "Möchtest du dich wirklich abmelden? Deine Anmeldung und Einstellungen werden aus dem Bot gelöscht.",
    },
    "btn_logout_yes": {"en": "👋 Yes, log out", "de": "👋 Ja, abmelden"},
    "btn_cancel": {"en": "Cancel", "de": "Abbrechen"},
    "cancelled": {"en": "Cancelled", "de": "Abgebrochen"},
    "logged_out": {
        "en": "👋 Logged out – all your data was deleted. Send your email to log in again.",
        "de": "👋 Abgemeldet – alle deine Daten wurden gelöscht. Schick deine E-Mail, um dich neu anzumelden.",
    },
    # --------------------------------------------------- background messages
    "blocked_notice": {
        "en": "🚫 <b>Too Good To Go is currently blocking requests from the bot</b> (captcha).\n\n"
        "This is tied to the IP address of the server the bot runs on. "
        "The bot pauses automatically and retries with increasing delays – "
        "you will get a message once it works again.\n\n"
        "💡 If this persists for hours: restart the router (new IP) or set a proxy in config.ini.",
        "de": "🚫 <b>Too Good To Go blockiert gerade die Anfragen des Bots</b> (Captcha).\n\n"
        "Das hängt an der IP-Adresse des Servers, auf dem der Bot läuft. "
        "Der Bot pausiert automatisch und versucht es mit wachsenden Abständen erneut – "
        "du bekommst eine Nachricht, sobald es wieder klappt.\n\n"
        "💡 Hält das stundenlang an: Router neu starten (neue IP) oder einen Proxy in der config.ini eintragen.",
    },
    "offline_notice": {
        "en": "📡 <b>Too Good To Go has not been reachable for a while.</b>\n"
        "I keep trying and will let you know when it works again.",
        "de": "📡 <b>Too Good To Go ist seit einer Weile nicht erreichbar.</b>\n"
        "Ich versuche es weiter und melde mich, sobald es wieder klappt.",
    },
    "restored": {
        "en": "✅ Connection to Too Good To Go restored – notifications are active again.",
        "de": "✅ Verbindung zu Too Good To Go wiederhergestellt – Benachrichtigungen sind wieder aktiv.",
    },
    # ------------------------------------------------------------- formatting
    "status_new_stock": {"en": "✅ New bags available!", "de": "✅ Neue Tüten verfügbar!"},
    "status_sold_out": {"en": "❌ Sold out", "de": "❌ Ausverkauft"},
    "status_stock_reduced": {"en": "📉 Fewer bags left", "de": "📉 Weniger Tüten übrig"},
    "status_stock_increased": {"en": "📈 More bags available", "de": "📈 Mehr Tüten verfügbar"},
    "available": {"en": "available", "de": "verfügbar"},
    "none_left": {"en": "none left", "de": "keine mehr"},
    "pickup": {"en": "Pickup", "de": "Abholung"},
    "today": {"en": "Today", "de": "Heute"},
    "tomorrow": {"en": "Tomorrow", "de": "Morgen"},
    "weekdays": {"en": "Mon Tue Wed Thu Fri Sat Sun", "de": "Mo Di Mi Do Fr Sa So"},
    "and_more": {"en": "… and {count} more", "de": "… und {count} weitere"},
    "unknown_store": {"en": "Unknown store", "de": "Unbekannter Laden"},
}

COMMANDS = {
    "en": [
        ("info", "What's available right now"),
        ("settings", "When do you want to be notified?"),
        ("status", "Login and connection status"),
        ("login", "Log in with your TGTG email"),
        ("logout", "Log out and delete your data"),
        ("help", "Help"),
    ],
    "de": [
        ("info", "Was gibt es gerade?"),
        ("settings", "Wann möchtest du benachrichtigt werden?"),
        ("status", "Login- und Verbindungsstatus"),
        ("login", "Mit deiner TGTG-E-Mail anmelden"),
        ("logout", "Abmelden und Daten löschen"),
        ("help", "Hilfe"),
    ],
}


def language_for(code: str | None) -> str:
    """Map a Telegram ``language_code`` (e.g. ``de-AT``) to a supported language."""
    code = (code or "").lower()
    for lang in LANGUAGES:
        if code.startswith(lang):
            return lang
    return DEFAULT_LANGUAGE


def t(lang: str | None, key: str, **kwargs) -> str:
    entry = TEXTS[key]
    text = entry.get(lang or DEFAULT_LANGUAGE) or entry[DEFAULT_LANGUAGE]
    return text.format(**kwargs) if kwargs else text
