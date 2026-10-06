"""Synthetic stdio server fixture; no credentials or upstream calls."""

from xiaomi_s400.mcp import create_mcp


class SyntheticClient:
    def probe(self):
        return {"ok": True, "authenticated": True, "error": None}

    def get_measurements(self, from_date=None, to_date=None):
        if from_date == "2000-01-01":
            return {"measurements": [], "received": 0, "filtered": 0, "invalid": 0, "errors": []}
        return {
            "measurements": [
                {
                    "device_timestamp": 1700000000000,
                    "weight_kg": 70.25,
                    "heart_rate_bpm": None,
                    "impedance_ohm": 457.5,
                    "impedance_low_ohm": None,
                    "body_composition": {},
                }
            ],
            "received": 1,
            "filtered": 0,
            "invalid": 0,
            "errors": [],
        }


if __name__ == "__main__":
    create_mcp(SyntheticClient()).run(transport="stdio")
