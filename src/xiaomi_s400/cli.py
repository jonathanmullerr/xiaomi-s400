"""Command-line adapters. JSON is stdout; diagnostics and QR URLs are stderr."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .auth import MODEL, qr_login
from .client import XiaomiS400Client
from .errors import InputError, LoginCancelled, S400Error
from .session import DEFAULT_SESSION, save_session


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="xiaomi-s400")
    result.add_argument("--version", action="version", version=__version__)
    result.add_argument("--session", default=os.environ.get("XIAOMI_S400_SESSION", str(DEFAULT_SESSION)))
    result.add_argument("--region", default=os.environ.get("XIAOMI_S400_REGION", "us"))
    result.add_argument("--profile", default=os.environ.get("XIAOMI_S400_USER_TYPE", "1"))
    result.add_argument("--timezone", default=os.environ.get("HEALTH_TIME_ZONE", "America/Sao_Paulo"))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="Log in by QR; cancel with Ctrl-C")
    commands.add_parser("import-session", help="Import userId/passToken JSON").add_argument("file", type=Path)
    commands.add_parser("status", help="Check remote authentication")
    measurements = commands.add_parser("measurements", help="Export normalized JSON")
    measurements.add_argument("--from", dest="from_date")
    measurements.add_argument("--to", dest="to_date")
    measurements.add_argument("--output", type=Path)
    commands.add_parser("mcp", help="Run the local read-only stdio MCP server")
    serve = commands.add_parser("serve", help="Run the compatible HTTP collector")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if os.environ.get("XIAOMI_S400_MODEL", MODEL) != MODEL:
            raise InputError()
        client = XiaomiS400Client(
            session_path=args.session, region=args.region, profile=args.profile, timezone=args.timezone
        )
        if args.command == "login":

            def show(login_url, qr_url, expires):
                print(
                    f"Open {login_url}\nOr open and scan {qr_url}\nExpires in {expires} seconds; Ctrl-C cancels.",
                    file=sys.stderr,
                )

            save_session(Path(args.session), qr_login(show=show))
            print("Session saved.", file=sys.stderr)
        elif args.command == "import-session":
            save_session(Path(args.session), json.loads(args.file.read_text(encoding="utf-8")))
            print("Session imported.", file=sys.stderr)
        elif args.command == "status":
            print(json.dumps(client.probe(), allow_nan=False))
        elif args.command == "measurements":
            payload = client.get_measurements(args.from_date, args.to_date)
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            if args.output:
                args.output.write_text(encoded, encoding="utf-8")
            else:
                sys.stdout.write(encoded)
        elif args.command == "mcp":
            from .mcp import create_mcp

            create_mcp(client).run(transport="stdio")
        elif args.command == "serve":
            from .http import create_server

            if not 1 <= args.port <= 65535:
                raise InputError()
            with create_server(client, host=args.host, port=args.port) as server:
                print(f"Listening on {args.host}:{args.port}", file=sys.stderr)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    return 0
        return 0
    except KeyboardInterrupt:
        error = LoginCancelled()
    except S400Error as caught:
        error = caught
    except (OSError, ValueError):
        error = InputError()
    print(f"{error.code}: {error}", file=sys.stderr)
    return 1
