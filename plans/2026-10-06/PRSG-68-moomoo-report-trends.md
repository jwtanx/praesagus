# PRSG-68 — Carry Moomoo daily-bar trends into the dated report

Type · Modules · Owner · Priority · Effort · Impact
feature · connectors, financial-data, frontend, market-research, skills, harness · Lead · P1 · M (3–5 person-days) · high — makes the requested 30 US quote rows' Moomoo-derived trend visible in the already-published daily report; trend is descriptive context, not a forecast.

## Objective

Use Moomoo REST historical daily K-lines to calculate a transparent SMA-5 versus SMA-20 trend for each supported US report symbol, retain provenance in the private capture store, project only the explicitly allowlisted derived trend fields into the dated report, and display the trend on the Technical analysis ticker chips. Keep the original forecast direction/target/confidence independent. Malaysia rows and failed/short history remain explicitly unavailable.

## Behavior and limits

- Request `GET /api/v1.0/quote/{symbol}/history-kline` for each of the report's 30 US symbols with daily bars (`ktype=2`), no price adjustment (`autype=0`), and a bounded history count. Keep the existing isolated worker, bounded response, private append-only raw storage, and rate-limit/upstream failure categories.
- Derive `bullish` when the latest five completed daily closes' mean is above the latest twenty completed daily closes' mean, `bearish` when below, `neutral` only when equal, and `unavailable` when fewer than 20 valid completed bars exist. Exclude an in-progress current US session bar. Retain method, bar dates, both means, last bar date, provider, endpoint, retrieval time and status.
- These are locally derived SMA comparisons from Moomoo bars, not a Moomoo-issued recommendation and not the report's forecast. Do not change forecast fields, infer a price target, or translate the trend into an action class.
- Keep private capture identifiers (`run_id`, `attempt_id`, and content hashes) inside the capture store only. Do not generate them in report JSON or require them in report-facing schemas; the public boundary validator continues to reject private identifiers if supplied.
- Add a visible trend label/status to report rows and the hosted Technical analysis ticker controls; retain an explicit unavailable state for MY listings and incomplete/failing US captures. Sanitize all text and preserve keyboard/touch behavior.
- Refresh `2026-10-06.json` only from the actual supported API response and a cutoff after collection. If history cannot be collected, keep all affected trend values unavailable; do not fabricate a favorable/bearish split.

## Non-goals

No live quote push, automatic background schedule, trade/order behavior, ML/model change, forecast rewrite, Malaysian market connector, private credentials/account data in the report, or changes to the previously published report history.

## Frozen scope

- Base SHA: `c3c6b0fdac118bb702fae017016aa48b5af62f64`.
- Owner: Lead. Lead owns implementation/integration and final review; financial forecast judgment remains with Trader.
- Allowed paths: this spec and manifest; `connectors/moomoo_rest.py`; `ingest/market_collector.py`; `ingest/private_market_store.py`; `ingest/daily_report_projection.py`; `scripts/daily-market-brief/run_private_quote_report.py`; `scripts/daily-market-brief/validate_report_json.py`; `artifacts/daily-market-brief/index.html`; `artifacts/daily-market-brief/tradingview.js`; `artifacts/daily-market-brief/2026-10-06.json`; `tests/test_moomoo_rest.py`; `tests/test_market_collector.py`; `tests/test_daily_report_projection.py`; `tests/daily_report_viewer_checks.cjs`; `tests/test_daily_report.py`; `skills/daily-market-brief/SKILL.md`; `plans/2026-10-06/PRSG-68-moomoo-report-trends.md`; `plans/2026-10-06/PRSG-68.harness.json`.
- Protected paths: all other repository paths.
- Preserve pre-existing dirty work in the primary checkout; this ticket is implemented in the isolated `codex/report-oct6-demo` worktree.

## Acceptance checklist

- [x] PRSG-68-D1: REST history request is bounded and strictly validates symbol, dates, provider response, unique daily bars and finite positive closes; transport/upstream/malformed errors remain sanitized.
- [x] PRSG-68-D2: History is captured by the isolated worker and appended to the private store; query/projection is limited to the same run and report cutoff.
- [x] PRSG-68-D3: Per-symbol SMA trend is derived from the latest 20 completed Moomoo daily closes and carries method/date/time/provenance; missing, short, failed, future or in-progress data yields unavailable.
- [x] PRSG-68-D4: Report/viewer presents Moomoo-derived trend separately from forecast direction and shows explicit unavailable states; existing report behavior and keyboard controls remain intact.
- [x] PRSG-68-D5: Today's report is updated only with verifiable run evidence after collection; the report validator and ticket checks pass.
- [x] PRSG-68-D6: Lead independently reviews the full diff, tests, cutoff, and delivery evidence.

## Verification

- `pytest -q tests/test_moomoo_rest.py tests/test_market_collector.py tests/test_daily_report_projection.py tests/test_report_json_validator.py`
- `node tests/daily_report_viewer_checks.cjs`
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-06`
- `python3 scripts/planning/validate_ticket.py plans/2026-10-06/PRSG-68.harness.json`
- Manual review of one captured success and one unavailable/short-history case; no secret contents are emitted.

## Progress

- 2026-10-06 MYT: scope frozen against the current pushed base. The REST K-line endpoint and daily-bar fields were checked against Moomoo's official API reference; implementation, tests, viewer, dated-report generation, and Lead review are complete.
- 2026-10-06 MYT: the 30-symbol collection completed with transport failures and no returned bars. The dated report records all 30 US trends unavailable and all 20 MY rows unsupported; forecasts remain Unrated. Private capture IDs are not emitted in report JSON.

- Verification: REST 140 passed; collector 85 passed; projection/report 131 passed; chart asset and report DOM checks passed; public report validation and ticket-scope validation passed.
