# PRSG-61 — Trader Moomoo market snapshot, trend, and forecast

Type: feature · Modules: financial-data, market-research, frontend, skills, harness · Owner: Engineer · Priority: P1 · Effort: M (3–6 person-days) · Impact: high; makes timestamped Moomoo evidence and the existing forecast inspectable in the shared Pages viewer; evidence confidence medium because the read-only REST path and price-only public mapper exist, while scheduled live coverage and public artifact integration have not been demonstrated end to end. Created 2026-10-05 MYT.

## Goal and baseline

At the existing Trader 08:00 MYT report run, use the existing direct HTTPS Moomoo REST collector and its isolated credential/worker path to capture timestamped market data. The Trader consumes that run's quote/news evidence before authoring the existing SPY/QQQ report forecasts, freezing their reference/horizon, source evidence, bull/bear case, invalidation, and visible confidence; if evidence is insufficient, record an honest abstention. Keep raw responses and full provenance in the existing private append-only store. Project a deliberately small public allowlist into a new date-keyed static snapshot artifact only when verified public-use evidence permits the exact fields and market. Display an observed-price trend beside the existing SPY/QQQ report forecasts in the GitHub Pages daily-report viewer. Preserve the full existing 50-name report and forecast set: the REST snapshot API accepts US codes only, so capture the 30 US names and label the other 20 MY names unsupported/unavailable rather than removing their report rows. Add a market-level chart for SPY and QQQ; the daily report's existing 50 forecast rows remain authoritative. No autonomous or model forecast engine is in scope.

The checked-in direct REST read client, HTTPS transport, encrypted Ed25519/Keychain credential loader, isolated worker, `scripts/market_collect.py`, and `ingest.market_collector` already perform bounded read-only US quote/news requests and persist sanitized/validated source records to the private market store. `scripts/daily-market-brief/run_private_quote_report.py` can create only an external private draft; `ingest.daily_report_projection.map_public_snapshot` is a price-only allowlist mapper, while the docs explicitly forbid copying private drafts to `artifacts/`. There is no public snapshot writer or daily Pages bridge. This ticket adds that narrowly scoped projection path. The existing offline `harness/forecast_review.py` scores frozen ledger rows at an explicit review timestamp, but does not generate predictions or verify source prices. Do not use `/api/v1/moomoo/*` or OpenD for this feature; no OpenD download/configuration is needed.

## Frozen delivery boundary

Lead accepted this scope for implementation on 2026-10-05 MYT. Base is `5e9ec0cd51769b192cf45225596ae028258f79a7` (`origin/main` in the isolated checkout). Engineer may change only the paths below. Dated report JSON and `reports.json` remain ordinary output of the already-authorized Trader workflow and are not implementation-owned by this ticket. The new snapshot artifact directory is ticket-owned output. No pre-existing reports are rewritten.

**Allowed paths**

- `scripts/daily-market-brief/publish_market_snapshot.py` (same-run projection and rights-gated snapshot writer)
- `ingest/daily_report_projection.py` (public projection from selected private-store records)
- `scripts/daily-market-brief/validate_report_json.py`
- `artifacts/daily-market-brief/index.html`
- `skills/daily-market-brief/SKILL.md`
- `docs/PRIVATE_REPORT_PROJECTION.md`
- `tests/test_market_snapshot_publication.py` (new)
- `tests/test_daily_report_projection.py`
- `tests/test_daily_report.py`
- `tests/daily_report_viewer_checks.cjs`
- `tests/market_snapshot_viewer_checks.cjs` (new)
- `artifacts/daily-market-brief/market-snapshots/` (new date-keyed runtime outputs only; no pre-existing files)
- `plans/2026-10-05/PRSG-61-trader-moomoo-market-snapshot-dashboard.md`
- `plans/2026-10-05/PRSG-61.harness.json`

**Protected paths**

- `backend/` (including `/api/v1/moomoo/*`; do not use or change)
- `connectors/moomoo_rest.py`
- `connectors/moomoo_rest_live.py`
- `scripts/market_collect.py`
- `ingest/market_collector.py`
- `ingest/private_market_store.py`
- `scripts/daily-market-brief/run_private_quote_report.py`
- `scripts/daily-market-brief/project_private_quotes.py`
- `frontend/`
- `agent-operations/` (including schedules, roles, and active role handoffs)
- `.github/`
- `artifacts/daily-market-brief/reports.json`
- `artifacts/daily-market-brief/2026-09-30.json`
- `artifacts/daily-market-brief/2026-10-01.json`
- `artifacts/daily-market-brief/2026-10-02.json`
- `artifacts/daily-market-brief/2026-10-03.json`
- `artifacts/daily-market-brief/2026-10-04.json`
- `artifacts/daily-market-brief/2026-10-05.json`
- `artifacts/financial-calendar/`
- `harness/engineering/price-prediction/forecast-ledger.csv`
- `scripts/daily-market-brief/monthly_calendar.py`
- `plans/2026-10-05/PRSG-60*`
- `AGENTS.md`
- all other paths

## Behavior and data contract

1. Reuse the direct `https://webapi.moomoo.com` HTTPS implementation via the existing collector/worker and secure AppKey/Ed25519/Keychain loader. The scheduled Trader invokes the collector with the exact 30 US codes derived from `watchlist-universe-five.json` and at most ten distinct supported news queries (sizes 1–50, supported language values); the collector already validates the plan, isolates credentials/network access, stores raw evidence privately, runs jobs serially without retries, and reports sanitized outcomes. Do not call OpenD, `/api/v1/moomoo/*`, or browser-side Moomoo services. Never pass credential contents through arguments, environment, logs, report JSON, or Pages. Preserve the existing private store and private draft workflow.
2. The public projector reads only selected same-run, cutoff-eligible store results and emits a separate schema-versioned date-keyed artifact under `artifacts/daily-market-brief/market-snapshots/YYYY-MM-DD.json`. Use a top-level report date/cutoff/provider, `quotes` array, `news_queries` array, and bounded coverage/status fields. `quotes` contains one row for every instrument in the current universe: 30 US rows have selected/missing/conflicted/failed status and explicit gaps; 20 MY rows have unsupported status. A selected quote may include only REST fields accepted by the connector/store: price, provider volume with unit/session explicitly unverified, and optional provider previous-close as an unverified provider metric. Retain source/update, observed, ingested, known and report-cutoff timestamps, provider and endpoint; include explicit unknown currency/session/adjustment/prior-close values. Do not infer quote currency, market session, adjustment basis, official close, percent change, turnover or unsupported metrics. `news_queries` contains one bounded English size-10 query for each `SPY` and `QQQ`, each with success/empty/unavailable status and safe records containing title, HTTPS URL, news type, publication time and capture/availability time. Deduplicate by provider item ID but do not publish internal identifiers.
3. The public publisher requires a separate operator-provisioned rights-evidence record outside the repository. It must identify provider/authority, permitted market(s), every exported quote/news field, permission for public website display/redistribution, an authoritative evidence URL, verifier, and timezone-aware verification/expiry times. Fail closed without valid current evidence covering US plus every exported field; do not emit a public artifact and do not copy the record's private filesystem path or account details. Synthetic fixtures may exercise the permitted branch; no real credentials/network are used in tests. The official [Moomoo Terms of Use](https://www.moomoo.com/terms?global_content=%7B%22promote_id%22%3A13643%2C%22sub_promote_id%22%3A4) state that market data must not be redistributed absent prior written consent of the applicable data providers. No such field/market-specific permission is verified in this ticket's base; live public snapshot publication stays disabled until evidence is verified. This is a publisher gate, not a reason to omit projector/dashboard implementation.
4. The artifact contains no private draft, raw response, private path, run/attempt ID, hash, provider auth, or account data. All source/retrieval timestamps are timezone-aware, ordered, and no later than the frozen report cutoff. A successful zero-result news search is distinct from an unavailable query. The validator rejects malformed fields, invalid/future timestamps, HTML, and private/credential-shaped data. Older daily reports without a snapshot remain valid.
5. Extend `skills/daily-market-brief/SKILL.md` so the existing 08:00 MYT run captures REST quotes/news before forecast judgment and the Trader authors the existing SPY/QQQ forecast rows from that frozen evidence. Require reference/horizon, linked evidence, visible qualitative confidence, bull/bear case and invalidation; preserve an explicit unknown/unavailable abstention when support is insufficient. Keep forecast judgment manual; do not build a model/agent forecast engine. Publish the allowlisted market artifact with that day's normal report/index delivery only after the rights-evidence gate passes. Preserve all 50 rows and validate the artifact. Do not change schedules or imply guaranteed execution. Late collection is unavailable for the frozen vintage.
6. The viewer loads only same-origin date-keyed public snapshot artifacts. It preserves the current full 50-name report and forecast display, then adds a five-capture observed-price trend for SPY and QQQ. Plot only distinct report dates with positive validated prices; label the times as MYT capture observations (not official session closes), identify Moomoo REST, show source age/data gaps, and limit older report views to snapshots known by that report's cutoff. Show a trend only with at least three valid dates; otherwise show an explicit warmup/insufficient-data state. Display news titles/links and timestamps from the selected report's public artifact, or explicit empty/unavailable status.
7. Beside the trend, show the existing report's SPY and QQQ forecasts authored by Trader at the existing 08:00 run from the frozen capture and primary-source context: authored target date/horizon, reference date/price/source, direction, range only when defensible, visible qualitative confidence/reason, bull/bear evidence, invalidation, and sources. The capture is evidence input, not an autonomous forecast. If evidence is insufficient, preserve the forecast row as unknown/unavailable with null numeric targets and a reason. Preserve the full existing 50-name forecast coverage and horizon. A point snapshot alone does not establish a completed-session reference or forecast; do not reinterpret provider previous-close as a verified official close.
8. Keep the existing forecast ledger append-only and use `harness/forecast_review.py` at an explicit review time for matured scoring. Do not revise frozen forecast vintages. Score only matching target closes with source and timezone-aware availability time; `forecast_review.py` does not provide an exchange calendar. Show denominators, missing actuals and abstentions. Do not claim predictive skill or show a success-rate badge before 20 distinct eligible instrument-target outcomes; correlated vintages are not independent samples. Preserve existing next-session/week-end distinctions and scoring.

## Non-goals and constraints

- No edits to schedules, role ownership, PRSG-60 files, REST client/transport/credential loader/collector/private store, backend routes, Vite dashboard, or OpenD configuration.
- No always-on ingestion, push feed, historical bar service, new provider, private-store schema changes, model-generated forecast, autonomous self-editing, trading or order execution.
- No unsupported quote/news values, invented probabilities, or claims that capture timestamps are exchange close times. The current connector supports 30 US report symbols; MY quote values remain unavailable.
- Static Pages reads only committed same-origin public snapshot artifacts; it never calls a local/private endpoint. Continue the existing dated-report publication path and verify deployment separately.

## Measurement and rollout

Baseline: the viewer currently has per-instrument forecast rows but no multi-day Moomoo trend. REST collector data and drafts stay in the private store/outside Pages. Functional success is a validated public snapshot attempt for all 30 supported US instruments (with missing/conflicts represented), 20 explicit unsupported-MY rows, a timestamped news result including successful-empty, and a visible SPY/QQQ trend plus existing forecast state. Coverage metric: among the first 20 scheduled report dates, count dates with all 30 US instruments represented by selected/missing/conflicted/unavailable status, a timestamped news result/status, and a rendered trend/forecast state. Report credential, entitlement, network, provider or field gaps honestly without changing the 50-name report. This is a data-coverage measure, not an accuracy or adoption lift claim. Forecast outcomes are summarized only with sample size and abstentions; broadening the market-level chart beyond SPY/QQQ needs Lead review of first-20-date evidence.

## Checks

- `python3 -m pytest -q tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py tests/test_market_collector.py tests/test_private_market_store.py tests/test_market_snapshot_publication.py tests/test_daily_report_projection.py tests/test_daily_report.py`
- `node tests/daily_report_viewer_checks.cjs`
- `node tests/market_snapshot_viewer_checks.cjs`
- Public snapshot validation/projection against deterministic private-store fixtures covering missing/expired/wrong-market/wrong-field rights evidence, a permitted synthetic evidence case, selected/missing/conflicted quote rows, 20 unsupported MY instruments, empty/unavailable news, future/late timestamps, HTML, and credential/private/account-shaped values. Re-run daily report validation on existing schema-2/schema-3 files and a report with public snapshot points.
- `python3 harness/forecast_review.py --ledger harness/engineering/price-prediction/forecast-ledger.csv --as-of YYYY-MM-DDTHH:MM:SS+08:00` against frozen eligible, abstention, repeated-vintage, immature-target, missing-actual, and unavailable-actual-time fixtures. Existing ledger state is not changed by tests.
- Manual: with synthetic REST/store fixtures, inspect the rendered viewer at current and historical dates; confirm same-origin static reads, capture-time labels, 3-point warmup, failure/empty-news rendering, hidden later snapshots, 50 forecast rows/20 MY gaps, sourced forecast/confidence/abstention beside the trend, and no credential/private metadata in generated artifacts. Verify applicable terms/permission evidence covers every published field and market before enabling any live public write. Live REST/Keychain availability and Pages deployment remain separate operational evidence; do not run real credentials or live provider requests as implementation tests.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-05/PRSG-61.harness.json` with every ticket-owned changed path supplied using `--changed-file`.

## When it's considered done

- [x] PRSG-61-D1: The existing 08:00 workflow uses the direct REST collector for the 30 supported US symbols and bounded SPY/QQQ news queries, retains secure credential/private-store boundaries, and represents 20 MY names as unsupported without deleting report rows.
- [x] PRSG-61-D2: The public projector emits only same-run cutoff-eligible allowlisted fields, rejects missing/expired/wrong-market/wrong-field rights evidence, and excludes private data; permitted-path tests use synthetic fixtures only.
- [x] PRSG-61-D3: The static viewer preserves all 50 report rows/forecasts and presents a timestamp-labeled five-capture SPY/QQQ trend with warmup/gap/failure/news-empty and historical cutoff behavior.
- [ ] PRSG-61-D4: Trader's existing SPY/QQQ forecast rows visibly carry frozen reference/horizon, sourced evidence, confidence, bull/bear, invalidation, and honest abstention beside the trend; no forecast engine is added and scoring retains denominators/sample-size controls.
- [x] PRSG-61-D5: Workflow/documentation preserves the existing 08:00 automation identity, target, ACTIVE status and cadence; creates no duplicate automation; preserves the calendar/private collector/store; avoids PRSG-60 changes; and receives final Lead review. The separately authorized 08:00 heartbeat prompt update is documented; live public publication remains gated on verified permitted use.

## Delivery evidence

2026-10-05 MYT Lead accepted implementation scope on frozen base `5e9ec0cd51769b192cf45225596ae028258f79a7`. The integration branch is `codex/prsg-61` at `1b26df1ec7de2785aa474268d813f77be4261dc0`, fast-forwarded from the frozen base; report commits `d168e1b` and `1b26df1` remain in history. Lead post-rebase verification passed 514 focused Python tests, both DOM checks, 2026-10-05 report validation, ticket path validation, and diff-check. The viewer replay additionally covers malformed snapshot cutoff rejection, invalid point timestamps, and no older-date news fallback. Forecast review at `2026-10-05T21:17:21+08:00` was valid with 70 pending and zero scored; synthetic matured/abstention/missing-actual fixture cases remain unverified. D1–D3 and D5 are complete; D4 remains pending because no supported rated SPY/QQQ row or live data is available. Lead independently reviewed the final 12-file scope and found no out-of-scope paths. Lead separately updated the existing 08:00 heartbeat prompt to direct REST under standing authority while preserving its ID, target, ACTIVE status and rrule; no duplicate automation was created. No credential path was verified/configured, and no live request or public write occurred. No commit or push was made.
