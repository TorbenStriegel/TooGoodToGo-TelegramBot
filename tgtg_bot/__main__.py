"""Entry point: ``python -m tgtg_bot``."""

from __future__ import annotations

import logging
import os
import signal
import sys

from . import __version__


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Never log full request URLs/headers of the HTTP libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("TeleBot").setLevel(logging.WARNING)

    from .bot import TelegramBot
    from .config import ConfigError, load_config
    from .storage import Storage

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    logging.getLogger("tgtg_bot").info("TGTG Telegram bot v%s", __version__)
    storage = Storage(config.data_dir)

    def _terminate(signum, frame):  # docker stop / systemctl stop → clean shutdown
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _terminate)
    try:
        TelegramBot(config, storage).run()
    except KeyboardInterrupt:
        logging.getLogger("tgtg_bot").info("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
