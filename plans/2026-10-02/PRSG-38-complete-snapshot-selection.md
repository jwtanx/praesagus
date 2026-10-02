# PRSG-38 · Complete run-specific snapshot selection

Type: feature · Modules: financial-data · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high

## Why the ticket is created?
Existing query/attempts methods cap global results at1000. A daily report could miss its own run or pick an arbitrary revision. This ticket supplies trustworthy private selection for the already approved quote/report work, not report publication.

## Approach, choices and tradeoffs
Add PrivateMarketStore.select_snapshots(run_id, cutoff, expected_codes). Reuse existing immutable schema and integrity validation. Stream all as-of snapshot attempts for that exact run in one read-only transaction; no global LIMIT or raw-derived metadata bypass. This costs work proportional to run size but bounds output to400 names. Preserve existing methods/interfaces. Frozen base4ba12997e2016257c066918013b59424039340eb; only five manifest paths allowed.

Validate explicit unique US universe1–400, existing run-ID syntax and aware cutoff. Examine all matching attempts known by cutoff, verify requested universe equals expected universe for each available snapshot attempt; mismatch fails closed. Missing run and post-cutoff-only run both return no_available_attempts without disclosing future existence. view_complete means all available rows examined, never collector finished or complete useful data.

Verify raw hash, metadata, semantic hash, ordinal binding, source time and observation count integrity using existing normalization. Select only positive-price records with known source time<=cutoff and<=observed_at and known_at<=cutoff. Select greatest eligible provider timestamp, not ingestion revision. Equal code/time identical semantic hash is a replay; differing hashes withhold that latest quote as conflicted, never pick last-write or older fallback to resolve conflict. Preserve diagnostics for excluded records. Synthetic evidence remains explicitly synthetic, not authenticated trusted evidence.

Return run/cutoff/view_complete; bounded expected/requested/returned/eligible/selected/missing/conflicted lists+counts, available attempt status counts and per-code quote-or-null/gap reasons. Selected provenance retains attempt ID, raw/semantic hashes, actual observed/ingested/source times, origin and existing quality flags; bounded representative provenance with replay count, no unlimited historical output. Separate attempted coverage from eligible/selected coverage; failure!=empty. Unknown currency/session/adjustment/prior-close remain null with explicit gaps. No derived change/RVOL/targets or implicit freshness/calendar policy.

## Non-goals and dependencies
No schema migration, network/credentials, collector/CLI changes, MY support, scheduler, public artifact export or prediction. Later projection must freeze freshness/reference metadata and publication policy separately. Process-local/private data remains outside Git.

## When it's considered done
- [x] PRSG-38-D1: Offline selection/store/collector regressions pass; >1000 own/other-run rows cannot truncate selection; cutoffs, mismatch, eligibility, conflicts, replay and integrity corruption covered.
- [x] PRSG-38-D2: Lead independently reviews all five paths, unchanged schema/data and explicit completeness/metadata limitations.

## Validation
Run exact manifest argv on modern Python. Test missing vs future-only indistinguishability, source unknown/future/zero, precision, failed/partial/all-missing, same-time conflicts, no later evidence fallback, missing raw/hash/ordinal/count tampering and read-only byte/schema invariance. Engineer replay 2026-10-02: exact command `python3 -m pytest -q tests/test_private_market_selection.py tests/test_private_market_store.py tests/test_market_collector.py`, repository root, isolated Python 3.12.14 / cryptography 50.0.2: **189 passed in 4.44s**. Transcript `/tmp/PRSG-38-tests.txt`. Earlier replays passed179 and188 during added integrity cases; no failed run in this implementation pass. Python3.11 unavailable/not tested. No live network, credentials or public artifact output.

Selection streams available exact-run attempts in one read-only transaction, checks all normalized record/observation bindings and counts, and keeps at most400 per-code states with at most two conflict provenance representatives. Tests include actual >1000-row immutable ingestions for own/other runs, all400 codes, missing/future-only indistinguishability, cutoff precision, exact universe, failed/partial/all-missing, temporal rejection, same-time price/volume conflicts, replay, metadata/raw/source/ordinal/count/run corruption, and unchanged DB/raw bytes/schema. Existing store/query/collector behavior replays unchanged.

Manifest/all five supplied changed paths validate; scoped whitespace is clean. Lead reviewed all five paths and independently replayed 189 tests in 4.41s. Researcher independently replayed 189 tests in 4.47s and found no reproducible blockers. Lead accepts D2 and completion; unrelated .DS_Store preserved. Commit/push evidence is derived from Git history, not an invented self-referential hash. Completeness describes all available rows examined, not run completion, useful data completeness or freshness. Unknown reference metadata and rights remain explicit; no schema, scheduling, collector or report projection changes. Validation remains offline synthetic only; live entitlement and publication were not tested.
