# PRSG-40 · Daily quote orchestration

Type: feature · Modules: financial-data · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day estimate) · Impact: high

## Why the ticket is created?
Oct3 report generator did not invoke the delivered collector/projection: six legacy quotes, 44 missing, no observed_quote. Fresh Lead SPY probe proves authenticated HTTP200 with price/volume fields, not complete universe entitlement. Join the existing APIs rather than add more infrastructure.

## Approach and tradeoffs
One explicit manual command validates accepted schema3 template/universe/private output and existing store, derives exact approved30US codes, constructs one snapshot-only plan, calls existing collect, project_report, validator and write_private_draft. Explicit unique run ID; no fallback/retry/newstorage/credentials discovery. Worker owns credential access; coordinator passes only locator, never reads or logs secrets. Preflight template/universe/output collision before network. Keep every50 row, MY unsupported, forecasts unknown/null, unknown quote reference metadata visible. Publication remains separate: never copy private draft wholesale into artifacts.

Cutoff is explicit and matches template.as_of. Reject starting at/after cutoff; collection must occur in a declared pre-cutoff window. Never retroactively use new captures in Oct3's earlier08:04 cutoff. Late ingestion remains excluded. This command does not generate narrative; caller supplies accepted cutoff-safe template, clock is injectable for offline tests. Do not pretend an existing report can be retimed without rebuilding decision-time sources.

Failures preserve actual attempts. Return degraded nonzero status on failed/partial/allmissing or insufficient selected coverage; no successful-complete claim from view_complete. Safe queryable upstream failures may produce honest private missing draft. Storage/integrity/cleanup failures stop and surface sanitized error, no forged coverage or retries. Output collision checked before collector and atomic no-clobber after. Public data, broker watchlist mutations, portfolio, news scheduling, ratings and dependencies changes out of scope.

## Checks and value
Five exact paths frozen at0f17e42acdae0fd5010ac924f369da5a143caf6d. Offline synthetic injected collector/store/clock only. Cover exact30US plan, same run/cutoff,50rows, partial/empty/failed/storage failure, degraded exit, late ingestion exclusions, template mismatch/no-clobber before worker, secret/raw/path exclusion, and old regressions. Documentation must explain practical pre-cutoff template/capture window and no public activation. Metric: one manual invocation reaches private50-row draft with explicit selected/missing counts; no measured live coverage uplift yet.

## When it's considered done
- [x] PRSG-40-D1: Focused exact suite and deterministic orchestration regressions pass.
- [x] PRSG-40-D2: Lead full scope/temporal/failure review accepted.

## Progress
Lead accepted after full five-path review and independent exact193-test replay in4.13s. Historical pending handoff below retained. Daily skill wiring/public projection and broker watchlist remain separate delivery dependencies, not claimed by this ticket. Live30US batch transport remains unresolved; offline delivery does not prove operational coverage.



## Engineer handoff evidence — 2026-10-03

Exact manifest command `python3 -m pytest -q tests/test_daily_quote_report.py tests/test_market_collector.py tests/test_daily_report_projection.py tests/test_private_market_selection.py`, repository root, existing isolated Python3.12.14 / cryptography50.0.2: **193 passed in4.13s**; `/tmp/PRSG-40-tests.txt`. Earlier184/190 replays passed as bounded rejection cases were added; no failing replay this pass. Python3.11 unavailable/not tested. Only injected synthetic collector/clock fixtures used; no worker/live/credential read, dependency installation, watchlist mutation or public export.

Delivered manual orchestration script and focused tests, operational docs and ticket evidence in five allowed paths. Reuses existing collector/selection/projection/validator/writer with one exact30US snapshot plan, no news, preserved50 rows and explicit20MY unsupported. Validated before collection: accepted template/calendar/universe/forecast/cutoff, private destination, locator, existing store and unused run identifier (including post-cutoff old runs via identifier-only readonly SQL). Matching one-job collector outcome is required; storage/integrity/cleanup/clock failures write no draft. Safe transport/upstream/empty/partial/late failures preserve attempt evidence and produce degraded/nonzero honest private draft. Full30US selected coverage is narrowly named us-coverage-complete, not freshness/reference/MY/source-authentication proof.

Current time is checked within the declared window and immediately before collection; actual late ingestion is excluded, never backdated. Narrative is caller-accepted and not generated/certified here. No atomic distributed run reservation/overlap lock: caller must supply a unique run and avoid overlapping invocations. Output preflight is followed by existing atomic no-clobber writer. Unknown reference facts and unconfirmed rights remain explicit; publication and workflow activation separate. Lead's single-SPY HTTP200 vs30-code transport failure/no valid response is a separate live diagnostic, not Engineer evidence of entitlement or symbol availability. No retry or connector widening performed.

Five-path scope/whitespace validation is recorded in handoff. D2 independent Lead review remains pending; no staging/commit/push. Patch `/tmp/PRSG-40-engineer-handoff.patch` contains the full five-file delivery.
