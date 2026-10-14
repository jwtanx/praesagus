# PRSG-115 — stock research exports guide

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Timestamped CSV/XLSX bundles, safe output paths, zero-argument defaults and reproducible dummy preview.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/export.py`
- `scripts/stock-research/run.py`
- `scripts/stock-research/demo.py`
- `scripts/stock-research/README.md`
- `scripts/stock-research/examples/`
- `.gitignore`
- `tests/test_stock_research_exports.py`
- `plans/2026-10-14/PRSG-115-stock-research-exports-guide.md`
- `plans/2026-10-14/PRSG-115.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-115-D1: Master/horizons/top20/ranking/sector/ETF/speculative/evaluation exports reconcile with typed values and safe workbook formatting.
- [ ] PRSG-115-D2: Zero-arg/demo/offline workflows, immutable timestamp collisions and Git exclusion proven; actual bundle verified separately.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.
