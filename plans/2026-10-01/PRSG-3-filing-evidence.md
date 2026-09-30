# PRSG-3 — Filing evidence detail

Type: feature · Modules: backend, frontend, financial-data · Owner: Engineer · Priority: P2 · Effort: M (2–4 person-days) · Impact: medium-high

Harness manifest: [PRSG-3.harness.json](PRSG-3.harness.json). Created 2026-10-01, Asia/Kuala_Lumpur. Owner: Engineer; acceptance: Lead.

State: planned, not assigned. Target: researchers verifying SEC filing facts. Effort: 2–4 person-days. Expected impact: medium-high verification speed and evidence clarity. Depends on the inbox item/source contract, but can be implemented from existing filing rows independently.

## Scope and source contract

Add a read-only filing detail endpoint addressed by encoded source_id/accession, returning only a matching stored record. Expose SEC filing/document links, company/CIK/ticker, form, amendment flag, report period, filing date, acceptance time with known precision/timezone, and original ingestion time. Unknown IDs return 404; safe length/encoding validation prevents path traversal. Do not read arbitrary file paths from request input.

For financial metrics, show value, unit, currency, data period, source attribution, and whether the value belongs to this filing or a separate company-facts vintage. Current `FinancialMetrics` values have limited attribution; audit extraction before presenting them as facts from the selected filing. If period/unit/accession linkage cannot be established, show unavailable or clearly separate company-level context. Do not manufacture citations for every displayed number from a general filing URL.

Frontend opens a detail panel from the inbox or filings table. Show facts separately from existing heuristic signal labels. Link to source documents; mark missing evidence, amendment differences, and extraction limitations. Generated summaries, DCFs, and recommendations are outside the MVP.

## Acceptance and measurement

Replay fixtures cover original/amended filings, absent metrics, contradictory periods, units/currency, source URLs, unknown accession and malformed input. API must preserve lineage; UI must not display a mismatched metric as selected-filing fact. Test original-source links and date labels; run full pytest and frontend checks.

Metric: 100% of displayed selected-filing metrics in a reviewed fixture set have valid period/unit and verified filing attribution; unsupported metrics are withheld or explicitly labeled contextual. Measure user time-to-source before/after on five fixed filings. No production accuracy claim without review.

Breakdown: attribution audit 0.5–1 day; API/UI 1–1.5; fixtures/review 0.5–1.5. Main risk is extraction lineage, so prototype with three forms before broader coverage. Rollback removes additive detail route/UI; stored evidence remains intact.

## When it's considered done

- [ ] PRSG-3-D1: Detail API/UI preserve original filing identity, dates, amendment status and safe source links.
- [ ] PRSG-3-D2: Every selected-filing metric has verified period/unit/accession attribution or is withheld/contextual.
- [ ] PRSG-3-D3: Amendment, missing/mismatched metrics and malformed/unknown IDs pass fixtures.
- [ ] PRSG-3-D4: Focused/full checks pass; Lead accepts diff and records coverage limits and release evidence.

Check items and manifest acceptance evidence together; usability time-to-source remains separate from functional completion.
