# PRSG-36 · Private snapshot/news SQLite evidence and read-only queries

Type: feature · Modules: financial-data, connectors · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimated) · Impact: high

## Why the ticket is created?
Human needs repeated daily Consultant analysis without committing raw/private data. PRSG-34 provides verified quote/news reads but no persistence. Existing harness/evidence_store.py deliberately accepts synthetic completed bars only.

## Approach
Build a separate standard-library SQLite market store, not an alteration of synthetic guards. Freeze this MVP: offline ingestion of injected trusted PRSG-34 responses plus read-only cutoff queries, no live scheduler/credential discovery/public export. Root explicitly outside repository and public trees; reject symlinks/unsafe permissions/unknown schema. Directory0700, DB0600, SHA256 exact raw exclusive/read-only files. SQLite distinct application_id/user_version, parameterized transactions/bounded lock, never rewrite versions/raw.

Store immutable run/attempt coverage, exact raw response hash, normalized snapshot/news versions and observations. Wrapper captures bounded ReadResponse.body before core decode; never headers/AppKey/signature/nonce/private paths. Non200 has no body, record sanitized failure without invented raw. Malformed/provider-error200 may be quarantined, never eligible evidence. All validation precedes transactional references; orphan raw on failed DB transaction is explicit. Verify hashes on queries.

Snapshots stay point observations, never completed bars: provider code, quote timestamp milliseconds, market date, retrieval/ingestion, unknown currency/session/adjustment unless supported metadata; numeric finite/nonnegative, bool rejected, zero volume retained, zero price unusable. US-only supported capture; MY remains explicitly unattempted unsupported. Missing requested codes and all-missing differ from successful-empty news. No RVOL/targets/currency guesses.
News identity provider+item_id; literal title/URL, publication seconds, unknown availability explicit. Duplicate news across queries preserves query observations; equal headlines differentIDs retained. Exact replay idempotent; equal semantic payload new observation; changed payload append revision, ingestion revision not authoritative correction order.
Queries require aware cutoff, known_at=max(observed,ingested)<=cutoff and source quote/publication time<=cutoff when known. Strict mode excludes missing required source times; observation-known mode explicitly labels uncertainty. Later revisions/backfills cannot leak. Return provenance/quality/coverage, bounded rows. Read-only SQLite URI/query_only; queries never create/repair/write. No arbitrary SQL CLI, portfolio/accounts/watchlists, model/forecast changes, network or paid enrollment.

## Options and tradeoffs
Separate live-market store avoids weakening synthetic test invariants. SQLite and immutable local files reuse existing design without a cloud database. MVP exposes normalized evidence, not predictions or public data permission. CLI only fixture ingestion/query; real collection and daily scheduling are separate follow-ups after storage review and hard-deadline gate.

## Findings
Researcher reviewed actual core: ReadResult drops raw envelope; capture trusted ReadResponse bytes before decoding rather than relabel json.dumps(data) as raw. Snapshotempty with requested universe must retain missing coverage. PRSG-34 manual quote/news probes passed, but retention/public licensing remains unconfirmed. No private data in fixtures.

## When it's considered done
- [x] PRSG-36-D1: Deterministic store/capture/query regressions pass including raw integrity, secret exclusion, partial/empty/failed coverage, duplicate/corrections and cutoff leakage.
- [x] PRSG-36-D2: Lead independently reviews outside-repo private storage/read-only behavior and unchanged synthetic safeguards.

## Progress

Lead accepted offline foundation after source/schema/CLI review, independent Researcher precision blocker and fix review, and Python3.12 replay150passed0.70s. Prior failed regression evidence retained. Actual data retention, live collection/scheduling, public rights and currency/session metadata remain separate gates; no claim of deployed ingestion.
Accepted scope frozen at068e679362c3391717d9237bcaa7e492d6be76ab on2026-10-02 MYT before implementation. PRSG33UI,35docs,Leadskill/.DS_Store unrelated changes protected. No real retention or collector schedule enabled.


2026-10-02 MYT — Engineer implementation ready for independent review.
Added separate stdlib SQLite private market store, explicit trusted-response
capture before core decode, synthetic-only fixture CLI and read-only cutoff queries.
No network/credentials/scheduling/portfolio/public exports/forecast changes.
Root/private file permissions, canonical outside-repo/public-root guards,
distinct application_id/schema, immutable append triggers, bounded locks,
exclusive SHA256 raw archival, orphan semantics and raw/normalized hash binding
implemented. Readers use mode=ro/query_only and reject WAL/journals before opening.
Snapshot partial/all-missing, empty news and failed attempts distinct; MY explicitly
unattempted unsupported. No non200/provider-error/malformed/secret-bearing raw
persisted. Nullable source times are degraded context only, excluded strict and
explicitly ineligible in observation-known mode. Zero prices unusable; no inferred
currency/session/adjustment/bars/RVOL/targets. Literal news titles and independent
query observations retained; revisions are ingestion order, not correction authority.
Fixture origin and caller-supplied unverified source authenticity recorded.

Exact frozen command: `python3 -m pytest -q tests/test_private_market_store.py
tests/test_evidence_store.py` — **132 passed**, no live credentials/data/network.
Existing synthetic safeguard implementation/tests unchanged against frozen base
(Git diff exit0). Time fences round capture times upward and cutoff downward;
original aware strings retained and full-precision ingestion ordering checked.
Later source/observation/revisions/backfills cannot enter older cutoff.
All six owned paths validated and whitespace checked; full owned patch saved
`/tmp/PRSG-36-engineer-handoff.patch`. D1 tests demonstrated; D2/manual Lead review
remains pending. No staging/commit/push; unrelated Lead skill/.DS_Store/PRSG-35
work preserved (Lead integrated PRSG-33 independently during this assignment).

Limits for review: declared/trusted input is not authenticated by store; known-key/
known-value secret screening is not a universal arbitrary-text secret classifier.
Private filesystem is not encryption or protection from malicious same-UID actors;
operators must declare custom served/public roots. Active journals/WAL fail closed,
lock timeout bounds waits rather than all I/O/CPU; archive-before-transaction may
leave an explicit orphan raw file. Repeated query observations are not independent
confirmations. Data rights/real retention/MY/collector scheduling remain unconfirmed
and unenabled. No runtime answer harness or automated investment judgment added.

### 2026-10-02 MYT — Independent review failure; acceptance held

Lead reproduced Python3.12 silent truncation above six fractional digits:
ingested00:01:00.000000900Z appears known at cutoff00:01:00.000000100Z,
and observed00:00:00.000000900Z followed by ingested00:00:00.000000100Z
incorrectly passes ordering. Prior132-test Python3.9 evidence was insufficient;
D1 returned pending and test check marked failed. Same-scope correction accepted:
shared explicit aware ISO lexical parser, at most six fractional digits and
conventional Z/±HH:MM offsets only, used before every timestamp parse/comparison.
Modern3.12 replay required, with nano cutoff/reversed order/fractional offsets.
Also clarify bounded query results cannot establish full coverage and strict
results still require temporal-eligibility filtering.

Engineer reproduced the review blocker on isolated Python3.12.14 before fixing:
new timestamp regressions **13 failed,134 passed in0.85s**. Output retained at
`/tmp/PRSG-36-before-parser-fix.txt`. Failure history/evidence preserved.

Correction implemented within unchanged scope: one lexical parser permits only
YYYY-MM-DDTHH:MM:SS, optional1–6 fractional digits, and Z/±HH:MM. It rejects
nanoseconds, fractional/second offsets, compact/spaced/comma/omitted-second forms
before datetime can normalize/truncate. All timestamp conversions, stored original
validation and observation/ingestion ordering route through that parser; aware
offsets and conservative millisecond fences/original strings preserved.

Intermediate modern replay147passed0.72s; final isolated Python3.12.14 exact frozen
argv **150passed0.75s**, adding independent reversed nano ordering, strict-result
eligibility filtering and limit-versus-full-coverage tests. Existing synthetic
implementation/tests unchanged (frozen-base Git diff exit0). Documentation explicitly
requires eligible_for_temporal_evidence filtering even in strict mode and explains
limits omit matching observations and cannot demonstrate full coverage. The
pre-fix13failed/134passed evidence remains preserved. D1 tests restored; D2/final
Lead acceptance pending. Scope/whitespace valid, no secrets/live/commits/push.
