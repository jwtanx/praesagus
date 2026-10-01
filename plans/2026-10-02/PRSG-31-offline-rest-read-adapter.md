# PRSG-31 Offline Moomoo REST read adapter

Type: feature · Modules: connectors, financial-data · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: medium-high

## Why the ticket is created?

Human approved preparing ingestion/analysis tools while Keychain access is unresolved. Existing connector depends on OpenD. A small injectable REST adapter lets us verify contracts without credentials or broker calls.

## Approach

Implement an explicit read-only adapter with injected transport, signer, millisecond clock and nonce factory. No default network transport, file credential loader, Keychain integration or automatic execution. The signer receives exact canonical bytes and returns signature bytes; Base64 encode only at request construction. Do not implement cryptography or install dependencies in this ticket. Never include secrets, signature, headers, account payloads or provider error bodies in repr/errors/logs.

Read methods only: search_news(keyword, size1–50 and documented filters); snapshot(codes1–400); account_funds(account_id,currency required); positions(account_id); list_groups(ALL/SYSTEM/CUSTOM); list_group_members(group_name max100). No arbitrary public request method or arbitrary host/path injection. Account IDs remain strings (leading zeros preserved), validated before path construction. Only verified US symbol format supported for snapshot initially; reject/unavailable MY rather than claim BMS endpoint support.

Exact routes: GET /api/v1.0/quote/find-news; POST /api/v1.0/quote/snapshot (semantic read); GET /api/v1.0/accounts/{acc_id}/funds; GET /api/v1.0/accounts/{acc_id}/positions; GET /api/v1.0/quote/user-security-group; GET /api/v1.0/quote/user-security. Query encoding/order and body bytes used for signing must be exactly those handed to transport. Signing fields: timestamp_ms, uppercase method, path, raw query, lowercase SHA256(body) or empty, separated by newline. Include nonce header but do not add nonce to undocumented signing-string fields.

Decode quote ret_code/ret_msg/data and account s/d/errcode envelopes separately; HTTP200 alone not success. Preserve decimal strings and validity flags without derived price/volume metrics. Retain provider times with explicit seconds news versus milliseconds snapshot semantics; retrieval provenance and missing snapshot symbols retained. Successful empty differs from failed request. Treat news highlighted titles as plain text. Private account results stay memory-only, no public files. Fail closed on malformed/nonfinite payload shapes, duplicate/unrequested quote identifiers and unknown envelopes. Define controlled result/error classes with no sensitive repr.

Bounded requests/timeouts; no automatic retry in this MVP (explicit typed429/retry-after or upstream failure lets a later coordinator decide). This avoids inventing quotas or replay policies. No write methods, orders, watchlist ADD/create, OAuth fallback, persistence, FastAPI exposure, polling or live requests. Unknown MY support/watchlist creation/entitlements remain gates.

## Options and tradeoffs

Injectable protocol core chosen over live client because secure credential access and provider entitlement are unresolved. Retain existing OpenD unchanged. A full SDK/automatic sync would expand risk before contracts are tested. No retry reduces complexity but callers must explicitly handle transient failures.

## Findings and references

Researcher verified public docs; Lead reviewed signing/snapshot source. https://open.moomoo.com/api/overview/getting-started ; https://open.moomoo.com/api/quote/basic-data/search ; https://open.moomoo.com/api/quote/realtime/market-snapshot ; https://open.moomoo.com/api/trading/account/get-funds ; https://open.moomoo.com/api/trading/account/get-positions ; https://open.moomoo.com/api/quote/watchlist/user-security-group ; https://open.moomoo.com/api/quote/watchlist/user-security .
MY format in overview is not evidence snapshot support. Portfolio permission/account availability and paper routes not exercised. Batch caps are not rate limits.

## Frozen scope and acceptance

Base 9c5821fb90fa878f17f8a689781c95a9d564209c. Write only connector, deterministic tests, documentation and this ticket pair. Preserve .DS_Store and all existing adapters. All tests synthetic and fake signer/transport; no real credential reads. Test canonical emptyGET trailing newline, URLencoded Unicode and rawJSON body digest; exact signed wire bytes; each read endpoint; bounds/missing symbols/envelopes/decimal strings/timestamp units; HTTP200 failure/nonJSON4295xx/timeouts; invalidpath injection; secret-safe repr/errors; disallowed mutation surfaces. No offline test proves actual Ed25519 validity, entitlement or live security.

## When it's considered done

- [x] PRSG-31-D1: Offline read adapter and safety regressions pass; Lead reviews scope/contracts and records remaining live gates.

## Progress

2026-10-02 MYT — Engineer implemented the injectable offline core in
`connectors/moomoo_rest.py`, six read methods, exact canonical signing bytes,
separate quote/account envelopes, local bounds, preserved decimal strings/flags,
provider time units, partial-symbol reconciliation and controlled secret-safe
errors/repr. No network transport, cryptography, dependencies, credential loader,
mutations, persistence, backend changes or derived metrics were added.

Focused harness: `python3 -m pytest -q tests/test_moomoo_rest.py` — **126 passed
in 0.13s**. First run passed 112 tests; added input/header/date/transport regressions
and reran successfully. All fixtures and dependencies synthetic and offline.
Documentation: `docs/MOOMOO_REST.md` records callable interfaces, exact routes,
canonical bytes, error categories, conservative schema/ID boundaries and live gates.
Researcher excerpts agree with separately retrieved public docs; no authenticated
API probes or private-folder access occurred. Initial public web-tool timeouts
were resolved using bounded public-document retrieval, without a scope change.

Implementation ready for Lead review. PRSG-31-D1 and manual review remain pending:
o offline test proves live signature validity, entitlement, MY snapshot support,
secure live transport or credential handling. Account IDs are conservatively
ASCII digits only; funds accepts decimal strings plus currency/risk_status, and
positions/members validate documented optional fields when present. These schema
boundaries require review before broader provider compatibility claims.
Unrelated pre-existing `.DS_Store` modification preserved. No staging/commit/push.

## Lead acceptance

Lead independently reviewed all connector functions and docs, reran python3 -m pytest -q tests/test_moomoo_rest.py:126passed0.09s; full python3 -m pytest -q:531passed16.78s with5 existingBoto3/Python3.9warnings. Five-path scope validated. Explicit injected semanticreads, exact canonical/wirebytes, controlled errors and no transport/credential loading/persistence/mutations. Strict funds schema may reject extra provider metadata; caller transport is trusted, not sandboxed. No live cryptographic/auth/entitlement/Keychain/MY coverage proof.

