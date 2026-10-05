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

## PRSG-34 private capabilities — offline reviewed implementation

`connectors/moomoo_rest_live.py` adds explicit callables for a separately reviewed
private integration. Importing the module performs no credential or network I/O.
The protocol core above still has no default transport and OpenD is unchanged.
Lead owns integration, final review and authorized live probes. The dependency
scope amendment is accepted; dependency declarations are now present below.

### Encrypted signer and exact Keychain loader

`EncryptedEd25519Signer(pem_loader=..., passphrase_loader=...)` consumes encrypted
PKCS8 PEM bytes and a nonempty passphrase in memory, loads an Ed25519 private key,
and signs the exact canonical bytes passed by the core. Other key algorithms,
plaintext PEM, wrong passphrases and malformed inputs fail closed. Signature bytes
are returned raw; the core retains responsibility for Base64 headers. PEM is
capped at 64 KiB, passphrase at 4096 bytes and canonical input at 64 KiB. The signer
retains the decrypted key, with safe repr, without storing the input PEM/passphrase
as attributes. Python/OpenSSL memory is **not guaranteed zeroized**; debugger
locals and deliberate caller access are outside repr/error suppression.

`encrypted_pem(absolute_path)` explicitly reads only a file named `private.pem`
outside the repository. It requires a regular file owned by the current UID,
without group/other permissions, rejects final symlinks, opens nonblocking and
bounds the read. The caller must choose and protect the outside-repo directory;
parent-directory ownership/races and full disk security are not enforced here.
No AppKeyID directory scanner, automatic credential discovery or key writes exist.

`keychain_passphrase()` invokes exactly `/usr/bin/security find-generic-password`
with service `praesagus.moomoo.private-key-passphrase`, account `praesagus-lead`,
`-w` and the explicit current UID's `Library/Keychains/login.keychain-db` (home
from the OS user database, not `$HOME`). No other
Keychain/service search or environment/file passphrase fallback exists. The
subprocess uses no shell, disables stdin/stderr, restricts its environment to a
system PATH, bounds stdout to 4097 bytes including the CLI newline, and uses a
five-second deadline with kill/reap/pipe cleanup. It removes one final CLI newline,
not significant spaces. Call this only through the reviewed private workflow;
it may trigger macOS access UI. **Engineer’s offline harness did not access a
real Keychain**; Lead separately exercised the private integration, summarized
without credentials or quote values below. Runner/PEM/passphrase/key-decoder seams are trusted test dependencies,
not protection from malicious injected code.

### Direct HTTPS transport

`SecureReadTransport()` is callable as the core's transport, with only two allowed
method/path pairs: GET news search and semantic POST snapshot. It does **not**
enable account, position, watchlist, mutation or arbitrary URL requests. It fixes
`webapi.moomoo.com:443`, uses a default certificate-verifying SSL context with
hostname checking and TLS 1.2 minimum, and uses stdlib `HTTPSConnection` directly.
It never reads proxy environment variables, sets tunnels or follows redirects.
Request headers are restricted to core authentication headers plus JSON content
type for snapshot. Raw query/body remain unchanged. Queries cap at 8192 characters
and request bodies at 32 KiB. Injected connection/context/clock factories are
trusted offline seams; unverified SSL contexts are rejected. The default CA trust
uses Python/OpenSSL system configuration, which may include CA environment
overrides; this is not certificate pinning against a compromised local environment.

Timeout input must be finite, positive and at most 30 seconds. Remaining time is
checked between connection/request/header/chunk operations and applied to socket
operations. Success reads use bounded `read1` chunks, capped at 2 MiB (configurable
lower cap), reject compression, validate declared length and detect truncation.
Every connection closes. HTTP 3xx raises a sanitized failure without contacting a
redirect target. Other non-200 results retain no body and at most a short Retry-After
hint; the core interprets HTTP/provider failures. No retry/pooling or log output is
added. Controlled failures suppress original exception context and provider data.

**Timing limitation:** stdlib blocking DNS and response-header parsing can exceed
the intended total deadline (for example an upstream trickling header bytes within
each socket timeout). Chunk-loop checks and socket timeouts are bounded, but this
is not a hard wall-clock cancellation mechanism. Lead must review this before
unattended use; live availability/entitlement and trustworthy local CA configuration
also remain gates. Offline tests establish no live market coverage, public data
redistribution, persistent outputs or unattended ingestion; Lead’s bounded probe
is separately recorded below.

### Dependency and validation gates

`cryptography` is lazy-loaded and now declared consistently as `>=50.0.2,<51`
in `pyproject.toml` and `requirements.txt`, under Lead’s accepted 2026-10-02 scope
amendment. No tracked Poetry lockfile exists, and none was added. Official package
metadata rechecked 2026-10-02 lists stable 50.0.2 and Python >=3.9 (excluding
3.9.0/3.9.1). The project declares Python ^3.11. No full project/model dependency
installation or global package changes were made.

Historical Engineer and independent Lead offline runs used Python3.9/available
cryptography49.0.0. Python3.11 was unavailable at standard explicit installation
locations and in the project venv. Focused isolated Python3.12/cryptography50.0.2
verification passed all 202 tests in 0.89s, with `pip check` and matching dependency
range/TOML checks passing. It does not substitute for Python3.11
or a full Poetry dependency-resolution check. Real crypto cases skip if the
optional package is absent; mocked missing-package failure still runs. Skipped
crypto cases must not be counted as proof of signing validity.

```sh
python3 -m pytest -q tests/test_moomoo_rest_live.py tests/test_moomoo_rest.py
```

The offline harness covers exact Keychain argv/bounded subprocess cleanup with
fakes, synthetic private-file restrictions, encrypted Ed25519 signing/verification
entirely in memory, wrong password/algorithm/missing dependency, secret-safe
repr/errors/context/logs, exact host/TLS/wire bytes, no redirects/proxy use, deadline
and size/error cleanup, plus PRSG-31 regressions. Test files never read real private
credentials or call the broker. Lead-reported independent offline verification on
2026-10-02 passed 202 tests in 0.38s. Separately, Lead’s human-authorized authenticated
US.SPY snapshot probe returned one row with price and volume fields present.
No quote values, secrets or public report updates were published. The first probe
had a local summary-shape error after the request; the corrected second probe
succeeded. Engineer did not perform those live calls or inspect private probe data.
This bounded observation does not establish broad entitlement, MY coverage,
redistribution rights or unattended ingestion. Final transport/dependency review
and ticket acceptance remain Lead-owned; MY support and data rights unverified.

References: [Ed25519 signing](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/),
[encrypted PEM loading](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/),
[package metadata](https://pypi.org/project/cryptography/),
[Python HTTPSConnection](https://docs.python.org/3.11/library/http.client.html).

## Secure onboarding and manual collection

Follow [Moomoo AppKey and macOS credential setup](MOOMOO_CREDENTIAL_SETUP.md) for the delivered PRSG-34 encrypted signer and exact login Keychain identifiers. The guide separates public-source verification, mocked failure replay and human-authorized live reads. It covers private files, item-level access approval, rotation and revocation without printing secrets.

[PRSG-37 manual private collection](PRIVATE_MARKET_COLLECTOR.md) supplies explicit credential-directory/AppKeyID locators and writes to an existing private store. It permits only news and US snapshots, with bounded worker supervision; no account reads, trading, watchlist writes or implicit scheduling. This does not expand the offline protocol core or OpenD routes. Official docs currently recommend OAuth; the implemented loader uses compatible traditional AppKey signing and has no OAuth flow.
