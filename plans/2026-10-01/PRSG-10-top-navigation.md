# PRSG-10 — Top report navigation

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-days) · Impact: medium

## Scope and value

Move existing sticky main navigation before the report header so users see it immediately, rather than below the summary cards. Preserve existing mobile menu, date picker, financial calendar and ticker navigation. Impact is improved discoverability; no measured adoption claim. No new backend or report-data changes.

## Delivery contract

Accepted base: `427f1d746ca5bc92785dd1d0d3533b6bf2a4bcd7`. Exact four-file scope in sibling manifest. Lead handles this small coupled edit directly. Preserve pending PRSG-9 and user .DS_Store edits. Add DOM-order regression and replay existing desktop/mobile interactions. Review sticky CSS and layout; browser visual evidence remains required before claiming actual rendering checked.

## When it's considered done

- [x] PRSG-10-D1: Navigation precedes header; date/view navigation regressions pass; Lead reviews layout and scope.

## Validation and review

2026-10-01 MYT: node tests/daily_report_viewer_checks.cjs passed existing desktop/mobile date/calendar/error/safety cases plus topbar-first/sticky DOM regression.

Lead reviewed exact four-file scope. Engineer read-only actual local browser QA:1280x720 topbar y0/header y63.25, sticky after720px scroll;390x844 topbar y0 after2874px scroll, menu calendar/tickers work and close,50 rows, popup x17–317, Sep30/Oct1 date transitions work, widths1280/1280 and390/390. Remote deployment/other engines not checked. Pending PRSG-9 and .DS_Store untouched.
