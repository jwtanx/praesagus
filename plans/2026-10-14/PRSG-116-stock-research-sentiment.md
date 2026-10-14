# PRSG-116 — stock research sentiment

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer model logic and Engineer RSS plumbing: permitted local-first cutoff-safe sentiment, optional remote/fallback.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/news.py`
- `scripts/stock-research/sentiment.py`
- `tests/test_stock_research_sentiment.py`
- `plans/2026-10-14/PRSG-116-stock-research-sentiment.md`
- `plans/2026-10-14/PRSG-116.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-116-D1: RSS conditional caching/dedup/backoff/budgets and text/source/cutoff handling tested.
- [ ] PRSG-116-D2: Numeric local sentiment calibration/training and forecast benefit assessed; absent/unvalidated addon falls back to price-only.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.
