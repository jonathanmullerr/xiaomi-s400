# Version 0.1.0 specification

R1: Standalone Python 3.12+ installable package, MIT license, pinned third-party QR provenance, no runtime code downloads or personal paths/data.

R2: QR login with expiration and cancellation; atomic POSIX 0600 session outside checkout; import userId with passToken or pass_token; sanitized auth/network/protocol/input errors. Remote rejection invalidates service state and retries once using passToken, then requires login.

R3: Xiaomi Home scale endpoint and ms104 model, configurable region/profile/timezone (defaults us/1/America/Sao_Paulo); 30-second call timeout; maximum 50 pages; deduplication; stalled cursor and exhausted page budget fail explicitly. Valid date ranges, UTC millisecond timestamps, local-day filtering; invalid records counted, finite positive weight, decimal impedance, missing values null.

R4: Library probe/get_measurements; CLI login/import-session/status/measurements/mcp/serve; JSON stdout/file exports and stderr diagnostics; read-only SDK MCP tools s400_status/s400_get_measurements/s400_get_latest_measurement over stdio; no raw payload by default. HTTP /probe remotely checks auth, /connect renews existing auth, /measurements preserves fields and envelope plus bruto_nuvem; 400 input and 502 sanitized upstream errors. Shared client access serialized. HTTP default 127.0.0.1:8080, explicit Docker host, legacy environment variables.

R5: Synthetic unittest coverage for auth states, renewal, pagination, malformed records, numeric/date boundaries, all adapters and real SDK stdio client; Ruff and package build in CI Python 3.12/3.13; clean wheel installation and Docker smoke checks. English usage and limitations docs, independent review, explicit pending real Xiaomi validation.

R6: New atomic Conventional Commits; public jonathanmullerr/xiaomi-s400 with green CI, tag/release v0.1.0 containing wheel/sdist, installation from published tag verified. Never overwrite an existing repository.
