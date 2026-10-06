# xiaomi-s400

[![CI](https://github.com/jonathanmullerr/xiaomi-s400/actions/workflows/ci.yml/badge.svg)](https://github.com/jonathanmullerr/xiaomi-s400/actions/workflows/ci.yml)

Unofficial Python integration for the **Xiaomi Body Composition Scale S400** (`yunmai.scales.ms104`), using **Xiaomi Home** cloud history. Includes a Python library, QR login, CLI, read-only local MCP server, and a Health Harness compatible HTTP collector. MIT licensed; Python 3.12 or later.

Sync your scale measurements through the Xiaomi Home app first, using the same Xiaomi account and region. This package reads cloud history; it does not connect to the scale over Bluetooth. Mi Fitness, a database, and Garmin uploads are outside version 0.1.0. Xiaomi can change these undocumented endpoints. Automated verification uses synthetic data; **live Xiaomi QR login and scale collection have not been validated for this release**.

## Install

Install the released tag in an isolated environment:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install 'git+https://github.com/jonathanmullerr/xiaomi-s400.git@v0.1.0'
xiaomi-s400 --version
xiaomi-s400 --help
```

Git is required for GitHub installation. You can also install a wheel from [GitHub Releases](https://github.com/jonathanmullerr/xiaomi-s400/releases). No local checkout, vault, dashboard, or external token extractor is required at runtime.

## Log in

```bash
xiaomi-s400 login
xiaomi-s400 status
```

Open the displayed login URL, or open the QR image URL and scan it with Xiaomi Home. The CLI displays the expiration time; press Ctrl-C to cancel. Requests have a timeout of at most 30 seconds. QR URLs are displayed only during interactive login on stderr; credentials are never printed. Password login is not supported.

The session is saved atomically at `~/.config/xiaomi-s400/session.json`. Files use mode `0600` on POSIX. Treat the file as a credential. Keep sessions and exports outside the checkout. Windows users must protect the session with their filesystem's access controls.

To import an existing session:

```bash
xiaomi-s400 import-session /secure/location/cloud_session.json
```

Accepted JSON contains `userId` and either `passToken` or `pass_token`. Imported sessions are validated remotely by `status`, not by the import command. A rejected service session is discarded and renewed once using the stored passToken. Persistent rejection requires a new QR login.

## Region, profile, and timezone

Put global options **before** the subcommand:

```bash
xiaomi-s400 --region us --profile 1 --timezone America/Sao_Paulo status
xiaomi-s400 --session /secure/location/session.json --region de measurements --from 2026-10-01 --to 2026-10-06
```

| Setting | Default | Environment variable |
| --- | --- | --- |
| Session | `~/.config/xiaomi-s400/session.json` | `XIAOMI_S400_SESSION` |
| Xiaomi Home region | `us` | `XIAOMI_S400_REGION` |
| Scale profile (`userType`) | `1` | `XIAOMI_S400_USER_TYPE` |
| Calendar timezone | `America/Sao_Paulo` | `HEALTH_TIME_ZONE` |
| Model | `yunmai.scales.ms104` only | `XIAOMI_S400_MODEL` |

Regions: `cn`, `de`, `us`, `ru`, `tw`, `sg`, `in`, and `i2`; an empty region means `cn`. Use the region configured in Xiaomi Home. Profile selection compares the scale record's `userType`; it is not a device ID. Other profiles are filtered out. Unsupported model overrides are rejected.

## Export measurements

```bash
xiaomi-s400 measurements --from 2026-10-01 --to 2026-10-06
xiaomi-s400 measurements --output /secure/location/measurements.json
```

Omit either date to leave that end of the interval unbounded. Dates must be `YYYY-MM-DD`, and the interval must be ordered. Filtering includes both boundary days in the configured timezone. Successful commands return zero; failures return a nonzero code with a sanitized diagnostic on stderr. Measurements are JSON on stdout or in the selected file, without banners.

The result is an object with `measurements`, `received`, `filtered`, `invalid`, and `errors`. `received` counts distinct records examined before filtering; duplicates do not count twice. `filtered` counts other profiles and records outside the date interval. `invalid` counts malformed records and invalid weights; valid records still survive. `errors` contains `invalid_records` when any record is invalid.

Each normalized measurement has UTC `device_timestamp` in **milliseconds**, `weight_kg`, nullable `heart_rate_bpm`, nullable `impedance_ohm` and `impedance_low_ohm`, and `body_composition`. Composition fields are `bmi`, `fat_percent`, `water_percent`, `muscle_mass_kg`, `bone_mass_kg`, `protein_percent`, `visceral_fat`, `bmr_kcal_day`, `metabolic_age_years`, and `body_type_name`. Missing numeric values are `null`; non-finite or non-positive weights are invalid. Decimal impedance is preserved. No composition is calculated or guessed. Results are sorted from oldest to newest.

The history endpoint pages backward. This client allows at most 50 pages, deduplicates records, and detects a stalled cursor. Exceeding the page budget fails explicitly rather than returning incomplete history as complete. Date filters currently apply after fetching the history, so they do not bypass that safety limit.

## Python library

```python
from xiaomi_s400 import XiaomiS400Client
from xiaomi_s400.errors import S400Error

client = XiaomiS400Client(
    session_path="/secure/location/session.json",
    region="us",
    profile="1",
    timezone="America/Sao_Paulo",
)
try:
    print(client.probe())
    result = client.get_measurements("2026-10-01", "2026-10-06")
    for measurement in result["measurements"]:
        print(measurement["device_timestamp"], measurement["weight_kg"])
except S400Error as error:
    print(error.code, str(error))
```

`probe()` performs a remote authenticated request on every call. `get_measurements()` returns the same envelope as the CLI, and accepts ISO date strings or `datetime.date` values. Calls through a shared client are serialized. `AuthenticationError`, `NetworkError`, `ProtocolError`, `PaginationError`, and `InputError` derive from `S400Error`; messages contain no upstream payload or credential. QR expiration and cancellation have separate error codes.

Raw cloud data is excluded by default. Trusted library consumers can explicitly request `include_raw=True`, which adds `bruto_nuvem`; nonfinite numbers in that raw payload are serialized as `null`. CLI and MCP do not offer raw exports.

## MCP over stdio

Log in with the CLI first. Configure your MCP client with an absolute path to the installed executable:

```json
{
  "mcpServers": {
    "xiaomi-s400": {
      "command": "/absolute/path/to/.venv/bin/xiaomi-s400",
      "args": ["--region", "us", "--profile", "1", "mcp"]
    }
  }
}
```

Available read-only tools:

- `s400_status`: check remote authentication.
- `s400_get_measurements`: return normalized history with optional `from_date` and `to_date`.
- `s400_get_latest_measurement`: return `{ "measurement": ... }`, or `{ "measurement": null }` for empty history; accepts the same date filters.

Tools expose input/output schemas and read-only annotations through the official MCP Python SDK. They accept no credentials and cannot initiate login. stdout is reserved for the stdio protocol; diagnostics use stderr. Each tool shares the same serialized client. A request can take multiple upstream calls when fetching history; configure your MCP client's tool timeout accordingly.

## Compatible HTTP collector

```bash
xiaomi-s400 serve
xiaomi-s400 serve --host 127.0.0.1 --port 8080
curl http://127.0.0.1:8080/probe
curl http://127.0.0.1:8080/connect
curl 'http://127.0.0.1:8080/measurements?from=2026-10-01&to=2026-10-06'
```

The default listener is `127.0.0.1:8080`. This adapter is intended for localhost or a trusted private network; it has no HTTP authentication. Bind another host explicitly when needed.

| Route | Success response |
| --- | --- |
| `GET /probe` | `{ "ok": true, "authenticated": true, "error": null }`, after a remote authentication check |
| `GET /connect` | `{ "authenticated": true }`, after validating/renewing the existing session; no QR flow |
| `GET /measurements` | Measurement envelope described above, with `bruto_nuvem` on each measurement for compatibility |

Invalid dates, ranges, repeated parameters, empty parameters, and unknown measurement query parameters return HTTP 400 with `error: "invalid_input"`. Upstream failures return HTTP 502 with a fixed code such as `authentication_required`, `network_error`, `protocol_error`, or `pagination_error`. Error envelopes include `ok: false` and `authenticated: false`. Request URLs and raw responses are not logged.

The HTTP field names, route names, and envelopes match the Health Harness S400 bridge contract. Existing `XIAOMI_S400_*` settings and `HEALTH_TIME_ZONE` are supported as listed above. This extraction does **not** switch Health Harness to the new package. A future migration can replace its collector image/command and mount its session at the configured path; validate that change separately.

## Docker

Build locally and log in on the host before mounting the session:

```bash
docker build -t xiaomi-s400:0.1.0 .
docker run --rm -p 127.0.0.1:8080:8080 \
  -v "$HOME/.config/xiaomi-s400:/home/app/.config/xiaomi-s400:ro" \
  -e XIAOMI_S400_REGION=us -e XIAOMI_S400_USER_TYPE=1 \
  -e HEALTH_TIME_ZONE=America/Sao_Paulo \
  --user "$(id -u):$(id -g)" xiaomi-s400:0.1.0
```

The image defaults to an unprivileged user and `serve --host 0.0.0.0`. The example overrides the UID/GID so the process can read your host's `0600` session file, while keeping the mount read-only. The explicit session environment path in the image is independent of the host user. Do not publish the collector's port to the public internet. No registry image is published in this release.

## Development and verification

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m unittest discover -s tests -v
python -m build
```

All fixtures are synthetic. Tests cover QR states, session storage, renewal, wire encryption, pagination limits, profiles, invalid measurements, decimal impedance, timezone boundaries, CLI/HTTP, and discovery/calls through a real MCP stdio client. CI runs Python 3.12 and 3.13 plus a Docker build and test. See [.specs/features/v1/validation.md](.specs/features/v1/validation.md) for evidence and pending live checks, and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for the QR source revision and MIT notice.
