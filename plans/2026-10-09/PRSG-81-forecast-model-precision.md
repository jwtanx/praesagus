# PRSG-81 — Measure and improve daily forecast precision

Type: spike · Modules: harness, financial-data, market-research, skills, docs · Owner: Lead · Priority: P2 · Effort: S (0.5–2 person-days, estimate) · Impact: high — tests whether the daily report's directional and range forecasts outperform simple baselines before any model change; user value is unmeasured.

Created 2026-10-09 MYT. Frozen planning base: `ba7c01480616ab0f4bca576c1be97d5a4961c9e9`.

## Objective

Establish an auditable, point-in-time evaluation for daily report forecast precision, then recommend the smallest evidence-supported change to the current forecast method. This ticket does not assume that Moomoo indicators or an external pretrained model improves precision. The current daily report prompt tells Trader to use quote-vs-previous-close and SMA-5/SMA-20 direction when eligible, but prompt text alone does not produce a validated model or ensure that a scheduled run executed it.

## Baseline and evidence

- The 2026-10-08 report has 49 rated forecasts (11 bullish, 17 bearish, 21 sideways) and one unrated row. All rated rows use a 20-session log-return drift with a 95% Gaussian volatility band. The report contains no Moomoo fields; these labels did not use Moomoo.
- The ranges are explicitly low-confidence and uncalibrated, with no out-of-sample evidence. The report forecast ledger and offline evaluator exist; the evaluator scores only supplied actuals and does not fetch them.
- A direct ledger audit on 2026-10-09 found 120 pending issuances, all targeting 2026-10-09, zero actual closes and zero `actual_available_at` values. They comprise 70 September 30 week-end rows, 49 October 8 week-end rows, and one October 9 next-session row. They map to 100 unique market/venue/ticker/horizon/target tuples, with 18 repeated-vintage tuple groups. Sixty-one rows mention intraday/snapshot reference ambiguity. These are not 120 independent matured tests; at this cutoff there are zero matured comparable outcomes, so no precision comparison is yet possible.
- The next step is to resolve outcome eligibility and point-in-time reference comparability, then compare the frozen current approach with preregistered baselines using chronological walk-forward folds or a future untouched date holdout. Keep direction and range accuracy separate. For direction, exclude flat calls and zero-return ties; for ranges, report inclusive coverage together with width/interval score. No `probability_up` values exist, so probability calibration cannot be evaluated. Do not treat an always-flat baseline as directional hit-rate evidence; compare it as a zero-return point forecast. Do not tune on evaluation cohorts.
- Week-end currently combines target-session counts of two and three sessions; preserve those horizon variants separately where recoverable. Outcomes on the same target date share market shocks and tickers/vintages are repeated; report clustering and uncertainty by independent target dates, not raw row count. Determine an evidence threshold from a preregistered detectable effect/power analysis or keep collecting outcomes rather than asserting a generic minimum sample.
- Existing report artifacts, schedule, skill and working-tree edits are outside this spike's write scope. Trader provides read-only financial-method review; no live market calls are part of the assignment.

## Decision question and timebox

Within 1–2 person-days, establish the minimum data and outcome collection needed for a fair precision comparison, and specify a preregistered walk-forward protocol. Compare the current return-drift/range method with (a) yesterday-close sign or a training-window direction majority and (b) a point-in-time Moomoo direction baseline only where signal timestamp/session is eligible before the forecast cutoff. Evaluate a zero-return baseline using MAE/RMSE, not hit rate. For ranges, compare coverage and normalized width/interval score against a trailing realized-volatility range fit only on prior training data. Include spreads/fees/slippage only for a separately labeled strategy-utility analysis. If sample size or metadata is inadequate, recommend data accumulation and no model change.

## Scope

This is a read-only feasibility spike. Deliver a dated Lead decision brief and, if feasible, a reproducible offline analysis proposal; do not alter report forecasts, frozen ledger values, production skills/prompts, model settings, code, data stores, external services, or report schedules.

## When it's considered done

- [ ] PRSG-81-D1: Establish the exact available forecast/outcome cohort counts, target horizons, missingness and comparability limits from the frozen ledger and source report.
- [ ] PRSG-81-D2: Define leakage-safe comparison metrics and at least two simple baselines; specify minimum evidence/sample threshold or explain why none is defensible.
- [ ] PRSG-81-D3: Trader reviews whether the Moomoo direction signals are financially interpretable for the proposed comparison, with source/time/session limitations stated.
- [ ] PRSG-81-D4: Lead records a recommendation (model change, continue collecting evidence, or abstain) and exact next implementation scope; no production change is implied by the spike.

## Validation and limits

Read-only review of ledger/source report and independent Trader review. If an offline replay is proposed, freeze inputs, rules, cutoff and cohort before calculation; report exact commands and counts. Do not claim statistical significance, calibrated probability, out-of-sample precision or predictive edge without an adequate predeclared sample and appropriate uncertainty analysis.

## Review evidence (2026-10-09)

- Direct CSV audit of `harness/engineering/price-prediction/forecast-ledger.csv`: 120 rows; 120 pending; zero actual closes; zero `actual_available_at`; all 120 target 2026-10-09; horizons 119 `week_end` and one `next_session`; 100 unique `(market, venue, ticker, horizon, target)` tuples; 61 scoring notes contain `intraday` or `snapshot`.
- Trader's read-only review confirmed zero matured/comparable outcomes at 15:16 MYT and no precision/calibration conclusion. All rows share one target date and represent a correlated cross-section; 18 tuple groups have repeated vintages. Trader recommended chronological folds, matched eligible cohorts, directional hit rate with uncertainty, range coverage with width/interval score, a training-window directional baseline and a zero-return point baseline evaluated by MAE/RMSE. Flat calls are not direction hits; probability calibration is unavailable.
- No model, forecast, report, source close or ledger row was changed. Model-change decision remains pending evidence accumulation and a separately accepted delivery scope.

## Ownership and protected work

Lead owns the decision brief and final recommendation. Trader has a read-only review assignment. The registered Engineer is not assigned implementation until Lead accepts a separate concrete implementation scope. Protect all existing working-tree changes, especially `AGENTS.md`, `agent-operations/schedules/trader-daily-report.md`, `artifacts/daily-market-brief/reports.json`, `docs/PRIVATE_REPORT_PROJECTION.md`, `ingest/daily_report_projection.py` and `skills/daily-market-brief/SKILL.md`.
