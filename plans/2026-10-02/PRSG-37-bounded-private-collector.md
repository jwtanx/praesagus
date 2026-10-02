# PRSG-37 · Bounded private quote/news collector

Type: feature · Modules: connectors, financial-data · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high

## Why the ticket is created?
Secure reads and immutable private storage exist, but no collector connects them. Socket timeouts alone cannot bound DNS or trickled headers. Deliver a manually invoked, bounded collection path; this unlocks evidence for later reports, not predictions or public export.

## Approach and choices
Reuse the existing REST core, encrypted signer, exact login Keychain loader, HTTPS transport and private store. Isolate credentials/network in a subprocess; only the parent writes SQLite. A thread cannot safely terminate a stalled network call. A new asynchronous client would duplicate the tested signing/transport boundary. Process supervision costs startup overhead but supplies a deadline and descendant cleanup boundary.

## Accepted scope
Frozen base: 21211aea0d9b54d692c0c7f26dbeae8d2a5b1e64. Write only the six manifest paths. Explicit CLI invocation only; importing modules does no I/O. No live requests during implementation/tests. Parent opens an existing private store, never silently initializes it. Private credential directory locator enters the child through bounded IPC; no credential values in argv/environment/logs. Validate owned private files before reading AppKeyID; reuse encrypted private.pem and exact Keychain retrieval.

Plan is an explicit nonsecret US universe and literal news keywords, validated before spawning: at most one snapshot batch of 400 names and ten news requests of at most 50 records, sequential without retries. These local caps are NOT provider rate-limit claims. Exclude MY, portfolio, watchlist writes, scheduling, public artifacts, prediction logic and schema changes.

Worker uses fixed interpreter/entry, no shell, new process session, stderr discarded. Per-job worker/IPC deadline 20 seconds plus at most two seconds bounded termination/reaping; whole-run admission/accounting budget 300 seconds including cleanup. Reserve cleanup before starting a last job. Check the budget before and after parent ingestion and stop further jobs on overrun. Parent filesystem/SQLite writes can exceed this budget: it is not a hard end-to-end deadline. Do not forcibly kill the SQLite writer or add an outer supervisor in this ticket. Use monotonic time for deadlines and aware UTC wall times for evidence. No unbounded communicate/wait, reads or output accumulation. Terminate then kill the process group including security descendants. Cleanup failure stops further jobs; do not guarantee termination of OS-uninterruptible processes.

Return one bounded length-prefixed frame: matching job digest, HTTP status, exact response bytes and actual receipt time, or allowlisted failure enum. Never relay authentication headers, signatures, nonce, private paths or exception strings. Screen secrets in the child before IPC, independently validate and normalize in the parent. Reuse store screening without changing existing modules; if a safe reuse interface is missing, request scope amendment rather than duplicating divergent secret policy.

Only parent ingest writes successful exact bytes through existing store.ingest. Worker/credential/timeout failure records a zero-status empty-body transport failure using actual failure observation/ingestion times, not fabricated raw evidence. Storage failure remains visible and stops collection; do not report a persisted attempt when storage failed. Current schema collapses granular transport categories; allowlisted outcome counts may retain granularity without provider content. Reject clock rollback/inconsistent time ordering; never backdate or compensate timestamps. Caller-declared trusted-capture is not authentication proof.

## Downstream boundaries
This ticket does not deliver an 08:00 report. Subsequent projection needs completeness-aware queries, temporal eligibility filtering, same-time conflict handling, verified currency/session/units/prior close, freshness policy and explicit schedule/overlap/missed-run behavior. Snapshot volume is not a completed bar or RVOL. Post-cutoff ingestion is unavailable to an earlier cutoff even if provider time is earlier. Public redistribution rights remain unconfirmed; this implementation has no export.

## When it's considered done
- [x] PRSG-37-D1: Synthetic process/IPC/deadline and store integration tests pass, including descendant cleanup, oversized/truncated/wrong-job frames, secret exclusion, clock rollback and failed/empty/partial coverage.
- [x] PRSG-37-D2: Lead independently reviews all six paths, bounded resource behavior and unchanged protected modules; docs clearly distinguish implemented collector from unimplemented scheduling/projection.

## Validation and evidence
Run the exact manifest tests offline. Include local synthetic hanging workers and descendant cleanup, no real Keychain or network. Replay existing REST/store regressions. Human live smoke testing is a separate later gate, not required or claimed here. Evidence recorded 2026-10-02: exact manifest command `python3 -m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py` from repository root, using isolated Python 3.12.14 / cryptography 50.0.2, **343 passed in 2.35s**. Transcript: `/tmp/PRSG-37-tests.txt`. Python 3.11 was unavailable and was not tested.

The first collector run had 35 failures / 28 passes: fixtures used noncanonical macOS `/tmp` and incorrectly prohibited the existing PEM loader from opening the PEM. Those fixture errors were corrected without weakening path/file validation. Subsequent focused and shared replays passed (63 focused; 338, 339 and 341 shared during additions; final 343). Final coverage has 72 collector cases, including a real synthetic worker ignoring TERM and requiring group KILL. No live network, real Keychain or real credential reads occurred.

Implemented six scoped paths: manual CLI, isolated bounded worker IPC, parent-only existing-store integration, offline tests, operational documentation and ticket evidence. Parent records actual failed attempts without fabricated raw bytes; failures/clock rollback/storage errors stop or reject as specified. Worker process cleanup is bounded; OS-uninterruptible termination is not guaranteed. The Lead-approved 300-second admission/accounting exception is documented and tested with synthetic slow storage. Post-cutoff ingestion is excluded by the unchanged store.

Independent Lead review accepted 2026-10-02 after reading all six files and replaying 343 tests in 2.41s on Python3.12/cryptography50. Researcher independent read-only review found no reproducible blocker. Acceptance covers manual US-only private collection, not live validation, scheduling, report projection, public export, complete evidence coverage or a hard storage deadline. Delivery commit/push is recorded through Git history; deployment remains separately verified.

## Findings and tradeoffs
Engineer supplied the bounded worker design; Consultant identified strict-query eligibility and completeness/reference-metadata gaps. Lead inspected the existing transport and fixture CLI before freezing scope. Preserve their restrictions rather than relabeling point snapshots as completed sessions. Relevant implementation: connectors/moomoo_rest_live.py, ingest/private_market_store.py, scripts/market_ingest.py; these remain protected.
