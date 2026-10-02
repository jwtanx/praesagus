# Private market observations (PRSG-36)

`ingest/private_market_store.py` stores immutable quote snapshots and news
observations separately from the synthetic completed-bar ledger. It adds no
network transport, credential discovery, live collector, scheduling, portfolio,
public export, forecasting, targets or RVOL. Tests and CLI ingestion use synthetic
fixtures only. Real retention/data rights remain unconfirmed; this ticket does not
enable real collection or grant redistribution rights.

## Storage and interfaces

Explicitly initialize `PrivateMarketStore(root, create=True)`. Ordinary
`PrivateMarketStore(root)` opens an existing store without creating or repairing
anything. Root must be an absolute canonical path outside this repository, known
public directory names (`public`, `www`, `htdocs`, `artifacts`, `dist`) and any
additional `public_roots` supplied by the operator. Parent must already exist.
Symlinked paths are rejected; choose a separately protected private directory.
Root/raw directories require exact 0700; SQLite requires owned regular 0600; exact
raw objects require owned regular 0400. Unsafe storage is rejected, never repaired
by chmod. These checks cannot discover every web-server configuration; the owner
must identify custom public roots. Parent races and malicious same-UID processes
are not sandboxed. Storage is private by filesystem permissions, not encrypted.

SQLite has application_id `0x50524D36`, user_version 1 and an exact checked schema.
Unknown schemas are rejected without migrations/reset. Runs, attempts, versions
and observations have immutable UPDATE/DELETE triggers; append transactions use
foreign keys/parameter binding and BEGIN IMMEDIATE. Lock timeout defaults to one
second, accepts >0 through five seconds. This bounds lock waits, not all CPU/I/O.
WAL and journal sidecars are rejected before opening queries, preventing reader
side effects/recovery; an active writer may cause a bounded failure instead of a
read. No schema changes or deleted history are performed automatically.

`ingest(request, response, run_id=..., observed_at=..., ingested_at=..., origin='trusted-capture')` accepts
trusted `ReadRequest`/`ReadResponse` objects, only news GET and US snapshot POST.
Inputs are bounded and fully normalized before committing references. Archive
bytes are the exact HTTP response body: no `json.dumps(ReadResult.data)` is labeled
raw. SHA256 filenames, exclusive creation, file/directory fsync and raw-hash
verification preserve exact bytes. A database failure after archival can leave an
**orphan raw object**; the call fails and no partial references commit. Orphans are
not deleted automatically and can be reused by an explicit retry.

`CaptureTransport(store, transport, run_id=..., observed_clock=...,
ingestion_clock=...)` explicitly wraps an injected trusted transport and captures
its bounded body before the core decoder. No transport/clocks are supplied by
default. Transport exceptions record sanitized failure coverage with no invented
raw; capture/storage/clock failures propagate controlled errors. All offline
fixtures use fake transport/clocks; no credentials or broker calls are used.

## Coverage, identities and source quality

Attempts record origin (`synthetic` or `trusted-capture`) and caller-supplied,
unverified authenticity; the store does not authenticate its injected source.
The CLI always retains synthetic origin. Analysis must not treat fixture observations
as real provider evidence. Attempts record provider/connector, endpoint, normalized request filters/universe,
original aware observation/ingestion strings, UTC millisecond known time, raw hash,
coverage status, missing codes and unconfirmed rights. No request/response headers,
AppKey/signature/nonce or filesystem/private credential paths are recorded.
Successful snapshots can be `success`, `partial` or `all-missing`. Empty news is
`successful-empty`; HTTP/transport/provider/malformed failures are `failed`.
MY is explicitly `unattempted-unsupported`, never a fabricated missing response.
Invalid request input fails before creating an attempt. Missing attempts say
nothing about collection success.

Only validated HTTP200 success envelopes are archived. Other statuses discard
bodies; malformed/provider-error/secret-bearing200 responses record failed coverage
without raw or versions (this MVP does not quarantine raw error bodies).
Duplicate JSON keys/nonfinite values, duplicate or unrequested snapshot codes,
negative/bool numeric fields, bad dates and duplicate news IDs fail closed.
Secret guards reject sensitive key variants, credentialed/token-bearing URLs and
known sufficiently long request credential values appearing in decoded payloads.
They are structural/known-value checks, **not a universal classifier for an unknown
secret hidden in arbitrary news text**. Capture inputs must remain trusted; no
arbitrary request metadata or private account/watchlist responses are accepted.
Controlled errors/repr and CLI failures suppress provider/path details; deliberate
caller serialization or debugger locals are outside that protection.

Snapshots are point observations, not completed bars. Prices/volumes remain finite
nonnegative provider values; zero volume is retained, zero price is flagged
unusable. Quote timestamps are milliseconds, market date is preserved, source
timezone is UTC for epoch format, market timezone/currency/session/adjustment are
unknown. No currency/session/product inference or derived technical metric is
introduced; provider validity flags stay explicit.

News identity is provider + item ID; equal headlines with different IDs remain
separate. Titles are literal text (including highlighting tags); do not render as
HTML. Publication is provider seconds, with unknown availability explicit. News
queries retain separate observations. Snapshot identity includes provider/code/
quote time; changed values at the same point append a revision. Revision numbers
are **ingestion order, not authoritative provider correction order**. Exact replay
of the same capture metadata/raw is idempotent. Semantic equality reuses a version
but appends distinct query/time/run/raw observations.

Nullable missing source times are recognized degraded observations, not temporal
proof; strict queries exclude them. They may be archived even when PRSG-31's
stricter decoder rejects that source-time shape. Observation-only coverage status
is not a claim the core accepted the response or evidence is usable for analysis.

## Read-only cutoff queries

- `query(kind, cutoff, mode='strict', limit=1000)`: snapshot/news observations with
  provenance, semantic revision/hash, source time and quality. Limit 1–1000.
- `attempts(cutoff, limit=1000)`: immutable coverage visible by cutoff, including
  failed/empty/all-missing attempts. No fabricated runs when absent.
- `raw(hash)`: explicitly read and verify an immutable raw object; not cutoff
  filtered by itself. Analysis consumers should use cutoff queries.

Cutoff is required. All timestamp inputs first pass one shared lexical validator:
`YYYY-MM-DDTHH:MM:SS`, optional `.` plus 1–6 fractional digits, followed by `Z`
or conventional `±HH:MM` (hours 00–23, minutes 00–59). Calendar dates/times must
also be valid. Nanoseconds/excess precision, fractional/second offsets, compact
forms, commas, spaces, missing seconds and unsupported forms are rejected before
`fromisoformat` can truncate or normalize them. Previously stored unsupported
timestamp forms also fail closed on read; no silent repair occurs. The same parser governs cutoff,
observation, ingestion, stored timestamp validation and ordering comparisons. Every result has
`known_at=max(observed,ingested)<=cutoff`; known source time must also be <=cutoff.
No later backfill, revision, query observation or raw provenance leaks into an
older cutoff. Original observation/ingestion timestamps are retained; their
millisecond fences round up, while cutoff rounds down, conservatively avoiding
sub-millisecond leakage. Ingestion must not precede observation at full precision.

Strict mode excludes missing source time. `observation-known` includes unknown
source-time context explicitly flagged; it does not invent publication or quote
time. `eligible_for_temporal_evidence` is false for unknown times, source times
later than observation or zero snapshot price. That flag is not an investment
judgment or trade readiness. Quality exposes unknown availability/currency/session/
adjustment and point-observation status; no staleness threshold is invented.
Strict mode is a time filter, not a guarantee every returned row is eligible.
Analysis consumers must still filter `eligible_for_temporal_evidence` and inspect
quality/provenance; zero prices and source-after-observation remain ineligible.
A bounded query/attempt limit is not proof of full coverage: hitting the limit may
omit additional matching observations/attempts. This MVP provides no total count or
pagination cursor; do not infer complete universe coverage from a limited result.
Results return each cutoff-visible observation, so the same semantic version may
appear more than once. Both query methods verify referenced raw hashes; records
also verify normalized payload hashes and their binding to raw ordinal. Integrity
failures stop the query; damaged data is never silently skipped.

Readers use SQLite URI mode=ro and query_only; queries never create stores,
initialize schema, repair journals or write SQL. Hash/schema checks detect damage,
not authenticated tamper-proof storage against an owner able to rewrite everything.

## Offline CLI

```sh
python3 scripts/market_ingest.py --root /absolute/canonical/private-market init
python3 scripts/market_ingest.py --root /absolute/canonical/private-market ingest-fixture --fixture synthetic.json
python3 scripts/market_ingest.py --root /absolute/canonical/private-market query --kind snapshot --cutoff 2026-10-02T00:01:00Z
python3 scripts/market_ingest.py --root /absolute/canonical/private-market attempts --cutoff 2026-10-02T00:01:00Z
```

Fixture JSON requires exactly: `schema_version:1`, `origin:"synthetic"`, `run_id`,
`observed_at`, `ingested_at`, `method`, `path`, `query`, `request_body_base64`,
`http_status`, `response_body_base64`. Base64 preserves original bytes. Fixtures
must contain synthetic data, never real broker/credential payloads. Origin is a
caller declaration, not proof of authenticity. Query stdout is explicit local
private output, with no public destination/export command or arbitrary SQL.
Operators remain responsible for terminal logs and shell redirection. No fixture
file is added to the repo by this ticket.

## Verification and remaining gates

```sh
python3 -m pytest -q tests/test_private_market_store.py tests/test_evidence_store.py
```

The deterministic suite covers exact bytes/idempotence, private paths/permissions,
schema/immutable/read-only behavior, raw/normalized tampering, orphan rollback,
coverage and secret exclusion, duplicate/revision/query observations, missing/
future/backfilled/sub-millisecond cutoff leakage, capture and synthetic CLI.
Existing synthetic-store rejection cases are replayed unchanged. Lead independently
reviews private storage behavior and acceptance. Real retention/licensing, collection,
secure live transport hard-deadline limitations, scheduling and MY support remain
separate gates. No hosted model answer or runtime research harness is added.
