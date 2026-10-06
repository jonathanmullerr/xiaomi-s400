import base64
import unittest
from threading import Event
from unittest.mock import Mock

import requests

from xiaomi_s400.auth import ServiceSession, qr_login
from xiaomi_s400.errors import AuthenticationError, LoginCancelled, LoginExpired, NetworkError, ProtocolError


def response(payload=None, status=200):
    import json

    return Mock(
        status_code=status, text="&&&START&&&" + json.dumps(payload or {}), cookies=requests.cookies.RequestsCookieJar()
    )


class AuthTests(unittest.TestCase):
    def test_qr_completion_expiration_and_cancellation(self):
        http = Mock(headers={}, cookies=requests.cookies.RequestsCookieJar())
        http.get.side_effect = [
            response(
                {
                    "qr": "https://account.xiaomi.com/qr",
                    "loginUrl": "https://account.xiaomi.com/login",
                    "lp": "https://account.xiaomi.com/poll",
                    "timeout": 60,
                }
            ),
            response({"userId": "123", "passToken": "synthetic"}),
        ]
        show = Mock()
        self.assertEqual(qr_login(http=http, show=show), {"userId": "123", "passToken": "synthetic"})
        self.assertEqual(show.call_args.args, ("https://account.xiaomi.com/login", "https://account.xiaomi.com/qr", 60))
        self.assertTrue(all(call.kwargs["timeout"] <= 30 for call in http.get.call_args_list))
        cancel = Event()
        cancel.set()
        with self.assertRaises(LoginCancelled):
            qr_login(http=http, cancel=cancel)
        http.get.side_effect = [
            response(
                {
                    "qr": "https://account.xiaomi.com/qr",
                    "loginUrl": "https://account.xiaomi.com/login",
                    "lp": "https://account.xiaomi.com/poll",
                    "timeout": 1,
                }
            )
        ]
        clock = Mock(side_effect=[0, 2])
        with self.assertRaises(LoginExpired):
            qr_login(http=http, show=Mock(), clock=clock)

    def test_poll_timeout_retry_rejection_and_sanitization(self):
        init = response(
            {
                "qr": "https://account.xiaomi.com/qr",
                "loginUrl": "https://account.xiaomi.com/login",
                "lp": "https://account.xiaomi.com/poll",
                "timeout": 60,
            }
        )
        http = Mock(headers={}, cookies=requests.cookies.RequestsCookieJar())
        http.get.side_effect = [
            init,
            requests.Timeout("synthetic-secret"),
            response({"userId": "123", "passToken": "synthetic"}),
        ]
        self.assertEqual(qr_login(http=http, show=Mock())["userId"], "123")
        for failure, expected in [
            (requests.ConnectionError("synthetic-secret"), NetworkError),
            (response({"private": "synthetic-secret"}), ProtocolError),
            (response(status=401), AuthenticationError),
        ]:
            http.get.side_effect = [failure]
            with self.assertRaises(expected) as caught:
                qr_login(http=http, show=Mock())
            self.assertNotIn("synthetic-secret", str(caught.exception))

    def test_service_auth_cookie_and_timeout(self):
        http = Mock(headers={}, cookies=requests.cookies.RequestsCookieJar())
        jar = requests.cookies.RequestsCookieJar()
        jar.set("serviceToken", "synthetic-service")
        final = response()
        final.cookies = jar
        http.get.side_effect = [
            response(
                {
                    "location": "https://sts.api.io.mi.com/sts",
                    "ssecurity": base64.b64encode(b"0123456789abcdef").decode(),
                    "userId": "123",
                }
            ),
            final,
        ]
        service = ServiceSession({"userId": "123", "passToken": "synthetic"}, "us", http=http)
        self.assertEqual(service.user_id, "123")
        self.assertEqual(service.cookies["serviceToken"], "synthetic-service")
        self.assertTrue(all(call.kwargs["timeout"] == 30 for call in http.get.call_args_list))
        http.post.return_value = response(status=403)
        with self.assertRaises(AuthenticationError):
            service.call("/eco/common/scale/getUserDataByPage", {})
        self.assertEqual(http.post.call_args.kwargs["timeout"], 30)
        self.assertEqual(http.post.call_args.args[0], "https://us.api.io.mi.com/app/eco/common/scale/getUserDataByPage")
        for payload in ({}, {"location": "https://evil.invalid/", "ssecurity": "synthetic-secret"}):
            http.get.side_effect = [response(payload)]
            with self.assertRaises(AuthenticationError):
                ServiceSession({"userId": "123", "passToken": "synthetic"}, "us", http=http)
