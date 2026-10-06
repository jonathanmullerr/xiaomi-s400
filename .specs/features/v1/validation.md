# Validation evidence

## Deterministic gates

- Python 3.12.12 and 3.13.11: 21 unittest methods passed, no skipped tests.
- Ruff lint and formatting: passed.
- Isolated wheel/sdist builds: passed; third-party license included in both.
- Clean wheel installation outside the checkout: all 21 tests and CLI help passed, including MCP stdio discovery/calls.
- Docker build and unprivileged synthetic suite: all 21 tests passed. Default HTTP startup returned sanitized 502 for a missing session and 400 for invalid dates.
- Distribution privacy scan: no personal filesystem paths or session files.

## Test coverage matrix

Every test maps to an explicit version 1 requirement. Each row records a concrete assertion; additional assertions in the same test cover its listed edge cases.

| Requirement | Test evidence | Assertion |
| --- | --- | --- |

| R4 | `tests/test_adapters.py:53` — test_cli_json_stdout_file_exit_codes_and_login | `self.assertEqual(code, 0)` |

| R4 | `tests/test_adapters.py:90` — test_http_contract_validation_and_errors | `self.assertEqual(response.status, 200)` |

| R4 | `tests/test_adapters.py:137` — test_legacy_environment_defaults | `self.assertEqual(                     factory.call_args.kwargs,                     {"session_path": "/synthetic/session.json", "region": "de", "profile": "2", "timezone": "UTC"},                 )` |

| R2, R3 | `tests/test_auth.py:35` — test_qr_completion_expiration_and_cancellation | `self.assertEqual(qr_login(http=http, show=show), {"userId": "123", "passToken": "synthetic"})` |

| R2, R3 | `tests/test_auth.py:71` — test_poll_timeout_retry_rejection_and_sanitization | `self.assertEqual(qr_login(http=http, show=Mock())["userId"], "123")` |

| R2, R3 | `tests/test_auth.py:99` — test_service_auth_cookie_and_timeout | `self.assertEqual(service.user_id, "123")` |

| R2, R3 | `tests/test_auth.py:145` — test_encrypted_wire_request_response_and_protocol_errors | `self.assertEqual(                 service.call("/eco/common/scale/getUserDataByPage", {"model": "yunmai.scales.ms104"}), upstream             )` |

| R2, R3, R4 | `tests/test_client.py:28` — test_normalization_precision_missing_and_finite | `self.assertEqual(item["weight_kg"], 70.25)` |

| R2, R3, R4 | `tests/test_client.py:40` — test_timestamps_and_local_day_boundaries | `self.assertEqual(timestamp_ms(1700000000), 1700000000000)` |

| R2, R3, R4 | `tests/test_client.py:56` — test_empty_history_and_profile_invalid_records_raw_opt_in | `self.assertEqual(self.client([[]]).get_measurements()["measurements"], [])` |

| R2, R3, R4 | `tests/test_client.py:86` — test_multiple_pages_dedup_and_cursor | `self.assertEqual(len(data["measurements"]), 21)` |

| R2, R3, R4 | `tests/test_client.py:94` — test_stalled_cursor_and_limit_fail_not_partial | `self.assertRaises(PaginationError)` |

| R2, R3, R4 | `tests/test_client.py:107` — test_invalid_upstream_protocol_and_configuration | `self.assertRaises(ProtocolError)` |

| R2, R3, R4 | `tests/test_client.py:130` — test_remote_probe_refresh_once_and_persistent_rejection | `self.assertRaises(AuthenticationError)` |

| R2, R3, R4 | `tests/test_client.py:162` — test_shared_client_access_is_serialized | `self.assertTrue(entered.wait(2))` |

| R4, R5 | `tests/test_mcp.py:17` — test_sdk_stdio_discovery_calls_schema_annotations_and_no_raw | `self.assertEqual(                     {t.name for t in listing.tools},                     {"s400_status", "s400_get_measurements", "s400_get_latest_measurement"},                 )` |

| R4, R5 | `tests/test_mcp.py:53` — test_actual_cli_mcp_without_session_has_sanitized_error | `self.assertTrue(result.isError)` |

| R2 | `tests/test_session.py:17` — test_import_formats_and_private_atomic_storage | `self.assertEqual(load_session(path), {"userId": "123", "passToken": "synthetic-token"})` |

| R2 | `tests/test_session.py:25` — test_missing_malformed_and_sanitized_session | `self.assertRaises(AuthenticationError)` |


| R2, R3 | `tests/test_regressions.py:23` — malformed code | `self.assertRaises(ProtocolError)` for list/dict/string/null/bool code values |
| R3, R4 | `tests/test_regressions.py:80` — finite HTTP raw payload | `self.assertEqual(item["bruto_nuvem"]["nested"], [None, {"value": None}])` |

## Independent review

Independent review: PASS after correcting malformed upstream codes and nonfinite raw exports. Seven behavior mutations killed, zero survivors. See [review.md](review.md) for coverage evidence and corrected findings.


## Pending evidence

- Real Xiaomi QR authentication and real S400 retrieval have not been performed. No live personal sessions, measurements, database, or collector credentials were accessed by tests.
## Publication evidence (R6)

- Public MIT repository: https://github.com/jonathanmullerr/xiaomi-s400 (created after checking the name did not exist, using the intended owner credential).
- Green release-source CI: https://github.com/jonathanmullerr/xiaomi-s400/actions/runs/37542028798 — Python 3.12, Python 3.13, Docker, and clean-wheel gates succeeded.
- Published tag `v0.1.0` resolves to source commit `9e42578ad7e3528cfd867bcdf739e5c3ef188d91`.
- Release: https://github.com/jonathanmullerr/xiaomi-s400/releases/tag/v0.1.0 — wheel and source distribution available. Anonymous downloads were verified against the local build using SHA-256.
- Fresh environment installation from `git+https://github.com/jonathanmullerr/xiaomi-s400.git@v0.1.0` succeeded outside the checkout. Console `--version` returned `0.1.0`, `--help` succeeded, two real SDK stdio tests and three CLI/HTTP adapter smoke tests passed.
- Tracked files, all seven pre-publication commits, wheel, and sdist were scanned for session filenames, personal paths, and credential patterns; no private artifact was found.
- No Health Harness file, personal database, or real Xiaomi credential was modified or used. GitHub's previously active account was restored after delivery.

The sole remaining validation limitation is real Xiaomi QR login and real scale history, which were not exercised.
