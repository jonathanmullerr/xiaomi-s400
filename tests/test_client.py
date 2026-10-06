import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from xiaomi_s400.client import XiaomiS400Client, normalize, timestamp_ms
from xiaomi_s400.errors import AuthenticationError, InputError, PaginationError, ProtocolError
from xiaomi_s400.session import save_session


def row(timestamp=1700000000, **body):
    return {"createTime": timestamp, "data": json.dumps({"userType": "1", "weight": 70.25, **body})}


class ClientTests(unittest.TestCase):
    def client(self, pages, **kwargs):
        client = XiaomiS400Client(**kwargs)
        client._service = Mock(user_id="123")
        client._service.call.side_effect = [{"code": 0, "result": page} for page in pages]
        return client

    def test_normalization_precision_missing_and_finite(self):
        item = normalize(
            {"weight": "70.25", "bodyRes": "457.5", "bodyRes2": "458.75", "heartRate": 0, "bfp": float("nan")},
            1700000000000,
        )
        self.assertEqual(item["weight_kg"], 70.25)
        self.assertEqual(item["impedance_ohm"], 457.5)
        self.assertEqual(item["impedance_low_ohm"], 458.75)
        self.assertIsNone(item["heart_rate_bpm"])
        self.assertIsNone(item["body_composition"]["fat_percent"])
        self.assertIsNone(item["body_composition"]["muscle_mass_kg"])
        self.assertNotIn("bruto_nuvem", item)
        for weight in (None, "", 0, -1, float("nan"), float("inf"), True, "invalid"):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                normalize({"weight": weight}, 1700000000000)

    def test_timestamps_and_local_day_boundaries(self):
        self.assertEqual(timestamp_ms(1700000000), 1700000000000)
        self.assertEqual(timestamp_ms(1700000000123), 1700000000123)
        # 2024-01-02 02:59:59 UTC is still January 1 in Sao Paulo.
        c = self.client([[row(1704164399), row(1704164400)]])
        data = c.get_measurements("2024-01-01", "2024-01-01")
        self.assertEqual([x["device_timestamp"] for x in data["measurements"]], [1704164399000])
        self.assertEqual(data["filtered"], 1)
        for value in (None, 0, -1, float("inf"), "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                timestamp_ms(value)
        for interval in [("2024-01-02", "2024-01-01"), ("2024-02-30", "2024-03-01"), ("20240101", "2024-01-02")]:
            with self.assertRaises(InputError):
                c.get_measurements(*interval)
        self.assertEqual(c._service.call.call_count, 1)

    def test_empty_history_and_profile_invalid_records_raw_opt_in(self):
        self.assertEqual(self.client([[]]).get_measurements()["measurements"], [])
        c = self.client(
            [
                [
                    row(),
                    row(1700000001, userType="2"),
                    row(1700000002, weight=-2),
                    {"createTime": 1700000003, "data": "{synthetic-secret"},
                    None,
                    row(1700000004, weight=72),
                    row("bad"),
                    {"createTime": 1700000005, "data": "[]"},
                ]
            ]
        )
        data = c.get_measurements(include_raw=True)
        self.assertEqual(data["received"], 8)
        self.assertEqual(data["invalid"], 5)
        self.assertEqual(data["filtered"], 1)
        self.assertEqual([x["weight_kg"] for x in data["measurements"]], [70.25, 72])
        self.assertEqual(data["measurements"][0]["bruto_nuvem"]["userType"], "1")
        self.assertNotIn("synthetic-secret", json.dumps(data["errors"]))
        c = self.client([[row(), row(1700000001, userType="2")]], profile="2")
        self.assertEqual(c.get_measurements()["measurements"][0]["device_timestamp"], 1700000001000)

    def test_multiple_pages_dedup_and_cursor(self):
        first = [row(1700000000 - i) for i in range(20)]
        second = [first[-1], row(1699999900)]
        c = self.client([first, second])
        data = c.get_measurements()
        self.assertEqual(len(data["measurements"]), 21)
        self.assertEqual(data["received"], 21)
        self.assertEqual(c._service.call.call_args_list[1].args[1]["beginTime"], 1699999980999)
        self.assertEqual(c._service.call.call_args_list[0].args[0], "/eco/common/scale/getUserDataByPage")
        self.assertEqual(c._service.call.call_args_list[0].args[1]["model"], "yunmai.scales.ms104")

    def test_stalled_cursor_and_limit_fail_not_partial(self):
        page = [row(1700000000 - i) for i in range(20)]
        with self.assertRaises(PaginationError):
            self.client([page, page]).get_measurements()
        pages = [[row(1700000000 - p * 100 - i) for i in range(20)] for p in range(50)]
        c = self.client(pages)
        with self.assertRaises(PaginationError):
            c.get_measurements()
        self.assertEqual(c._service.call.call_count, 50)

    def test_invalid_upstream_protocol_and_configuration(self):
        c = self.client([])
        for result in ({"code": 1, "private": "synthetic-secret"}, {"code": 0, "result": {}}, {}):
            c._service.call.side_effect = None
            c._service.call.return_value = result
            with self.assertRaises(ProtocolError) as caught:
                c.get_measurements()
            self.assertNotIn("synthetic-secret", str(caught.exception))
        for kwargs in ({"region": "evil.invalid"}, {"profile": ""}, {"timezone": "invalid"}):
            with self.assertRaises(InputError):
                XiaomiS400Client(**kwargs)

    def test_remote_probe_refresh_once_and_persistent_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            save_session(path, {"userId": "123", "passToken": "synthetic"})
            for fails in (False, True):
                c = XiaomiS400Client(session_path=path)
                old = Mock(user_id="123")
                old.call.side_effect = AuthenticationError()
                c._service = old
                renewed = Mock(user_id="123")
                if fails:
                    renewed.call.side_effect = AuthenticationError()
                else:
                    renewed.call.return_value = {"code": 0, "result": []}
                with patch("xiaomi_s400.client.ServiceSession", return_value=renewed) as factory:
                    if fails:
                        with self.assertRaises(AuthenticationError):
                            c.probe()
                        self.assertIsNone(c._service)
                    else:
                        self.assertEqual(c.probe(), {"ok": True, "authenticated": True, "error": None})
                    self.assertEqual(factory.call_count, 1)
                    self.assertEqual(old.call.call_count, 1)
                    self.assertEqual(renewed.call.call_count, 1)

    def test_shared_client_access_is_serialized(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor

        c = self.client([])
        entered, release = threading.Event(), threading.Event()
        active = maximum = 0
        guard = threading.Lock()

        def remote(*args):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            entered.set()
            release.wait(2)
            with guard:
                active -= 1
            return {"code": 0, "result": []}

        c._service.call.side_effect = remote
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = [pool.submit(c.probe if i % 2 else c.get_measurements) for i in range(4)]
            self.assertTrue(entered.wait(2))
            release.set()
            results = [job.result(timeout=3) for job in jobs]
        self.assertEqual(maximum, 1)
        self.assertEqual(c._service.call.call_count, 4)
        self.assertEqual(results[0]["measurements"], [])
        self.assertTrue(results[1]["authenticated"])
