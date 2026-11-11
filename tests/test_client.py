import json

import pytest
import responses
from tgtg.exceptions import TgtgAPIError, TgtgLoginError

from tgtg_bot.client import DATADOME_SDK_URL, BotTgtgClient, is_protection_block, is_unauthorized, parse_cookie_string

BASE = "https://api.toogoodtogo.com/api/"
CAPTCHA = json.dumps({"url": "https://geo.captcha-delivery.com/interstitial/?x=1"})


def sdk_ok(value="fresh"):
    responses.add(
        responses.POST,
        DATADOME_SDK_URL,
        json={"status": 200, "cookie": f"datadome={value}; Max-Age=31536000; Domain=.toogoodtogo.com; Path=/; Secure"},
    )


def logged_in_client(**kw):
    import datetime

    return BotTgtgClient(
        access_token="acc",
        refresh_token="ref",
        cookie="datadome=stored; Max-Age=31536000; Domain=.toogoodtogo.com; Path=/; Secure; SameSite=Lax",
        last_time_token_refreshed=datetime.datetime.now(),
        device_index=0,
        **kw,
    )


def test_parse_cookie_string_ignores_attributes():
    raw = "datadome=abc~1; Max-Age=31536000; Domain=.x.com; Path=/; Secure; SameSite=Lax, other=1; Expires=Wed, 21 Oct 2027 07:28:00 GMT"
    assert parse_cookie_string(raw) == {"datadome": "abc~1", "other": "1"}
    assert parse_cookie_string("a=1; b=2") == {"a": "1", "b": "2"}
    assert parse_cookie_string(None) == {}


def test_protection_detection():
    assert is_protection_block(403, CAPTCHA.encode())
    assert is_protection_block(403, b"")
    assert is_protection_block(429, CAPTCHA)
    assert not is_protection_block(429, b"rate limited")
    assert not is_protection_block(401, CAPTCHA)
    # real TGTG answer for an invalid access token – not a captcha
    assert not is_protection_block(403, b'{"errors":[{"code":"UNAUTHORIZED"}]}')
    assert is_unauthorized(403, b'{"errors":[{"code":"UNAUTHORIZED"}]}')
    assert is_unauthorized(401, b"")
    assert not is_unauthorized(403, CAPTCHA)


def test_modern_user_agent_and_device_consistency():
    c = logged_in_client()
    assert c.user_agent.startswith("TGTG/26.11.1 Dalvik/2.1.0 (Linux; U; Android 15; Pixel 8 Pro")
    assert c.credentials()["device"] == 0


@responses.activate
def test_stored_cookie_is_sent_and_updated_from_response():
    responses.add(
        responses.POST,
        BASE + "item/v9/",
        json={"items": []},
        headers={"Set-Cookie": "datadome=rotated; Max-Age=100; Domain=.toogoodtogo.com; Path=/; Secure"},
    )
    c = logged_in_client()
    assert c.get_items() == []
    sent = responses.calls[0].request.headers["Cookie"]
    assert sent == "datadome=stored"  # no attributes, no SDK call because a cookie exists
    assert c.cookie == "datadome=rotated"
    assert len(responses.calls) == 1


@responses.activate
def test_captcha_block_fetches_new_datadome_cookie_and_retries_once():
    responses.add(responses.POST, BASE + "item/v9/", body=CAPTCHA, status=403)
    responses.add(responses.POST, BASE + "item/v9/", json={"items": [{"item": {"item_id": "1"}}]})
    sdk_ok("fresh")
    c = logged_in_client()
    items = c.get_items()
    assert items == [{"item": {"item_id": "1"}}]
    item_calls = [call for call in responses.calls if "item/v9" in call.request.url]
    assert item_calls[0].request.headers["Cookie"] == "datadome=stored"
    assert item_calls[1].request.headers["Cookie"] == "datadome=fresh"
    sdk_body = [call for call in responses.calls if call.request.url == DATADOME_SDK_URL][0].request.body
    assert "mdl=Pixel+8+Pro" in sdk_body and "osr=15" in sdk_body


@responses.activate
def test_persistent_block_raises():
    responses.add(responses.POST, BASE + "item/v9/", body=CAPTCHA, status=403)
    sdk_ok()
    with pytest.raises(TgtgAPIError) as exc:
        logged_in_client().get_items()
    assert exc.value.args[0] == 403
    assert len([c for c in responses.calls if "item/v9" in c.request.url]) == 2  # exactly one retry


@responses.activate
def test_login_flow_with_pin():
    sdk_ok("dd")
    responses.add(responses.POST, BASE + "auth/v5/authByEmail", json={"state": "WAIT", "polling_id": "poll-1"})
    responses.add(
        responses.POST,
        BASE + "auth/v5/authByRequestPin",
        json={"access_token": "A", "refresh_token": "R"},
        headers={"Set-Cookie": "datadome=after-login; Path=/; Secure"},
    )
    c = BotTgtgClient(email="me@example.com", device_index=1)
    assert c.start_login() == "poll-1"
    c.finish_login("poll-1", "123456")
    pin_body = json.loads(responses.calls[-1].request.body)
    assert pin_body == {
        "device_type": "ANDROID",
        "email": "me@example.com",
        "request_pin": "123456",
        "request_polling_id": "poll-1",
    }
    creds = c.credentials()
    assert creds["access_token"] == "A" and creds["refresh_token"] == "R"
    assert creds["cookie"] == "datadome=after-login"
    assert creds["last_refresh"] and creds["device"] == 1


@responses.activate
def test_login_unknown_email_and_block():
    sdk_ok()
    responses.add(responses.POST, BASE + "auth/v5/authByEmail", json={"state": "TERMS"})
    with pytest.raises(ValueError):
        BotTgtgClient(email="new@example.com").start_login()
    responses.replace(responses.POST, BASE + "auth/v5/authByEmail", body=CAPTCHA, status=403)
    with pytest.raises(TgtgLoginError) as exc:
        BotTgtgClient(email="me@example.com").start_login()
    assert exc.value.args[0] == 403


@responses.activate
def test_refresh_without_set_cookie_header():
    responses.add(responses.POST, BASE + "token/v1/refresh", json={"access_token": "A2", "refresh_token": "R2"})
    responses.add(responses.POST, BASE + "item/v9/", json={"items": []})
    c = logged_in_client()
    c.last_time_token_refreshed = None
    c.get_items()
    assert c.access_token == "A2" and c.refresh_token == "R2"
    assert responses.calls[1].request.headers["authorization"] == "Bearer A2"


def test_not_logged_in_raises():
    with pytest.raises(TgtgLoginError):
        BotTgtgClient(email="x@example.com").get_items()


@responses.activate
def test_custom_base_url_and_endpoint():
    responses.add(responses.POST, "https://apptoogoodtogo.com/api/item/v8/", json={"items": []})
    c = logged_in_client(base_url="https://apptoogoodtogo.com/api/", item_endpoint="item/v8/")
    assert c.get_items() == []


@responses.activate
def test_403_unauthorized_is_not_retried_as_captcha():
    responses.add(responses.POST, BASE + "item/v9/", json={"errors": [{"code": "UNAUTHORIZED"}]}, status=403)
    with pytest.raises(TgtgAPIError):
        logged_in_client().get_items()
    assert len(responses.calls) == 1  # no DataDome SDK call, no retry
