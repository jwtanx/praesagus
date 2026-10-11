# PRSG-91 — Review the history response contract offline

Type: spike · Modules: connectors, financial-data, docs · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-day, estimate) · Impact: medium-high — tests a concrete intake blocker; no forecast coverage or accuracy improvement is established.

Created 2026-10-11 MYT. Status: in progress. Lead accepted this bounded continuation of the selected forecast-input readiness direction. Frozen base: `8d10f41ca106ce4b5020fcfdd947811708d6ee25`. Engineer performs read-only contract review; Lead owns the ticket and decision. Repository write scope is only this spec and its manifest.

## Question, evidence and timebox

Within 30 minutes, does the existing daily-history request/response screening demonstrably reject a documented supported shape, or is the PRSG-90 live rejection still unexplained? PRSG-90 performed one exact US.SPY daily/unadjusted/100-bar request ending 9 October; it failed `invalid-response` and retained zero normalized rows. The screened body was discarded, so an exact live fault cannot be reconstructed. Existing HTTP transport and signing-path evidence do not prove logical API success. This review needs no credentials, private store, live request or login.

## Accepted scope and approach

Read `ingest/market_collector.py`, `ingest/private_market_store.py`, `connectors/moomoo_rest.py`, `connectors/moomoo_rest_live.py` and their existing tests at the frozen base. Compare request bounds, response envelope/return-code handling, daily-bar date/time/offset/close types and normalization invariants against the [official history contract](https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline). Record exact primary-source support and unavailable dynamic documentation. Distinguish a documented example, an authored fixture and an actual provider capture. Never call fixtures proof of the discarded response.

Run the existing focused collector/store/REST tests in the clean frozen checkout using approved Python. If useful, an in-memory authored example may be evaluated privately without changing tracked files; preserve secret rejection, duplicate-date, nonfinite-close, timestamp, quota and failure controls. Do not weaken screening, infer a specific live rejection field, create a client, access credentials/Keychain/store, issue a provider request or change code/tests/reports/methods. No subagent or overlapping review assignment.

Return an evidence-linked contract comparison, exact commands/results, reproducible candidate discrepancy if any, known limitations and a recommended next step. An actual defect requires a separate frozen implementation/regression scope before any fix. If no defect is demonstrated, retain the explicit unknown; a future diagnostic capture needs its own accepted bounds and privacy handling. Do not repeat PRSG-90 or expand instrument coverage.

## When it's considered done

- [ ] PRSG-91-D1: Engineer compares documented request/response semantics with the existing screening and distinguishes supported facts, authored examples and unresolved live cause.
- [ ] PRSG-91-D2: Exact focused tests and any private deterministic replay are recorded without repository or secret/provider access.
- [ ] PRSG-91-D3: Lead independently reviews findings, verifies protected paths unchanged and records a bounded next decision or explicit blocker.

## Checks and delivery

The manifest maps contract review, focused regression replay, preservation and Lead decision. Lead independently reviews returned evidence before completion. Only these two ticket files can be committed. Preserve all unrelated shared-checkout edits, particularly the existing projection edit. No new predictions, scoring, confidence change or performance claim. This is an offline feasibility review, not authorization to repair production behavior or take another live sample.
