# Stock-research evidence gates

Apply the frozen [PRSG-109 program](../../../plans/2026-10-14/PRSG-109-stock-research-program.md) and the [PRSG-113 frozen model acceptance contract](../../../plans/2026-10-14/PRSG-113-stock-research-training-validation.md#frozen-model-acceptance-contract), plus the accepted child manifest; do not silently transfer this program's numbers to unrelated model assignments. Changes to these policies require reviewed scope and human acceptance before adoption. This document is agent guidance, not an executable promotion checker.

## Before seeing results

Freeze origin-time data vintages, universe, causal features, realized targets, date folds, purge/calibration boundaries, baseline configuration, costs, metrics and thresholds. All instruments share chronological date boundaries. Training/calibration features and labels must actually be available before the next fold starts: purge by recorded availability as well as label-window end, excluding late retrievals/revisions even when the market window already ended; next-week label-end purging uses the actual calendar window, not a fixed five-day approximation. Retain an untouched chronological holdout across regimes. Delisting, historical membership, revisions and point-in-time adjustment gaps mean retrospective evidence with stated limits; they do not establish fully point-in-time dynamic-universe validation.

Whole-window low/high are separate from terminal return. Allow windows entirely above/below reference. PRSG-113 rejects crossing quantiles and median low above median high; do not silently repair them. Incompatible units and invalid OHLC also require explicit rejection. Calibrate on prior validation data, never the untouched holdout. Measure joint envelope containment separately from endpoint interval coverage.

## Actual-data promotion requirements

PRSG-113 is the authoritative frozen numerical contract. Read its exact thresholds, weighting, sample requirements and paired-bootstrap policy before evaluating; the earlier program's pooled coverage/subgroup-floor summary is superseded for this model acceptance.

- Match baseline and challenger at origin for all three targets (minimum low, maximum high, terminal log return) and all quantiles, with identical horizon lead/count and instrument/leverage conditioning. Fit and calibrate on earlier available data only, and save both immutable forecasts at origin. An absent baseline or unassessable near-zero error blocks the relative-improvement gate.
- Assess low and high median endpoint errors separately, aggregate pinball as declared, and apply the separate terminal-return accuracy/pinball gate before directional promotion. Use the frozen paired 95% common date-block confidence interval criterion, weights, block lengths, replicates and seed; positive pooled point estimates alone are insufficient.
- Each adequately sampled promoted class/horizon must meet the frozen 85–95% endpoint interval coverage band and matched-coverage width requirement. Do not accept a subgroup because pooled coverage passes or its coverage exceeds the earlier 80% floor. Report joint whole-window envelope containment separately.
- Apply the contract's overall distinct-date and subgroup nonoverlapping-block minimums. Correlated ticker-row counts do not replace independent dates or blocks; insufficient groups remain unvalidated and cannot inherit pooled acceptance.
- Strong promotion additionally requires contemporary universe membership, delistings and origin-vintage evidence. A current-universe backfill, provenance-limited retrospective study, synthetic success, baseline fallback or tuning-set gain cannot satisfy that dynamic-universe actual-data gate. Freeze a supported horizon/class deployment map; failed or unknown gates stay research only.
- Score saved forecasts against actual OHLC only after the full window ends and actuals become available, including former universe members. Pending/missing windows are never counted as successful outcomes; never substitute later predictions or reconstructed baselines for origin-time records.

## Hardware and artifact acceptance

CPU-first on the actual 8 GB Apple Silicon target: peak memory at most 2 GB; training target at most ten minutes; cached 110-name inference target at most ten seconds. Record measured wall time, peak-memory method, hardware/OS/dependencies, input size and threads. A Colab/other-machine run is supplementary. A target is not a measurement; exceedances or absent measurements go to Lead with a bounded proposal, without claiming acceptance.

Save estimators plus exact feature order/schema, calendar and adjustment policy, training cutoff, calibration, dependencies, model/data/baseline hashes and resource receipts. Trusted local reload must reproduce inference and reject incompatible artifacts. Keep prior accepted artifacts and failed candidates. Never silently retrain or overwrite immutable forecasts.

## Review disposition

Report each horizon/class as qualified for review, failed or insufficient evidence, with numerical results, paired uncertainty and the precise rejection reason. Trader reviews financial meaning and research decisions; Lead independently accepts scope/evidence; human review gates model/prompt/risk-policy adoption. This program currently authorizes implementation, not production-model promotion. Do not weaken thresholds after a failed result to make acceptance pass.
