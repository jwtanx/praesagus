# PRSG-29 Consistent Pages branding and sticky navigation

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: S (0.5–2 person-days, estimate) · Impact: medium

## Why the ticket is created?

Human requested this to make the static research site easier to navigate and understand.

## Approach

Use the existing daily-market-brief favicon on landing and tickets pages; match landing PRAESAGUS brand dimensions/weight to the daily brief; make tickets navigation sticky with mobile-safe wrapping and no hidden content.

## Options and tradeoffs

Reuse existing static assets and hosted widgets rather than add a build system or ingest chart prices. External charts require third-party connectivity and may be delayed; vendor coverage is not guaranteed. No backend/credential changes.

## Findings and references

Existing Pages serves artifacts directly. TradingView research established historical date selection selects a watchlist, not a frozen historical chart. References: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/ and https://www.tradingview.com/widget-docs/tutorials/iframe/build-page/dynamic-symbols/

## Frozen scope and validation

Base: 775e8a151a620644caa0d21dae765072069f4f24. Only manifest allowed_paths may change. Preserve unrelated .DS_Store and other ticket edits. All three Pages entry points resolve the same favicon; landing brand matches daily brief CSS; tickets header sticks at top without mobile overflow; existing ticket functionality remains intact.

## When it's considered done

- [x] PRSG-29-D1: Implement behavior with deterministic regressions and independent Lead review.

## Progress

Accepted for implementation. No test or deployment claimed yet.

## Lead acceptance

Lead independently inspected implementation and reran node tests/tradingview_checks.cjs (including existing viewer replay), node tests/pages_branding_checks.cjs and node tests/ticket_dashboard_checks.cjs: all passed. PRSG29 independent review identified skip stacking and anchor offsets; fixed single final skip rule z30 and measured ResizeObserver offset, regressions pass. PRSG30 external scripts mocked; live rendering/entitlements and visual browser QA not verified. No credentials/private data/backend changed.

