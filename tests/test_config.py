import pytest

from tgtg_bot.config import ConfigError, load_config

ENV = ["TELEGRAM_TOKEN", "ALLOWED_USERS", "POLL_INTERVAL", "TIMEZONE", "DATA_DIR", "TGTG_PROXY", "TGTG_BOT_CONFIG"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ENV:
        monkeypatch.delenv(key, raising=False)


def test_placeholder_token_is_rejected(tmp_path):
    cfg = tmp_path / "config.ini"
    cfg.write_text("[Telegram]\ntoken = <YOUR_TOKEN>\n")
    with pytest.raises(ConfigError):
        load_config(cfg)


def test_ini_values(tmp_path):
    cfg = tmp_path / "config.ini"
    cfg.write_text(
        "[Telegram]\ntoken = 1:abc\nallowed_users = 1, 2;3\n[TGTG]\npoll_interval = 90\nproxy = http://p:1\n[Bot]\ntimezone = Europe/London\n"
    )
    c = load_config(cfg)
    assert c.telegram_token == "1:abc"
    assert c.allowed_users == {"1", "2", "3"}
    assert c.poll_interval == 90 and c.proxy == "http://p:1"
    assert str(c.timezone) == "Europe/London"
    assert c.base_url == "https://api.toogoodtogo.com/api/" and c.item_endpoint == "item/v9/"


def test_env_overrides_and_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "2:env")
    monkeypatch.setenv("POLL_INTERVAL", "120")
    c = load_config(tmp_path / "missing.ini")
    assert c.telegram_token == "2:env" and c.poll_interval == 120 and c.proxy is None
    monkeypatch.setenv("POLL_INTERVAL", "10")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.ini")
    monkeypatch.setenv("POLL_INTERVAL", "60")
    monkeypatch.setenv("TIMEZONE", "Mars/Olympus")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.ini")
