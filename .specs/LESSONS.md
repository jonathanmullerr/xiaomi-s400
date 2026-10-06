# LESSONS — auto-maintained by .cursor/skills/tlc-spec-driven/scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation — do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 — Validate the type of upstream discriminants before membership checks so malformed JSON produces sanitized protocol errors.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `upstream` · harmful: 0
- features: v1
- evidence: tests/test_regressions.py:23 (upstream)
- last seen: 2026-10-06T22:38:36Z

### L-002 — Sanitize nonfinite raw values before strict JSON export so optional raw fields cannot discard valid normalized measurements.
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `exports` · harmful: 0
- features: v1
- evidence: tests/test_regressions.py:80 (exports)
- last seen: 2026-10-06T22:38:36Z

## Quarantined (failed when applied — ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
