# PRSG-182 — Frozen-Origin US Price Model Replay

Type: spike · Modules: market-research, financial-data, harness · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium — obtain an actual same-origin model comparison and expose whether candidate forecasts improve over simple baselines.

Created 2026-11-01 MYT. Scope accepted by Lead before external model inference.

## Objective

Replay external zero-shot price models against the exact immutable 30-name history packet used for the 29 October 2026 PRSG-155 forecast. The packet was captured before the 29 October US session; score the replay against that later completed session. Compare the existing Praesagus prediction and matched baseline, the zero-return baseline, TimesFM-2.5 and Chronos v1. This is a single-origin exploratory replay, not a historical multi-date backtest, a statistical validation, or evidence of trading value.

## Approach

Freeze the verified 28 October origin input, load pinned Apache-2.0 zero-shot checkpoints in an isolated environment, and generate one-session outputs without fitting or tuning. Bind source, code, checkpoint and output hashes. Score the exact 29 October actual closes against the already saved Praesagus and baseline forecasts; keep full outcomes private.

## Choices

Use TimesFM-2.5 and Chronos v1 because a recent equity-return study ranked them among its strongest options and both weights are Apache-2.0. Exclude Moirai-2.0 because its weights are CC-BY-NC-4.0 and use rights for this project are unresolved. Keep the current Praesagus model, matched volatility baseline and zero-return baseline as comparators. A one-session cross-section is descriptive only.

## Findings

Frozen inputs and both challenger outputs matched 30 of 30 names. Lead independently reproduced the private score artifact hash. The numeric score remains in the private results bundle; no public performance claim is made. Chronos and Praesagus each called the same number of directions correctly in this one date, while TimesFM called fewer; the sample is too small and correlated to establish a winner.

## Tradeoffs

This replay measures whether current off-the-shelf challengers can be evaluated cheaply on identical frozen inputs, but one origin cannot measure performance across market regimes. Vendor finality and adjustment-formula limits remain. Multi-date OOS evidence still requires admissible historical snapshots and PRSG-113's unchanged validation gates.

## Frozen boundary

Accountable owner: AI Engineer. Allowed Git writes: this spec and `plans/2026-11-01/PRSG-182.harness.json` only. Private outputs: `~/.codex/lead-state/PRSG-182/`, excluding raw bar copies and account identifiers. No application/model-runtime edits, training, tuning, promotion, publication, live trading or additional data collection.

Input bundle: `/Users/jwtan/.codex/lead-state/PRSG155/ai/public-batches/prsg155-29oct-1793247080920/verified-inputs/history.csv`; forecast bundle: matching `2026-10-29_121126/predictions.json`; outcome bars: `/Users/jwtan/.codex/lead-state/PRSG-1NOV/history-US30-OHLCV-2026-10-30.json`. Private review confirmed 30/30 exact code and typed ID matches, 30/30 exact 28 October reference-close matches, 30/30 USD and declared adjustment-label matches, and 30/30 29 October target bars. The original forecast preceded the target session. Freeze the input hash, target session and model/checkpoint hashes in the private output before scoring.

Base SHA: `fc626445d46212b577abc3029ee5b4af1d555352`.

## Candidate shortlist and limits

The June 2026 financial-return study across AAPL, AMZN, GOOG, JPM and META reported average ranks Moirai-2.0 2.9, TimesFM-2.5 3.1, Chronos v1 3.4, and Chronos-2 3.9. Gains over random walk were small and sparse. This is external benchmark context, not Praesagus evidence. Sources: [financial-return study](https://arxiv.org/abs/2606.27100), [TimesFM weights](https://huggingface.co/google/timesfm-2.5-200m-pytorch), [Chronos models and weights](https://github.com/amazon-science/chronos-forecasting), [Moirai-2 weights and license](https://huggingface.co/Salesforce/moirai-2.0-R-small).

Use TimesFM-2.5 (Apache-2.0) and Chronos v1 / `amazon/chronos-t5-small` (Apache-2.0) as zero-shot challengers. Do not download or run Moirai-2.0: its weights are CC-BY-NC-4.0, and permitted use for this project has not been established. No candidate may use observations after the frozen 28 October origin or be adapted on the target outcomes.

## Frozen scoring

Use every eligible name in the fixed 30-name packet; retain and explain any model-specific missing output. Single target: 29 October close-to-close log return. Compare direction hit rate (zero output is a miss when realized return is nonzero), median absolute log-return error, q05/q50/q95 pinball loss where the model supplies the corresponding quantiles, central 90% interval coverage and width where defined, and count. The same single date makes all names correlated; report raw counts and per-name results, with no confidence interval, significance, or generalized accuracy/profitability claim. A zero-return baseline has no interval. All outputs remain research-only / NO TRADE.

## Data qualifications

The later actual packet was retrieved 1 November. Moomoo OpenD provider finality is unverified; QFQ is mapped to forward-excluding-dividends, but the provider formula/dividend policy is uncertified. Current typed identities were matched; this does not establish historical membership. Preserve these limitations alongside all results. This fixed-origin comparison does not repair PRSG-113's empty historical folds, establish an untouched multi-date holdout, or qualify a model for public use.

## Acceptance

- [x] PRSG-182-D1: Lead freezes the immutable origin, 30-name cohort, 29 October outcome, candidates, license boundary, metrics and private-only result path before challenger inference.
- [x] PRSG-182-D2: Input/forecast/outcome hashes reproduced; typed identity, exact origin close, currency, adjustment label and target-session checks passed 30/30. TimesFM-2.5 and Chronos v1 each returned 30 zero-shot outputs from the 51-session input ending 28 October; no fit, tuning, or post-origin model input. Private receipts preserve pinned model revisions, weights hashes, versions and runtime/resource details.
- [x] PRSG-182-D3: All 30 names scored against the saved Praesagus model, matched volatility baseline and zero-return comparator. Results, hashes and per-name derived metrics are private at `~/.codex/lead-state/PRSG-182/private-results.md` and `score.json`. Descriptive one-date results only; no confidence intervals or generalized skill claim.
- [x] PRSG-182-D4: Lead independently re-ran the private deterministic scoring replay, reproduced the exact score JSON SHA-256, reviewed input/model/runtime provenance and accepted the result only as a one-vintage diagnostic; no promotion, public report or trade action.

## Duplication review

PRSG-113 owns model fitting and strong multi-date chronological validation; its current saved folds yield zero OOS forecasts because historical inputs were retrieved after the fold cutoffs. PRSG-153 owns the fixed US30 research fit and one-time output. PRSG-155 contains the immutable pre-target forecast/input used here. PRSG-181 owns the public report and later outcome scoring. PRSG-182 adds only a one-origin, private zero-shot challenger replay; it does not change those tickets' gates or status.
