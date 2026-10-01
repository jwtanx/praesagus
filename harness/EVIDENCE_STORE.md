# Offline synthetic evidence store

`harness/evidence_store.py` is a standard-library, synthetic-only storage foundation.
It does not collect market data, classify events, select movers, calculate returns,
train models, schedule jobs or implement the future answer harness.

## Storage and errors

`EvidenceStore(root, lock_timeout=1.0)` creates a private root (`0700`), private
`raw/` directory, and `evidence.sqlite3` (`0600`). Root must be outside this repository,
including its public artifacts. Existing roots/files with group/other permissions,
root/raw/file symlinks, or unknown database schemas are rejected. The caller must also
keep the root outside any other public hosting tree, backups shared with others, or
synced public folder. The module cannot discover external hosting configuration.
No generated batches or databases belong in Git. SQLite uses schema version 1,
foreign keys, parameterized queries and transactions. Lock waiting is bounded to
0–5 seconds, default 1 second. It is a single local store, not distributed storage.

`EvidenceError` (a `ValueError`) reports validation, schema, lock and integrity
failures without interpolating payload values. Filesystem access failures can raise
`OSError`. The CLI returns status 2 with a bounded rejection message. Callers should
surface failures rather than substitute an empty result. Correctness assumes a
trusted local filesystem and caller: immutable means no overwrite/update/delete
through this API, not OS tamper protection, encryption or credential scanning.

Raw input must be UTF-8 JSON **bytes**. SHA256 addresses the exact bytes, including
whitespace, at `raw/<hash>.json`. Exclusive creation, `fsync` and read-only file mode
precede transactional database references. Reuse verifies the hash. A database
failure can leave an unreferenced batch; it cannot commit references before writing
raw. Invalid mixed batches are validated completely before writing. Read APIs verify
all encountered raw references and reject missing/corrupted content, including
otherwise ineligible version history. Reingesting exact original bytes can restore
a missing file exclusively; it never overwrites a corrupted existing file.

## Batch contract (schema 1)

Required envelope:

| Field | Contract |
| --- | --- |
| `schema_version`, `origin` | Integer `1`, literal `synthetic`; real/live origins rejected |
| `provider`, `run_id` | Nonempty identifiers, at most 512 characters |
| `retrieved_at`, `ingested_at` | Aware ISO timestamps; ingestion >= retrieval |
| `rights` | Object with `status: synthetic-only`; additional metadata retained |
| `run` | Explicit status, universe, session and nullable error reason below |
| `bars`, `news` | Explicit lists, including empty lists |

All timestamps are caller-declared fixture provenance, not wall-clock attestation.
Unknown fields are retained in raw; record metadata and rights survive replay.
Duplicate JSON keys, nonfinite numbers (also in optional metadata), unsupported
schema and malformed timestamps are rejected. A record's `observed_at` must equal
batch retrieval. There is no substitution of publication time for observation time.

A run has a unique nonempty `universe` list of instrument identifiers and a
`session` date (`YYYY-MM-DD`). Status is `success` (one or more records),
`successful-empty` (zero), `partial` (zero or more, with bounded error reason), or
`failed` (zero, with bounded error reason). Successful statuses require null/absent
`error_reason`; failed/partial reasons are nonempty and at most 512 characters.
These are *declared* outcomes, not provider coverage verification. No stored run
means unattempted/unknown coverage; successful-empty means nothing observed in that
attempt, not proof no news existed. Each distinct raw batch preserves an outcome
revision for its provider/run ID. Exact raw replay creates no second outcome.

### Completed daily bars

Required fields: `instrument`, `venue`, `currency`, `exchange_timezone` (IANA),
`interval: 1d`, `session` matching run session, `session_type: regular`,
`adjustment_basis`, `bar_at`, `completed_at`, `available_at`, `observed_at`,
`completed: true`, `open`, `high`, `low`, `close`, `volume`,
`corporate_actions` (explicit object, possibly empty), `source_version`.

Prices are finite positive numbers; volume finite nonnegative. Require
`low <= open/close <= high` and
`bar_at <= completed_at <= available_at <= observed_at <= ingested_at`.
The exchange-local bar date must match session. Numeric strings and booleans are
not prices. Snapshots, unfinished bars and extended-session bars are rejected.
Completion/session values are declared, not checked against an exchange calendar.

Identity is provider/instrument/venue/interval/session/adjustment basis/bar instant.
A changed payload appends a revision; unchanged payload adds an observation without
another version. Corporate-action metadata and source version are retained; there
is no adjustment or return computation.

### News

Required fields: `item_id`, `instruments` (nonempty subset of run universe),
`source_tier` (`primary`, `secondary`, `vendor`, `social`, `unknown`), `content`,
`content_hash` (SHA256 of UTF-8 content), `source_version`, `observed_at`.
Explicit nullable fields: `url`, `publication_raw`, `publication_timezone` (IANA),
`publication_at`, `provider_available_at`, `event_cluster`.
A URL, when supplied, must be public HTTPS without embedded credentials.
Parsed publication requires raw publication text and its source timezone.

Provider/item ID is identity; the payload hash is version identity. Missing
publication remains null. Unknown publication/availability, publication later than
observation, availability later than observation, publication after availability,
and parseable raw/parsed disagreement are retained with flags and excluded from
as-of evidence. Raw ISO publication text with no offset is compared using its
explicit IANA timezone; arbitrary unparseable provider text is retained, not repaired.
A parsed timestamp is caller-declared; arbitrary text cannot be independently verified
by this module. Future/contradictory flags persist on that version. Corrections must
append a changed payload, not rewrite the original. No causal attribution is inferred.

## Python API and replay

```python
from harness.evidence_store import EvidenceStore

store = EvidenceStore('/private/caller-chosen/praesagus-fixtures')
counts = store.ingest(batch_bytes)
exact_bytes = store.raw(counts['raw_hash'])
news_versions = store.versions('news', as_of='2026-10-02T00:00:00Z')
bar_versions = store.versions('bars', as_of='2026-10-02T00:00:00Z')
coverage_attempts = store.runs(as_of='2026-10-02T00:00:00Z')
historical = store.versions('news', as_of='2026-09-01T00:00:00Z', historical=True)
```

Counts: `raw_hash`, `batches_added`, `runs_added`, `bar_versions_added`,
`news_versions_added`, `observations_added` (bar/news observations). Exact raw replay
returns zero additions. Whitespace-different batches archive separately, but identical
bar/news payloads reuse versions and preserve the new observation. Runs retain each
batch separately. Returned versions include identity, revision, payload hash,
record metadata, flags, raw-linked observations, `first_observed_at`, `first_known_at`,
`eligible` and `view`. Query instants/observation times are UTC Unix seconds; original
ISO text is preserved in raw and records/run metadata. First observed is derived from
stored observations, never publication. First known is minimum of each observation's
`max(observed_at, ingested_at)`. An as-of evidence view includes only observations
known by cutoff, and requires known availability <= cutoff with no flags.
It returns *all eligible revisions*, not just the latest, in identity/revision order.
Revision numbers reflect ingestion order, **not authoritative source chronology**.
Do not use `max(revision)` to choose the newest source truth: an older source version
backfilled later receives a greater revision. Publication time alone also does not
establish correction authority or bar vintage. Future consumers must resolve source
vintage using provider-specific version/correction metadata and provenance, after
applying the decision-time cutoff. If that evidence is insufficient, retain the
ambiguity rather than assume the last ingested version supersedes earlier evidence.
This store neither orders source vintages nor automatically selects source truth.

Late backfilled news cannot become system-known at its old publication date.
Historical mode intentionally returns later/ineligible evidence too, labeled
`historical-explanation` and with eligibility relative to cutoff. It must never be
used as decision-time evidence. Omitting `as_of` retrieves all eligible stored
versions; there is no assertion about real-world freshness or current time.

## Minimal synthetic US/MY example

Save this standard-library example as a temporary script outside the repository;
its `TemporaryDirectory` storage is removed on exit. Names/venues are invented and
are not claims of US/MY market coverage or live-data rights.

```python
import json
from tempfile import TemporaryDirectory
from harness.evidence_store import EvidenceStore

observed = '2026-10-01T22:00:00Z'
bars = []
for instrument, venue, currency, timezone, start, end in [
    ('SYNTH-US', 'TEST-US', 'USD', 'America/New_York',
     '2026-10-01T09:30:00-04:00', '2026-10-01T16:00:00-04:00'),
    ('SYNTH-MY', 'TEST-MY', 'MYR', 'Asia/Kuala_Lumpur',
     '2026-10-01T09:00:00+08:00', '2026-10-01T17:00:00+08:00'),
]:
    bars.append(dict(instrument=instrument, venue=venue, currency=currency,
        exchange_timezone=timezone, interval='1d', session='2026-10-01',
        session_type='regular', adjustment_basis='unadjusted', bar_at=start,
        completed_at=end, available_at=end, observed_at=observed, completed=True,
        open=100, high=105, low=98, close=103, volume=1000,
        corporate_actions={}, source_version='synthetic-v1'))
batch = dict(schema_version=1, origin='synthetic', provider='fixture-provider',
    run_id='synthetic-us-my', retrieved_at=observed,
    ingested_at='2026-10-01T22:01:00Z', rights={'status': 'synthetic-only'},
    run=dict(status='success', universe=['SYNTH-US', 'SYNTH-MY'],
             session='2026-10-01', error_reason=None), bars=bars, news=[])
with TemporaryDirectory() as root:
    store = EvidenceStore(root)
    print(store.ingest(json.dumps(batch).encode('utf-8')))
    assert len(store.versions('bars', '2026-10-02T00:00:00Z')) == 2
```

CLI (batch file and storage must remain private):

```sh
python3 harness/evidence_store.py --root /private/fixture-ledger ingest /private/batch.json
python3 harness/evidence_store.py --root /private/fixture-ledger query news --as-of 2026-10-02T00:00:00Z
python3 harness/evidence_store.py --root /private/fixture-ledger query runs --as-of 2026-10-02T00:00:00Z
```

`query bars/news --historical` is the explicitly labeled explanation view.
CLI output contains stored synthetic content: do not publish it automatically.
Tests use `pytest tmp_path`; no credentials, network, model or dependency download:

```sh
python3 -m pytest -q tests/test_evidence_store.py tests/test_forecast_review.py
```

Later tickets must settle live provider contracts, entitlements, retention/redistribution,
verified calendars/timezones, historical availability and run coverage completeness.
Movers, attribution, volume thresholds, forecast horizons and skill learning remain
deferred pending PRSG-24 review and separately accepted scope.
