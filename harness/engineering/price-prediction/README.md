# Price-prediction review ledger (proposed manual workflow)

This folder supports evidence-based review of the `daily-market-brief` and `technical-trend-analysis` skills. It is a research artifact and a proposed workflow only: no program currently runs the ledger, automatically evaluates reports, routes requests, or edits skills. See `harness/research_harness.yaml` for the separate future contract; it is not runtime-enforced.

## At report generation

1. Freeze `as_of` timestamp/timezone, market/venue/session, input window, source links, and whether prices are live, delayed, or prior close.
2. Search earlier dated briefs for forecasts due to mature. Preserve their original wording and baseline; do not retroactively edit a forecast.
3. For each discrete directional forecast, append one row to `forecast-ledger.csv`. Record ticker/instrument, benchmark, baseline close and date, forecast direction or range, confidence (prefer calibrated probability only when method supports it), `llm_model` (the model that collected or authored the forecast row; leave blank for historical rows where unknown), horizon type, target date, and invalidation condition. Use separate rows for next-session and week-end targets.
4. If prior reports or required actual prices are unavailable, state `not scored` and why. Never synthesize a T-1 forecast or fill missing price data by inference.

## When a target matures

Append actual close/date/source and compute realized return from the frozen reference close: `(actual_close / reference_close - 1) × 100`. Score direction only for forecasts with a predeclared non-flat direction and comparable venue/adjustment basis. A range hit requires the forecasted range and scoring rule to have been recorded before the target. Keep next-session and weekly horizons separate. Mark unresolved rows pending; do not score early.

Report correct/eligible count, coverage/abstentions, sample size, and a simple benchmark (such as prior-close direction or always-flat) alongside hit rate. Hit rate alone can reward low-value or uncalibrated calls; where probability forecasts and sufficient samples exist, track Brier score/calibration and return/risk metrics as well. Show uncertainty around small samples and avoid claiming skill from a handful of outcomes. Record revisions, data corrections, and source vintage without overwriting the original forecast.

Candidate errors can become frozen regression cases after human review. Any forecast-skill, prompt, model, or scoring-rule change requires a versioned evaluation set, out-of-sample/replay evaluation, and human approval before adoption. No autonomous self-editing or self-training of production instructions.

## CSV columns

`forecast_id` is a stable unique identifier. Use ISO-8601 timestamps with timezone offsets and decimal prices in the instrument's quote currency. Store blank cells for unknown/unmatured values, not invented zeros. Suggested status values: `pending`, `scored`, `not_scored`, `data_unavailable`, `abstain`. Preserve source URLs where licensing permits. The `llm_model` column records which LLM collected or authored that audit row (for example `Composer`); it is provenance for review, not a quality score.
