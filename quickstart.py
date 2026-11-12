#!/usr/bin/env python3
"""Set up and start the bot – safe to run every time.

1. asks for the Telegram bot token (first run only) and writes config.ini
2. creates a private Python environment in .venv and installs the requirements
   (again only when requirements.txt changed)
3. starts the bot

Usage:  python quickstart.py        (or start.sh / start.bat)
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
CONFIG = ROOT / "config.ini"
REQUIREMENTS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"
TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{30,}$")


def fail(message: str) -> int:
    print(f"\n❌ {message}")
    return 1


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_token() -> None:
    if not CONFIG.exists():
        shutil.copy(ROOT / "config.ini.example", CONFIG)
    content = CONFIG.read_text(encoding="utf-8")
    if "<YOUR_TOKEN>" not in content:
        return
    print("You need a bot token from Telegram:")
    print("  1. open https://t.me/BotFather and send /newbot")
    print("  2. choose a name and a username ending in 'bot'")
    print("  3. copy the token (looks like 123456789:ABC-DEF...)\n")
    while True:
        token = input("🔑 Paste your bot token: ").strip()
        if TOKEN_RE.match(token):
            break
        print("   That doesn't look like a bot token – please try again.")
    CONFIG.write_text(content.replace("<YOUR_TOKEN>", token, 1), encoding="utf-8")
    print("✅ Token saved in config.ini\n")


def pip_works() -> bool:
    return (
        venv_python().exists()
        and subprocess.call(
            [str(venv_python()), "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        == 0
    )


def ensure_environment() -> bool:
    if not pip_works():
        print("📦 Creating a Python environment in .venv (first run only) …")
        try:
            venv.EnvBuilder(with_pip=True, clear=True).create(VENV)
        except (Exception, SystemExit):  # noqa: BLE001 – Debian's venv exits if python3-venv is missing
            pass
        if not pip_works():
            shutil.rmtree(VENV, ignore_errors=True)
            print("   Python's 'venv' module is missing.")
            print("   Debian/Ubuntu/Raspberry Pi OS:  sudo apt install python3-venv   – then start again.")
            return False
    wanted = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    if STAMP.exists() and STAMP.read_text().strip() == wanted:
        return True
    print("📦 Installing dependencies …")
    cmd = [str(venv_python()), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r", str(REQUIREMENTS)]
    if subprocess.call(cmd) != 0:
        return False
    STAMP.write_text(wanted)
    print("✅ Dependencies installed\n")
    return True


def main() -> int:
    getattr(sys.stdout, "reconfigure", lambda **_: None)(line_buffering=True)  # show progress immediately
    print("🍽  Too Good To Go – Telegram Bot\n")
    if sys.version_info < (3, 11):  # noqa: UP036 – friendly message for old Pythons
        return fail(f"Python 3.11 or newer is required (you have {sys.version.split()[0]}). See README.")
    try:
        ensure_token()
    except (KeyboardInterrupt, EOFError):
        return fail("Cancelled.")
    if not ensure_environment():
        return fail("Could not set up the Python environment (see message above).")
    print("🚀 Starting the bot – open it in Telegram and tap Start. Stop with Ctrl+C.\n")
    try:
        return subprocess.call([str(venv_python()), "-m", "tgtg_bot"], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
