# PRSG-161 — Forecast Outcome and Quality Scorecard

Type: feature · Modules: market-research, financial-data, harness · Owner: AI Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high — makes model failure and unsupported quality claims inspectable; accuracy improvement is not promised.

## Objective

Make original forecast follow-through and matched-baseline quality evidence inspectable through an offline scorecard, reusing existing immutable forecasts and eligible retained outcomes.

## Approach

Human30October explicitly directs the newly appointed Lead to lead the team through the most impactful final changes. Combine AI Engineer's quality scorecard with Trader's forecast follow-through. Inventory and reuse existing evaluation.py, forecast_review.py and existing reviewed ledgers rather than duplicate numerical policies. AI Engineer proposes the exact explicit-input contract and retained-cohort route first; Lead freezes it before numerical implementation. Freeze review cutoff, targets, baseline pairing and sample/qualification rules before reviewing new outcomes. A research scorecard never promotes a model.

## Choices

Use offline deterministic scoring and private human-readable output, no model or provider. Prefer one small actually issued mature next-session cohort for end-to-end demonstration; the current US30 prospective windows must stay pending until genuinely complete. Reuse retained source observations and prior reviews only when the actual target/basis/identity/availability contract matches. Preserve forecast bytes and original known times. Missing baseline means unavailable comparison, not a synthetic origin baseline introduced after outcomes. Use existing frozen qualification thresholds if present; absent thresholds mean insufficient/unvalidated, not invented review success.

## Findings

PRSG-114 implements inference/evaluation and PRSG-83 a synthetic-only eligibility harness. forecast_review.py scores frozen ledger terminal-close rows. These implementations do not establish real model quality or an actually usable integrated scorecard. Existing PRSG-113 strong acceptance remains open and unchanged. PRSG-155's US30 forecast first target is still future at current planning time; do not score it early. Older retained issued cohorts may have mature eligible actuals; prove that with bounded metadata and provenance inspection.

## Tradeoffs

A transparent scorecard can expose poor or insufficient results without improving the model. Do not use hindsight thresholds, correlated editions as independent samples, terminal closes as intraday extrema, or consumed/inspected holdouts as untouched validation. Private actuals and outputs stay outside Git. No new rights, sources, trading, fit or promotion authority.

## Frozen Ownership and Scope

Base cca89e514ed6217d3afb980063b604a53ff069c3. AI Engineer owns only quality_scorecard.py, test_quality_scorecard.py and FORECAST_QUALITY_SCORECARD.md. Lead owns canonical pair and integration; Engineer's PRSG-157 files are disjoint. Trader financial review occurs before accepting actual score evidence. AI Engineer private artifacts live under /Users/jwtan/.codex/lead-state/PRSG161/ai; Trader under PRSG161/trader, Lead under PRSG161/lead. No shared private file writes. No commit/push by worker; return exact paths/hashes/results and command to current registered Lead. Human's goal authorizes scoped project return messages and resumed work; existing schedule pauses remain.

Allowed: plans/2026-10-30/PRSG-161-forecast-outcome-quality-scorecard.md, plans/2026-10-30/PRSG-161.harness.json, scripts/stock-research/quality_scorecard.py, tests/test_quality_scorecard.py, docs/FORECAST_QUALITY_SCORECARD.md. Protected: scripts/stock-research/evaluation.py, harness/, artifacts/, ingest/, connectors/, skills/, agent-operations/, .DS_Store. Any required policy/interface change outside these files needs a reviewed scope extension, not a workaround. No changes to original ledgers/source/model artifacts.

## When It Is Considered Done

- [x] PRSG-161-D1: Freeze a bounded explicit-input contract reusing existing ledgers/evaluators, immutable forecast/model/source references, target semantics and origin-time matched baselines; Lead reviews before numerical implementation.
- [x] PRSG-161-D2: Implement a reproducible offline scorecard with per-instrument/horizon/market sample counts and pending/insufficient/failed/qualified-for-review dispositions; distinguish terminal-close and whole-window extrema, missing actuals, correlated vintages and missing matched baselines.
- [x] PRSG-161-D3: Preserve original forecasts and require completed reviewed comparable outcomes. Report low/high/terminal errors and interval coverage/width only where their target and evidence support them; never invent a baseline or label a missing metric as success.
- [x] PRSG-161-D4: Produce and independently review an actual retained frozen-cohort scorecard plus human-readable local HTML/JSON/CSV evidence or exact per-row missing/pending reasons. At least one genuinely matured previously issued cohort is scored from existing retained approved actuals if such evidence is present; absent evidence must be resolved or remain an explicit unmet gate.
- [x] PRSG-161-D5: Focused negative/reproducibility checks pass; actual artifact/hash/issue/review/currentness provenance is demonstrated from a clean directory. No new source call, fit, calibration, risk-policy or model promotion.

## Checks

Focused command is the manifest's exact argv. Cover malformed/missing/future/stale evidence, duplicates/conflicting actuals, look-ahead and incomplete windows, wrong basis/currency/identity, absent baselines, immutability, reproducibility and bounded private output. Lead independently reviews actual retained evidence and exact scores. Fixtures establish implementation only. All checks/acceptance remain pending until executed and reviewed; existing quality gates and historical misses are unchanged.

## Frozen Interface and Origin Baseline Addendum — 30 October 2026

Lead read and independently hash/byte matched the immutable two-cohort proposal a2ed2381f18b3f76a5d1a02d606b8ad80bed35582059779d085520c7f8aa0c85(11012B), with frozen review cutoff2026-10-30T01:13:35+08:00 and null qualification policy. Both terminal_close_csv and saved_ohlc adapters are required, reusing their existing evaluators. Trader reviewed30retainedUS20Octterminalactuals and original50rowedition; the US forecasts were intraday-issued at17:30UTC, not before13:30UTCopen. New155120horizonrows remain pending at this cutoff. No terminal-only narrowing of whole-window support.

The retained origin audit contains30US baseline_point/low/high entries. Lead approves a separately versioned explicit baseline-ref contract: original audit SHA7abc1ceac2fa0362fb4e58b065b4a2c6a1b873716d8cb24d682205cdf71004d6(258139B), original manifest SHA1e8345cbc9eb1aec937a4f80160463b03b9b4854cb8a50738d9dcc9451ac811f(1028B), all original CSV/row/evidence/admission/result and issue-time bindings preserved. Paired comparisons use BOTH model and baseline original unrounded audit estimates; display-rounded CSV outcomes remain separately labeled. No new origin estimates, hindsight thresholds or postscore cohort selection. Missing or mismatched originals withhold comparison. Preserve the original null-baseline proposal as historical evidence and obtain the narrow Trader precision addendum before accepting paired comparison. This does not grant source/public/model promotion or replace strong113 criteria.

## Independent Acceptance — 30 October 2026

Lead58passed0.62s; AI58passed0.59s. Exact final scorer178d088b5169d15082ad11c834d97dd324ab0335cecf1cc0686b9834d9db95f2; testsf1408bae9615f180d95b7ae2ce76b87adb7151c2bf587330df867e41e0910e7c.

Lead clean-/tmp actualCLI exit0 independently reproduced4artifact hashes,38originalrefs unchanged; final acceptanced8b88bfa4d2260f0c851550b3f048d8df90d078b47c01a0aef0dd74c56e7e4ae. Original30US20Oct intraday-issued terminalforecasts scored:15directionhits28rangehits;5missingactual15withheld. Paired unrounded modelerror1.1533458060% vs originalbaseline1.0775827966%,12/30lowererror. One targetdate, no edge/calibration/qualification. All120newOHLCrows pending at frozen2026-10-30T01:13:35+08:00. Trader precisionreview7652383a3d52b59e4eb18a84b1361046115705db41096b753c4a2b9cccad33e0. PrivateHTML browserpreview explicitly blocked; no workaround. Human-readableHTML/JSON/CSV produced+tested; independently visually reviewed six-page directJSON staticPDF is safer readingalternative, not HTMLcontrol certification. No fit/model/provider/promotion.
