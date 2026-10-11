# PRSG-91 — Review the history response contract offline

Type: spike · Modules: connectors, financial-data, docs · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-day, estimate) · Impact: medium-high — tests a concrete intake blocker; no forecast coverage or accuracy improvement is established.

Created 2026-10-11 MYT. Status: complete; Lead independently accepted the offline findings. The actual live rejection remains unexplained and forecast readiness remains blocked. Frozen base: `8d10f41ca106ce4b5020fcfdd947811708d6ee25`. Engineer performed read-only contract review; Lead owns the ticket and decision. Repository write scope is only this spec and its manifest.

## Question, evidence and timebox

Within 30 minutes, does the existing daily-history request/response screening demonstrably reject a documented supported shape, or is the PRSG-90 live rejection still unexplained? PRSG-90 performed one exact US.SPY daily/unadjusted/100-bar request ending 9 October; it failed `invalid-response` and retained zero normalized rows. The screened body was discarded, so an exact live fault cannot be reconstructed. Existing HTTP transport and signing-path evidence do not prove logical API success. This review needs no credentials, private store, live request or login.

## Accepted scope and approach

Read `ingest/market_collector.py`, `ingest/private_market_store.py`, `connectors/moomoo_rest.py`, `connectors/moomoo_rest_live.py` and their existing tests at the frozen base. Compare request bounds, response envelope/return-code handling, daily-bar date/time/offset/close types and normalization invariants against the [official history contract](https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline). Record exact primary-source support and unavailable dynamic documentation. Distinguish a documented example, an authored fixture and an actual provider capture. Never call fixtures proof of the discarded response.

Run the existing focused collector/store/REST tests in the clean frozen checkout using approved Python. If useful, an in-memory authored example may be evaluated privately without changing tracked files; preserve secret rejection, duplicate-date, nonfinite-close, timestamp, quota and failure controls. Do not weaken screening, infer a specific live rejection field, create a client, access credentials/Keychain/store, issue a provider request or change code/tests/reports/methods. No subagent or overlapping review assignment.

Return an evidence-linked contract comparison, exact commands/results, reproducible candidate discrepancy if any, known limitations and a recommended next step. An actual defect requires a separate frozen implementation/regression scope before any fix. If no defect is demonstrated, retain the explicit unknown; a future diagnostic capture needs its own accepted bounds and privacy handling. Do not repeat PRSG-90 or expand instrument coverage.

## When it's considered done

- [x] PRSG-91-D1: Engineer compares documented request/response semantics with the existing screening and distinguishes supported facts, authored examples and unresolved live cause.
- [x] PRSG-91-D2: Exact focused tests and any private deterministic replay are recorded without repository or secret/provider access.
- [x] PRSG-91-D3: Lead independently reviews findings, verifies protected paths unchanged and records a bounded next decision or explicit blocker.

## Checks and delivery

The manifest maps contract review, focused regression replay, preservation and Lead decision. Lead independently reviews returned evidence before completion. Only these two ticket files can be committed. Preserve all unrelated shared-checkout edits, particularly the existing projection edit. No new predictions, scoring, confidence change or performance claim. This is an offline feasibility review, not authorization to repair production behavior or take another live sample.

## Reviewed findings and evidence

The fixed request is a documented bounded subset. Engineer identified three response-contract findings; Lead independently retrieved all five primary documentation pages and matched their full-document hashes to the recorded 19:37 MYT retrievals. Documentation is public contract evidence, not an actual market response or proof of entitlement.

1. The endpoint examples omit date and offset fields that their field tables describe. Existing connector/store checks require them. An authored example-shaped reduction rejects and explicit consistent metadata passes. Whether the example is incomplete or production metadata is optional remains unresolved; no fallback was introduced.
2. The endpoint describes pagination within data, while general quote/pagination guidance describes outer pagination and a different next-time location. Exact store envelope screening rejects an authored valid row with outer pagination. These conflicting descriptions do not establish what the discarded SPY response contained; no extra-key whitelist was broadened.
3. The daily-date relationship described by the endpoint is not enforced. A synthetic row with timestamp1779249600000, offset-240 and stated date20260521 passes normalization, although its local date is20May. Core validation also lacks the relation check. Existing positive fixtures contain another timestamp/date mismatch. This is a reproducible temporal guard gap that permits a contradictory row; it cannot explain a rejection.

Engineer ran existing focused tests: approved Python with bytecode/cache writes disabled, `-m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py`: 461 passed in2.61s. Lead independently repeated that exact focused set: 461 passed in2.62s. Lead inspected and replayed the pure authored24case script: 21rejected/3accepted, all expected outcomes. The three accepted cases were a consistent row, the deliberately contradictory date and empty logical success. Secret, duplicate, invalid-date/type, nonfinite/invalid-close, over-count and provider-error cases rejected. No real credentials, Keychain, private store or provider call was used for the review.

Lead independently verified protected implementation/tests/report/ledger/calendar paths have no diff against the frozen base in the isolated checkout. The shared checkout retains only its unrelated projection edit with unchanged original hash. Engineer wrote only authorized private review evidence. No production behavior or financial artifact changed.

Lead accepts D1–D3. The next bounded implementation candidate is to enforce daily timestamp/explicit-offset/date consistency in both core and store validation, replacing contradictory positive fixtures and adding mismatch/boundary regressions. Missing metadata and unresolved pagination remain fail-closed. Controlled diagnostics are a separate scope decision; no new live sample is authorized here. Forecast targets remain unsupported, and the precise PRSG-90 rejection cause remains unknown.

Primary references: [Chinese endpoint contract](https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline.md), [English endpoint contract](https://open.moomoo.com/api/quote/basic-data/history-kline.md), [naming dictionary](https://open.moomoo.com/zh-cn/api/quote/naming-dictionary.md), [quote overview](https://open.moomoo.com/zh-cn/api/quote/overview.md), [pagination guidance](https://open.moomoo.com/zh-cn/api/quote/pagination.md). No source update dates were supplied; the offset example's seasonal label is inconsistent, so it cannot justify an inferred market-zone fallback.
