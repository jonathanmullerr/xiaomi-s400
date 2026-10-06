"""Xiaomi Home authentication and encrypted requests.

QR flow adapted from Xiaomi-cloud-tokens-extractor; see THIRD-PARTY-NOTICES.md.
"""

import base64
import hashlib
import json
import math
import os
import struct
import time
from threading import Event
from urllib.parse import urlparse

import requests
from Crypto.Cipher import ARC4

from .errors import AuthenticationError, InputError, LoginCancelled, LoginExpired, NetworkError, ProtocolError
from .session import credentials

PREFIX = "&&&START&&&"
MODEL = "yunmai.scales.ms104"
HISTORY_PATH = "/eco/common/scale/getUserDataByPage"
REJECTED_CODES = {-3, -6, 401, 403}


def safe_url(value: object) -> str:
    if not isinstance(value, str):
        raise ProtocolError()
    url = urlparse(value)
    host = url.hostname or ""
    if (
        url.scheme != "https"
        or url.username
        or url.password
        or url.port not in (None, 443)
        or not any(host == domain or host.endswith("." + domain) for domain in ("xiaomi.com", "mi.com"))
    ):
        raise ProtocolError()
    return value


def request(http, method: str, url: str, **kwargs):
    try:
        response = getattr(http, method)(url, timeout=kwargs.pop("timeout", 30), **kwargs)
    except requests.RequestException:
        raise NetworkError() from None
    if response.status_code in (401, 403):
        raise AuthenticationError()
    if response.status_code != 200:
        raise ProtocolError()
    return response


def parse_response(response) -> dict:
    try:
        text = response.text.removeprefix(PREFIX)
        result = json.loads(text)
    except (ValueError, TypeError):
        raise ProtocolError() from None
    if not isinstance(result, dict):
        raise ProtocolError()
    return result


def validate_cloud_response(result: object) -> dict:
    if not isinstance(result, dict) or type(result.get("code")) is not int:
        raise ProtocolError()
    if result["code"] in REJECTED_CODES:
        raise AuthenticationError()
    if result["code"] != 0:
        raise ProtocolError()
    return result


def qr_login(*, http=None, show=None, cancel: Event | None = None, clock=time.monotonic) -> dict[str, str]:
    """Show login/QR URLs, poll until expiry, return credentials without logging them.

    ``show(login_url, qr_image_url, expires_in_seconds)`` runs once. Ctrl-C or a
    set cancellation event cancels; each pending poll lasts at most 30 seconds.
    """
    http = http if http is not None else requests.Session()
    cancel = cancel if cancel is not None else Event()
    try:
        if cancel.is_set():
            raise LoginCancelled()
        initial = parse_response(
            request(
                http,
                "get",
                "https://account.xiaomi.com/longPolling/loginUrl",
                params={
                    "_qrsize": "480",
                    "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
                    "callback": "https://sts.api.io.mi.com/sts",
                    "_hasLogo": "false",
                    "sid": "xiaomiio",
                    "serviceParam": "",
                    "_locale": "en_GB",
                    "_dc": str(int(time.time() * 1000)),
                },
            )
        )
        try:
            login_url, qr_url, poll_url = (safe_url(initial.get(key)) for key in ("loginUrl", "qr", "lp"))
            expires = float(initial["timeout"])
            if not math.isfinite(expires) or expires <= 0 or expires > 3600:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise ProtocolError() from None
        deadline = clock() + expires
        if show:
            show(login_url, qr_url, int(expires))
        while True:
            if cancel.is_set():
                raise LoginCancelled()
            remaining = deadline - clock()
            if remaining <= 0:
                raise LoginExpired()
            try:
                response = http.get(poll_url, timeout=min(30, remaining))
            except requests.Timeout:
                continue
            except requests.RequestException:
                raise NetworkError() from None
            if cancel.is_set():
                raise LoginCancelled()
            if clock() >= deadline:
                raise LoginExpired()
            if response.status_code in (401, 403):
                raise AuthenticationError()
            if response.status_code != 200:
                raise ProtocolError()
            payload = parse_response(response)
            if payload.get("code") in (70016, 70017):
                raise LoginExpired()
            try:
                return credentials(payload)
            except InputError:
                raise AuthenticationError() from None
    except KeyboardInterrupt:
        raise LoginCancelled() from None


def rc4(key: bytes, payload: bytes) -> bytes:
    cipher = ARC4.new(key)
    cipher.encrypt(bytes(1024))
    return cipher.encrypt(payload)


class ServiceSession:
    def __init__(self, credential: dict, region: str, *, http=None):
        self.http = http if http is not None else requests.Session()
        self.http.headers["User-Agent"] = "APP/com.xiaomi.mihome APPV/10.5.201"
        self.region = region
        payload = parse_response(
            request(
                self.http,
                "get",
                "https://account.xiaomi.com/pass/serviceLogin",
                params={"_json": "true", "sid": "xiaomiio"},
                cookies={"userId": credential["userId"], "passToken": credential["passToken"]},
            )
        )
        try:
            location = safe_url(payload.get("location"))
            self.ssecurity = base64.b64decode(payload["ssecurity"], validate=True)
            if not 5 <= len(self.ssecurity) <= 256:
                raise ValueError()
            self.user_id = str(payload.get("userId", credential["userId"]))
        except (KeyError, ValueError, TypeError, ProtocolError):
            raise AuthenticationError() from None
        final = request(self.http, "get", location)
        self.cookies = {"userId": self.user_id, **self.http.cookies.get_dict(), **final.cookies.get_dict()}
        if not self.cookies.get("serviceToken"):
            raise AuthenticationError()
        self.cookies["yetAnotherServiceToken"] = self.cookies["serviceToken"]

    def call(self, path: str, data: dict) -> dict:
        nonce = os.urandom(8) + struct.pack(">I", int(time.time()) // 60)
        signed = hashlib.sha256(self.ssecurity + nonce).digest()

        def signature(form):
            parts = [
                "POST",
                path,
                *(f"{key}={value}" for key, value in form.items()),
                base64.b64encode(signed).decode(),
            ]
            return base64.b64encode(hashlib.sha1("&".join(parts).encode()).digest()).decode()

        form = {"data": json.dumps(data, separators=(",", ":"))}
        form["rc4_hash__"] = signature(form)
        form = {key: base64.b64encode(rc4(signed, value.encode())).decode() for key, value in form.items()}
        form["signature"] = signature(form)
        form["_nonce"] = base64.b64encode(nonce).decode()
        base = "https://" + ("" if self.region in ("", "cn") else self.region + ".") + "api.io.mi.com/app"
        response = request(
            self.http,
            "post",
            base + path,
            data=form,
            cookies=self.cookies,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "MIOT-REQUEST-MODEL": MODEL,
            },
        )
        # Auth errors may be plaintext even when success responses are RC4.
        if response.text.lstrip().startswith(("{", PREFIX)):
            validate_cloud_response(parse_response(response))
            raise ProtocolError()
        try:
            result = json.loads(rc4(signed, base64.b64decode(response.text, validate=True)))
        except (ValueError, TypeError, UnicodeError):
            raise ProtocolError() from None
        return validate_cloud_response(result)
