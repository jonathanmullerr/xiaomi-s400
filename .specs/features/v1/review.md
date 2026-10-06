# Independent pre-publication review

Date: 2026-10-06. Verifier: independent sub-agent, not the implementation author. Scope: new package, synthetic tests, CI, Dockerfile, notices, README, and R1–R5 in spec.md. R6 publication is deliberately outside this review.

**Final verdict: PASS for R1–R5 after independent re-verification of fix commit `41a39f6`.** Initial findings F1/F2 below are retained as resolved historical evidence. R6 release publication and live Xiaomi validation remain pending. No production code or test was modified by the verifier. Scratch mutations were discarded.

## Gates and task completion

Independently executed: Ruff check PASS, Ruff format check PASS (21 files), unittest PASS (19 methods, no skipped methods), and isolated wheel/sdist build PASS on Python 3.12. This is a new project, so the pre-feature baseline is zero tests, now 19. Package inventories contain no session filenames, environment files, private paths, virtual environments, or personal absolute paths; both license notices are included in the wheel.

T1–T3 are marked complete; T4 is pending final validation/review; T5 is pending publication. The implementer separately reports 19 passing tests on Python 3.13, clean wheel installation outside the checkout with all 19 tests, Docker build and all 19 synthetic tests, and Docker HTTP 502 missing-session/400 invalid-date checks. Those latter checks were reported by the implementer, not rerun by this verifier. Live Xiaomi QR/login/history validation remains explicitly pending in README.

## Historical pre-fix spec-anchored evidence

| Requirement / outcome | Concrete evidence | Result |
| --- | --- | --- |
| R1 standalone package / license / provenance | pyproject.toml declares Python >=3.12, install entrypoint and ordinary dependencies; isolated build produces both distributions. THIRD-PARTY-NOTICES.md pins upstream revision and includes complete MIT notice; provenance.md identifies selected collector and differences. Wheel/sdist inspection found zero private-path hits. | PASS by build/inspection |
| R2 import both token spellings, 0600 atomic session | tests/test_session.py:17 `assertEqual(load_session(path), {userId: 123, passToken: synthetic-token})`; :19 permission equals 0600; :20 directory has only destination. | PASS |
| R2 missing/malformed session, sanitized diagnostics | tests/test_session.py:25/:29 AuthenticationError; :31 `assertNotIn(synthetic-secret, str(caught.exception))`. | PASS |
| R2 QR success, expiry and cancellation | tests/test_auth.py:35 exact credentials; :36 exact URLs and expiry; :40 LoginCancelled; :53 LoginExpired; :71 retry after poll timeout. | PASS |
| R2 one refresh then login required | tests/test_client.py:130 AuthenticationError on persistent rejection, :132 cached service is None, :134 exact probe success, :135–137 factory/old/new each called once. | PASS |
| R2 sanitized protocol classification for malformed upstream code | Existing tests/test_client.py:105 covers integer error code, missing code and invalid result only. Synthetic `code: []` raises uncaught TypeError. | FAIL F1 |
| R3 finite positive weight, decimal impedance and null composition | tests/test_client.py:28–33 weight=70.25, impedances=457.5/458.75 and null optional values; :36 invalid weight raises. | PASS |
| R3 malformed records preserve valid peers/profile | tests/test_client.py:72–75 exact received=8, invalid=5, filtered=1, surviving weights=[70.25,72]; :79 selected profile timestamp. | PASS |
| R3 dates, milliseconds and timezone boundary | tests/test_client.py:40–41 exact seconds/milliseconds conversion; :45 exact local-day timestamp; :46 filtered=1; :51 invalid interval raises; :53 no extra remote call. | PASS |
| R3 pagination, endpoint/model, dedup, 50-page limit | tests/test_client.py:86–90 exact 21 survivors/received, cursor 1699999980999, endpoint and model; :94/:98 PaginationError; :100 exactly 50 calls. | PASS |
| R4 serialization of shared session | tests/test_client.py:165 maximum concurrent remote calls equals 1; :166 exactly four calls; :167–168 both API outcomes. Lock-removal mutation killed in 10/10 repeats. | PASS |
| R4 CLI JSON, file, error exit and no credential output | tests/test_adapters.py:53–56 success=0/exact JSON/empty stderr/no raw; :61–62 exact file JSON; :67–68 imported session/no synthetic token; :73–75 failure=1/empty stdout/auth code. | PASS |
| R4 HTTP contract/probe/connect/input/upstream errors | tests/test_adapters.py:90–95 200/authenticated, two probes, exact envelope, raw opt-in; :106–107 invalid request=400/invalid_input; :113–116 upstream=502/false authenticated/exact error code. | PASS except F2 |
| R4 raw HTTP optional nonfinite measurements remain readable | Existing HTTP tests use a mocked already-normalized envelope. Actual client normalizes NaN optional bfp to null but retains NaN in raw payload, causing strict HTTP serializer to reject entire valid history. | FAIL F2 |
| R4 MCP SDK schemas/discovery/read-only/stdout | tests/test_mcp.py:17 exact three tools; :22–26 annotations/input/output/no token input; :29 status; :32–37 exact weight, no raw, decimal/latest and empty=null; :53–55 actual CLI stdio auth error without path. | PASS |
| R5 CI / docs / clean installation / Docker | CI contains Python 3.12/3.13 Ruff/unittest/build/clean wheel and Docker jobs. README covers every public entrypoint, limits and pending live checks. Gates above plus implementer-reported clean install/Docker evidence. | PASS evidence, final release CI still pending |

Every test method maps to R2, R3, or R4; packaging/build/CI/docs map to R1/R5. No unrelated features or extra abstractions found. No human interactive UAT is required for this backend package; actual Xiaomi validation is explicitly pending.

## Discrimination sensor

All changes ran in temporary copies with the synthetic tests and no real credentials/network calls. Bytecode caches were removed when necessary to avoid same-second timestamp reuse; final outcomes below reflect the real mutated source.

| Mutation | Assertion killing it | Outcome |
| --- | --- | --- |
| Allow zero/negative weights | tests/test_client.py:36 raises ValueError; :73 invalid=5 | KILLED (three failures) |
| Remove both shared client locks | tests/test_client.py:165 maximum=1, observed=4 | KILLED in 10/10 runs |
| Stop converting seconds into milliseconds | tests/test_client.py:40 timestamp equals 1700000000000 | KILLED |
| Disable the second auth attempt | tests/test_client.py:134 exact successful probe after renewal | KILLED |
| Reduce budget to 49 pages | tests/test_client.py:100 call_count=50, observed=49 | KILLED |

Five distinct mutations killed. The concurrency test empirically discriminates; its bounded Event coordination exercises both probe and history. No surviving mutant remains.

## Historical ranked fix tasks — both resolved below

### F1 — Major: validate upstream error code before set membership

Root cause: client.py:119 and auth.py:203/:212 use an unvalidated `code` as a set member. A legal JSON object with `code: []` or `code: {}` triggers TypeError instead of ProtocolError; CLI does not catch TypeError and exposes a traceback. Reproduced independently with a synthetic service result `{code: [], result: []}` calling probe.

Fix the shared upstream validation/classification boundary, including plaintext and encrypted service responses and client result validation. Verify malformed nonhashable codes raise sanitized ProtocolError through the library and produce nonzero, traceback-free CLI diagnostics. HTTP/MCP should retain sanitized upstream errors. Do not only mask the symptom in CLI.

### F2 — Major: raw payload must be JSON-safe without discarding valid measurements

Root cause: client.py:63 returns the original raw dict, while http.py:14 uses `allow_nan=False`. A synthetic valid weight 70.25 with optional `bfp: NaN` returns one valid measurement and normalized `fat_percent: None`, but HTTP serialization raises ValueError and becomes 502. The invalid optional value must not hide valid peers or turn a complete collection into an upstream failure.

Make opt-in raw values JSON-safe (nonfinite numbers become null, preserving field names). Verify an actual-client HTTP integration response stays 200 with weight 70.25, normalized fat=null, raw fat=null and valid-peer preservation. Include positive/negative infinity and nested raw values if accepted. Existing default library/CLI/MCP normalization must remain unchanged.

## Re-verification and limits

After F1/F2 are implemented, rerun focused regressions, full Ruff/unittest/build and package privacy checks, then update this independent verdict. The parent owns validation.md and release evidence. No lesson helper is present in this new project; these two grounded rules are persisted here: validate upstream discriminants before membership operations, and ensure raw exports cannot defeat normalized-record survivability.

## Independent re-verification — 2026-10-06

Reviewed fix commit `41a39f641e36fe4ddd618b753ffb2d49611c62d7` and new tests/test_regressions.py. No production or tests changed by verifier. Shared `validate_cloud_response` checks exact integer type before membership (rejecting boolean codes too), is reused by the client and plaintext/encrypted service paths, and preserves AuthenticationError for recognized auth rejection. Raw JSON roundtrip converts nonfinite constants recursively to null while preserving ordinary field values.

- **F1 RESOLVED:** tests/test_regressions.py:23 requires ProtocolError for list/dict/string/null/bool upstream codes; :25 asserts no synthetic secret; :47 covers plaintext malformed cloud codes through ServiceSession. Independent actual-client CLI check returned code=1, empty stdout, protocol_error stderr, no traceback and no secret. Existing renewal/auth-wire tests remain green.
- **F2 RESOLVED:** tests/test_regressions.py:59 requires raw NaN=null; :60 nested positive/negative infinity=null; :72 actual-client HTTP status=200; :74 invalid=0; :75 one surviving measurement; :77 weight=70.25; :78 normalized fat=null; :79 raw fat=null; :80 nested raw values=null. This traverses the real normalizer, shared client and HTTP serializer rather than mocking a pre-normalized envelope.
- **Repeated gates:** Ruff check PASS; format check PASS (24 files); full unittest PASS (21 methods, zero failures/skips); isolated wheel/sdist build PASS. No tests removed or assertions weakened; two regression methods added.
- **Additional scratch sensors:** removing the integer code guard was KILLED by three errors and one failure in the malformed-code regression; reverting raw sanitization to the original body was KILLED by the raw-null assertion. Temporary copies discarded, bytecode disabled/caches removed. Total independent sensor: seven distinct mutations killed; zero survivors. Previous lock mutation remained killed in all ten runs.

No unresolved ranked correctness gaps remain in the reviewed synthetic scope. Parent reports the repeated Python 3.13, clean-wheel and Docker gates on the fixed tree are complete with all 21 tests passing; those implementer-run evidence updates belong in validation.md. Live Xiaomi behavior is not claimed verified; README already states that limitation. Public CI, tag/release and installation from the tag are R6 follow-up gates, not pre-publication review failures.
