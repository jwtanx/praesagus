# PRSG-112 — stock research datasets

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own causal features, whole-window labels, CSV/SQLite equivalence and purged splits after role registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/data.py`
- `scripts/stock-research/features.py`
- `scripts/stock-research/calendar.py`
- `tests/test_stock_research_data.py`
- `plans/2026-10-14/PRSG-112-stock-research-datasets.md`
- `plans/2026-10-14/PRSG-112.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [ ] PRSG-112-D1: Completed-session OHLC adjustment/calendar/missing/future and CSV/SQLite contracts tested.
- [ ] PRSG-112-D2: Hand-computed extrema/week labels, availability and date-purged partitions proven.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Frozen financial/data contract

Every completed label has label_available_at equal to maximum actual availability of all required outcome bars. Require label_available_at <= fit cutoff; purge across ALL instruments/windows when label/end availability reaches the next partition. Next-calendar-week extrema use ONLY following Mon–Fri exchange sessions, not intervening current-week sessions; terminal logreturn is log(C_week_last/C_origin) and includes intervening movement. Missing any required session makes the full label pending. One instrument/origin has total training weight1 divided across available horizons; repeated generation runs do not increase independent observations. Do not apply current financial/class/ETFmandate metadata retrospectively without contemporaneous evidence.
