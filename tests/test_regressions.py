import base64
import json
import threading
import unittest
from unittest.mock import Mock
from urllib.request import urlopen

import requests

from xiaomi_s400.auth import ServiceSession
from xiaomi_s400.client import XiaomiS400Client, normalize
from xiaomi_s400.errors import ProtocolError
from xiaomi_s400.http import create_server


class ReviewRegressionTests(unittest.TestCase):
    def test_malformed_cloud_code_is_sanitized_protocol_error(self):
        client = XiaomiS400Client()
        client._service = Mock(user_id="123")
        for code in ([], {}, "synthetic-secret", None, False):
            with self.subTest(code=code):
                client._service.call.return_value = {"code": code, "result": [], "private": "synthetic-secret"}
                with self.assertRaises(ProtocolError) as caught:
                    client.probe()
                self.assertNotIn("synthetic-secret", str(caught.exception))
        http = Mock(headers={}, cookies=requests.cookies.RequestsCookieJar())
        final = Mock(status_code=200, cookies=requests.cookies.RequestsCookieJar())
        final.cookies.set("serviceToken", "synthetic")
        http.get.side_effect = [
            Mock(
                status_code=200,
                text=json.dumps(
                    {
                        "userId": "123",
                        "location": "https://sts.api.io.mi.com/sts",
                        "ssecurity": base64.b64encode(b"0123456789abcdef").decode(),
                    }
                ),
            ),
            final,
        ]
        service = ServiceSession({"userId": "123", "passToken": "synthetic"}, "us", http=http)
        for code in ([], {}, None):
            http.post.return_value = Mock(
                status_code=200, text=json.dumps({"code": code, "private": "synthetic-secret"})
            )
            with self.assertRaises(ProtocolError):
                service.call("/eco/common/scale/getUserDataByPage", {})

    def test_nonfinite_raw_values_do_not_discard_healthy_measurement_over_http(self):
        body = {
            "userType": "1",
            "weight": 70.25,
            "bodyRes": 457.5,
            "bfp": float("nan"),
            "nested": [float("inf"), {"value": -float("inf")}],
        }
        direct = normalize(body, 1700000000000, include_raw=True)
        self.assertIsNone(direct["bruto_nuvem"]["bfp"])
        self.assertEqual(direct["bruto_nuvem"]["nested"], [None, {"value": None}])
        client = XiaomiS400Client()
        client._service = Mock(user_id="123")
        client._service.call.return_value = {
            "code": 0,
            "result": [{"createTime": 1700000000, "data": json.dumps(body)}],
        }
        server = create_server(client, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(f"http://127.0.0.1:{server.server_port}/measurements") as response:
                self.assertEqual(response.status, 200)
                result = json.load(response)
            self.assertEqual(result["invalid"], 0)
            self.assertEqual(len(result["measurements"]), 1)
            item = result["measurements"][0]
            self.assertEqual(item["weight_kg"], 70.25)
            self.assertIsNone(item["body_composition"]["fat_percent"])
            self.assertIsNone(item["bruto_nuvem"]["bfp"])
            self.assertEqual(item["bruto_nuvem"]["nested"], [None, {"value": None}])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
