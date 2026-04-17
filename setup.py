#!/usr/bin/env python3
"""Setup and launch script for the TGTG Telegram Bot."""

import os
import sys
import shutil
import subprocess


def main():
    print("🍽  Too Good To Go – Telegram Bot Setup\n")

    # Step 1: Check Python version
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ is required (you have {sys.version})")
        sys.exit(1)

    # Step 2: Create config.ini from template if missing
    if not os.path.exists("config.ini"):
        if os.path.exists("config.ini.example"):
            shutil.copy("config.ini.example", "config.ini")
            print("📄 Created config.ini from config.ini.example")
        else:
            print("❌ config.ini.example not found!")
            sys.exit(1)

    # Step 3: Check if token is set
    with open("config.ini", "r") as f:
        content = f.read()

    if "<YOUR_TOKEN>" in content:
        token = input("🔑 Enter your Telegram bot token: ").strip()
        if not token:
            print("❌ No token provided. Exiting.")
            sys.exit(1)
        content = content.replace("<YOUR_TOKEN>", token)
        with open("config.ini", "w") as f:
            f.write(content)
        print("✅ Token saved to config.ini")
    else:
        print("✅ config.ini already configured")

    # Step 4: Install dependencies
    print("\n📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])
    print("✅ Dependencies installed")

    # Step 5: Start the bot
    print("\n🚀 Starting bot...\n")
    subprocess.call([sys.executable, "Telegram.py"])


if __name__ == "__main__":
    main()

