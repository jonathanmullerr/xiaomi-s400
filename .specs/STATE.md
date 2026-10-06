# State

## Decisions

- AD-001: Xiaomi Home only; no Mi Fitness, BLE, database, or Garmin integration.
- AD-002: Shared client behind CLI, read-only MCP, and compatible HTTP. Synthetic tests only.
- AD-003: Public MIT release v0.1.0 is authorized. Health Harness remains unchanged.

## Handoff

T1–T5 complete. Public MIT repository and v0.1.0 release published. CI passed; 21 synthetic tests pass on Python 3.12/3.13, clean wheel, and Docker. Independent review passed with seven killed mutations. Installation from the public tag and CLI/HTTP/MCP smoke passed outside the checkout. Live Xiaomi QR authentication and real S400 collection remain unverified. Health Harness was not modified.
