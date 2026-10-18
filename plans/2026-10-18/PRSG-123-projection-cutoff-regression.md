# PRSG-123 — Preserve Projection Cutoff Validation

Type: bug · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: high — retain decision-time integrity when finalizing pending changes.

## Why the ticket is created?

The human requested committing all pending project work and continuing forecasts. An existing uncommitted projection edit replaces the exact template/cutoff guard with a date-only comparison. Reproduction: tests/test_daily_report_projection.py::test_reject_inconsistent_input[cutoff] fails (191 other focused checks pass). Expected: incompatible decision-time cutoffs fail, including a future template on the same MYT date; projection must not make stale narratives/forecasts current by rewriting metadata.

## Approach

Reproduce the failing mismatch check, restore the parsed cutoff/date invariant and add same-day past/future rejection plus equivalent-timezone preservation checks. Review both owned files independently before committing.

## Choices

Keep the existing decision-time contract. Reject automatic metadata rollover: a new report edition requires its own reviewed template, not relabelled old or future content.

## Findings

The date-only edit admitted mismatched instants on the same MYT day. The repair rejects them before store selection, leaves inputs unchanged and accepts equivalent timezone representations of the same instant; 59 focused checks pass.

## Tradeoffs

Strict projection cannot recycle an older template at a later cutoff. The separate report-authoring/preparation workflow must provide a current reviewed template; source and forecast claims remain frozen.

## Frozen scope

Base c010988b1ceea7b8178732d9354c6a1f9f5174aa. Engineer owns only ingest/daily_report_projection.py and tests/test_daily_report_projection.py in the existing review checkout. Lead owns these two ticket records. The accepted starting input includes the pre-existing projection diff, archived privately before repair. Retain the smallest compatible part of that edit; preserve the existing rejection contract and tests. If rolling a prior template conflicts with that contract, document the rejected part rather than silently weakening validation. No forecast model/provider/report/calendar changes, no network or credentials. News integration, planning notes, viewer checks and OS metadata are protected.

## When it's considered done

- [x] PRSG-123-D1: Strict cutoff rejection and focused past/future template regressions pass without weakening existing checks.
- [x] PRSG-123-D2: Lead independently reviews exact source/tests, preserves unrelated work and delivers through mandatory hooks.

## Reviewed evidence

Engineer reproduced the pre-existing mismatch failure before repair, retained the original rejection test and added same-day past/future rejection before store selection plus equivalent-timezone/input immutability coverage. Existing date-only/metadata-rollover edit was rejected; its original patch is retained privately. Final source preserves the original strict parsed-time/MYT-date contract with an explanatory comment. Lead independently reviewed both exact files/hashes and ran59focused checks (0.54s); no provider or model work. Full clean-checkout commit/push hooks remain mandatory for delivery.

The first full commit gate caught missing decision-context sections in this new brief (1failed/2894passed). Those sections were completed; the quality gate was preserved and rerun before delivery.
