# PRSG-72 — Compact ticker trend chips

Type: bug · Modules: frontend, market-research · Owner: Engineer · Priority: P1 · Effort: XS (0.25–0.49 person-day) · Impact: medium — ticker chips become easier to scan while retaining the same signal meaning.

Created 2026-10-07 MYT. User accepted the visual scope.

## Objective

Replace the visible words on ticker trend chips with the sector emoji, ticker and a direction arrow. Use the existing per-quote signal only: up `↑`, down `↓`, sideways `↔`. Keep a visible `?` when the report has no valid signal. Do not derive the chip from forecast direction or historical SMA, and do not change data sources, public-data projection, report data or rights checks.

The current public 7 October report omits Moomoo direction fields, so its chips must remain visibly unavailable (`?`) until the report contains an authorized supported signal. This ticket changes presentation only; it does not make that report's data available or claim that unavailable means sideways.

## Accepted scope

- `artifacts/daily-market-brief/tradingview.js`
- `tests/daily_report_viewer_checks.cjs`
- This specification and its matching harness manifest.

Protected paths include the dated 7 October report, reports index, signal projection/validator, provider connectors, forecast fields and all unrelated worktree changes.

## Observable behavior

- Available quote directions render a compact chip containing the forecast's sector emoji, ticker and one arrow. No visible `Bullish`, `Bearish`, `Neutral`, `Up`, `Down` or `Flat` word is added to the chip.
- The arrow maps only the existing quote-direction signal: bullish/up to `↑`, bearish/down to `↓`, neutral/sideways to `↔`.
- Missing, invalid or unsupported signals render the sector emoji, ticker and `?`; they never borrow forecast or SMA direction.
- Accessible name and hover title retain the signal basis, use Up/Down/Sideways (or Unavailable) instead of Bullish/Bearish/Neutral, and preserve eligible source/retrieval times, reason, and separate forecast status.
- Existing ticker selection, keyboard navigation, visual status colors, and ticker/chart behavior continue to work.
- No Moomoo-derived data is added to public reports and no public validator or redistribution gate is weakened.

## When it's considered done

- [x] PRSG-72-D1: Supported signal states render as sector emoji + ticker + arrow, without visible word labels.
- [x] PRSG-72-D2: Missing/invalid signal renders `?` and never falls back to SMA or forecast direction; accessible details and existing interactions remain intact.
- [x] PRSG-72-D3: Focused viewer regression and Lead review pass; the October 7 public report remains unavailable until its data gate is independently satisfied.

## Delivery evidence

- `node tests/daily_report_viewer_checks.cjs` — passed; compact arrow mapping, Up/Down/Sideways accessible/title wording, unavailable states, row `sector_emoji` precedence without a matching group key, accessible details, and chip focus/selection verified.
- The 7 October public report contains no `moomoo_session_direction` in 0 of 50 forecast rows. Its chips therefore remain `?` until supported authorized signal data is available.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-07/PRSG-72.harness.json --changed-file artifacts/daily-market-brief/tradingview.js --changed-file tests/daily_report_viewer_checks.cjs --changed-file plans/2026-10-07/PRSG-72-compact-trend-chips.md --changed-file plans/2026-10-07/PRSG-72.harness.json` — passed.
- 2026-10-07 MYT Lead review: final diff stays within the four allowed paths. Focused DOM checks and ticket-scope validation passed. A synthetic local browser preview showed the compact sector emoji/ticker/arrow states and no direction words; missing public signals remain `?`. The live 7 October report still contains no `moomoo_session_direction` in 0 of 50 rows, so this presentation change does not supply report data or authorize redistribution.

Base: `26712926a2d1cef1fc4edaf97f31d77739691000` (`origin/main`, 2026-10-07 MYT). The existing renderer already maps the accepted quote-direction values but shows text labels. The existing dated report intentionally has no public `moomoo_session_direction`; this is a known input limitation outside this ticket.
