# PRSG-113 — stock research training validation

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own baseline/nine quantile fits, calibrated artifacts and strong actual-data gates after registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/model.py`
- `scripts/stock-research/train.py`
- `tests/test_stock_research_model.py`
- `plans/2026-10-14/PRSG-113-stock-research-training-validation.md`
- `plans/2026-10-14/PRSG-113.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-113-D1: Baseline/quantile train/save/reload, no random temporal validation and reproducibility tested.
- [ ] PRSG-113-D2: Actual-data walk-forward/untouched holdout passes frozen strong-model gates and measured hardware budgets.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Frozen model acceptance contract

The baseline covers min-low, max-high AND terminal logreturn, all q05/q50/q95, conditioned on the identical horizon lead/count and instrument/leverage class. Fit/calibrate baseline and challenger using earlier data only; save both at origin. Report price-normalized endpoint MAE, terminal-return MAE, pinball per target/quantile and equal date/target weights. Near-zero baseline errors (<=1e-8 normalized units) cannot establish relative improvement and leave that gate unassessable.

Require >=5% held-out improvement separately in low and high median MAE, aggregated pinball and terminal MAE/pinball for directional promotion. Paired95% date-block CI of baseline-minus-challenger must be >0, using common date blocks across all instruments/windows; block length at least maximum origin-to-label-end session distance, minimum10sessions; deterministic seed and1000bootstrapreplicates. No holdout tuning. Endpoint90% coverage must be85–95% for EACH adequately sampled promoted class/horizon and width no worse than matched-coverage baseline. Joint envelope coverage reported separately. q05<=q50<=q95 and medianlow<=medianhigh; crossing rejects forecast/promotions rather than silent repair. >=252 unique OOS dates overall and >=100dates/10nonoverlappingblocks per provisional subgroup/horizon; smallgroups unvalidated.

Actual-data gate additionally requires evidence of contemporary universe membership/delistings and origin vintages. Current100 retrospective backfills/synthetic fixtures cannot satisfy strong dynamic-universe model acceptance. Human review required before promoting candidate artifacts. Failed/unknown gates leave researcher model/baseline only and preserve strong-model criterion incomplete. Freeze all policies before test results; no model can manufacture assured profitability.
