# PRSG-116 — Optional Stock Research Sentiment

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

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

## Why the ticket is created?

Explore whether attributable numerical news sentiment can improve research while keeping the tool independent of LLM access.

## Approach

Plan cutoff-safe news caching, entity-specific tone, explicit missingness and local-first sentiment evaluation before numerical-model integration.

## Choices

Compare lexicon diagnostics and small TF-IDF/linear candidates first; keep price-only fallback until separate calibration and forecast-benefit evidence exists.

## Findings

The epic has not entered repository implementation. Private contract/source reviews and academic parsing mechanics do not establish calibrated sentiment or forecast benefit.

## Tradeoffs

News rights, polling permission, historical availability and multi-entity/ETF relevance can limit usable coverage; none may be replaced with neutral zeros.
