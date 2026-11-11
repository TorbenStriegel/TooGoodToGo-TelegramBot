#!/usr/bin/env python3
"""First-time setup: creates config.ini, installs dependencies and starts the bot.

Usage:  python quickstart.py
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


def main() -> int:
    print("🍽  Too Good To Go – Telegram Bot setup\n")

    if sys.version_info < (3, 11):  # noqa: UP036 – friendly message for old Pythons
        print(f"❌ Python 3.11 or newer is required (you have {sys.version.split()[0]}).")
        return 1

    config = ROOT / "config.ini"
    if not config.exists():
        shutil.copy(ROOT / "config.ini.example", config)
        print("📄 Created config.ini")

    content = config.read_text(encoding="utf-8")
    if "<YOUR_TOKEN>" in content:
        print("You need a bot token from @BotFather (https://t.me/BotFather → /newbot).")
        token = input("🔑 Telegram bot token: ").strip()
        if not TOKEN_RE.match(token):
            print("❌ That does not look like a bot token (format 123456789:ABC...).")
            return 1
        config.write_text(content.replace("<YOUR_TOKEN>", token, 1), encoding="utf-8")
        print("✅ Token saved to config.ini")
    else:
        print("✅ config.ini already contains a token")

    print("\n📦 Installing dependencies…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])
    print("✅ Dependencies installed")

    print("\n🚀 Starting the bot – open it in Telegram and send /start (stop with Ctrl+C)\n")
    return subprocess.call([sys.executable, "-m", "tgtg_bot"], cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
