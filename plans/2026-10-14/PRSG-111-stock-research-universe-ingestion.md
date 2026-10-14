# PRSG-111 — stock research universe ingestion

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Dynamic 80-stock/20ETF plus10speculative selection and immutable vintages/actuals retention.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/universe.py`
- `scripts/stock-research/collect.py`
- `scripts/stock-research/storage.py`
- `tests/test_stock_research_universe.py`
- `plans/2026-10-14/PRSG-111-stock-research-universe-ingestion.md`
- `plans/2026-10-14/PRSG-111.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-111-D1: Deterministic dedup/refill/liquidity/sector/exposure filters and honest shortfalls tested.
- [ ] PRSG-111-D2: Incremental histories/revisions and prior forecast instruments retained in timestamp folders.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Storage/universe invariants

Defaultparent ~/Documents/stock-research-data; every collect/train/predict generation creates exclusiveMYT YYYY-MM-DD_HHMMSS folder, rejects collisions, neveroverwrites. Artifacts/cache/modelstate liveinsidegenerationfolders. Latestcompatible state/modeldiscovery reads manifests; no destructive fixedlatestcache/model writes. In-repoparents require completeGit exclusion and reject repositoryroot/codepaths.

Universeselection is fromwholemarketdiscovery, not privateportfolio/reportlists. ForETFverifiedregistrytagging doesnotseedmarket discovery; sector/exposurefamilies need sourcedidentity. Corestocks>=5price,median20turnover>=25M,>=252validcompletedbars, sectorcap16;ETFsameprice/turnover/history and verifiedsignedleverage/reset, cap2perfam. Compute medians fromhistoricalbars, never substitute screenermean. Up to10speculativenamesdisjoint price>=1/median20turnover>=5M; flagsprice<5 orhistory<252 orATRfraction>.08 orabsreturn>.15. Noforceddailyrotation orfill.

Retain priorforecastsymbols inactualscollection even afterleavingselection; revisionvintagesappendonly. Point-in-timemembershipstarts atobservedfirstcollection; don'tbackfillfictionalhistoricalmembership. Historical backfillmode explicitlyretrospective and cannotqualifystrongdynamicuniverseacceptance. Defaultconfigsmallboundedrequestbudget+transparentpartialcoverage; resume incrementalcollector withoutautomaticretry orsilentquotaexpansion.
