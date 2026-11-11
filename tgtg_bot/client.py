"""Hardened wrapper around the official ``tgtg`` PyPI client.

The upstream library (https://github.com/ahivert/tgtg-python) does the heavy
lifting. This module only fixes the parts that caused bans/403s in practice:

* **Cookie handling** – upstream sends the stored login cookie as a raw
  ``Cookie`` header. ``requests`` then ignores the session cookie jar, so a
  fresh DataDome cookie is never sent and a 403 can never recover. Here all
  cookies live in one dict that is updated from every response.
* **User agent / fingerprint** – the default user agents (Android 9-12) are
  blocked by DataDome. We use current devices and send a DataDome SDK
  fingerprint that matches the chosen device.
* **Proxy** – the DataDome cookie is fetched through the same proxy as the API.
* **API host / item endpoint** – configurable, defaults follow upstream main.
* **Token refresh** – robust against missing ``Set-Cookie`` headers.
"""

from __future__ import annotations

import contextlib
import datetime
import io
import json
import logging
import random
import re
import time
from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import urlsplit

import tgtg as tgtg_module
from tgtg import AUTH_BY_EMAIL_ENDPOINT, REFRESH_ENDPOINT, TgtgClient
from tgtg.exceptions import TgtgAPIError, TgtgLoginError

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.toogoodtogo.com/api/"
DEFAULT_ITEM_ENDPOINT = "item/v9/"
FALLBACK_APK_VERSION = "26.11.1"
DATADOME_SDK_URL = "https://api-sdk.datadome.co/sdk/"
DATADOME_KEY = "1D42C2CA6131C526E09F294FE96F94"

_COOKIE_ATTRIBUTES = {
    "expires",
    "max-age",
    "domain",
    "path",
    "samesite",
    "secure",
    "httponly",
    "priority",
    "partitioned",
}
_COOKIE_RE = re.compile(r"(?:^|[;,])\s*([^=;,\s]+)=([^;,]*)")


@dataclass(frozen=True)
class Device:
    """A real Android device: user agent and DataDome fingerprint must match."""

    model: str
    build: str
    android: str  # release, e.g. "14"
    sdk: str  # API level, e.g. "34"
    codename: str  # Build.VERSION_CODES name as reported by the DataDome SDK
    screen_x: str
    screen_y: str
    density: str

    def user_agent(self, apk_version: str) -> str:
        return f"TGTG/{apk_version} Dalvik/2.1.0 (Linux; U; Android {self.android}; {self.model} Build/{self.build})"


DEVICES = (
    Device("Pixel 8 Pro", "AP3A.241105.008", "15", "35", "VANILLA_ICE_CREAM", "1344", "2992", "3.0"),
    Device("Pixel 9", "BP2A.250605.031", "16", "36", "BAKLAVA", "1080", "2424", "2.625"),
    Device("SM-S928B", "UP1A.231005.007", "14", "34", "UPSIDE_DOWN_CAKE", "1440", "3120", "3.5"),
    Device("SM-S921B", "AP3A.240905.015.A2", "15", "35", "VANILLA_ICE_CREAM", "1080", "2340", "2.8125"),
    Device("CPH2581", "UKQ1.230924.001", "14", "34", "UPSIDE_DOWN_CAKE", "1440", "3168", "3.5"),
)


def latest_apk_version() -> str:
    """Return the current TGTG app version from Google Play (cached per process)."""
    global _APK_VERSION
    if _APK_VERSION is None:
        try:
            from tgtg.google_play_scraper import get_last_apk_version

            _APK_VERSION = str(get_last_apk_version())
        except Exception:  # noqa: BLE001 – scraping is best effort
            logger.warning("Could not read TGTG app version from Google Play, using %s", FALLBACK_APK_VERSION)
            _APK_VERSION = FALLBACK_APK_VERSION
    return _APK_VERSION


_APK_VERSION: str | None = None


def parse_cookie_string(raw: str | None) -> dict[str, str]:
    """Parse a stored cookie string (``Cookie`` or ``Set-Cookie`` format) into a dict."""
    cookies: dict[str, str] = {}
    if not raw:
        return cookies
    for name, value in _COOKIE_RE.findall(raw):
        if name.lower() in _COOKIE_ATTRIBUTES:
            continue
        cookies[name] = value.strip()
    return cookies


def _text(body: bytes | str | None) -> str:
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return body or ""


def is_protection_block(status_code: int, body: bytes | str | None) -> bool:
    """True if a response is a DataDome captcha/interstitial block.

    Note: TGTG also answers 403 for invalid access tokens – with a JSON body
    ``{"errors":[{"code":"UNAUTHORIZED"}]}``. That is *not* a block.
    """
    if status_code not in (HTTPStatus.FORBIDDEN, HTTPStatus.TOO_MANY_REQUESTS):
        return False
    text = _text(body)
    if "captcha-delivery.com" in text:
        return True
    return status_code == HTTPStatus.FORBIDDEN and '"errors"' not in text


def is_unauthorized(status_code: int, body: bytes | str | None) -> bool:
    """True if TGTG rejected the access token (401, or 403 with UNAUTHORIZED)."""
    if status_code == HTTPStatus.UNAUTHORIZED:
        return True
    return status_code == HTTPStatus.FORBIDDEN and "UNAUTHORIZED" in _text(body)


def protection_url(body: bytes | str | None) -> str | None:
    """Extract the captcha URL from a DataDome block body, if present."""
    try:
        if isinstance(body, bytes):
            body = body.decode("utf-8")
        return json.loads(body).get("url")
    except Exception:  # noqa: BLE001
        return None


class BotTgtgClient(TgtgClient):
    """``TgtgClient`` with deterministic cookie handling and a modern fingerprint."""

    def __init__(
        self,
        *,
        email: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        cookie: str | None = None,
        last_time_token_refreshed: datetime.datetime | None = None,
        proxy: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        item_endpoint: str = DEFAULT_ITEM_ENDPOINT,
        user_agent: str | None = None,
        language: str = "en-GB",
        timeout: float = 30,
        device_index: int | None = None,
    ):
        self._cookies: dict[str, str] = {}
        self.version = latest_apk_version()
        self.device = DEVICES[device_index % len(DEVICES)] if device_index is not None else random.choice(DEVICES)
        proxies = {"http": proxy, "https": proxy} if proxy else None
        super().__init__(
            url=base_url,
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            user_agent=user_agent or self.device.user_agent(self.version),
            language=language,
            proxies=proxies,
            timeout=timeout,
            last_time_token_refreshed=last_time_token_refreshed,
            cookie=cookie,
        )
        # get_items() builds its URL from this module constant
        tgtg_module.API_ITEM_ENDPOINT = item_endpoint
        self.session.headers.clear()

    # ------------------------------------------------------------------
    # Cookies
    # ------------------------------------------------------------------

    @property
    def cookie(self) -> str:
        """All known cookies serialized as a ``Cookie`` header value."""
        return "; ".join(f"{k}={v}" for k, v in self._cookies.items())

    @cookie.setter
    def cookie(self, raw: str | None) -> None:
        # Upstream assigns raw Set-Cookie headers here; merge instead of replace.
        self._cookies.update(parse_cookie_string(raw))

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "Accept-Encoding": "gzip",
            "accept-language": self.language,
            "content-type": "application/json; charset=utf-8",
            "user-agent": self.user_agent,
            "x-correlation-id": self.correlation_id,
        }
        if self._cookies:
            headers["Cookie"] = self.cookie
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        return headers

    def _fetch_datadome_cookie(self, request_url: str) -> bool:
        """Request a DataDome cookie like the Android SDK does (one retry)."""
        if self._request_datadome_cookie(request_url):
            return True
        time.sleep(1)
        if self._request_datadome_cookie(request_url):
            return True
        logger.warning("Could not obtain a DataDome cookie")
        return False

    def _request_datadome_cookie(self, request_url: str) -> bool:
        d = self.device
        cid = "".join(
            random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789~_") for _ in range(120)
        )
        params = {
            "camera": '{"auth":"true", "info":"{\\"front\\":\\"2000x1500\\",\\"back\\":\\"5472x3648\\"}"}',
            "cid": cid,
            "ddk": DATADOME_KEY,
            "ddv": "3.0.4",
            "ddvc": self.version,
            "events": '[{"id":1,"message":"response validation","source":"sdk","date":'
            + str(int(time.time() * 1000))
            + "}]",
            "inte": "android-java-okhttp",
            "mdl": d.model,
            "os": "Android",
            "osn": d.codename,
            "osr": d.android,
            "osv": d.sdk,
            "request": request_url,
            "screen_d": d.density,
            "screen_x": d.screen_x,
            "screen_y": d.screen_y,
            "ua": self.user_agent,
        }
        try:
            r = self.session.post(
                DATADOME_SDK_URL,
                data=params,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*",
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate, br",
                },
                proxies=self.proxies,
                timeout=15,
            )
            self.session.cookies.clear()
            data = r.json()
            match = re.search(r"datadome=([^;]+)", data.get("cookie") or "")
            if data.get("status") == 200 and match:
                self._cookies["datadome"] = match.group(1)
                return True
            logger.debug("DataDome SDK answered %s: %s", r.status_code, str(data)[:200])
        except Exception as exc:  # noqa: BLE001
            logger.debug("DataDome SDK request failed: %s", exc)
        return False

    def _send(self, url: str, **kwargs):
        response = self.session.post(url, headers=self._headers, proxies=self.proxies, timeout=self.timeout, **kwargs)
        # Take over every cookie the API sets (e.g. a refreshed datadome cookie)
        self._cookies.update({c.name: c.value for c in response.cookies})
        self.session.cookies.clear()
        return response

    def _post(self, url: str, **kwargs):
        """POST with DataDome cookie handling and exactly one retry on a block."""
        if "datadome" not in self._cookies:
            self._fetch_datadome_cookie(url)
        response = self._send(url, **kwargs)
        if is_protection_block(response.status_code, response.content):
            self._cookies.pop("datadome", None)
            if self._fetch_datadome_cookie(url):
                response = self._send(url, **kwargs)
        return response

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def start_login(self) -> str:
        """Send the login PIN email. Returns the polling id.

        Raises ``TgtgLoginError`` (status, body) on HTTP errors and
        ``ValueError`` if the email has no TGTG account.
        """
        response = self._post(
            self._get_url(AUTH_BY_EMAIL_ENDPOINT),
            json={"device_type": self.device_type, "email": self.email},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgLoginError(response.status_code, response.content)
        data = response.json()
        state = data.get("state")
        if state == "WAIT":
            return data["polling_id"]
        if state == "TERMS":
            raise ValueError("This email is not linked to a Too Good To Go account.")
        raise TgtgLoginError(response.status_code, response.content)

    def finish_login(self, polling_id: str, pin: str) -> None:
        """Complete the login with the PIN from the email."""
        with contextlib.redirect_stdout(io.StringIO()):  # upstream prints "Logged in!"
            self._auth_by_pin(polling_id, pin)

    def login(self) -> None:
        """Called by every upstream API method: only refreshes the access token.

        The interactive email flow of the upstream library (``input()`` for
        the PIN) is never used – see ``start_login``/``finish_login``.
        """
        if not (self.access_token and self.refresh_token):
            raise TgtgLoginError(HTTPStatus.UNAUTHORIZED, b"Not logged in")
        self._refresh_token()

    def _refresh_token(self) -> None:
        if (
            self.last_time_token_refreshed
            and (datetime.datetime.now() - self.last_time_token_refreshed).total_seconds() <= self.access_token_lifetime
        ):
            return
        response = self._post(self._get_url(REFRESH_ENDPOINT), json={"refresh_token": self.refresh_token})
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)
        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.last_time_token_refreshed = datetime.datetime.now()

    def force_token_refresh(self) -> None:
        self.last_time_token_refreshed = None
        self._refresh_token()

    def credentials(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "cookie": self.cookie,
            "last_refresh": self.last_time_token_refreshed.isoformat() if self.last_time_token_refreshed else None,
            "device": DEVICES.index(self.device),
        }

    @property
    def api_host(self) -> str:
        return urlsplit(self.base_url).hostname or ""
