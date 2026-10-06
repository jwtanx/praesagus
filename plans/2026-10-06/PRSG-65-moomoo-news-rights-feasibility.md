# PRSG-65 — Moomoo news evidence and publication-rights feasibility

Type: spike · Modules: connectors, financial-data, market-research, docs · Owner: Lead · Priority: P2 · Effort: S (0.5–2 person-days) · Impact: high for a useful news-enabled brief; confidence medium because request/response collection and an allowlisted projection exist, while public content rights remain unverified. Created 2026-10-06 MYT.

## Decision question and objective

Can the existing Moomoo news-search and report-projection path support a timestamped U.S. news evidence item in Praesagus without exposing raw content, confusing publication time with availability time, or publishing fields without the required rights?

This is a feasibility and evidence-review spike. It does not authorize a new provider request, scheduled polling, storage changes, report edits, public publication, credential access, or implementation. The intended result is a clear evidence/rights boundary and the smallest next operator action.

## Current implementation and evidence

At frozen base `510552f4e928f73cdcc089d649dcd0064e9cba46`, the accepted PRSG-61 work uses a bounded direct Moomoo REST collector for request/response U.S. quote and news queries, keeps raw records in its private store, and defines a separate allowlisted date-keyed public projection. Its projector fails closed when rights evidence is absent or does not match the requested market/fields. Public news display is therefore gated; successful private collection does not imply a public artifact or deployment of live data.

`connectors/moomoo_rest.py`'s `search_news` calls `/api/v1.0/quote/find-news`, validates the returned identifiers and fields, and records request/retrieval times separately. The OpenD route is a distinct adapter, not the REST collector used by PRSG-61. The current Moomoo OpenD Search News documentation describes keyword search (not a push feed), with title, subtype, source, `publish_time`, view count, related securities, and URL; it does not define the time zone/precision or first-availability/revision semantics for `publish_time`. It documents a maximum of 10 search requests per 30 seconds. Do not apply OpenD limits or fields to the separate REST endpoint without its own documented contract.

Trader reported that the Oct 6 private U.S. SPY query returned 10 records. Lead verified the query plan and successful collector process metadata, and independently reviewed the separate private report projection: all 50 quote rows remain null/missing and all 50 forecasts remain unknown/unavailable. The addendum records the ten news publication times as 2026-05-27 through 2026-10-03 MYT, with no provider update/first-available timestamp. That is limited historical search output, not proof of feed completeness, timely delivery, or a prediction. The query and report remain private; no headline/body is copied here.

The existing PRSG-61 projection and offline tests already cover a field allowlist and synthetic rights-denial/permitted fixtures. On 2026-10-06 MYT, the Lead independently ran `tests/test_moomoo_rest.py`, `tests/test_daily_report_projection.py`, and `tests/test_market_snapshot_publication.py` with the checkout's configured Python 3.11 environment: 185 passed. These tests demonstrate the checked-in contract on fixtures, not provider entitlement, source completeness, legal permission, or Pages deployment of a live artifact.

## Rights finding and options

The official Moomoo Securities Malaysia Client Agreement dated 2024-04-26 contains restrictions on reproducing, retransmitting, publishing, or routing information/reports from its electronic services through another linked system without express written consent. This is a material reason not to assume that an account/API login grants public dashboard rights. It does not by itself determine how that agreement applies to this user's account, whether the searched third-party news content has additional publisher restrictions, or whether short derived summaries are allowed. Moomoo and any relevant news/content rights holders must confirm the exact use in writing.

1. **Private evidence only (recommended while rights are unknown).** Keep raw records and provenance in the existing private store; publish no titles, snippets, source labels, or derived summaries. This preserves the useful research path with the least rights risk but leaves the Pages report without Moomoo news.
2. **Public allowlisted fields after written permission.** Enable only fields explicitly permitted for public display, with required attribution, delay, retention, and market restrictions. This best serves the report if permission covers the exact fields and third-party content. It is blocked until evidence is supplied and reviewed.
3. **Public Moomoo deep links or derived summaries only.** This may reduce copied content but is not automatically permitted: titles, excerpts, URLs, source labels, or summaries may still be restricted or create attribution/derivative-use obligations. Do not adopt this as a workaround without written terms.

Recommendation: retain option 1. Do not publish Moomoo news-derived fields to GitHub Pages until written permission identifies the authorized account/entity, U.S. news fields and content sources, storage/retention, public display, derived summaries, attribution, delay, and applicable territory/expiry. If permission is unavailable, use only separately cleared primary-source links and keep them distinct from Moomoo results.

## Scope, boundaries, and measurement

This ticket reviews the existing route, private collector evidence, projection tests, current official API documentation, and applicable account terms. It changes only these two planning files. It does not call Moomoo, access credentials, launch OpenD, schedule polling, ingest or publish news, modify the report/dashboard, purchase data, or make a forecast.

Success metric: a reviewed rights matrix has a supported `allow`/`deny`/`unknown` decision for each proposed public field and use. Current result: public Moomoo news fields are `unknown`/not approved; the implementation must continue to fail closed. Any later live query or implementation needs a separate accepted scope after the operator supplies the relevant written rights evidence.

## Sources

- Moomoo OpenD, [Search News API](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-search-news.html), accessed 2026-10-06 UTC. Documents keyword query fields, publication-time field, result limit, and request quota; it does not settle rights or first-availability semantics.
- Moomoo Open API, [Getting Started](https://open.moomoo.com/api/overview/getting-started), accessed 2026-10-06 UTC. Documents the separate REST API and timestamp conventions generally; it does not document this repository's news endpoint's content rights.
- Moomoo Securities Malaysia, [Client Agreement dated 2024-04-26](https://static.moomoo.com/upload/document_file/Moomoo%20Securities%20Malaysia%20Sdn.%20Bhd.%20Client%20Agreement_20240426-a014107bc7f93ff38d55ff2d034e18d3.pdf?_=1714138438280), official provider document. Its applicability and any later/supplementary permission must be confirmed for the user's account and intended use.
- Existing accepted implementation contract: `plans/2026-10-05/PRSG-61-trader-moomoo-market-snapshot-dashboard.md` and `plans/2026-10-05/PRSG-61.harness.json` at the frozen base.

## When it's considered done

- [x] PRSG-65-D1: Verify the existing REST news route, private collector, report projection boundary, and distinguish them from OpenD search. Evidence: source review at frozen base `510552f4e928f73cdcc089d649dcd0064e9cba46`.
- [x] PRSG-65-D2: Record observed provider publication-time versus local request/retrieval time and explicitly preserve unknown first-availability, timezone, completeness, and revision semantics. Evidence: official API documentation and reviewed private report metadata; no headline/body copied.
- [x] PRSG-65-D3: Review official account terms and state the field-specific written permission needed before publication, without giving a legal determination. Evidence: official Moomoo MY Client Agreement and API documentation.
- [x] PRSG-65-D4: Lead accepts the safe current decision: keep news private and leave public projection fail-closed until written field/use permission is provided; no new API call or implementation is authorized here.

## Validation and Lead review

- Focused existing offline tests: `tests/test_moomoo_rest.py`, `tests/test_daily_report_projection.py`, and `tests/test_market_snapshot_publication.py`; 185 passed with the configured Python 3.11 environment on 2026-10-06 MYT.
- Planning manifest/path validation and `git diff --check` are required for this two-file delivery.
- `verify_ticket.py PRSG-65 --output /tmp/PRSG65-verification-final.json` inventoried exactly the two declared planning paths and reported unchanged HEAD/worktree. Its overall `needs_attention` is expected for this manual-evidence spike because it labels every manual check `manual_review_required`; Lead then independently reviewed that evidence and accepted it.
- Lead independently reviewed the source-vs-inference distinction, private evidence boundary, official links, exact write scope, and `implementation_authorized=false`.

**Status:** Research spike complete; public Moomoo news display remains blocked pending written rights evidence. This ticket does not change PRSG-61's pending forecast item or imply live dashboard data is deployed.
