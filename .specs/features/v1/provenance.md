# Provenance

Reference: Health Harness `services/xiaomi-s400-collector/collector.py` at commit `ee9b02ee0f2022c4324f7ad1fef4e3568b2e6e89`, with the working-tree version as the extraction reference. The working tree differs in three lines: raw upstream errors and exception text were replaced with fixed sanitized diagnostics. This package preserves that sanitization and adds validated session storage, QR authentication, bounded service renewal, date validation, record accounting, and explicit pagination failure.

Only the S400 collector was used; no other integration, repository history, database, session, or measurement was copied. The RC4 call and normalized fields retain Xiaomi Home semantics and model `yunmai.scales.ms104`. QR provenance and the upstream MIT notice are in THIRD-PARTY-NOTICES.md.
