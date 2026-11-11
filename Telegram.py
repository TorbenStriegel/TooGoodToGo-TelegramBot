#!/usr/bin/env python3
"""Backwards-compatible entry point – the bot now lives in the ``tgtg_bot`` package.

Start it with ``python Telegram.py`` or ``python -m tgtg_bot``.
"""

import sys

from tgtg_bot.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
