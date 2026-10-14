# PRSG-110 — stock research api contracts

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Bounded standalone REST discovery and typed field/unit/OHLC contracts reusing secure signing.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/provider.py`
- `scripts/stock-research/contracts.py`
- `scripts/stock-research/config.py`
- `scripts/stock-research/config.example.toml`
- `scripts/stock-research/requirements.txt`
- `tests/test_stock_research_provider.py`
- `plans/2026-10-14/PRSG-110-stock-research-api-contracts.md`
- `plans/2026-10-14/PRSG-110.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-110-D1: Mocked screen/snapshot/history paging and field units/errors/caps validated; no account/order access.
- [ ] PRSG-110-D2: Capability receipt distinguishes exact native UI counts, entitlements and quota unknowns.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.
