# PRSG-73 — Show the report's technical trend on ticker chips

Type: bug · Modules: frontend, market-research · Owner: Lead · Priority: P1 · Effort: XS (0.25–0.49 person-day) · Impact: high — the visible chip should answer the user's stated trend question using the report's established technical trend field.

Created 2026-10-07 MYT. This is a correction to the already accepted compact chip presentation after the user clarified that the arrow must mean trend.

## Objective

Render the compact sector emoji + ticker + arrow from each forecast's `moomoo_trend` field, which represents the established historical SMA-5/SMA-20 trend. The chip currently reads `moomoo_session_direction`, a last-price-versus-previous-close snapshot; that is not the historical trend the user asked to see.

## Accepted scope

- `artifacts/daily-market-brief/tradingview.js`
- `tests/daily_report_viewer_checks.cjs`
- This specification and its matching harness manifest.

Do not alter report data, collection, publication, validators, rights gates, forecast direction or provider behavior in this ticket.

## Observable behavior

- Available historical trend values render as sector emoji + ticker + ↑/↓/↔ for bullish/bearish/neutral.
- Missing, invalid or unavailable trend stays `?`; there is no fallback to same-session quote direction or forecast direction.
- Accessible label and hover detail identify the SMA-5/SMA-20 basis and last completed bar date when available.
- Keyboard selection and existing chip behavior remain intact.
- The public 2026-10-07 artifact contains no `moomoo_trend` values on its 50 forecast rows, so those chips correctly remain `?` pending a real supported data refresh. This ticket does not claim data collection or report publication.

## When it's considered done

- [x] PRSG-73-D1: Chip arrows use historical SMA-5/SMA-20 trend and ignore conflicting quote direction.
- [x] PRSG-73-D2: Missing/invalid trend remains unavailable and never borrows quote or forecast direction; accessible basis/date and interactions are retained.
- [x] PRSG-73-D3: Focused viewer regression, ticket validation and independent Lead review pass; data gaps are stated accurately.

## Delivery evidence

- `node tests/daily_report_viewer_checks.cjs` — passed. A deliberate conflict fixture (bearish session move, bullish historical SMA trend) renders `↑`; neutral, unsupported/missing signals, accessibility basis/date, keyboard navigation and selection are covered.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-07/PRSG-73.harness.json` with all four changed paths — passed; `git diff --check` — passed.
- Public `artifacts/daily-market-brief/2026-10-07.json` has 50 forecast rows and no `moomoo_trend` fields. The local OpenD endpoint is unavailable; no trend values were invented or added.
- Lead review accepted the exact four-path UI correction and regression evidence. This completes chip semantics only; the Oct 7 public chips remain `?` until genuine trend data is available and passes the existing publication path.
