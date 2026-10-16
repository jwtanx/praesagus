# PRSG-114 — Saved Model Inference and Forecast Evaluation

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own four-window inference/immutable ongoing scores with ETF-aware ranking after registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `0fc637f80372610b44d45db9536b63e79d8086fb`. Allowed paths:

- `scripts/stock-research/inference.py`
- `scripts/stock-research/predict.py`
- `scripts/stock-research/evaluation.py`
- `scripts/stock-research/ranking.py`
- `tests/test_stock_research_inference.py`
- `plans/2026-10-14/PRSG-114-stock-research-inference-evaluation.md`
- `plans/2026-10-14/PRSG-114.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-114-D1: Numerical forecasts/dates/invalid input/baseline labels and long-only actions/caps tested.
- [x] PRSG-114-D2: Matured saved forecasts/baselines matched against actuals with pending/missing and no silent model changes.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Frozen decisions/evaluation contract

Cost c is nonnegative roundtrip fraction including fees/spread/slippage; unknown is not0. Gross medianR=exp(q50_terminal_logreturn)-1. ThresholdT=max(.005,2c), or max(.01,2c) when abs(leverage)>1. Compare grossR withT directly, not a double-subtracted cost: R>T BUYcandidate, R<-T SELL/avoid, elseWATCH, subject to input and horizon/class/terminal validation. Baseline or unvalidated candidate =>WATCH/research-only. Missing data/tradability =>NO TRADE. BUYrisk score uses(R-c)/holding-period-volatility; SELLresearch score uses(-R)/risk and is not short-sale profit. Numeric bull/bear/disconfirming/reason fields have no invented causal claim.

Persist funddirection separately from underlyingexposuredirection; a BUYinverseETF is bearish underlying exposure. Negative sign never negates the actual fundforecast twice. Top20 leveraged/inverse union counts each -2/-3 fund once. Exposure-family cap treats inverse/long variants as commonfamily; unknown ETF metadata excludes verified buckets/actions.

Each origin stores immutable model+baseline predictions and exact sessionwindow. Evaluate ONLY completed windows against complete actualOHLC even when symbol leaves currentuniverse. Missingactuals/pendingwindows never score as0. Preserve prior outcome revisions and underlying actual provenance. Ongoing scoring never automatically retrains, recalibrates or promotes models.

## Lead display decision — validated candidates and visible research

Trader's six-case financial boundary review was independently reconciled on 2026-10-15. The numerical thresholds and promotion gates are unchanged. Missing required cost is NO TRADE, never cost zero; unvalidated model/baseline forecasts remain WATCH/research-only when inputs otherwise pass. Failed data/tradability takes precedence.

`top20.csv` and Summary's primary candidate table contain up to 20 validated BUY/SELL candidates that pass data/tradability, required metadata, cost, diversity and unstarted-window checks. Do not fill the table with unvalidated forecasts or force a BUY/SELL balance. A run without a qualifying promoted model reports zero validated candidates. Preserve all available numeric research forecasts in Master/Forecasts and a separately labeled WATCH/research diagnostic table in Summary, with model status, validation blocker and reasons. Diagnostic rows do not count toward the primary top20; do not imply missing forecasts or hide usable research merely because promotion is blocked. This is an output distinction, not a new financial policy or evidence of predictive accuracy.

## Accepted implementation release — 2026-10-15 MYT

Lead re-freezes at63d17c706c27731309c2ca982404e9d37ebeb3ff after accepted PRSG-113 research implementation and exact compact resource checkpoint. PRSG-113 actual-data/quality/hardware D2 stays open; this release implements research inference and scoring without promoting a model. AI Engineer owns only the five implementation/test paths above; Lead owns the two ticket records. No provider, storage, training, dataset, dependency or financial-policy changes are released.

Reuse the versioned trusted model/runtime contract and actual per-fund numerical predictions from PRSG-113. Load a configured existing model without fitting or silently selecting an untrusted artifact. Save model and matched baseline results, identity/currency/adjustment/data/model versions, issue/as-of/reference times, explicit exchange sessions and dates, and all failure/status/reason fields. All four windows use the same completed-session reference close. Outer endpoint quantiles and median whole-window extrema remain distinct; never force the interval to contain the reference. Invalid quantiles, nonpositive converted prices, expm1 overflow/underflow, missing compatible model/baseline, unknown mandate or mismatched identity/basis produce explicit unavailable/invalid results, not fabricated numbers.

Inference feature cutoff is the actual issued/as-of time, using completed bars only; the reference session close is not a false availability timestamp for data actually retrieved later. Preserve research-retrospective gaps when applicable; current metadata cannot become historical membership. Require latest usable completed regular session and explicit staleness/partial-bar handling. A window is started when as-of reaches its first exchange open; retain its original forecast but exclude it from fresh-entry candidates. Prediction never reads future bars to construct features or labels.

Freeze a typed versioned forecast/evaluation payload for PRSG-115 before its implementation. Public Python functions return typed/dictionary payloads suitable for a shared open generation; CLI standalone may own and finalize one stock-research-prediction generation. Do not append to finalized manifests. Run orchestration/CSV/XLSX/shared-generation storage support remains PRSG-115 Engineer scope; request an exact path extension if an integration dependency cannot be satisfied without it. Prediction artifacts must expose forecast_symbols/pending_forecast_symbols for later collection of exited names, and immutable per-issuance model+baseline rows. --offline prohibits provider and LLM calls; import/help/offline tests need no credentials. Online standalone may reuse the existing reviewed collector without modifying its provider contract; never collect twice in a shared run. No training/model promotion or LLM price inference.

Score only complete ended windows against original matched-security actual OHLC visible at the review cutoff. Missing, pending, stale/incompatible or identity/basis-conflicting actuals are unscored with reason. Retain outcome revisions/provenance separately from immutable predictions, including exited symbols; do not overwrite or treat a later prediction as actual. Export per-forecast and cumulative model/baseline endpoint MAE, pinball, endpoint coverage/width and terminal-return diagnostics by horizon/class/leverage; distinct-session/calendar grouping and weighting must be explicit. Scoring does not retrain, calibrate or promote. Freeze deterministic fixtures including holidays/next-week boundaries, started windows, gaps entirely above/below reference, threshold equality/cost/inverse direction, diversity caps, model rejection, pending/missing/revised actuals and offline CLI behavior.

## Summary visibility clarification

Available numerical forecasts with NO TRADE actions (for example missing required cost or identity evidence) remain visible in the secondary main-panel research diagnostics alongside WATCH rows, retaining their actual action and reasons. They never enter the primary validated top20 and are never relabeled WATCH to hide an input failure. Keep speculative rows in their separate panel. Display counts distinguish available numerical forecasts from validated candidates. ETF issuer/security proof remains required as in PRSG-111; stock share-class deduplication does not impose an additional ETF-manager concentration cap.

## Implementation acceptance — 2026-10-15 MYT

Lead independently reviewed all five implementation/test paths and the two records; final exact three-suite check passed116tests in7.03s (owner116/7.02s). Deterministic cases verify four windows, no fit calls, cutoff/model/identity/basis rejection, exact quantile conversions, gaps, immutable saved predictions, ended/pending/missing/revised actuals including exited names, intraday weighting and long-only ranking. Trader financial review informed the final ETF stock-group distinction, manager dedup correction, numeric NO TRADE visibility and full reference-to-next-week-end risk span; those fixes have focused regressions.

Initial implementation base63d17c7 is retained in private scope history; review base advanced to delivered corrective dependency0fc637f without changing these five paths. Clean-checkout delivery isolates the accepted patch from concurrent PRSG-115 export support work. D1/D2 here accept implementation and fictional OHLC review regressions, not actual provider forecasts or model quality. PRSG-113 actual-data/strong-model/full hardware gates remain open; current research artifacts yield zero validated BUY/SELL candidates. Component-reader adoption for combined export runs remains a bounded integration follow-up after PRSG-115 storage API is reviewed. Mandatory hooks/push are separate delivery gates and their results are recorded only after execution.

## Why the ticket is created?

Generate four explicit forecast windows and score original saved predictions against later realized OHLC.

## Approach

Load trusted existing artifacts without retraining; save matched baselines, long-only decisions and append-only pending/missing/scored outcomes.

## Choices

Use the three-session decision horizon and diversity caps; keep unvalidated numerical research separate from qualified BUY/SELL candidates.

## Findings

Inference/evaluation mechanics passed deterministic review. No actual promoted strong model or prospective trading performance has been established.

## Tradeoffs

Missing costs, identities or validation can exclude candidates even when numerical forecasts remain available for research.
