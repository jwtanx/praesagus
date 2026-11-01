# PRSG-184 — Reusable Private Forecast Archive Benchmark

Type: feature · Modules: financial-data, harness, docs · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium — let the team repeat source-bound model-vs-baseline scoring without a bespoke private script for each report.

Created 2026-11-01 MYT. Scope accepted by Lead before implementation.

## Objective

Commit a reusable CLI that reads an explicit private JSON config of saved one-session forecast bundles, exact source input histories, later actual OHLC rows and typed identities, then generates private JSON and Markdown benchmark reports. Keep saved model hashes separate and include each forecast's own matched baseline and zero-return comparator.

## Approach

Use existing `evaluation.forecast_metrics` and `model.pinball` for forecast scoring. The CLI validates input issue times, one-session target dates, exact origin close, typed IDs, currency/basis and later completed actual rows. It records source hashes, excludes unsupported rows with reasons, rejects output paths inside the repo and never overwrites a nonempty report directory.

## Choices

Use a small explicit JSON config rather than implicit state discovery. Require absolute source paths, keep source receipts and rights review with the caller, and write outputs outside Git. Score only saved one-session forecasts; this tool does not collect, fit, tune, download candidate weights, promote or publish.

## Findings

PRSG-183's `score_archive.py` is private and hard-coded to three historical bundles. Its replay also exposed a simple-return/log-return quantile mismatch, corrected in the PRSG-183 private report and ticket evidence within this acceptance review. `scripts/stock-research/evaluation.py` already provides trusted forecast metric conversion, but no reusable CLI accepts independent archived bundles and emits a benchmark Markdown report. This ticket adds that missing wrapper and focused regression coverage.

## Tradeoffs

The report is reproducible and source-hash-bound but still depends on caller-provided provenance and source rights; matching rows do not certify provider finality or historical membership. Correlated one-date cross-sections remain descriptive and cannot establish model skill or trading value.

## Frozen scope

Allowed paths: `scripts/stock-research/score_forecast_archive.py`, `tests/test_stock_research_archive_scoring.py`, `scripts/stock-research/README.md`, this spec and `plans/2026-11-01/PRSG-184.harness.json`, plus the PRSG-183 report/spec/manifest correction required to keep the replay evidence accurate. Base SHA: `c3d681637777c6ae93093cc22a759ab6f456bfb4`. Generated configs, source data and benchmark results remain outside Git.

## Acceptance

- [x] PRSG-184-D1: CLI accepts a versioned explicit config with multiple saved bundles and generates JSON + Markdown outside Git without overwriting existing output.
- [x] PRSG-184-D2: It scores eligible one-session records against their saved model, matched baseline and zero return, keeping model generations separate and checking input availability/target compatibility.
- [x] PRSG-184-D3: Focused tests cover successful scoring, future-known inputs, repository output rejection and no-overwrite behavior; docs include the repeatable command/config.
- [x] PRSG-184-D4: Re-run the committed PRSG-183 archive from an equivalent private config; reproduce all 33 eligible rows and independently inspect hashes/report before completion.

## Duplication review

PRSG-113's `evaluation.py` scores full canonical live/local runs and persists append-only outcomes; PRSG-182/183 are completed private one-off analyses. PRSG-184 adds only an explicit-config CLI/report wrapper over existing metrics for repeatable arbitrary archived bundles; it does not replace evaluation, create another model, or weaken model validation gates.
