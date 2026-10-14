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
New workers emit version3 with exactly `version`, `job_digest`, `status`,
`observed_at`, `failure`, `body_size`, `retry_after`, `diagnostic_stage`,
`normalization_version` and `diagnostic_structure`. History uses normalization4,
snapshot2 and news1. The parent also accepts exact version1 seven-key and
version2 eight-key legacy headers; legacy history remains normalization3 and
legacy structures null. Deploy worker and parent together: older parents reject
version3. Private inventory is carried only on eligible history rejections.
Unknown versions, extra/missing keys, duplicate keys, wrong digest, malformed
stage combinations, truncation, excessive sizes and extra body bytes fail closed
as `bad-frame`, with no retained stage. Failure bodies must be empty; successful
bodies undergo independent parent normalization. Injected supervisor replies
are also checked for bounded failure values, response types and stage consistency.
Receipt and ingestion times are actual aware UTC observations, never backdated;
unsupported fractional precision and wall-clock rollback/order failures are
rejected. Timestamp rejection leaves the job visibly not persisted.

## Results and failure evidence

The CLI prints only the run identifier and per-job digest, status, attempt identifier
and allowlisted failure category. Default output keys and exit semantics remain
unchanged. It returns nonzero for a failed, unattempted,
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

### Optional private diagnostics (PRSG-94)

Add `--diagnostics` to the manual invocation to include `schema_version: 2` in the
private CLI summary and a nullable `diagnostic_stage` on each outcome. Without
that flag, neither field is present. This output mode does not authorize a
provider request and does not change exit codes, report behavior or store format.

A nonnull stage applies only to a history job with HTTP 200, `invalid-response`
and an empty discarded body. Version-2 frames require an allowlisted stage for
that combination; legacy version-1 replies can have a null stage. All other
results have a null stage. The fixed stages describe trusted validation
boundaries, without provider messages/codes, input keys/values, row indices,
identifiers, paths, credential values or exception text:

| Stage | Boundary |
|---|---|
| `decode-screen` | Bounded bytes/UTF-8/JSON, duplicate/nonfinite or secret screening |
| `envelope` | Legacy coarse stage retained for earlier frames; new history rejections use the fixed boundaries below |
| `envelope-root-type` | Root is not an object |
| `envelope-root-fields` | Root field set does not match the exact contract |
| `envelope-ret-code-type` | Return code fails the existing integer type guard |
| `envelope-ret-msg-type` | Return message fails the existing string type guard |
| `envelope-data-type` | History data container is not an object |
| `envelope-data-fields` | History data field set fails the existing required/allowlisted contract |
| `envelope-next-time` | Optional pagination cursor fails its existing integer/range guard |
| `envelope-volume-precision` | Optional volume precision fails its existing integer/range guard |
| `provider-rejection` | Typed exact envelope with a nonzero integer return code; its value is withheld |
| `history-rows` | List/count/row shape, close, request-date range or duplicates |
| `metadata-missing` | At least one required history metadata key is absent |
| `metadata-invalid` | Metadata scalar, calendar date or representable local-day arithmetic fails |
| `date-relation` | Declared date disagrees with timestamp and explicit minute offset |
| `core-validation` | Screening passed, then a known core validation rejection occurred |
| `unknown` | History screening rejection without a recognized controlled annotation |

Syntax and secret rejection share `decode-screen`; no secret-specific diagnostic
is exposed. Guards retain their acceptance policy and order: decode/screen,
root type, exact root fields, return-code type, return-message type, provider
rejection, history container type, container fields, cursor, precision, list/row
shape, metadata presence, metadata validity, date relationship, range/duplicates,
then close. The first rejected guard supplies the stage. No metadata is inferred,
pagination whitelist expanded, row salvaged or rejected body decoded again for
diagnostics. Arbitrary exception attributes cannot supply stages.

Clock/storage/cleanup replacements clear an earlier stage. An already rejected
job retains its own `invalid-response` stage if the run budget expires afterward;
later unattempted jobs receive no stage. Malformed injected replies become
`bad-frame`; cleanup failure retains its stop behavior.

Diagnostics are ephemeral CLI evidence. The immutable store retains its existing
generic failure reason, normalization version and null raw hash; it does not
persist the stage or rejected body. There is no automatic summary file. A
separately authorized workflow may retain the sanitized private summary outside
Git. Stages cannot recover the PRSG-90 rejection's cause or establish authentication,
entitlements, data rights, completed-price availability or forecast eligibility.

This collector does not deliver an 08:00 brief. Later report projection must check
cutoff availability, temporal eligibility, completeness, conflicts, currency,
session, units, prior close and freshness. Post-cutoff ingestion cannot support an
earlier cutoff. Snapshot volume is not a completed bar or RVOL. Redistribution
rights remain unconfirmed.

## Offline regression command

```sh
python3 -m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py
```

PRSG-104 splits only the existing history composite envelope guards. It does not
add accepted fields, wrappers, defaults or pagination shapes. Multiple faults
report the first guard above; actual return code/message, extra or absent keys,
values and rejected bytes remain undisclosed. A root-fields stage alone cannot
identify which arbitrary field differed. Legacy `envelope` remains allowlisted
for older private summaries/version2 frames; immutable store records stay
unchanged. This change performs no live request and does not establish source
readiness; a fresh bounded request requires separate reviewed execution.


## Version4 history envelope and private structural receipt (PRSG-106)

Current history intake uses normalization4. History1–3 acceptance/replay remains
unchanged; stored history metadata3 and4 replay using their recorded version.
Snapshot/news normalization, payloads and connector validation are unchanged.
No previous attempt is rewritten or diagnostic added to immutable SQLite data.

V4 root requires ret_code/ret_msg/data with only optional pagination/extra.
Return code is nonbool integer, message string; provider rejection precedes deeper
metadata validation. Existing data.kline_list plus optional next_time and
volume_precision and exact scalar bounds remain. If present, pagination is an
exact object with required bool has_more and optional nonbool int total0..2**63-1;
extra is exactly next_time nonbool int0..2**63-1. No next_key/aliases/alternate
status/error wrappers or other root fields. Duplicate cursors in data and extra
must both be valid and equal. Malformed metadata uses fixed envelope-pagination,
envelope-extra or envelope-cursor-conflict stages. Existing data cursor/precision
checks run before these new v4 guards, followed by unchanged list/row/date/offset/
dedup/close guards. Explicit date/time_zone still required. No automatic paging,
requests/retries, window-completeness inference, currency or finality assertion.
Pagination/empty rows are not proof that21 qualifying closes exist. Accepted raw
bytes retain their original shape in the private archive; failed bodies remain
empty/discarded with null raw hash.

Optionally add `--diagnostic-receipt /absolute/private/new-history-receipt.json`
to the existing approved manual collector invocation. Preflight occurs before
plan/store/collector/credential activity: canonical new JSON path outside every
Git checkout/public serving path; no symlink traversal; owned0700 parent. The
0600 receipt is atomic/no-overwrite and its temporary is removed on ordinary
failure. A failure after linking/fsync clears only its own new link. Existing
files are never replaced/deleted, including temporary-name collisions. Closing
or writing failures produce the existing fixed private collector error.
This flag does not grant live-call authorization or change plans/credentials.

The exact private receipt is schema_version1/history_failures, each entry only
fixed diagnostic_stage and structure. No run/job/attempt IDs, codes, timestamps,
paths, hashes, prices, return-code/cursor/count values or raw body. At most30
history failures within the existing41-job cap. Inventory exists only for
HTTP200/history/invalid-response after existing bounded decode/duplicate/nonfinite/
secret screening. Syntax/screening failure gives only schema_version1/status
unavailable. Core/unknown failures may likewise lack usable structure. Diagnostics
cannot recover a previous discarded body or authenticate a provider/reviewer.

Available structure contains schema_version1/status available and root/data/
pagination/extra/first_row sections. Each has a fixed type enum, fixed fields
mapped to type enums and unexpected_fields absent/present/unavailable. Root's
seven fixed labels are ret_code/ret_msg/data/pagination/extra/code/error; data
three labels kline_list/next_time/volume_precision; pagination has_more/total;
extra next_time; first_row time_key/date/time_zone/close. These17 labels are code
constants, never provider names copied from input. `code`/`error` are diagnostic
only and still reject admission. No error.code recursion or arbitrary nested
projection. Types are absent/null/bool/int/float/string/array/object, with bool
separate from integer. Unknown field names (including ASCII IDs) never emitted;
a fixed presence flag indicates them. First-row presence/types do not imply
accepted bars; no row length/count or values. Unsupported inventory becomes
unavailable; invalid/extra/forged fields or inconsistent type linkage fail closed.

Clock/storage/cleanup/status/frame replacements clear inventory with stage;
run-budget retains only a prior actual rejected job's diagnostic. New frame3
requires exact normalization4/history eligibility for inventory; old frames1/2
cannot carry it and cannot admit v4 optional metadata. Repr remains generic.
No receipt flag means inventory is discarded after in-memory collection. Existing
stdout and `--diagnostics` schema2 remain unchanged and never include structural
fields/types. An empty receipt is not proof of accepted rows. Review the private
receipt after a separately approved bounded intake; if mandatory field types
conflict, obtain the exact official contract/support clarification rather than
admit undocumented wrappers or repeat the same request indefinitely.
