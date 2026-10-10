# PRSG-84 Allow bounded REST history through live transport

Type: bug · Modules: connectors, financial-data · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: high — restores an implemented read-only history operation; no accuracy claim.

Created2026-10-11 MYT. Human selected direction1 then2, requested existing AppKey alternative while laptop unavailable. Actual single AAPL snapshot succeeded HTTP200 after existing signer loaded; history failed locally before network.

## Reproduction and expected behavior

MoomooRESTConnector.history_kline emits GET /api/v1.0/quote/US.AAPL/history-kline, but SecureReadTransport._validate allows only news GET/snapshot POST, rejecting history as invalid-request. Expected: permit only bounded valid US daily history requests already supported by core; keep unknown/account/order/malformed requests rejected before any connection.

## Accepted boundary

Engineer changes only connectors/moomoo_rest_live.py and tests/test_moomoo_rest_live.py. Lead owns this spec/manifest. Freeze current SHA in manifest. Preserve existing snapshot/news behavior, TLS/deadline/size/cleanup/secret sanitization; no dependencies, credential changes or stored-data/report edits. Add narrow GET US-symbol history route and strict query validation: required end,ktype2,autype0..2,num1..370; optional valid start<=end; bounded valid symbol/path, empty body, no duplicate/unknown query fields, injection/encoded traversal/account routes. Exercise core history-to-transport integration preserving exact signed query and request bytes. No blanket quote route allowlist.

Offline tests use synthetic response and injected network. Lead independently reviews every owned path and runs focused tests. After reviewed patch, reuse existing private signer and bounded worker for one AAPL daily history request (max10 rows), no retries/account/order/raw-secret outputs; record sanitized stage/status/row count/timestamp coverage. A provider denial or malformed result remains visible and does not negate transport defect repair; live source eligibility/indicator mapping remain pending. No direction2 cohort capture or OpenD mapping substitution.

## When it's considered done

- [x] PRSG-84-D1: Valid core-generated daily history reaches transport; unauthorized/malformed requests rejected before network.
- [x] PRSG-84-D2: Focused regressions pass; existing snapshot/news/security behavior preserved.
- [x] PRSG-84-D3: Lead independently reviews full owned diff and records bounded live smoke outcome/limitations.

## Checks

python3 -m pytest -q tests/test_moomoo_rest_live.py tests/test_moomoo_rest.py tests/test_market_collector.py

## Lead acceptance — 2026-10-11 MYT

Reviewed all four owned paths; focused336 passed independently.35 new integration/security cases preserve existing controls. One bounded max10-row AAPL history call receivedHTTP200 at07:16:32.956753MYT; core validation rejected malformed-response and worker cleaned up. No history rowcoverage/eligibility claimed; rawresponse not retained/output. This completes local transport-route repair only; response-contract mismatch is unresolved follow-up evidence. SDK/OpenD adjacent indicator mapping and direction2 remain pending.
