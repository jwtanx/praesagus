# Manual private market collector (PRSG-37)

`scripts/market_collect.py` connects the existing read-only REST adapter to the
private immutable store. It runs only when explicitly invoked. Imports perform no
credential, network or store I/O. There is no scheduler, retry loop, report
projection, public export, portfolio access or Malaysian quote collection.

## Inputs and invocation

Use the project's Python environment with the declared dependencies installed.
The implementation was checked offline on Python 3.12.14 with cryptography 50.0.2;
Python 3.11 was not available for this validation.

The store must already exist; use the separate explicit initialization workflow in
[PRIVATE_MARKET_STORE.md](PRIVATE_MARKET_STORE.md). The collector does not initialize
or repair a missing store. Its canonical absolute root must be private and outside
the repository and public serving directories.

Create a nonsecret plan JSON:

```json
{
  "schema_version": 1,
  "codes": ["US.SPY"],
  "news": [{"keyword": "SPY", "size": 10, "lang": "en"}]
}
```

At most one snapshot batch with 1–400 unique US codes and ten distinct literal
news queries with sizes 1–50 are allowed. Either list may be empty, but the plan
must contain a job. News languages are `en`, `ja`, `zh-CN`, or `zh-HK`. Unknown
fields, duplicate jobs, malformed plans and unsupported quote markets fail before
worker launch. Jobs run serially, without retries. Local caps do not establish
provider quotas, entitlement or complete coverage.

The credential directory must be a canonical absolute directory outside the
repository/public serving paths, owned by the current user with mode `0700`.
Provide an explicitly named AppKeyID file (mode `0600` or `0400`, ASCII identifier,
at most 512 bytes plus an optional trailing newline), and an encrypted
`private.pem`. Owned regular files are checked, symlinks rejected, and AppKeyID
checks are repeated on the opened descriptor. The existing encrypted PEM loader
and signer retain their validation. The worker reuses the existing exact login
Keychain lookup; it does not enumerate items or fall back to other Keychains.
Never put credential values in the plan, command arguments or environment.

```sh
python3 scripts/market_collect.py \
  --root /absolute/private/store \
  --plan /absolute/nonsecret/collection-plan.json \
  --credential-directory /absolute/private/credentials \
  --app-key-name app-key-id \
  --run-id manual-20261002-01
```

These paths are placeholders. Running this command with real credentials makes
real read-only provider requests and requires working entitlement/connectivity.
The engineering tests use synthetic fixtures, subprocesses and missing synthetic
credential directories; they do not establish live service success or data rights.

## Isolation and bounds

The parent alone opens/writes SQLite and archives raw responses. Each worker uses
the current fixed Python interpreter and repository entry point, without a shell,
in a new process session. Only a bounded job and credential directory locator are
sent through stdin; the store root is never sent. Worker environment is minimal,
and stderr is discarded. Credential values, authentication headers, signatures,
nonce, private locator paths and exception text are excluded from result IPC and
summary output. Shared store screening handles structured secrets and known
request secrets before IPC; the parent independently normalizes successful bodies.
This is process separation, not an OS filesystem sandbox or a guarantee against
arbitrary compromised worker code.

Worker I/O has a monotonic 20-second deadline plus at most two seconds for TERM,
then KILL of the process group and bounded direct-child reaping. Descendants such
as Keychain helper processes share that group. A cleanup failure stops further
jobs. No unbounded `communicate`, `wait`, output accumulation or pipe read occurs
in the parent. OS-uninterruptible processes are not guaranteed to terminate.

The run has a 300-second admission/accounting budget including cleanup; cleanup
is reserved when admitting each job. The budget is checked around parent ingestion.
Filesystem/SQLite latency can exceed it; this is **not a hard end-to-end deadline**.
An overrun is visible as `run-budget`, stops subsequent jobs and does not forcibly
kill the SQLite writer. An already persisted attempt remains persisted.

One length-prefixed reply contains a bounded JSON header and exact body bytes.
Job digest, status, timestamp precision, body size and allowlisted failures are
validated. Truncation, extra data, wrong digest or malformed content fail closed.
Receipt and ingestion times are actual aware UTC observations, never backdated;
unsupported fractional precision and wall-clock rollback/order failures are
rejected. Timestamp rejection leaves the job visibly not persisted.

## Results and failure evidence

The CLI prints only the run identifier and per-job digest, status, attempt identifier
and allowlisted failure category. It returns nonzero for a failed, unattempted,
not-persisted or over-budget outcome. Partial snapshots, all-missing snapshots and
successful empty news responses are coverage states, not promises of completeness.

Worker/credential/deadline failures are stored as zero-status empty-body transport
attempts with actual failure observation/ingestion times and no raw evidence.
HTTP failures retain only HTTP status and no provider body. Invalid successful
responses are screened before IPC and do not archive raw bytes. A received HTTP
200 response rejected by screening retains HTTP 200 and its actual receipt time
with the controlled `invalid-response` category and an empty body. A genuine
transport exception before receipt remains status zero with `transport`; rejected
rows are never salvaged. This classification does not establish the cause of a
live batch failure. The existing
store schema collapses failure reasons; the CLI outcome preserves bounded category
detail. Storage failures stop collection and cannot be reported as persisted
attempts. Caller-declared `trusted-capture` remains unauthenticated provenance.

This collector does not deliver an 08:00 brief. Later report projection must check
cutoff availability, temporal eligibility, completeness, conflicts, currency,
session, units, prior close and freshness. Post-cutoff ingestion cannot support an
earlier cutoff. Snapshot volume is not a completed bar or RVOL. Redistribution
rights remain unconfirmed.

## Offline regression command

```sh
python3 -m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py
```
