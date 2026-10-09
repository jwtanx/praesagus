# PRSG-80 — Preserve and score the October 8 forecast cohort

Type: bug · Modules: financial-data, market-research, harness, skills, docs · Owner: Lead · Priority: P1 · Effort: XS (0.3–0.5 person-days, estimate) · Impact: medium-high — preserves report signals before outcomes and lets the daily report state whether bullish/bearish forecasts were actually right without using later evidence.

Created 2026-10-09 MYT. Frozen integration base: `007fba1a2a8abe474972bd58505c87c95c22f5cf`.

## Objective

Check the October 8 report’s Bullish/Bearish/Sideways cohort against target-date closes without hindsight, record all rated signals before the close, show the outcome status in the October 9 report, make the freeze-and-score workflow part of the daily report skill, and support forecasts issued earlier on the same venue-local target date.

## Evidence and limits

The October 8 report has 49 rated rows: 11 Bullish, 17 Bearish, 21 Sideways, and one Unrated; each rated row targets October 9. The report uses low-confidence, uncalibrated historical statistical ranges. At the October 9 12:55 MYT review, verified target-date closing actuals were not available; therefore no result can yet be called a hit or miss. Preserve all rated forecasts as pending and score only after the relevant venue close and actual-close availability are evidenced. This ticket makes no claim about predictive edge.

The worktree contained pre-existing Trader edits to `ingest/daily_report_projection.py` and `skills/daily-market-brief/SKILL.md`. Those edits are excluded from this ticket and must remain untouched/unstaged; only the new rating-and-scoring skill hunks are in scope.

## Frozen scope

- `artifacts/daily-market-brief/2026-10-09.json`
- `artifacts/daily-market-brief/reports.json`
- `harness/engineering/price-prediction/forecast-ledger.csv`
- `skills/daily-market-brief/SKILL.md` (only forecast freeze/scoring guidance and version metadata)
- `harness/forecast_review.py`, `harness/FORECAST_REVIEW.md`, `tests/test_forecast_review.py`
- `plans/2026-10-09/PRSG-80-oct8-forecast-outcome-tracking.md`
- `plans/2026-10-09/PRSG-80.harness.json`

The October 8 report, all other reports, viewer, monthly calendar, projection code, provider data, and all unrelated working-tree changes are protected. The optional `forecast_target_close_at` field must preserve venue-local target date, reject a forecast made at/after close and actual data available before close, and leave same-day targets pending until that timestamp.

## When it’s considered done

- [x] PRSG-80-D1: All 49 rated October 8 forecasts and the October 9 same-day SPY forecast are preserved with accurate target-close metadata, pending status and no invented actual values.
- [x] PRSG-80-D2: October 9 report and report index identify the October 8 Bullish/Bearish/Sideways counts and report both cohorts pending because target closes are not verified.
- [x] PRSG-80-D3: Daily report skill requires freezing rated forecasts at publication and scores Bullish/Bearish direction and inclusive ranges only after a comparable target close and its availability time are verified.
- [x] PRSG-80-D4: The deterministic evaluator supports explicit same-day venue-close timestamps, rejects forecast/actual availability leakage and retains future-target behavior.
- [x] PRSG-80-D5: Lead reviewed scope/evidence; commit e550b32 is pushed, Pages run 37886457572 succeeded, and the live report/index show the update.

## Validation record

- Forecast review at `2026-10-09T12:55:04+08:00`: valid, 120 issuances, 100 instrument-target pairs, 0 scored, 120 pending, 18 correlated-vintage warnings. The 49 Oct 8 rows and Oct 9 SPY row remain pending until their venue closes.
- `python3 -m pytest tests/test_forecast_review.py -q`: 16 passed. Full repository suite from both commit and push hooks: 1,239 passed, 41 warnings.
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-09 --public`: passed; 50 forecasts, 65 calendar events, 10 report dates.
- Skill Creator `quick_validate.py skills/daily-market-brief`: passed; version 1.8 metadata and frontmatter are valid.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-09/PRSG-80.harness.json` with all nine changed paths: pending final checklist synchronization/review.
- Field comparison confirms the 70 original issuance/outcome values are unchanged; scheduled close timestamps were added for target-date rows, 49 Oct 8 rated forecasts were added, and one Oct 9 SPY row was added with a venue-local NYSE Arca close time. Actual values remain blank.
- Trader's read-only outcome review confirms the Oct 8 counts and no close actuals available at 12:48 MYT. Lead diff/scope review is complete. Commit e550b32 is pushed and verified at origin/main; GitHub Pages run 37886457572 succeeded. The deployed report page and index were checked live; the selected date is Oct 9 and the scorecard shows the new pending cohort. The Oct 8 forecasts remain unevaluated until final closes and verified availability arrive.
