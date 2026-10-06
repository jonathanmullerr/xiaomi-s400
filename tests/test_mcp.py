import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_sdk_stdio_discovery_calls_schema_annotations_and_no_raw(self):
        params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("mcp_fixture.py"))])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                self.assertEqual(
                    {t.name for t in listing.tools},
                    {"s400_status", "s400_get_measurements", "s400_get_latest_measurement"},
                )
                for tool in listing.tools:
                    self.assertTrue(tool.annotations.readOnlyHint)
                    self.assertFalse(tool.annotations.destructiveHint)
                    self.assertEqual(tool.inputSchema["type"], "object")
                    self.assertIsNotNone(tool.outputSchema)
                    self.assertNotIn("passToken", str(tool.inputSchema))
                status = await session.call_tool("s400_status")
                self.assertFalse(status.isError)
                self.assertTrue(status.structuredContent["authenticated"])
                history = await session.call_tool("s400_get_measurements", {"from_date": "2023-01-01"})
                self.assertFalse(history.isError)
                self.assertEqual(history.structuredContent["measurements"][0]["weight_kg"], 70.25)
                self.assertNotIn("bruto_nuvem", str(history))
                latest = await session.call_tool("s400_get_latest_measurement")
                self.assertEqual(latest.structuredContent["measurement"]["impedance_ohm"], 457.5)
                empty = await session.call_tool("s400_get_latest_measurement", {"from_date": "2000-01-01"})
                self.assertIsNone(empty.structuredContent["measurement"])
                bad = await session.call_tool("s400_get_measurements", {"from_date": "invalid"})
                self.assertTrue(bad.isError)
                self.assertIn("invalid_input", str(bad))

    async def test_actual_cli_mcp_without_session_has_sanitized_error(self):
        with tempfile.TemporaryDirectory() as directory:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "xiaomi_s400", "--session", str(Path(directory) / "absent.json"), "mcp"],
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    for name in ("s400_status", "s400_get_measurements", "s400_get_latest_measurement"):
                        result = await session.call_tool(name)
                        self.assertTrue(result.isError)
                        self.assertIn("authentication_required", str(result))
                        self.assertNotIn(directory, str(result))
