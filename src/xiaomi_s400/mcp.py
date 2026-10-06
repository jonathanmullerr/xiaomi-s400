"""Read-only MCP tools; authentication is performed separately through the CLI."""

from typing import TypedDict

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from .client import date_range
from .errors import S400Error


class Status(TypedDict):
    ok: bool
    authenticated: bool
    error: str | None


class Measurement(TypedDict):
    device_timestamp: int
    weight_kg: float
    heart_rate_bpm: float | None
    impedance_ohm: float | None
    impedance_low_ohm: float | None
    body_composition: dict[str, float | str | None]


class History(TypedDict):
    measurements: list[Measurement]
    received: int
    filtered: int
    invalid: int
    errors: list[str]


class Latest(TypedDict):
    measurement: Measurement | None


def create_mcp(client) -> FastMCP:
    server = FastMCP(
        "xiaomi-s400", log_level="ERROR", instructions="Read Xiaomi Home S400 history. Log in with the CLI first."
    )
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

    def invoke(action):
        try:
            return action()
        except S400Error as error:
            raise ToolError(f"{error.code}: {error}") from None
        except Exception:
            raise ToolError("protocol_error: S400 operation failed.") from None

    @server.tool(annotations=annotations, structured_output=True)
    def s400_status() -> Status:
        """Verify Xiaomi Home authentication remotely. No credentials or measurements are returned."""
        return invoke(client.probe)

    def history(from_date, to_date):
        date_range(from_date, to_date)
        return client.get_measurements(from_date, to_date)

    @server.tool(annotations=annotations, structured_output=True)
    def s400_get_measurements(from_date: str | None = None, to_date: str | None = None) -> History:
        """Get normalized history. Optional YYYY-MM-DD dates are inclusive in the configured timezone."""
        return invoke(lambda: history(from_date, to_date))

    @server.tool(annotations=annotations, structured_output=True)
    def s400_get_latest_measurement(from_date: str | None = None, to_date: str | None = None) -> Latest:
        """Get the newest measurement in the optional date interval, or measurement=null when empty."""

        def latest():
            rows = history(from_date, to_date)["measurements"]
            return {"measurement": max(rows, key=lambda item: item["device_timestamp"]) if rows else None}

        return invoke(latest)

    return server
