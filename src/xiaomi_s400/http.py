"""Local/private-network HTTP adapter compatible with Health Harness."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .client import date_range
from .errors import InputError, S400Error


def create_server(client, *, host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status: int, payload: dict):
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):  # noqa: N802
            try:
                url = urlparse(self.path)
                if url.path == "/probe":
                    self.send_json(200, client.probe())
                elif url.path == "/connect":
                    client.probe()
                    self.send_json(200, {"authenticated": True})
                elif url.path == "/measurements":
                    query = parse_qs(url.query, keep_blank_values=True)
                    if set(query) - {"from", "to"} or any(len(v) != 1 or not v[0] for v in query.values()):
                        raise InputError()
                    start = query.get("from", [None])[0]
                    end = query.get("to", [None])[0]
                    date_range(start, end)
                    self.send_json(200, client.get_measurements(start, end, include_raw=True))
                else:
                    self.send_json(404, {"error": "not_found"})
            except S400Error as error:
                self.send_json(
                    400 if isinstance(error, InputError) else 502,
                    {"ok": False, "authenticated": False, "error": error.code},
                )
            except Exception:
                self.send_json(502, {"ok": False, "authenticated": False, "error": "protocol_error"})

        def log_message(self, format, *args):
            pass  # Request URLs and upstream data never enter logs.

    return ThreadingHTTPServer((host, port), Handler)
