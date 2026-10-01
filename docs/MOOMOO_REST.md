# Offline Moomoo REST read protocol (PRSG-31)

`connectors/moomoo_rest.py` provides `MoomooRESTConnector`. It is an injectable
protocol core with **no default network transport, credential loader, crypto
implementation, dependency additions or automatic execution**. It leaves OpenD
unchanged. Private account and watchlist results remain in memory; no persistence,
backend route or polling is added.

## Caller contract

Construction requires keyword arguments `api_key`, `signer`, `transport`,
`clock_ms` and `nonce_factory`; `timeout` defaults to 10 seconds (accepted range
more than zero through 30). All tests use synthetic values and fake callables.

- `signer(canonical_bytes) -> bytes`: return raw signature bytes. This adapter
  Base64 encodes them once. The caller implements signing separately.
- `transport(ReadRequest) -> ReadResponse`: receives exact method, path, query,
  body bytes, headers, timeout and a computed URL on `https://webapi.moomoo.com`.
  There is no configurable host or public arbitrary-request method.
- `clock_ms() -> int`: positive UTC epoch milliseconds. Called before signing
  and after transport; a backwards clock fails. Provenance is local observation,
  not a guarantee of provider freshness or synchronized time.
- `nonce_factory() -> str`: 1–64 ASCII letters, digits, `_` or `-`.
- `ReadResponse(status, body, headers={})`: status is an integer HTTP code, body
  is UTF-8 JSON bytes for HTTP 200; successful bodies are capped at 2 MiB.

An injected transport must honor timeouts, bound reads before allocating response
bodies, enforce TLS/host policy, avoid redirects and suppress sensitive logging.
The core cannot interrupt a blocking callable. Injection and Python private
methods are programming interfaces, not a sandbox against untrusted caller code.
No transport is supplied by this ticket.

## Reads and response handling

| Method | Wire route | Input boundary | Returned `data` |
|---|---|---|---|
| `search_news(keyword, size=10, news_type=None, sort_type=None, lang=None)` | GET `/api/v1.0/quote/find-news` | Keyword is wire `symbol`, 1–512 characters; size 1–50; type 1/2/3; sort 1/2; language zh-CN/zh-HK/en/ja | News array; `publish_time` seconds; titles kept as literal text |
| `snapshot(codes)` | POST `/api/v1.0/quote/snapshot` | 1–400 unique US uppercase codes, max 64 characters each | `snapshot_list`; `update_time` milliseconds; market-local `data_date` |
| `account_funds(account_id, currency)` | GET `/api/v1.0/accounts/{acc_id}/funds` | Required uppercase three-letter currency | Account `d` object; decimal strings preserved |
| `positions(account_id)` | GET `/api/v1.0/accounts/{acc_id}/positions` | String ID; no optional filters added | Account `d` array; decimal strings and validity flags preserved |
| `list_groups(group_type="ALL")` | GET `/api/v1.0/quote/user-security-group` | ALL/SYSTEM/CUSTOM | `group_list` |
| `list_group_members(group_name)` | GET `/api/v1.0/quote/user-security` | Nonblank Unicode name up to 100 characters | `security_list`; no US-only restriction on returned members |

Account IDs accept **1–64 ASCII digits only**, retaining leading zeros. This is a
conservative local boundary; provider docs specify a string but do not establish
all valid ID formats. The US snapshot matcher permits `US.` plus an uppercase
initial letter and uppercase letters/digits/dots/dashes. Syntax acceptance does
not prove a symbol exists or a product is entitled. MY/BMS and other snapshot
markets are rejected here; member/position results can contain other markets.
Keyword, ID and response-byte caps are local safety limits, **not provider quotas**.

Quote success requires integer `ret_code == 0`, string `ret_msg` and endpoint-shaped
`data`. Account success separately requires `s == "ok"` and endpoint-shaped `d`;
`s == "error"` requires integer `errcode`. Mixed or unknown envelopes fail.
HTTP 200 alone never means success. Duplicate JSON keys, nonfinite numeric values,
malformed shapes and duplicate news/snapshot/member/group identifiers fail.
Unrequested snapshot codes fail; omitted requested codes appear in `missing_codes`
in request order. Valid empty data has status `empty`; nonempty partial snapshots
have `partial`; other nonempty successful data has `success`.

`ReadResult` includes requested/retrieved epoch milliseconds, provider, endpoint,
private classification, optional provider time unit and missing codes. Data is
preserved without conversion into derived metrics. Funds objects currently accept
numeric decimal strings plus string `currency`/`risk_status`; additional metadata
shapes require a reviewed schema update. Positions and members validate documented
optional fields when present. No full future-provider-schema compatibility is
claimed, and validity flags are retained for callers to honor rather than turned
into inferred values. News titles must be rendered as text, never HTML.

## Exact signing bytes

UTF-8 canonical bytes are five fields joined by `\n`, with no extra sixth field:

1. Millisecond timestamp matching `X-Timestamp`.
2. Uppercase wire method.
3. Exact path.
4. Final URL-encoded query (in the transport's order).
5. Lowercase SHA256 hex digest of the **exact body bytes**, or an empty string for
   no body (not the digest of an empty body).

An empty-query, bodyless GET ends in **two newline characters**: they delimit the
empty fourth and fifth fields. Snapshot serializes `{"code_list":[...]}` once as
compact UTF-8 JSON; those identical bytes are hashed and sent. Headers include
`X-Api-Key`, `Authorization` (Base64 signature **without Bearer**), `X-Timestamp`
and `X-Nonce`, plus JSON content type for snapshot. Nonce is a header, not an
extra canonical field. No unrelated identity header is inferred.

## Failures and privacy

`RESTError.kind` is a controlled category: `invalid-input`, `clock-failed`,
`nonce-failed`, `signer-failed`, `transport-failed`, `timeout`, `malformed-response`,
`provider-failed`, `http-failed`, `upstream-failed` or `rate-limited`.
HTTP 429 may carry sanitized `retry_after` integer seconds (0–86400); supported
hints are integer seconds or a timezone-aware HTTP date relative to the injected
retrieval clock. Invalid/out-of-bound hints become `None`. HTTP 5xx maps to
`upstream-failed`; other non-200 codes map to `http-failed`. No automatic retries
or quota calculations are added.

Connector, request, response and result repr suppress headers, signatures, account
IDs, query/body data and balances. Errors never copy provider messages/bodies or
chain dependency exceptions. Explicit payload/attribute access remains sensitive;
this is not protection from debugger locals, caller logging or deliberate
serialization. Keep transport/signer logs and consumers private. No live account
values or keys appear in fixtures.

## Evidence and remaining gates

Run the exact offline harness:

```sh
python3 -m pytest -q tests/test_moomoo_rest.py
```

It checks canonical trailing newlines, Unicode query order, exact body digest,
all six read routes, bounds, empty/partial results, separate envelopes, decimals,
flags, timestamp units, HTTP/provider failures, timeout and secret suppression.
These tests **do not prove Ed25519/RSA signature validity, broker entitlement,
live API compatibility or runtime security**. Keychain/file credential handling,
secure live transport, OAuth, account permissions, clock synchronization, MY
snapshot support, paper routes, exact quotas, persistence and mutation remain
separate gates. No orders, group creation or watchlist ADD operation exists here.

Public official references reviewed 2026-10-02 MYT (public documentation only,
not authenticated API probes):

- [Getting started and signing](https://open.moomoo.com/api/overview/getting-started)
- [News search](https://open.moomoo.com/api/quote/basic-data/search)
- [Market snapshot](https://open.moomoo.com/api/quote/realtime/market-snapshot)
- [Account funds](https://open.moomoo.com/api/trading/account/get-funds)
- [Positions](https://open.moomoo.com/api/trading/account/get-positions)
- [Watchlist groups](https://open.moomoo.com/api/quote/watchlist/user-security-group)
- [Watchlist members](https://open.moomoo.com/api/quote/watchlist/user-security)
