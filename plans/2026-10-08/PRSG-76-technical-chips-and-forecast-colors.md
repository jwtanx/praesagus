# PRSG-76 — Show available trend symbols and color forecast direction

Type: feature · Modules: frontend, market-research · Owner: Trader · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium-high — trend basis is visible in the selected report, and archived forecast ranges remain accessible without being presented as current.

Created 2026-10-08 MYT.

## Objective

Use the selected report's available evidence to render directional symbols and red/green/yellow forecast styling in the daily brief and Technical analysis ticker chips. Make the existing 2026-09-30 forecast-range archive easy to open from newer reports.

## Accepted scope

- `artifacts/daily-market-brief/index.html`
- `artifacts/daily-market-brief/tradingview.js`
- `tests/daily_report_viewer_checks.cjs`
- This specification and its matching harness manifest.

Do not change stored historical forecasts, invent technical values, or carry an old forecast range forward as a current prediction.

## Observable behavior

- Technical chips prefer historical SMA trend, then timestamped quote direction, then the selected report's saved forecast direction. Their accessible title names the basis and available timestamp. When none exists, the chip shows an em dash.
- Forecast direction appears as green ↑ for bullish, red ↓ for bearish, and yellow ↔ for sideways.
- Newer report views link to the preserved 2026-09-30 report with its saved price ranges and explicitly identify those estimates as historical.

## When it's considered done

- [x] PRSG-76-D1: Chip arrows and colors follow the first available trend evidence in the documented priority, while missing data remains explicit.
- [x] PRSG-76-D2: Forecast rows use green, red, and yellow direction styling; saved 2026-09-30 ranges are reachable and clearly historical.
- [ ] PRSG-76-D3: Viewer regression, both report validations, scope validation, diff review, and independent Lead review pass.

## Delivery evidence

- `node tests/daily_report_viewer_checks.cjs` — passed, including rendering the actual archived AAPL range and saved-forecast arrow from 2026-09-30.
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-07 --public` — passed; the report was not changed by this ticket.
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-09-30` — passed; the archived report and its estimates were not changed.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-08/PRSG-76.harness.json` with all five changed paths — passed; `git diff --check` — passed.
- Independent Lead review remains pending.
