import json

import pytest
from tgtg.exceptions import TgtgAPIError, TgtgLoginError

from tgtg_bot.config import Config
from tgtg_bot.service import SessionExpiredError, TgtgService
from tgtg_bot.storage import Storage

CAPTCHA = json.dumps({"url": "https://geo.captcha-delivery.com/x"}).encode()


def item(iid, count):
    return {"item": {"item_id": iid}, "items_available": count, "store": {"store_name": f"Store {iid}"}}


class FakeClient:
    """Stands in for BotTgtgClient; behaviour is scripted per test."""

    script: list = []
    refresh_error = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.access_token = kwargs.get("access_token")
        self.refresh_token = kwargs.get("refresh_token")
        self.forced = 0

    def login(self):
        if FakeClient.refresh_error:
            raise FakeClient.refresh_error

    def force_token_refresh(self):
        self.forced += 1
        self.access_token = "new-access"
        self.login()

    def get_items(self, **kwargs):
        step = FakeClient.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def credentials(self):
        return {"access_token": self.access_token, "refresh_token": self.refresh_token, "cookie": "", "device": 0}


@pytest.fixture
def env(tmp_path):
    FakeClient.script = []
    FakeClient.refresh_error = None
    storage = Storage(tmp_path, legacy_dir=None)
    storage.set_credentials("1", {"access_token": "a", "refresh_token": "r"}, email="a@b.de")
    sent = []
    service = TgtgService(Config(telegram_token="t"), storage, lambda c, k, p: sent.append((c, k, p)), FakeClient)
    return service, storage, sent


def statuses(sent):
    return [(p[0]["item"]["item_id"], p[1]) for _, kind, p in sent if kind == "item"]


def test_first_poll_is_baseline_then_changes_are_notified(env):
    service, storage, sent = env
    for k in ("sold_out", "stock_reduced", "stock_increased"):
        storage.set_setting("1", k, True)
    FakeClient.script = [
        [item("a", 0), item("b", 2)],
        [item("a", 3), item("b", 0)],
        [item("a", 1), item("b", 0), item("c", 5)],
        [item("a", 4), item("c", 5)],
    ]
    for _ in range(4):
        service.poll_once()
    assert statuses(sent) == [
        ("a", "new_stock"),
        ("b", "sold_out"),
        ("a", "stock_reduced"),
        ("c", "new_stock"),  # newly added favorite with bags
        ("a", "stock_increased"),
    ]
    assert storage.last_stock("1") == {"a": 4, "c": 5}


def test_only_enabled_notifications_are_sent(env):
    service, storage, sent = env  # default: only new_stock
    FakeClient.script = [[item("a", 2)], [item("a", 0)], [item("a", 1)]]
    for _ in range(3):
        service.poll_once()
    assert statuses(sent) == [("a", "new_stock")]


def test_users_without_notifications_are_not_polled(env):
    service, storage, sent = env
    storage.set_setting("1", "new_stock", False)
    FakeClient.script = []  # would raise IndexError if called
    service.poll_once()
    assert sent == []


def test_pages_are_fetched_until_short_page(env, monkeypatch):
    import tgtg_bot.service as svc

    monkeypatch.setattr(svc, "PAGE_SIZE", 2)
    service, storage, sent = env
    FakeClient.script = [[item("a", 0), item("b", 0)], [item("c", 0)]]
    assert len(service.fetch_favorites("1")) == 3


def test_expired_access_token_is_refreshed_once(env):
    service, storage, sent = env
    FakeClient.script = [TgtgAPIError(401, b"unauthorized"), [item("a", 1)]]
    assert service.fetch_favorites("1") == [item("a", 1)]
    assert storage.credentials("1")["access_token"] == "new-access"


def test_invalid_refresh_token_requires_new_login(env):
    service, storage, sent = env
    FakeClient.refresh_error = TgtgAPIError(401, b"invalid refresh token")
    service.poll_once()
    assert not storage.is_logged_in("1")
    assert any("expired" in p for _, kind, p in sent if kind == "text")
    with pytest.raises(SessionExpiredError):
        service.fetch_favorites("1")


def test_server_error_does_not_log_out(env):
    service, storage, sent = env
    FakeClient.script = [TgtgAPIError(500, b"oops")]
    service.poll_once()
    assert storage.is_logged_in("1") and sent == []


def test_captcha_block_backs_off_and_reports_recovery(env, monkeypatch):
    import tgtg_bot.service as svc

    service, storage, sent = env
    now = [1000.0]
    monkeypatch.setattr(svc.time, "time", lambda: now[0])
    FakeClient.script = [TgtgAPIError(403, CAPTCHA)]
    service.poll_once()
    assert service.is_blocked("1")
    texts = [p for _, kind, p in sent if kind == "text"]
    assert texts == ["blocked_notice"]
    service.poll_once()  # still in back-off: no API call (script is empty)
    now[0] += svc.BLOCK_BACKOFF_START + 1
    FakeClient.script = [TgtgAPIError(403, CAPTCHA)]
    service.poll_once()  # blocked again: no second message, longer delay
    assert len([1 for _, k, _ in sent if k == "text"]) == 1
    assert service._block_delay["1"] == 2 * svc.BLOCK_BACKOFF_START
    now[0] += 2 * svc.BLOCK_BACKOFF_START + 1
    FakeClient.script = [[item("a", 1)]]
    service.poll_once()
    assert not service.is_blocked("1")
    assert [p for _, k, p in sent if k == "text"][-1] == "restored"


class LoginClient(FakeClient):
    def start_login(self):
        if self.kwargs["email"] == "blocked@x.de":
            raise TgtgLoginError(403, CAPTCHA)
        return "poll"

    def finish_login(self, polling_id, pin):
        if pin != "123456":
            raise TgtgLoginError(400, b"wrong pin")
        self.access_token, self.refresh_token = "A", "R"


def test_login_flow(tmp_path):
    from tgtg_bot.service import LoginError

    storage = Storage(tmp_path, legacy_dir=None)
    service = TgtgService(Config(telegram_token="t"), storage, lambda *a: None, LoginClient)
    with pytest.raises(LoginError, match="login_blocked"):
        service.start_login("9", "blocked@x.de")
    with pytest.raises(LoginError, match="no_login_in_progress"):
        service.finish_login("9", "123456")
    service.start_login("9", "me@x.de")
    assert service.has_pending_login("9")
    with pytest.raises(LoginError, match="pin_wrong"):
        service.finish_login("9", "000000")
    service.finish_login("9", "123456")
    assert storage.credentials("9")["refresh_token"] == "R"
    assert storage.email("9") == "me@x.de"
    assert not service.has_pending_login("9")
    service.logout("9")
    assert not storage.is_logged_in("9")


def test_403_unauthorized_on_items_triggers_token_refresh(env):
    service, storage, sent = env
    FakeClient.script = [TgtgAPIError(403, b'{"errors":[{"code":"UNAUTHORIZED"}]}'), [item("a", 1)]]
    assert service.fetch_favorites("1") == [item("a", 1)]
    assert not service.is_blocked("1")


def test_network_errors_are_quiet_until_a_longer_outage(env, monkeypatch):
    import requests

    import tgtg_bot.service as svc

    service, storage, sent = env
    now = [1000.0]
    monkeypatch.setattr(svc.time, "time", lambda: now[0])
    FakeClient.script = [requests.exceptions.ProxyError("proxy down")]
    service.poll_once()
    assert service.is_offline("1") and sent == []
    now[0] += svc.OFFLINE_NOTIFY_AFTER
    FakeClient.script = [requests.exceptions.ConnectTimeout("timeout"), requests.exceptions.ConnectionError("x")]
    service.poll_once()
    service.poll_once()
    assert [p for _, k, p in sent if k == "text"] == ["offline_notice"]  # exactly once
    FakeClient.script = [[item("a", 0)]]
    service.poll_once()
    assert not service.is_offline("1")
    assert [p for _, k, p in sent if k == "text"] == ["offline_notice", "restored"]


def test_short_outage_recovers_silently(env):
    import requests

    service, storage, sent = env
    FakeClient.script = [requests.exceptions.ConnectionError("x"), [item("a", 0)]]
    service.poll_once()
    service.poll_once()
    assert sent == [] and not service.is_offline("1")
