# 002 — Connector and dataset freshness

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
