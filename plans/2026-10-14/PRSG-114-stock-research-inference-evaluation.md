# PRSG-114 — stock research inference evaluation

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own four-window inference/immutable ongoing scores with ETF-aware ranking after registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/inference.py`
- `scripts/stock-research/predict.py`
- `scripts/stock-research/evaluation.py`
- `scripts/stock-research/ranking.py`
- `tests/test_stock_research_inference.py`
- `plans/2026-10-14/PRSG-114-stock-research-inference-evaluation.md`
- `plans/2026-10-14/PRSG-114.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-114-D1: Numerical forecasts/dates/invalid input/baseline labels and long-only actions/caps tested.
- [ ] PRSG-114-D2: Matured saved forecasts/baselines matched against actuals with pending/missing and no silent model changes.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Frozen decisions/evaluation contract

Cost c is nonnegative roundtrip fraction including fees/spread/slippage; unknown is not0. Gross medianR=exp(q50_terminal_logreturn)-1. ThresholdT=max(.005,2c), or max(.01,2c) when abs(leverage)>1. Compare grossR withT directly, not a double-subtracted cost: R>T BUYcandidate, R<-T SELL/avoid, elseWATCH, subject to input and horizon/class/terminal validation. Baseline or unvalidated candidate =>WATCH/research-only. Missing data/tradability =>NO TRADE. BUYrisk score uses(R-c)/holding-period-volatility; SELLresearch score uses(-R)/risk and is not short-sale profit. Numeric bull/bear/disconfirming/reason fields have no invented causal claim.

Persist funddirection separately from underlyingexposuredirection; a BUYinverseETF is bearish underlying exposure. Negative sign never negates the actual fundforecast twice. Top20 leveraged/inverse union counts each -2/-3 fund once. Exposure-family cap treats inverse/long variants as commonfamily; unknown ETF metadata excludes verified buckets/actions.

Each origin stores immutable model+baseline predictions and exact sessionwindow. Evaluate ONLY completed windows against complete actualOHLC even when symbol leaves currentuniverse. Missingactuals/pendingwindows never score as0. Preserve prior outcome revisions and underlying actual provenance. Ongoing scoring never automatically retrains, recalibrates or promotes models.
