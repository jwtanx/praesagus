# PRSG-2 — Connector and dataset freshness

Type: feature · Modules: backend, frontend, connectors, observability · Owner: Engineer · Priority: P2 · Effort: M (3–5 person-days) · Impact: high

Harness manifest: [PRSG-2.harness.json](PRSG-2.harness.json). Created 2026-10-01, Asia/Kuala_Lumpur. Owner: Engineer; acceptance: Lead.

State: planned, not assigned. Target: researchers and operators who need to know whether monitored evidence is available and current. Effort: 3–5 person-days. Expected impact: high trust and failure-detection improvement; do not equate a successful run with complete market coverage.

## Baseline and boundary

`backend/services.py` constructs Healthy platform status and current last_run values from configuration rather than observed execution. Financial datasets contain ingest timestamps, but this does not prove that the last attempted run succeeded. Instrument the four financial scripts first; generic social connectors and cloud scheduler integration follow only after a separate scope decision.

## Proposed contract

Persist a bounded run ledger keyed by run UUID and dataset/connector. Record started_at, finished_at, state (running/succeeded/partial/failed), records fetched/accepted/rejected, latest observed publication time where known, and a sanitized error code. Record attempts before fetching and terminal state even on exception. Never store credentials, webhook addresses, or full exception/provider bodies. A configurable timeout can label abandoned runs unknown; it must not invent success.

Provide a read-only health API with last_attempt, last_success, latest_data_time, coverage_warning, and freshness classification per supported dataset. Freshness thresholds come from explicit per-dataset configuration, with different schedules for filings/news/calendar; missing policy means unknown. Distinguish valid empty run, absent data, stale data, failed run, and never run. File modification time is not provider freshness. Moomoo remains explicitly on-demand.

Use atomic local metadata storage for the single-host MVP with concurrent-writer protection; deployment across replicas needs shared storage and is a later decision. Add truthful Financial/Platforms/Pipeline statuses only for instrumented paths. Uninstrumented paths show unknown/configured, never Healthy.

## Validation and impact measurement

Fixtures cover successful empty runs, partial acceptance, upstream failures, interrupted runs, stale/future timestamps, invalid config, concurrent writes, corruption and secret redaction. API and UI tests prove last_attempt and last_success differ after failure and no invented timestamps appear. Preserve prior run evidence.

Metric: every instrumented dataset card displays a real last-success time or explicit unknown/never-run state; simulated failures become visible after one refresh. Establish an incident-detection baseline with scripted failures rather than guessed production savings.

Work breakdown: ledger/instrumentation 1.5–2 days; API/UI 1; tests/failure drills 0.75–1.25; docs/review 0.5. Dependency: approved single-host retention and status storage location. Rollout one script first, then extend to four. Stop if metadata failures affect ingestion; status reporting must not silently discard raw data.

## When it's considered done

- [ ] PRSG-2-D1: Four financial scripts persist real attempts/successes with bounded retention and sanitized failures.
- [ ] PRSG-2-D2: API/UI distinguish stale, absent, failed, never-run and successful empty datasets.
- [ ] PRSG-2-D3: Interrupted/concurrent writes and stale/future timestamps pass fixture tests without losing raw data.
- [ ] PRSG-2-D4: Focused/full checks pass and Lead accepts scoped diff, limitations and rollout evidence.

Check items and manifest acceptance evidence together; simulated failure-detection metric must be demonstrated before claiming impact.

## Lead review progress — 2026-10-08 MYT

The authorized fifteen-path phase-one diff passed manifest scope validation. Fresh checks on the configured Python 3.11.17 / pytest 8.4.2 environment: focused command 86 passed; full suite 1,208 passed; frontend build passed; React freshness replay passed using the existing isolated test-dependency location; `git diff --check` passed. October 8 report JSON separately passed schema/public validation and the existing schema-3 colored viewer preview. Those report results are outside PRSG-2 and do not expand its scope.

This remains a partial delivery. Only SEC filings are instrumented; insider, news and calendar invocation coverage remains unknown. The manifest correctly distinguishes an existing empty ledger (`never-run`) from an absent or corrupt ledger (`unknown`). The live desktop/mobile refresh-failure drill is still pending, as are original D1–D3 requirements and final ticket acceptance. No live provider, credential, raw-data or deployment checks were performed.

## Accepted phase-one scope freeze — 2026-10-05 MYT

Lead accepts a bounded **partial delivery**, frozen at `0a43f04f03b406cb73480a50cec9dc1b7f15f36e`; original October 1 key/date and Engineer owner retained. State: accepted/in progress for scope preparation. **Code implementation is not yet authorized.** Original D1–D4 stay pending, including the four-script requirement; historical proposed full rollout above is not this initial implementation scope. Every repository path outside the following exact fifteen paths is protected:

- `connectors/financial/run_status.py`
- `backend/freshness_services.py`
- `backend/services.py`
- `backend/main.py`
- `scripts/run_sec_filings.py`
- `ingest/config/financial_freshness.yaml`
- `frontend/src/services/api.ts`
- `frontend/src/pages/Financial.tsx`
- `frontend/src/pages/Platforms.tsx`
- `frontend/src/pages/Pipeline.tsx`
- `tests/test_connector_freshness.py`
- `tests/connector_freshness_checks.cjs`
- `plans/2026-10-01/PRSG-2-connector-freshness.md`
- `plans/2026-10-01/PRSG-2.harness.json`
- `AGENTS.md` (narrow factual capability/runtime opt-in documentation only)

### Frozen storage and error contract

Opt in through `PRAESAGUS_RUN_STATUS_DIR`, a canonical absolute owned/private directory with mode `0700` outside Git. No default/public root or Compose provisioning. With the variable unset, preserve existing SEC ingestion behavior, emit a fixed unconfigured-status warning and return API unknown/unconfigured; never invent run evidence. Explicit configured-but-invalid root/ledger or failure to persist start metadata fails before provider work with sanitized nonzero status. Terminal metadata failure preserves raw writes, emits fixed nonzero status and leaves unknown evidence; Lead accepts this availability tradeoff for the opted-in path.

Use stdlib SQLite, parameterized short transactions and a bounded five-second busy timeout; private DB mode `0600`. A nonblocking per-dataset `flock` admits one actual instrumented writer, not arbitrary external writers. Persist UUID/start before authentication/fetch; updates are keyed and conditional, with aware UTC/order validation and controlled error enums, no exception/provider bodies or credentials. Retain at most **1000 terminal rows per dataset including the pinned last success**, with retention floor/pruned counts. Never prune raw datasets. Interrupted/running rows become unknown/abandoned in the read view after explicit policy, with no fabricated finish time/success. GET never creates DB/schema/folders, prunes rows or marks state.

### Frozen status semantics and boundaries

Stage one counts yielded/stored invocation records only. Unobservable rejected counts and source coverage remain null/unknown. Connector internals currently swallow SEC metrics, insider parsing and calendar estimate failures; RSS may obscure failure/empty distinctions and substitute publication time. Wrappers cannot establish complete provider health. Missing or invalid freshness/abandonment policy means unknown. Separate last attempt, last success and invocation freshness from source coverage; dataset absent, valid empty and unreadable are distinct. Expose only valid aware source timestamps or explicit date precision with future flags. File modification, ingestion and API read time are not provider freshness; future calendar event dates are not source publication.

Fix generic config-derived fake Healthy/scheduled/last-run/next-run values to configured/unknown/null independently of SEC instrumentation. Generic `edgar` is not mapped to financial SEC; Moomoo remains on demand. Add an authenticated read-only financial freshness route and a separate Financial status section, preserving catalyst and Moomoo behavior. UI refresh failure clears previous status. No scheduler, new provider, private portfolio or classifier expansion. Existing storage concurrency and uninstrumented writers remain outside the ledger guarantee.

### Frozen verification and remaining decisions

Commands below are planned, **not executed by this scope freeze**. Resolve Python through the persistent supported 3.11 environment while retaining exact argv/cwd:

```sh
# Repository root
python3 -m pytest -q tests/test_connector_freshness.py tests/test_api_integration.py tests/test_catalyst_inbox.py tests/test_moomoo_api.py
node tests/connector_freshness_checks.cjs
python3 -m pytest -q
# frontend cwd
npm run build
```

Focused fixtures must cover successful empty invocation, last-attempt/last-success after failure, absent/corrupt data and ledger, invalid/missing policy, future/naive timestamps, bounded retention/pinned success, concurrent process lock and killed-run abandonment, metadata start/finish failures preserving raw bytes, sanitized errors, API auth/read-only and stale UI refresh. Full pytest/hooks remain required. Lead owns desktop/mobile synthetic one-refresh failure drill and final scope acceptance; no claimed automatic dispatch through the existing verification policy, which is protected.

Operator must provision the opted-in root privately; no runtime provisioning or real provider/credential/raw-data operation in implementation tests. Subsequent insider/news/calendar rollout requires another explicit scope amendment and review of invocation-only versus provider outcome semantics before whole-ticket acceptance. No installs, additional tickets, code changes, tests, commits or pushes in this scope-only assignment.

### Lead scope clarification — 2026-10-05 MYT

`AGENTS.md` is the fifteenth allowed path, limited to factual SEC invocation ledger/read-only freshness API, opt-in runtime, other three scripts untracked, unknown coverage and no deployment claim. No role, policy, skill or safeguard changes. Stable phase-one progress ID `PRSG-2-P1` records partial delivery/check evidence without completing original D1–D4. If existing tests/API expectations require other edits, report a scope amendment rather than write them. Implementation remains unauthorized pending Lead readback.

### Numeric policy and operator freeze — 2026-10-05 MYT

SEC filings invocation policy: `max_success_age_seconds: 172800` (48 hours), `abandoned_after_seconds: 7200` (2 hours). These are explicit local policy estimates, not a provider SLA, provisioned scheduler or hard network deadline. Insider/news/calendar remain uninstrumented/unknown; missing ledger entries for these paths do not mean never-run or healthy. No generic `edgar` mapping. Operator provisions an existing owned/private `0700` directory outside Git and sets `PRAESAGUS_RUN_STATUS_DIR` consistently for backend and SEC script on the same host. GET never provisions the root. Lead independently confirmed fabricated generic health/current last/next times and no existing SEC ledger. Fifteen-path freeze including narrow AGENTS amendment remains recorded; implementation awaits authorization and all D1–D4 remain pending.

### Implementation authorization — 2026-10-05 MYT

Lead explicitly authorized phase-one implementation after independent final fifteen-path scope/policy readback. This dated approval supersedes earlier awaiting-authorization statements. Frozen base unchanged; original D1–D4 remain pending. PRSG-2-P1 is partial delivery awaiting review; no whole-ticket completion.

## Lead integration re-freeze — 2026-10-09 MYT

For selective integration onto the current canonical branch, Lead re-froze the same fifteen allowed paths and protected-path boundaries at `ec35583d0019e5cc974cb50d95c24d53faf77081` (`origin/main`). This supersedes the prior base only for the integration diff; the original implementation authorization and historical base remain recorded above. The PRSG-2 patch applied without conflicts to current `backend/main.py` and `frontend/src/services/api.ts`, preserving the Moomoo routes/client. No report viewer, report JSON, or calendar path is part of this change. The 2026-10-08 colored report and current viewer remain from `origin/main`. Original D1–D4 and the desktop/mobile behavior drill remain pending; this is still a partial SEC-only delivery.

## PRSG-2-P1 Engineer partial delivery — 2026-10-05 MYT

2026-10-05 MYT phase-one partial delivery: opt-in SEC invocation SQLite/flock ledger, bounded1000 terminal rows including last success, read-only freshness API/data classifications, generic configured/unknown/null times and isolated refresh-safe UI. Exact fifteen paths changed; raw storage/providers/Moomoo/catalyst untouched. Original D1-D4 remain pending; other three scripts uninstrumented/coverage unknown. GET does not provision/write/prune; 48h/2h local policy. Initial focused collection failed because existing feedparser dependency absent from persistent test runtime; fixture now imports SEC script with mocked provider module, no package installation or skip. Supported3.11 exact focused four-test command:72 passed,12 dependency warnings in0.79s. Exact Node replay passed; npm run build cwdfrontend passed45modules/394ms. Full suite intentionally pending required integration hook; Lead desktop/mobile HTTP drill/review pending. No live providers/credentials/raw-data operations, commit/push/deployment.

Implementation uses operator-preexisting private root, writer-only schema initialization, parameterized short transactions and owned `0600` files. POSIX nonblocking dataset lock covers only instrumented SEC writers. Previous orphaned start rows retain unknown termination time when a new writer proves no predecessor holds the lock; reads derive abandonment without updates. API response inspections and source time are separate from invocation success. Raw dataset presence is read strictly with a16MiB bound, not through the legacy absent/corruption-to-empty loader. No raw dataset pruning or change to provider/alert/store contracts. A terminal metadata failure can leave surviving start counts unknown; no data rollback or provider retry occurs. Filesystem/SQLite operations are not a hard end-to-end deadline.

Python checks resolved exact `python3` argv using PATH `/Users/jwtan/.codex/venvs/praesagus-tests-311/bin` (3.11.17); no skipped tests. Coverage includes actual script orchestration with mocked connector authentication/fetch/normalize/store failures, successful empty, partial acceptance, start/finish metadata failure/raw preservation, two-process lock/kill abandonment, retention pinned within1000, future/naive source/run time, invalid policy/root/schema/corrupt dataset, GET auth/no creation/no state marking and removal of fabricated generic run times. Node replay uses existing external renderer; no dependencies were installed. Scope/diff checks and readback passed. Full pytest/check evidence and Lead browser review remain pending; not whole-ticket completion.

### Lead manual HTTP fixture recipe (not executed by Engineer)

Both commands use synthetic temporary paths/data only and existing runtimes. No real Keychain, broker or credential access. From repository root:

```sh
PATH=/Users/jwtan/.codex/venvs/praesagus-tests-311/bin:$PATH python3 -m tests.test_connector_freshness
```

In another terminal, cwd `frontend`:

```sh
VITE_API_BASE_URL=http://localhost:8016 VITE_API_KEY=synthetic-api-key npm run dev -- --host 127.0.0.1 --port 5179
```

Open `http://localhost:5179/financial` (frontend router path; use its Financial navigation if needed). First freshness GET shows a successful empty SEC invocation. First **Refresh status** produces failed attempt with retained last success. Next refresh returns syntheticHTTP503 and must remove all old freshness cards/timestamps while existing financial/catalyst/Moomoo state remains separate. Verify desktop and390px width. Calls after the third stay503; restart fixture to reset the sequence. Ctrl+C stops server and cleans temporary fixture data. No scheduled jobs, private-root provisioning or real provider probe was performed.

### Lead reader finding correction — 2026-10-05 MYT

2026-10-05 MYT Lead independent reader finding corrected within scope: contradictory succeeded/error rows and running/unknown finish/error combinations now fail closed; canonical UUID4, integer nonnegative yielded/stored bounds, terminal time ordering and retention metadata validated. Writer validates existing ledger before provider work; reader query/schema errors sanitized. Thirteen deterministic corrupt-row variants exercise unavailable/unknown/no last-success, no API crash, unchanged metadata bytes and no script work on corrupt ledger. Final exact focused four-test command:85passed12 dependency warnings in0.83s on persistent3.11. No full-suite rerun; existing Node/Vite pass still applies because no later frontend edits.

### Manual fixture dependency correction — 2026-10-05 MYT

2026-10-05 MYT Lead independent checks: focused85passed12warnings0.90s, Nodeexit0, Vite45modules400msexit0. Original manual fixture recipe failed before listening: ModuleNotFoundError uvicorn in persistent3.11 runtime; no browser pass. Allowed test helper corrected to stdlib HTTPServer bound127.0.0.1:8016 with2s connection timeout, bounded4096 path, CORS/preflight, actual get_freshness and synthetic data routes. New local HTTP regression proves success -> failed attempt with retained success ->503 sequence and clean server shutdown. Final exact focused four-test command86passed12warnings1.63s. No install/dependency change or browser success claim; fullsuite/manualLeadreview remain pending.

Corrected launcher remains `PATH=/Users/jwtan/.codex/venvs/praesagus-tests-311/bin:$PATH python3 -m tests.test_connector_freshness` from repository root; now no Uvicorn requirement. Lead frontend dev server already on5179; do not start a duplicate. Restart fixture between desktop/mobile sequence drills. No browser pass recorded.


## Selective integration verification — 2026-10-09 MYT

On the re-frozen `origin/main` base `ec35583d0019e5cc974cb50d95c24d53faf77081`, the fifteen-path PRSG-2 patch applied without conflicts; Moomoo routes/client remain intact and no report-viewer, report-JSON, or calendar paths changed. Exact focused tests passed (115; 42 existing warnings), the full suite passed (1,281; 42 existing warnings), the connector freshness Node replay passed, and the frontend build passed (Vite 5.4.21, 46 modules). Frontend checks used temporary links to existing dependencies and removed them; no project dependency was installed or changed. The behavior drill and whole-ticket acceptance remain pending.
