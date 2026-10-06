# Delivery tasks

| Task | Deliverable | Requirements | Verification | Status |
| --- | --- | --- | --- | --- |
| T1 | Package and secure session storage | R1, R2 | Ruff, session unittest, wheel build | Complete |
| T2 | Xiaomi QR and shared measurement client | R2, R3 | Ruff, synthetic auth/pagination/normalization tests | Pending |
| T3 | CLI, MCP, and compatible HTTP | R4 | Ruff, adapter tests and SDK stdio integration | Pending |
| T4 | Documentation, CI, Docker, independent review | R1, R5 | Full unittest, build, clean install, Docker, review | Pending |
| T5 | GitHub release and installation from tag | R6 | CI status, public URLs, release assets, tag smoke | Pending |

Each task is committed separately after its gate. Gate commands: `python -m ruff check .`, `python -m unittest discover -s tests -v`, and (build gate) `python -m build`. Tests map to requirements in validation.md. No credentials or real health measurements are used.
