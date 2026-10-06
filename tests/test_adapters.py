import contextlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import urlopen

from xiaomi_s400.cli import main
from xiaomi_s400.errors import AuthenticationError, NetworkError
from xiaomi_s400.http import create_server
from xiaomi_s400.session import load_session

ENVELOPE = {
    "measurements": [
        {
            "device_timestamp": 1700000000000,
            "weight_kg": 70.25,
            "impedance_ohm": 457.5,
            "heart_rate_bpm": None,
            "impedance_low_ohm": None,
            "body_composition": {},
            "bruto_nuvem": {"userType": "1"},
        }
    ],
    "received": 1,
    "invalid": 0,
    "filtered": 0,
    "errors": [],
}


class AdapterTests(unittest.TestCase):
    def cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_cli_json_stdout_file_exit_codes_and_login(self):
        client = Mock()
        public = {
            **ENVELOPE,
            "measurements": [{k: v for k, v in ENVELOPE["measurements"][0].items() if k != "bruto_nuvem"}],
        }
        client.get_measurements.return_value = public
        client.probe.return_value = {"ok": True, "authenticated": True, "error": None}
        with patch("xiaomi_s400.cli.XiaomiS400Client", return_value=client):
            code, out, err = self.cli(["measurements", "--from", "2023-01-01", "--to", "2023-12-31"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out), public)
            self.assertEqual(err, "")
            self.assertNotIn("bruto_nuvem", out)
            self.assertEqual(client.get_measurements.call_args.args, ("2023-01-01", "2023-12-31"))
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "export.json"
                code, out, err = self.cli(["measurements", "--output", str(target)])
                self.assertEqual((code, out, err), (0, "", ""))
                self.assertEqual(json.loads(target.read_text()), public)
                source, session = Path(directory) / "import.json", Path(directory) / "session.json"
                source.write_text('{"userId":"123","pass_token":"synthetic"}')
                code, out, err = self.cli(["--session", str(session), "import-session", str(source)])
                self.assertEqual(code, 0)
                self.assertEqual(load_session(session), {"userId": "123", "passToken": "synthetic"})
                self.assertNotIn("synthetic", out + err)
                with patch("xiaomi_s400.cli.qr_login", return_value={"userId": "123", "passToken": "synthetic"}):
                    self.assertEqual(self.cli(["--session", str(session), "login"])[0], 0)
            client.probe.side_effect = AuthenticationError()
            code, out, err = self.cli(["status"])
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertIn("authentication_required", err)
        self.assertEqual(self.cli(["--timezone", "bad", "status"])[0], 1)
        self.assertEqual(self.cli(["--session", "/unused", "import-session", "/does-not-exist"])[0], 1)

    def test_http_contract_validation_and_errors(self):
        client = Mock()
        client.probe.return_value = {"ok": True, "authenticated": True, "error": None}
        client.get_measurements.return_value = ENVELOPE
        server = create_server(client, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            for route in ("probe", "connect"):
                with urlopen(base + "/" + route) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(json.load(response)["authenticated"])
            self.assertEqual(client.probe.call_count, 2)
            with urlopen(base + "/measurements?from=2023-01-01&to=2023-12-31") as response:
                self.assertEqual(json.load(response), ENVELOPE)
            self.assertEqual(client.get_measurements.call_args.kwargs, {"include_raw": True})
            for query in (
                "from=bad",
                "from=2024-02-30",
                "from=2024-02-02&to=2024-01-01",
                "from=2024-01-01&from=2024-01-02",
                "unknown=1",
                "from=",
            ):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base + "/measurements?" + query)
                self.assertEqual(caught.exception.code, 400)
                self.assertEqual(json.load(caught.exception)["error"], "invalid_input")
            for error in (AuthenticationError(), NetworkError()):
                client.probe.side_effect = error
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base + "/probe")
                self.assertEqual(caught.exception.code, 502)
                body = json.load(caught.exception)
                self.assertFalse(body["authenticated"])
                self.assertEqual(body["error"], error.code)
            with self.assertRaises(HTTPError) as caught:
                urlopen(base + "/unknown")
            self.assertEqual(caught.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_legacy_environment_defaults(self):
        with patch.dict(
            "os.environ",
            {
                "XIAOMI_S400_REGION": "de",
                "XIAOMI_S400_USER_TYPE": "2",
                "XIAOMI_S400_SESSION": "/synthetic/session.json",
                "HEALTH_TIME_ZONE": "UTC",
            },
        ):
            with patch("xiaomi_s400.cli.XiaomiS400Client") as factory:
                factory.return_value.probe.return_value = {"ok": True, "authenticated": True, "error": None}
                self.cli(["status"])
                self.assertEqual(
                    factory.call_args.kwargs,
                    {"session_path": "/synthetic/session.json", "region": "de", "profile": "2", "timezone": "UTC"},
                )
