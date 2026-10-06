"""Shared Xiaomi Home history, filtering, and normalization."""

import json
import math
import time
from datetime import date, datetime
from datetime import timezone as utc_timezone
from pathlib import Path
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .auth import HISTORY_PATH, MODEL, ServiceSession, validate_cloud_response
from .errors import AuthenticationError, InputError, PaginationError, ProtocolError
from .session import DEFAULT_SESSION, load_session


def number(value: object, zero_missing: bool = False) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and not (zero_missing and parsed == 0) else None


def timestamp_ms(value: object) -> int:
    parsed = number(value)
    if parsed is None or parsed <= 0:
        raise ValueError()
    result = int(parsed * 1000 if parsed < 10_000_000_000 else parsed)
    datetime.fromtimestamp(result / 1000, utc_timezone.utc)  # Reject unrepresentable instants.
    return result


def normalize(body: dict, measured: int, *, include_raw: bool = False) -> dict:
    weight = number(body.get("weight"))
    if weight is None or weight <= 0:
        raise ValueError()
    keys = {
        "bmi": "bmi",
        "fat_percent": "bfp",
        "water_percent": "bwp",
        "muscle_mass_kg": "slm",
        "bone_mass_kg": "bmc",
        "protein_percent": "pm",
        "visceral_fat": "vfl",
        "bmr_kcal_day": "bmr",
        "metabolic_age_years": "ma",
    }
    fields = {key: number(body.get(source), key != "bmi") for key, source in keys.items()}
    name = body.get("bt")
    fields["body_type_name"] = str(name) if isinstance(name, (str, int)) and str(name) not in ("", "0") else None
    result = {
        "device_timestamp": measured,
        "weight_kg": weight,
        "heart_rate_bpm": number(body.get("heartRate"), True),
        "impedance_ohm": number(body.get("bodyRes"), True),
        "impedance_low_ohm": number(body.get("bodyRes2"), True),
        "body_composition": fields,
    }
    if include_raw:
        result["bruto_nuvem"] = json.loads(json.dumps(body), parse_constant=lambda _: None)
    return result


def date_range(from_date=None, to_date=None) -> tuple[date, date]:
    def parse(value, default):
        if value is None:
            return default
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError()
        return result

    try:
        start, end = parse(from_date, date.min), parse(to_date, date.max)
        if start > end:
            raise ValueError()
        return start, end
    except (ValueError, TypeError):
        raise InputError() from None


class XiaomiS400Client:
    def __init__(
        self,
        *,
        session_path: str | Path = DEFAULT_SESSION,
        region: str = "us",
        profile: str = "1",
        timezone: str = "America/Sao_Paulo",
    ):
        if region not in ("", "cn", "de", "us", "ru", "tw", "sg", "in", "i2"):
            raise InputError()
        if not isinstance(profile, (str, int)) or not str(profile).isdigit():
            raise InputError()
        try:
            self.timezone = ZoneInfo(timezone)
            self.session_path = Path(session_path).expanduser()
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise InputError() from None
        self.region, self.profile = region, str(profile)
        self._service = None
        self._lock = RLock()

    def _call(self, data: dict) -> dict:
        if self._service is None:
            self._service = ServiceSession(load_session(self.session_path), self.region)
        for attempt in range(2):
            try:
                result = validate_cloud_response(
                    self._service.call(HISTORY_PATH, {**data, "uid": self._service.user_id})
                )
                if not isinstance(result.get("result"), list):
                    raise ProtocolError()
                return result
            except AuthenticationError:
                self._service = None
                if attempt:
                    raise AuthenticationError() from None
                self._service = ServiceSession(load_session(self.session_path), self.region)
        raise AuthenticationError()

    def probe(self) -> dict:
        """Check remote authentication, even when a service session is cached."""
        with self._lock:
            self._call({"endTime": 1, "beginTime": int(time.time() * 1000), "model": MODEL, "did": 0, "accountId": 0})
        return {"ok": True, "authenticated": True, "error": None}

    def get_measurements(self, from_date=None, to_date=None, *, include_raw: bool = False) -> dict:
        """Return measurements and received/filtered/invalid counters, or raise.

        Dates are inclusive local calendar days; omission means all history.
        A failed or exhausted pagination never returns a partial history.
        """
        start, end = date_range(from_date, to_date)
        with self._lock:
            current = int(time.time() * 1000)
            measurements, seen = [], set()
            received = filtered = invalid = 0
            for _ in range(50):
                rows = self._call({"endTime": 1, "beginTime": current, "model": MODEL, "did": 0, "accountId": 0})[
                    "result"
                ]
                timestamps = []
                for row in rows:
                    key = json.dumps(row, sort_keys=True, separators=(",", ":"))
                    if key in seen:
                        continue
                    seen.add(key)
                    received += 1
                    try:
                        if not isinstance(row, dict):
                            raise ValueError()
                        measured = timestamp_ms(row.get("createTime"))
                        timestamps.append(measured)
                        body = json.loads(row.get("data") or "{}")
                        if not isinstance(body, dict):
                            raise ValueError()
                        if str(body.get("userType", "")) != self.profile:
                            filtered += 1
                            continue
                        item = normalize(body, measured, include_raw=include_raw)
                        day = datetime.fromtimestamp(measured / 1000, self.timezone).date()
                        if not start <= day <= end:
                            filtered += 1
                            continue
                        measurements.append(item)
                    except (ValueError, TypeError, OverflowError, OSError):
                        invalid += 1
                if len(rows) < 20:
                    break
                oldest = min(timestamps, default=0)
                if not oldest or oldest >= current:
                    raise PaginationError()
                current = oldest - 1
            else:
                raise PaginationError()
            measurements.sort(key=lambda item: item["device_timestamp"])
            return {
                "measurements": measurements,
                "received": received,
                "filtered": filtered,
                "invalid": invalid,
                "errors": ["invalid_records"] if invalid else [],
            }
