# PRSG-112 — Causal Stock Research Datasets

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own causal features, whole-window labels, CSV/SQLite equivalence and purged splits after role registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c162360064443307c68490d40b3e58a1eae1ec13`. Allowed paths:

- `scripts/stock-research/data.py`
- `scripts/stock-research/features.py`
- `scripts/stock-research/market_calendar.py`
- `tests/test_stock_research_data.py`
- `plans/2026-10-14/PRSG-112-stock-research-datasets.md`
- `plans/2026-10-14/PRSG-112.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-112-D1: Completed-session OHLC adjustment/calendar/missing/future and CSV/SQLite contracts tested.
- [x] PRSG-112-D2: Hand-computed extrema/week labels, availability and date-purged partitions proven.

## Evidence

Dataset/calendar implementation accepted after independent Lead review; actual training and forecasting quality remain separate unverified obligations.

## Frozen financial/data contract

Every completed label has label_available_at equal to maximum actual availability of all required outcome bars. Require label_available_at <= fit cutoff; purge across ALL instruments/windows when label/end availability reaches the next partition. Next-calendar-week extrema use ONLY following Mon–Fri exchange sessions, not intervening current-week sessions; terminal logreturn is log(C_week_last/C_origin) and includes intervening movement. Missing any required session makes the full label pending. One instrument/origin has total training weight1 divided across available horizons; repeated generation runs do not increase independent observations. Do not apply current financial/class/ETFmandate metadata retrospectively without contemporaneous evidence.


Lead implementation detail 2026-10-15: name the shared calendar module `market_calendar.py` to avoid shadowing Python standard-library `calendar` when entry points run directly from this folder. Its exchange-session calculations must respect actual early closes/holidays; use private Lead hand-computed label review fixtures as independent acceptance inputs, not model-quality evidence.


## Lead-reviewed reader and retrospective-study policy — 2026-10-15 MYT

The accepted implementation must support two explicit evidence policies. `strict` requires actual origin-time membership, instrument identity/mandate, feature-bar vintages and availability. Select a revision only from hash-verified saved generations whose observation was known at the origin; latest state alone is not a historical as-of dataset. Never replace retrieval/known time with the vendor session timestamp. Deduplicate repeated files/generations deterministically; distinct values at the same identity/session/known time are a conflict, not input-order priority.

`research-retrospective` permits training-code evaluation on downloaded historical OHLC with explicitly declared contemporary membership, delisting, adjustment-vintage and first-availability gaps. This bounded study is approved within the existing numerical research program. It preserves actual source/retrieval/known times and writes every admitted gap into the dataset/artifact receipt; it must never relabel those rows point-in-time, promote a model, satisfy the strong-model acceptance gate, or imply prospective performance. Missing OHLC, required sessions, incompatible adjustment/currency, invalid financial identity or future outcome information relative to fit/calibration boundaries remain rejection conditions. Freeze evaluation dates/configuration before inspecting outcomes. This permission does not supply missing market data or historical instrument mandates.

Preserve the canonical history schema exactly in both CSV and read-only SQLite paths, including explicit nullable values and strict boolean/integer handling. Carry generation/manifest hashes, code-to-stable-security binding and declared calendar/package/schedule/adjustment policy through readers. Current metadata is current-only; absent dated class/leverage is unavailable and cannot be inferred from today's ETF label. Symbol reuse or conflicting stable identity must be rejected or partitioned by independently dated identity evidence.

Benchmark-relative features consume separately supplied, attributable benchmark history under the same availability/calendar/basis policy. Do not silently add benchmark symbols to discovery or use portfolio/report symbols. If benchmark input is absent, use an explicit missing-feature mask/status and compatible fixed feature schema; do not fabricate a zero return or silently replace it with an arbitrary discovered instrument. Model training must freeze whether it uses the compatible price-only/no-benchmark variant before evaluation.

Implementation acceptance of these readers and fixtures is distinct from actual-data training and model-strength acceptance. A retrospective study must still purge labels by their declared actual availability before the next fit/evaluation cutoff; do not erase delayed revisions or allow outcomes from the future. For causal origin feature admission in research mode, distinguish the assumed historical vintage from measured availability and retain its unverified status.


## Lead implementation acceptance — 2026-10-15 MYT

Lead reviewed the four new implementation/test files and exact six-path frozen scope. Final focused checks: **32passed in0.47s**. A separate Lead fixture verified whole-window low97/high99 entirely below reference100 without clamping, while incomplete longer windows remained pending. Hand-computed Thanksgiving-week labels, holiday/earlyclose handling, next-week boundaries, missing/late actuals and reference revisions, open-boundary date purges and total origin weights were independently reviewed.

Readers preserve all29 canonical history columns and hash-checked generation sidecars, typed integer/decimal-string security identity, revisions, measured price/unit availability and explicit unknown provider finality/timezone. CSV and read-only SQLite paths share normalization and reject conflicts; SQLite canonical snapshot rows, rather than its main file alone, define the content receipt. Inputs/sidecars have aggregate budgets; histories are indexed per symbol and exchange sessions cached. Metadata provenance/timing, compatible class/leverage, benchmark availability and missingness remain explicit. A completed flag alone cannot admit price observations from before the exchange close.

The approved retrospective feature policy preserves actual label availability and can leave historical folds empty after fresh backfill. Strict row availability alone is not proof of historical universe membership, mandates, delistings or adjustment factors. These implementation/fixture checks do not train a model, establish accuracy, demonstrate measured resource budgets, or satisfy PRSG-113 strong-model gates. No provider, credentials, LLM, Colab or model-promotion operations occurred.

## Why the ticket is created?

Create consistent training inputs whose features and realized labels respect actual information availability.

## Approach

Normalize CSV, read-only SQLite and saved generations; construct exchange-calendar extrema and terminal-return labels with chronological purging.

## Choices

Share one canonical OHLCV schema across readers and use explicit missingness rather than retrospective zero filling.

## Findings

Reader/calendar/label fixtures and CSV/SQLite parity were reviewed; a present-day history backfill still cannot prove historical universe membership.

## Tradeoffs

Availability purging may leave insufficient folds, which remains visible rather than creating a misleading historical validation.
