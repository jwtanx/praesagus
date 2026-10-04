# PRSG-1 — Company catalyst inbox

Type: feature · Modules: backend, frontend, connectors · Owner: Engineer · Priority: P1 · Effort: M (3–5 person-days) · Impact: high

Harness manifest: [PRSG-1.harness.json](PRSG-1.harness.json). Created 2026-10-01, Asia/Kuala_Lumpur. Owner: Engineer; acceptance: Lead.

State: selected for implementation, assigned to Engineer on 1 October 2026. Target: a solo or small-team researcher reviewing tracked companies. Lead accepts the scope below; implementation remains pending.

## Problem and value

Financial Intelligence exposes filings, news, insider trades, and calendars in separate panels. Users must scan several lists and reconcile different timestamps to find relevant evidence. A source-linked inbox connects those existing records into one filterable workflow. Expected impact: high reduction in navigation and verification friction; no measured time saving yet.

Success hypothesis: at least four of five test users can find the original source for a supplied company event in under 60 seconds. Record time-to-source before/after using the same frozen fixture set. Failure means revisit layout or source coverage before adding automated interpretation.

## Scope and interfaces

Add `GET /api/v1/financial/catalysts` with existing API-key enforcement. Query parameters: optional `ticker` (trimmed, uppercased, bounded text), optional `event_type` from `filing`, `insider_trade`, `news`, `calendar`; `limit` default 50, range 1–200; `offset` default 0, range 0–10000. Invalid type/bounds return 422. Return `{records, count, total, limit, offset, retrieved_at, dataset_status}` where total is after filtering/deduplication and before slicing. Offset paging is stable for an unchanged dataset; concurrent ingestion may shift pages.

Read only the local financial datasets selected by `PRAESAGUS_FINANCIAL_DATA_DIR`. Do not fetch providers on this path. Preserve existing financial APIs and filter behavior; the inbox deliberately reads raw stored records rather than the visible-field projections or directional/transaction-value filters in `financial_filters.yaml`. Clearly label this as all stored evidence, so it does not quietly imply that existing signal filters apply.

Each item exposes:

| Field | Contract |
|---|---|
| `id` | Dataset-prefixed stable source ID; fallback exact-record hash if absent |
| `source_id` | Original ID or null; never fabricate provider identity |
| `event_type`, `subtype` | Four normalized types plus original form/event subtype when present |
| `ticker`, `title` | Original normalized ticker or null; sensible deterministic factual title fallback |
| `source`, `source_url` | Original news provider or SEC attribution; safe HTTP(S) URL or null |
| `event_at`, `time_precision`, `timezone` | Valid aware timestamp in UTC, or original date-only event with precision `date`; missing/invalid time remains null/unknown |
| `published_at`, `available_at`, `ingested_at` | Original source/publication, first-observed/available and ingestion times independently retained where known; no substitutes represented as facts |
| `scheduled`, `data_gaps` | Calendar future events labeled scheduled; explicit unavailable/ambiguous fields |

`retrieved_at` is API read time, not publication, ingestion success, or proof of fresh provider coverage. Do not equate event time with publication time. A future calendar event is valid scheduled information; a future observed news/filing timestamp is flagged and cannot lead the observed feed as if it already occurred.

## Normalization and ordering

- Filings: source URLs prefer document_url then filing_url; factual title includes company/ticker and form. Acceptance timestamp is the occurrence/publication candidate; filing_date is a date-only fallback. A timezone-naive acceptance string stays explicitly ambiguous; do not assume UTC.
- Insider: document_url then form_url; title describes owner/transaction without claiming informed direction. Transaction date is occurrence date; acceptance time separately records disclosure availability.
- News: link and source_name; published_at is publication; first_seen_at is observation, ingest_ts is ingestion. Preserve discrepancies and flag invalid/future values rather than replacing them with read time.
- Calendar: event_date/event_time and supplied timezone; date-only events remain date-only. Preserve estimated flag; obtain source_url only if actually present (including metadata). Global macro records can have null ticker; ticker filter excludes them unless they explicitly match.
- Deduplicate within each dataset by source_id. Never collapse an insider transaction into its filing or independently sourced articles into one event. For missing IDs, remove only exact duplicate normalized/raw content using a deterministic digest; report the gap. Choose duplicate representatives deterministically (valid latest ingestion timestamp, then canonical serialized record); do not depend on input order.
- Observed dated events sort newest first, missing/ambiguous times last, stable ID breaks ties. Show future scheduled calendar events in a clearly labeled upcoming group sorted soonest first, followed by observed/past events. Do not convert a date-only value into an invented midnight timestamp; a date sorting key is acceptable if precision stays visible.
- Dataset status distinguishes loaded, absent, and unreadable/malformed. Surface partial results with warnings; an empty valid dataset is not a failed run and an old file is not proof of health. Validate record lists, skip malformed rows with visible counts, and never log raw private payloads.

## Frontend and engineering boundary

Add a typed API client and a `CatalystInbox` component embedded in the Financial page. Include event-type/ticker controls, Apply/Refresh, pagination, loading/error/empty states, partial-dataset warnings, original-source link, precise/date-only/unavailable times, and research-only explanatory text. Display data gaps on demand without drowning the main feed. Source links use safe HTTP(S), `rel="noopener noreferrer"`; render text through React, never injected HTML. Ignore stale responses after filters change or unmount; refresh failure must not leave old records presented as new results.

Engineer owns `backend/catalyst_services.py` (new), minimal route wiring in `backend/main.py`, `frontend/src/services/api.ts`, new `frontend/src/components/CatalystInbox.tsx`, minimal embed in `frontend/src/pages/Financial.tsx`, optional component-scoped stylesheet, and focused tests. Lead owns `plans/` and documentation integration. Preserve existing Moomoo panel and shared report/skill/ledger work. No schema migration, LLM summaries, new signals, provider calls, notifications, or persistent Moomoo ingestion.

## Acceptance and harness

Deterministic service/API fixtures cover all four datasets, missing/malformed files, malformed rows, duplicate IDs, missing IDs, offset pages, invalid filters, empty results, null tickers, naive/date-only/offset timestamps, future news versus scheduled events, malicious links, and API authentication. Assert original timestamps/provenance survive normalization and that no upstream calls occur. Test filtering before limit and stable tie sorting.

Frontend checks cover source links, partial warnings, stale-request protection, apply/refresh/paging, and empty/error states. Use existing test tooling where available; if no component harness exists, add a small testable normalization/view helper plus documented browser fixture checks rather than claiming a build proves UI behavior. Run focused tests, full pytest, frontend build/type check, and desktop/mobile fixture review; report exact commands and outcomes.

Effort: normalization/API 1–1.5 days; frontend 0.75–1.25; failure/replay tests 0.75–1.25; review/runbook 0.5–1. Total 3–5 person-days. Largest uncertainty: timestamp/source completeness. Deliver complete end-to-end MVP before expanding. Rollback is removing the additive route/component; raw datasets remain untouched.

## When it's considered done

- [ ] PRSG-1-D1: Four datasets normalize with source/time precision, deduplication, filters and paging proved by replay tests.
- [ ] PRSG-1-D2: Authentication, malformed/absent datasets, unsafe links and future-observed versus scheduled events pass rejection tests.
- [ ] PRSG-1-D3: Desktop/mobile fixture review proves source links, partial warnings, stale-response handling and paging.
- [ ] PRSG-1-D4: Focused tests, full pytest and frontend checks pass; commands/results recorded in manifest checks.
- [ ] PRSG-1-D5: Lead reviews the scoped diff, records limitations and accepts release; commit/deployment evidence recorded where applicable.

Check items only with evidence; update corresponding manifest acceptance status/evidence in the same edit. User usability target is a separate post-release impact check and must be reported as unmeasured until tested.

## Accepted correction scope — 2026-10-05 MYT

Lead independently reproduced malformed/out-of-range URL ports accepted by safe_url, and metadata [], false, 0, empty string accepted as object via falsy default. Correction base c54c38abb5f250840cbcbbcee8719fadb8c872da; Engineer writes only catalyst_services.py, test_catalyst_inbox.py and this existing spec/manifest. Preserve historical baseline and all original acceptance/check definitions. Validate parsed.port and reject invalid ports without exceptions escaping; valid omitted/standard ports retained. Reject supplied nonobject metadata including falsy values; absent/null metadata remain supported. Add failing-before/passing-after direct normalization and dataset skipped-count/provenance regressions. Run focused16+ regressions and manifest/diff checks; no dependency installs/provider access/frontend edits/full-suite claims. Leave Lead review and D3-D5 pending. Preserve unrelated PRSG-54 skill work.


## Engineer correction delivery — 2026-10-05 MYT

Service correction reads `parsed.port` inside the existing ValueError boundary, rejecting malformed/out-of-range ports while retaining original valid URLs. Metadata defaults only for absent/null; supplied nonobjects, including falsy values, raise the existing malformed-row error. No other normalization or source semantics changed.

Command `python3 -m pytest -q tests/test_catalyst_inbox.py` ran at repository root on Python3.9.6. Added regressions failed before the service fix:7 failed,23 passed. After fix:30 passed in0.41s. Coverage includes direct URL/normalization rejection, malformed/negative/out-of-range ports, valid omitted/80/443/8443 ports, falsy/nonempty nonobjects, malformed dataset skipped counts, unchanged raw file bytes, retained source ID/provider and publication/availability/ingestion times, absent/null/empty-object metadata and calendar metadata source link/date precision.

Four-path manifest validation, correction-baseline scope assertion and `git diff --check` passed. Preserved Lead's pre-existing correction-scope edits and original historical baseline/checks/acceptance definitions. Focused evidence recorded; all D1-D5 checklist and Lead review remain pending. No frontend/full-suite/browser checks rerun; Python3.9 focused pass does not establish supported3.11 full suite. No dependency/provider/auth/schedule edits, commit or push. Lead owns correction acceptance and outstanding broader verification.

## Lead correction review and additional UI evidence

Correction accepted independently: all four changed paths reviewed; focused replay30passed0.46s onPython3.9.6. Original ticket completion remains pending supported-runtime full suite and final full historical scope acceptance. CUA synthetic HTTP desktop/mobile390 proves safe source href/target/rel,53rowpaging,calendar1rowfilter,SLOW superseded byEMPTY retained after delay;mobileAAPL/news52rowsnext/previous,pagewidth390. Actual API query wiring exercised by browser; credentials/provider freshness untested. Viewport reset. Do not report correction acceptance as whole-ticket completion.
