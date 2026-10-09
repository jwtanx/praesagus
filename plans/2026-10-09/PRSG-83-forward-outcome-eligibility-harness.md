# PRSG-83 — Add a forward-only forecast outcome eligibility harness

Type: feature · Modules: harness, financial-data · Owner: Engineer · Priority: P1 · Effort: M (3–5 person-days, estimate) · Impact: high — prevents incomparable or insufficiently sourced outcomes from entering precision metrics; the operational data source remains unverified.

Created 2026-10-09 MYT. Planning base: `bfbb76cf9bcfeecd4333568c58da6d131de12579`. Scope status: accepted for the bounded offline implementation below; reviews completed by Trader and Engineer on 2026-10-09.

## Objective

Add a deterministic, offline assessment for a future version-2 forecast-outcome record. It checks comparability metadata and returns `ready_for_human_review` or `blocked` with reasons. It never grants data rights, marks a real market observation verified, admits a row to scoring, or calculates forecast metrics. This is a separate standard-library API; it does not route records into the existing v1 scoring evaluator.

## Evidence and decision

PRSG-81 found zero legacy rows eligible for strict close-to-close scoring from tracked evidence. Historical v1 ledger rows remain immutable. The first operational contract is US-only, pending proof of an operator-provisioned source and permitted private retention/research rights. Trader recommends separating vendor-reported bars from exchange-certified closes. Engineer recommends versioned MIC, listing-map and venue-calendar references, exact UTC session instants, and fail-closed checks. No supported source rights, source capture, or reference fixtures are verified yet.

## Accepted contract and implementation boundaries

- Implement a pure, standard-library function in `outcome_v2.py` that assesses an in-memory, schema-versioned v2 record against explicit synthetic instrument/calendar/evidence fixtures. Do not persist v2 rows or send them through the v1 evaluator/scorer.
- Tie each record to `forecast_id` and a frozen v1 ledger revision. Require listing identity/MIC and effective mapping at reference and target, currency, declared source class and observation kind, price-field semantics, adjustment basis and immutable series-vintage ID, reference/target session dates and exact close instants, horizon kind/count, forecast cutoff, source availability/observation/retrieval times, calendar/instrument fixture versions, synthetic evidence fixture ID, and review state.
- Validate reference availability and retrieval at or before the forecast cutoff. Validate actual observation against the target session close, source availability at/after the close, retrieval at/after availability, and all actual timestamps at/before review time. Unknown availability stays null and cannot be inferred from retrieval time.
- Count trading sessions excluding the reference session and including the target. Require fixture-confirmed sessions, exact close instant (including early closes), valid effective listing mapping at both endpoints, matching MIC/currency/field/adjustment semantics, and identical immutable series vintage. Intraday snapshots are blocked from close-to-close comparison.
- Return separate `maturity`, `provenance_status`, `rights_status`, `review_status`, and `assessment_status` fields with deterministic reasons. Synthetic records may reach only `ready_for_human_review`; rights remain `unverified` and no state admits scoring. Missing/denied rights, review, fixture, or comparability gates are `blocked`.
- A fixture digest verifies identity against supplied bytes only. It does not prove source authenticity, price correctness, entitlement, license, or redistribution rights.
- Keep legacy v1 evaluation and CSV bytes unchanged. Do not add a v2 status to the v1 enum or append v2 columns to the v1 CSV. Legacy provenance gaps remain `legacy_unverifiable` in this separate assessment design; no existing row is rewritten.
- Cover with inline synthetic-only cases: a complete record reaching human review; missing/wrong MIC or listing effective dates; currency mismatch; intraday input; unknown price/adjustment semantics; mismatched vintage; reference availability/retrieval after forecast cutoff; null source availability without an explicit unknown/fallback declaration; actual before target close or invalid retrieval ordering; holiday/early-close mismatch; off-by-one horizon; absent fixture reference; unverified/denied rights or pending review; and future target still pending.

The module must not calculate returns, direction hits, ranges, interval scores, Brier scores, or other forecast-performance metrics. Only a later separately scoped and rights-reviewed workflow may consider scoring real outcomes.

## Explicit exclusions

Do not fetch provider/exchange data; inspect or modify private stores; write or backfill the historical v1 ledger; add real-market reference/data fixtures; infer entitlements or data rights; score outcomes; modify forecast/model logic, report JSON, dashboard, schedule, production skill, or Moomoo indicator display; or claim US source coverage is operational. No Malaysia eligibility in this first stage. No new dependency without Lead approval.

## Frozen write set

`plans/2026-10-09/PRSG-83-forward-outcome-eligibility-harness.md`, `plans/2026-10-09/PRSG-83.harness.json`, `harness/engineering/price-prediction/outcome_v2.py`, `harness/FORECAST_REVIEW.md`, and `tests/test_outcome_v2.py`. Base SHA is frozen in the manifest. Protected: `harness/engineering/price-prediction/forecast-ledger.csv`, all `ingest/`, `connectors/`, `artifacts/`, `skills/`, report schedules, backend/frontend, and any private storage outside the repository.

## When it's considered done

- [x] PRSG-83-D1: Define an in-memory v2 record contract separate from the legacy CSV, with no persistence or scoring dispatch.
- [ ] PRSG-83-D2: Implement a standard-library assessment that returns `ready_for_human_review` or `blocked`, with rights explicitly unverified and no score fields.
- [ ] PRSG-83-D3: Add synthetic-only tests for valid metadata and rejection of identity, source-time, session, horizon, basis/vintage, evidence-reference, rights and review failures.
- [ ] PRSG-83-D4: Demonstrate unchanged legacy evaluator behavior and byte-for-byte unchanged v1 ledger.
- [ ] PRSG-83-D5: Lead reviews complete scope and validation evidence.

A passing synthetic case is only structurally ready for human review. It does not establish authentic data, entitlement, licensing, forecast skill or permission to score.

## Dependencies and unresolved decisions

Before freezing implementation, Engineer and Trader must confirm that this scope is compatible with current evaluator interfaces and financially coherent. Trader requires rights review to remain independent of provenance checks: the fixture-only contract may validate declared metadata but cannot certify collection, retention, analysis, derivatives, or publication rights. A later source-onboarding scope must verify operator entitlement and license. Bind the exact listing mapping at both endpoint dates, source observation/availability/retrieval times, calendar and series vintage; unknown source availability remains null and cannot assert pre-cutoff availability. Synthetic fixtures must be explicitly labeled synthetic and cannot be treated as licensed market evidence. If source semantics require a different schema, Lead revises scope before implementation.
