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

- [x] PRSG-81-D1: Establish the exact available forecast/outcome cohort counts, target horizons, missingness and comparability limits from the frozen ledger and source report.
- [x] PRSG-81-D2: Define leakage-safe comparison metrics and at least two simple baselines; specify minimum evidence/sample threshold or explain why none is defensible.
- [x] PRSG-81-D3: Trader reviews whether the Moomoo direction signals are financially interpretable for the proposed comparison, with source/time/session limitations stated.
- [x] PRSG-81-D4: Lead records a recommendation (model change, continue collecting evidence, or abstain) and exact next implementation scope; no production change is implied by the spike.

## Validation and limits

Read-only review of ledger/source report and independent Trader review. If an offline replay is proposed, freeze inputs, rules, cutoff and cohort before calculation; report exact commands and counts. Do not claim statistical significance, calibrated probability, out-of-sample precision or predictive edge without an adequate predeclared sample and appropriate uncertainty analysis.

## Review evidence (2026-10-09)

- Direct CSV audit of `harness/engineering/price-prediction/forecast-ledger.csv`: 120 rows; 120 pending; zero actual closes; zero `actual_available_at`; all 120 target 2026-10-09; horizons 119 `week_end` and one `next_session`; 100 unique `(market, venue, ticker, horizon, target)` tuples; 61 scoring notes contain `intraday` or `snapshot`.
- Trader's read-only review confirmed zero matured/comparable outcomes at 15:16 MYT and no precision/calibration conclusion. All rows share one target date and represent a correlated cross-section; 18 tuple groups have repeated vintages. Trader recommended chronological folds, matched eligible cohorts, directional hit rate with uncertainty, range coverage with width/interval score, a training-window directional baseline and a zero-return point baseline evaluated by MAE/RMSE. Flat calls are not direction hits; probability calibration is unavailable.
- At that review cutoff, no model, forecast, report, source close or ledger row had been changed; the model-change decision was pending the authorized experiment documented below.

## Experiment report (2026-10-09, 18:49 MYT)

### Decision

**Do not promote either the existing 20-session drift forecast or Chronos-2 as a validated production price predictor.** Chronos-2 ran locally and is suitable for continued research-only comparison, but did not beat the zero-return price baseline on point MAE in the primary post-release SPY holdout. The current report's Gaussian bands also under-covered their nominal 95% level in the historical replay. Keep forecasts visibly uncalibrated; do not change report labels, confidence, or Moomoo signal counts based on this experiment.

### Forecast ledger at the actual report cutoff

Re-ran `python3 -m harness.forecast_review --ledger harness/engineering/price-prediction/forecast-ledger.csv --as-of 2026-10-09T18:34:00+08:00` (valid input, exit 0). It classified 0/120 rows as scored, 95 pending, and 25 mature-but-not-scored. All target-close and actual-availability fields remain blank. Bursa's stated target close time had passed, but no actuals were recorded; the US close was still ahead at this cutoff. This is not a score of the Oct 8 cohort. Even once outcomes are collected, these rows share one target date and are correlated rather than independent time tests.

### Experiment A — the method already used in the report

Retrieved SPY daily adjusted closes from the Yahoo chart endpoint for 2018-01-02 through 2026-10-08. The Oct 8 report's SPY reference is 779.09 on Oct 6. Recomputing the last 20 adjusted-close log returns, sample standard deviation (`ddof=1`), and a three-session Gaussian band gives 764.1828–798.9427, within one cent of the published 764.19–798.94. The method is therefore reproduced to rounding precision for this row, not independently validated as predictive.

Rolling-origin replay used the trailing 20 adjusted-close log returns, point forecast `h × mean`, and nominal 95% interval `h × mean ± 1.959964 × sample_sd × sqrt(h)`. A matched zero-return baseline used the same trailing volatility and zero drift. Forecast origins advanced by the horizon (2 or 3 sessions), so target-return windows do not overlap. The 2020-01-01–2026-10-08 replay is retrospective and single-instrument. MAE and interval scores are percentage points of cumulative log return; the interval-score comparison uses identical target rows.

| Horizon | N | Drift MAE | Zero-return MAE | Drift 95% coverage | Zero-drift 95% coverage | Drift interval score | Zero-drift interval score |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 sessions | 850 | 1.209 | 1.172 | 91.3% | 92.2% | 8.948 | 8.561 |
| 3 sessions | 566 | 1.535 | 1.469 | 91.3% | 92.0% | 11.202 | 10.121 |

The drift point forecast had higher MAE and RMSE at both horizons than zero return. The 95% ranges covered fewer than 95% of outcomes. Width and the proper interval score were reported because coverage alone rewards very wide ranges. This single-SPY replay does not establish performance across the report universe.

### Experiment B — local pretrained model

Tested Amazon `amazon/chronos-2` zero-shot with no fine-tuning. Official model metadata lists 120 million parameters and Apache-2.0; the model artifact is a safetensors file. Used pinned model-weight commit `95a9710e2596287d08352589f42634fa5abdf0a7` (SHA-256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`). The same weight blob is present at the current repository head for the model; model code/package version was Chronos Forecasting 2.3.2.

The laptop is Apple Silicon arm64 with 8 GB RAM. The system Python 3.9 had no PyTorch or Chronos packages, so dependencies and weights were installed in an isolated temporary Python 3.12 environment under `/tmp/praesagus-chronos-exp.av4w6b`; no repository or global Python files changed. CPU-only inference worked. Cold model download/load took about 83 seconds; one three-step forecast took 0.95 seconds. The 850 two-session and 566 three-session forecasts ran in batches of 32 in 1.40 and 0.91 seconds respectively. Cross-learning was disabled, so forecast windows did not share information. Public historical prices were fetched, but only local model inference received the numeric series; no credentials, Moomoo data, or private account data were used. This tests one univariate numeric price input, not arbitrary inputs or indicator covariates.

Each origin supplied exactly 20 prior SPY adjusted closes. The model's median forecast was the point estimate; native q10/q90 quantiles formed an 80% interval. No quantile extrapolation was used. The primary chronological holdout begins 2025-10-31, the first full session day after the model weights were initially uploaded on 2025-10-30. Only target dates after that cutoff are used for the primary result; earlier history is exploratory because it may overlap model pretraining. Holdout forecasts are non-overlapping by horizon. Uncertainty intervals below are exploratory circular moving-block bootstrap intervals using five forecast origins per block, 5,000 resamples and a fixed seed; one instrument still limits inference.

| Post-release SPY holdout | 2 sessions (N=118) | 3 sessions (N=78) |
|---|---:|---:|
| Target dates | 2025-10-31–2026-10-08 | 2025-11-03–2026-10-06 |
| Chronos median MAE | 0.977 | 1.146 |
| Zero-return MAE | 0.942 | 1.145 |
| Existing 20-session drift MAE | 0.956 | 1.178 |
| Chronos minus zero MAE; block-bootstrap 95% interval | +0.034 [−0.019, +0.090] | +0.001 [−0.077, +0.081] |
| Direction hit rate: Chronos median / previous-day sign / drift | 55.1% / 48.3% / 47.5% | 59.0% / 44.9% / 46.2% |
| Chronos q10–q90 empirical coverage (nominal 80%) | 78.8% | 78.2% |
| Chronos / zero-drift 80% interval score | 4.355 / 4.104 | 5.008 / 4.963 |
| Chronos minus zero interval score; block-bootstrap 95% interval | +0.251 [−0.131, +0.625] | +0.044 [−0.492, +0.549] |

The Chronos point forecast did not improve MAE over zero return in either post-release horizon; the uncertainty intervals include no difference. Direction rates are higher in this small holdout, but they do not establish repeatable forecasting skill, and they are not probabilities. Its interval coverage is near—but below—the nominal 80%; the score differences versus the same-volatility zero-drift interval are inconclusive. The broader pre-release replay is weaker: Chronos MAE was 1.287 vs 1.172 at two sessions and 1.604 vs 1.469 at three sessions; its directional hit rates were 44.2% and 48.6%.

### Example output (not validated)

With the 20 SPY adjusted closes through 2026-10-08 and reference 773.93, the model's next three sequential price observations were:

| Step | q10 | Median | q90 |
|---|---:|---:|---:|
| 1 | 765.568 | 772.998 | 780.248 |
| 2 | 761.416 | 771.811 | 782.468 |
| 3 | 758.732 | 770.774 | 783.443 |

These predictions have not matured or been scored; the model receives no exchange calendar and this output is not an investment recommendation. No report artifact, forecast label, ledger outcome, skill, schedule, or production code was changed.

### Trader review, limitations, and next decision

Trader's independent read-only review supports separate 2- and 3-session cohorts, point-in-time close and adjustment provenance, matched rows, zero-return and prior-sign baselines, separate direction and interval metrics, and uncertainty clustered over time. The current ledger cannot establish MAE, hit rate, interval coverage, calibration, or relative model skill until verified actual closes and availability timestamps are recorded. There is no defensible universal minimum sample count for all tickers; retain a chronological holdout and continue collecting eligible target dates before claiming market-wide performance.

**Recommendation:** keep both methods research-only. Do not wire Chronos-2 into the public daily report or use it to alter forecast confidence. Next, collect point-in-time forecasts and matching actual closes by venue and explicit 2-/3-session horizon; then rerun Chronos-2 and simple baselines on multiple US tickers, with Bursa evaluated separately. Add costs only if a separate strategy-utility experiment is proposed. The dated target cohort still needs its actual-close data recorded after each venue close; this report does not wait for or invent those outcomes.

## Follow-up experiment B — 30-name U.S. cohort (2026-10-09, 21:54 MYT)

This research-only replay extends the single-SPY comparison above to every U.S. ticker in the 2026-10-08 report, with the universe fixed before scoring. It does not use Moomoo indicators, change the forecast process, or establish that any result is available for Malaysian listings.

### Frozen protocol and data

- Universe: `AAPL, ABT, AVGO, CAT, COP, FCX, GE, GOOGL, GS, HD, IWM, JNJ, JPM, KO, LIN, LLY, MCD, MSFT, NEM, NVDA, PG, QQQ, SLB, SPY, TSLA, TSM, UPS, V, WMT, XOM` (30 symbols, exactly those in the cited report).
- Data: Yahoo Finance chart endpoint adjusted closes, daily interval, requested from 2018-01-01 through 2026-10-08 inclusive; 2,204 bars returned for each ticker and no fetch failures. Endpoint pattern: `https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1=1514764800&period2=1791504000&interval=1d&events=div%2Csplits`. Retrieved 2026-10-09 21:52 MYT. Raw provider responses were not committed; historical provider revisions remain possible.
- Model: `amazon/chronos-2`, `chronos-forecasting 2.3.2`, pinned revision `95a9710e2596287d08352589f42634fa5abdf0a7`; weight SHA-256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`. CPU inference on the local Apple Silicon laptop, no covariates, `cross_learning=False`; median is the point forecast and native q10/q90 are an 80% interval.
- At each origin, Chronos receives the latest 20 adjusted closes. Two- and three-session target windows do not overlap within a ticker; origins advance by the horizon. The target cohort is after the pinned model revision's public release date, but the model training cutoff is unverified, so this is not asserted to be an unseen-data holdout.
- Baselines: (1) zero-return point forecast at the latest close; (2) trailing 20-close-to-close log-return mean, scaled by horizon for the drift point forecast. The zero-drift 80% Gaussian range uses the prior 20 returns' sample standard deviation (`ddof=1`) and `sqrt(h)` scaling. Scores are cumulative log-return percentage points; interval score uses alpha 0.20. No trading costs apply to these forecast-error metrics.
- Uncertainty: percentile moving-block bootstrap over common target dates, five target dates per block, all ticker rows for each sampled date kept together, 3,000 resamples, seed 1742. This accounts for common date shocks better than treating ticker rows as independent; it does not remove model/universe-selection bias. No longer-block sensitivity or two-way ticker/date resampling was run, and five-date blocks may not capture longer regime dependence.

### Results

| Horizon | Forecast rows | Target dates | Chronos median MAE | Zero-return MAE | 20-return drift MAE | Chronos minus zero MAE; date-block 95% CI | Chronos direction hit | Prior-day sign hit | Drift direction hit | Chronos q10–q90 coverage | Zero-vol coverage | Chronos / zero-vol interval score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 sessions | 3,510 | 117 | 2.185 | 2.023 | 2.123 | +0.163; [+0.127, +0.199] | 50.4% | 50.5% | 49.0% | 78.5% | 80.1% | 10.636 / 9.592 |
| 3 sessions | 2,340 | 78 | 2.651 | 2.398 | 2.583 | +0.253; [+0.191, +0.320] | 50.2% | 50.1% | 50.2% | 76.8% | 81.1% | 12.668 / 11.353 |

Chronos q10–q90 mean widths were 7.232 and 8.527 log-return percentage points at two and three sessions, versus 6.686 and 8.184 for the zero-drift range. Interval score is `ISα = (U−L) + (2/α)(L−y)` when `y < L`, `ISα = (U−L) + (2/α)(y−U)` when `y > U`, and `ISα = U−L` otherwise, with `α=0.20`; all terms are cumulative log-return percentage points. Direction hit rates exclude zero realized returns and exclude flat forecasts from each denominator; the zero-return point baseline is therefore scored only by point error and interval metrics, never as a directional call. Previous-day-sign denominators were 3,497 and 2,337; Chronos denominators were 3,503 and 2,338. The drift denominators were 3,502 and 2,337.

### Interpretation and limits

On this fixed, report-selected U.S. cohort, Chronos median forecasts had higher MAE than the zero-return baseline at both horizons, with the five-date block-bootstrap intervals for the difference above zero. Its direction hit rates were around 50% and close to the prior-day-sign and drift baselines. Its nominal 80% ranges under-covered at both horizons and had worse interval scores than the narrower zero-drift ranges. These results do not support integrating Chronos as a price predictor or using it to raise forecast confidence.

This remains a one-year, report-selected survivor cohort, not a random universe or a verified model-unseen test set. The 3,510/2,340 rows are ticker-origin observations, not independent trials; the effective temporal information is much closer to 117/78 dates, with additional cross-ticker dependence. Trader review cautions that five-date bootstrap blocks may not cover longer serial/regime dependence; the positive intervals are conditional on this exploratory resampling design, not a clean independent-sample significance claim. No longer-block sensitivity or two-way date/ticker bootstrap was run. Yahoo adjusted closes were retrieved retrospectively, not from point-in-time vintages; corporate-action adjustments may revise historical levels and the information available at old origins. No Malaysian names were evaluated. Do not describe the result as market-wide precision, calibrated probability, proof of no possible edge, or validated out-of-sample performance. Continue research only if future evaluation uses a frozen point-in-time data snapshot, a verified model training cutoff or a clear limitation statement, separate US/MY cohorts, and additional distinct target dates. Actual-close ledger entries remain a separate blocked maintenance step; this backtest does not fill or score the 120 ledger rows.

No production code, report artifacts, forecasts, ledger rows, private store, or model settings were changed. The analysis script and aggregate JSON remain in the task's temporary experiment directory; only this documented result is retained in the repository.

## Ownership and protected work

Lead owns the decision brief and final recommendation. Trader has a read-only review assignment. The registered Engineer is not assigned implementation until Lead accepts a separate concrete implementation scope. Protect all existing working-tree changes, especially `AGENTS.md`, `agent-operations/schedules/trader-daily-report.md`, `artifacts/daily-market-brief/reports.json`, `docs/PRIVATE_REPORT_PROJECTION.md`, `ingest/daily_report_projection.py` and `skills/daily-market-brief/SKILL.md`.
