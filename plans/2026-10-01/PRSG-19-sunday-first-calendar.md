# PRSG-19 — Sunday-first financial calendar

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.05–0.15 days) · Impact: low

## Accepted scope

Place Sunday first and Saturday last, with Monday–Friday in the five middle columns. Change weekday labels and matching first-date offset only; preserve calendar data, click selection and today highlight. Existing date picker is already Sunday-first. Exact scope/base in sibling manifest. Lead implements locally; separate ticket commit.

## When it's considered done

- [x] PRSG-19-D1: Sunday-first labels and date offsets pass desktop/mobile DOM regression and Lead review.

2026-10-01 MYT: node tests/daily_report_viewer_checks.cjs passed desktop/mobile replay with Sun–Sat labels and October1 Thursday offset4; git diff --check passed. Lead reviewed four-file scope, data unchanged. Actual browser visual QA and remote deployment not verified.
