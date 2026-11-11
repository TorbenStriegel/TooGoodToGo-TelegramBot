import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _no_play_store(monkeypatch):
    """Never scrape Google Play in tests."""
    import tgtg_bot.client as client

    monkeypatch.setattr(client, "_APK_VERSION", "26.11.1")
