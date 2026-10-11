# PRSG-93 — Define safe history rejection diagnostics

Type: spike · Modules: financial-data, connectors, docs · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.2 person-day, estimate) · Impact: medium-high — makes the observed intake blocker actionable without retaining untrusted responses; no coverage or predictive gain is established.

Created 2026-10-12 MYT. Status: in progress, Lead accepted under the human's continuation of forecast-input readiness. Frozen base: `74fc1c36a66c2880a0bc38949b3afe8ebb7cff16`. Engineer owns bounded read-only technical review; Lead owns this ticket and acceptance. Repository write scope is only this spec and its manifest.

## Question and timebox

Within 15–20 minutes, define the smallest replayable diagnostic contract that can distinguish a future history rejection's validation stage using only trusted fixed categories. PRSG-90 persisted a failed attempt but discarded the screened body; PRSG-91 found unresolved example/envelope ambiguities, and PRSG-92 fixed a separate date-consistency guard. None identifies the actual earlier rejection. A repeated request with the same broad failure would add little evidence. No new live request is authorized by this spike.

## Accepted read-only scope

Inspect the existing store normalization errors, collector worker frame/parse/outcome/CLI serialization, core errors and consumers/tests. Compare: extending fixed failure categories versus a separate bounded stage enum while retaining existing failure semantics. Explain framing/version/compatibility, bounded serialization, malformed-frame handling, CLI consumers, rejected-body disposal and whether persistence needs any change. Prefer no existing-store migration and no public report/schema change. Every returned category must come from an explicit allowlist; unknown errors stay generic.

Distinguish malformed JSON/envelope, logical provider rejection, missing required history metadata, bad date/offset relationship, invalid rows and later core validation only where the checked code can establish the stage. Do not expose provider return-message/code values, field names taken from input, row values, identifiers, exception strings, response bodies, credentials or operational paths. Category precision must not imply authentication/entitlement assurance or a particular cause in PRSG-90.

Engineer returns a concrete proposed contract, exact minimal implementation/consumer/test paths, compatibility implications and authored failure-case matrix. Private in-memory deterministic design examples are allowed; label them synthetic. No repository implementation/test changes, credentials/Keychain/private store/provider access, ad hoc client, additional data request, schema weakening, inferred metadata/pagination whitelist, forecast/method/confidence/ledger/report changes or subagents. Existing privacy/security/temporal/quota controls remain binding.

## When it's considered done

- [ ] PRSG-93-D1: Review current error/frame/output consumers and compare bounded diagnostic alternatives with exact compatibility and privacy limits.
- [ ] PRSG-93-D2: Return a fixed-category contract and meaningful malformed/secret/unknown/history-stage replay matrix, plus exact proposed implementation/test paths.
- [ ] PRSG-93-D3: Lead independently accepts a concrete next scope or blocker and verifies protected files unchanged; no live request or repair occurs in this spike.

## Delivery and next gate

Checks are contract review, failure-matrix review, preservation and Lead decision. Engineer's repository write set is empty; sanitized findings belong in the approved private Lead context. Lead alone updates these two ticket files. Any implementation requires its own accepted frozen scope. After implementation and independent privacy/regression review, any future data probe needs a separately frozen single-job plan and fresh resources using the existing collector; this ticket grants none. Completed diagnostics still do not establish comparable completed prices, source availability, rights or forecast eligibility.
