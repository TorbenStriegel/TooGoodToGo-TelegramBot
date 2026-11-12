#!/usr/bin/env sh
# Start the Too Good To Go Telegram bot (Linux / macOS / Raspberry Pi).
# First run: asks for the bot token and installs everything into .venv.
cd "$(dirname "$0")" || exit 1

CANDIDATES="python3.14 python3.13 python3.12 python3.11 python3 python"
OK_VERSION='import sys; sys.exit(sys.version_info < (3, 11))'
OK_VENV='import sys, ensurepip; sys.exit(sys.version_info < (3, 11))'

# Prefer a Python that can create virtual environments, else take any 3.11+
# (quickstart.py then explains what is missing).
for check in "$OK_VENV" "$OK_VERSION"; do
  for candidate in $CANDIDATES; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$check" 2>/dev/null; then
      exec "$candidate" quickstart.py "$@"
    fi
  done
done

echo "Python 3.11 or newer is required but was not found."
echo "  Debian/Ubuntu/Raspberry Pi OS: sudo apt install python3 python3-venv"
echo "  macOS:                         brew install python"
echo "Or use Docker – see README.md."
exit 1
