# PRSG-59 — Stable acceptance regressions

Type: bug · Modules: harness · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: medium; removes CI failures caused by unrelated ticket lifecycle changes. Created 2026-10-05 MYT.

## Accepted frozen scope

Lead accepted base `72160e2222cb7bad18125d7649a159b60a0c2e8b` and only `tests/test_ticket_harness.py`, this spec, and `PRSG-59.harness.json`. Validator, application code, PRSG-1 plans and all other paths are protected. Existing PRSG-1 metadata edits are disjoint pre-existing work. No commit/push authorized.

## Reproduction and expected behavior

`test_checklist_sync` assigns D1 done regardless of its current state, so it stops constructing a mismatch when PRSG-1 D1 is already done. `test_complete_needs_evidence_and_review` changes only ticket status, so it stops rejecting after PRSG-1 acceptance. Construct controlled synthetic spec/manifest pairs for both pending/done checklist mismatch directions and a complete ticket with explicitly pending review. Preserve validator checks, real acceptance evidence and assertions; no skips.

## Checks and delivery

Demonstrate current mismatch failure and future-complete fixture failure before changes. Run supported Python 3.11 focused `python3 -m pytest -q tests/test_ticket_harness.py`, metadata scope validation and diff check after changes. Lead independently reviews scope/evidence; full hook/CI remains integration evidence.

## When it's considered done

- [x] PRSG-59-D1: Before/after evidence and controlled pending/done mismatch plus incomplete-review regressions pass.
- [x] PRSG-59-D2: Lead reviews three-path scope and accepts integration.

## Engineer delivery — 2026-10-05 MYT

2026-10-05 MYT supported Python3.11.17: before correction python3 -m pytest -q tests/test_ticket_harness.py at root failed1/passed56 in0.09s: checklist mismatch DID NOT RAISE with PRSG-1 D1 already done. External temporary fully accepted spec/manifest probe validated PRSG-1 then original completion test failed DID NOT RAISE. After correction same focused command58passed0.09s; repeated after authorized PRSG-1 final acceptance58passed0.09s. Controlled valid fixtures assert validator acceptance first, explicitly set review pending for complete rejection, and invert pending/done status against matching temporary Markdown for both mismatch directions. Live PRSG-1 evidence not altered by tests; validator unchanged.

Scope/metadata validation and diff check pass. Ticket-owned changes are the frozen three PRSG-59 paths and two disjoint authorized PRSG-1 metadata paths. Concurrent daily-market-brief reports.json and new 2026-10-05 report/evidence paths appeared during final validation; preserved untouched and excluded from this handoff. PRSG-59 D2/Lead review pending; no full-suite rerun, CI claim, commit or push. The helper keeps a valid controlled acceptance/spec fixture independent of live ticket status; the remaining live-manifest tests still validate real metadata.

## Lead acceptance — 2026-10-05 MYT

2026-10-05 MYT Lead acceptance: independently reviewed all three PRSG-59 owned paths, unchanged validator and controlled valid-fixture rejection cases. Independent focused python3 -m pytest -q tests/test_ticket_harness.py: 58 passed in 0.08s. D2 accepted; Lead will integrate PRSG-59 then PRSG-1 separately. No Engineer commit/push; full hook/remote CI remain integration evidence.
