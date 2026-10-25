# Current Fixed50 Forecast Command

This private research command coordinates existing history collection and the PRSG-140 fixed50 baseline. It uses no trained model, new connector, public export or trade execution. Numerical scenarios remain uncalibrated next-close research, not whole-window extrema or measured predictive accuracy. The standalone100 trained-model workflow is separate.

Use Python>=3.11 and an absolute script path from any working directory. Paths containing spaces are supported:

```sh
"/absolute/path/to/approved/python" \
  "/absolute/checkout/scripts/daily-market-brief/run_current_forecast.py" \
  --online --config "/absolute/private/online.json" \
  --release "/absolute/private/lead-trader-release.json"
```

Online mode requires a separately authorized finite release with exact source-use, runtime, plans, dates, quotas, pacing, deadline and capture IDs. This documentation and `--online` are not a collection grant. No paid access, new provider endpoint or recurring financial approval is implied.

For existing reviewed captures or after supplying independently reviewed admissions, use explicit offline mode:

```sh
"/absolute/path/to/approved/python" \
  "/absolute/checkout/scripts/daily-market-brief/run_current_forecast.py" \
  --offline --config "/absolute/private/captured-fixed50-config.json"
```

Offline mode calls the existing fixed50 adapter and never reads the credential locator/release or calls a provider. It reports `mode: offline_store`, `provider_refreshed: false`. Supplying `--release` offline, omitting it online, or selecting both modes fails.

## Source Review Boundary

A new capture changes raw hashes and original retrieval/ingestion/knowledge times even if prices are unchanged. These changes invalidate old exact-evidence admissions. The command never rewrites reviewer decisions/hashes, carries an old approval forward, trains a model, or returns an aging CSV as fallback. It can collect and export in one invocation only for rows with matching current independent admissions at preparation time.

Otherwise the command writes reviewable candidates and returns `insufficient_coverage`, exit2, with `next_action: review_required` when admissions are missing. Reviewers inspect those actual candidates and supply exact hash-named admissions through the existing [private fixed50 contract](MANUAL_FORECAST_CSV.md). Resume using the returned `resume_config` in **offline** mode to avoid collecting again. Currentness is rechecked at resume: a closed target or expired calendar/action coverage still withholds. There is no indefinite reviewer polling, automatic gate acceptance or guarantee of35 eligible names. Explicit independent review remains necessary when evidence changes.

## Private Inputs

All JSON files must be owner0600/0400 regular files under existing owner0700 private parents, outside Git/public paths, with no symlink components. Store, output, receipt and review directories are existing owner0700 paths. Existing readers reject malformed/duplicate-key/non-finite/oversized JSON. Source templates and prior forecast/review files are never mutated.

The ordinary fixed50 config is documented in [Manual Forecast CSV](MANUAL_FORECAST_CSV.md). Keep its exact50 ordered identity/code/currency entries and nullable unsupported rows. For each planned non-null template, prebind `source.vintage` to the assigned **new** capture ID described below. Its expected normalization version/dialect must match the released request. Do not change old reviews to match the future vintage. Supply reviewed complete US/MY sessions, current action/private-rights/narrative facts and per-session finality cutoffs; the orchestrator does not author them.

Online config schema1 has exactly these keys:

| Key | Value |
| --- | --- |
| `schema_version` | Integer1 |
| `fixed50_config` | Absolute private path to the reviewed fixed50 input config |
| `credential_locator_file` | Absolute private JSON path containing exactly existing `directory`/`app_key_name` references; no key material |
| `plans` | Nonempty finite list, at most50 entries; each `{path, sha256, run_seconds, fixed50_sha256}` |
| `run_prefix` | Unique1–120-character letters/digits/underscore/dash identifier |
| `minimum_start_interval` | Explicit approved positive start spacing in seconds, at most600; this is a budget, not inferred provider entitlement |
| `job_seconds` | Positive worker timeout, at most20seconds |
| `cleanup_seconds` | Positive cleanup allowance, at most2seconds |
| `total_seconds` | Positive whole-operation dispatch budget, at most600seconds |
| `receipt_parent` | Existing private0700 directory for exclusive claims/operation receipts |

Plan files retain the existing collector schema: `schema_version: 1`, `codes: []`, `news: []`, and `history` with at most30 daily unadjusted100-bar requests. Each history entry has exact `code`, `end` and, where required, explicit `normalization_dialect`. No snapshots, news, duplicate/cross-plan codes or names outside fixed50 are accepted. At most50 distinct jobs total. Plans may cover a separately released subset; names outside that subset get no old capture fallback. Each plan's `run_seconds` is positive and at most300seconds. Requests/plan order are frozen, not reranked.

`sha256` and `fixed50_sha256` are SHA256 of parsed JSON serialized with sorted keys, compact separators, ASCII escaping and `allow_nan=False`, matching `ingest.forecast_scenario._hash`. Each plan entry binds the full fixed50 config hash as well as its plan hash. The release binds the online config hash. Thus changing a file behind a path invalidates its binding. Runtime pins below are ordinary SHA256 of file bytes.

Assigned capture IDs are `run_prefix-001`, `run_prefix-002`, and so on in complete plan/job order. A planned non-null template must already declare that exact ID in `source.vintage`; source templates are not rewritten automatically. Existing successful, failed or empty run IDs are rejected by a bounded exact-ID read from the verified store. After collection the new captured-config references these explicit new IDs only; every unplanned identity has `run_id: null` even if the original config had an old selector. Null templates retain their missing state, without invented financial facts.

Before dispatch, each non-null planned template must have a current complete venue schedule, plan `end` equal to its latest completed reference, and the reviewed finality cutoff already reached. A date/window is never rolled forward to make a stale released request appear current. The command checks current venue windows again before later jobs and after capture. Operational finality still requires the actual original retrieval to be after the cutoff; waiting later does not repair an early capture.

## Exact Release

The release JSON has exactly `schema_version: 1`, `config_sha256`, `not_before`, `expires_at`, `one_use_id`, `source_rights_reference`, `reviewers`, `runtime_sha256`:

- `config_sha256` binds the online config using the JSON hash scheme above. The finite plan hashes, full fixed50 bindings, run prefix and all budgets are therefore included.
- `not_before`/`expires_at` are explicit aware timestamps. Invocation must already be inside this window; there is no long wait for a future release. Its expiry also bounds job dispatch and pacing.
- `one_use_id` uses the same safe identifier syntax/length as `run_prefix`. A consumed/uncertain release cannot be replayed automatically.
- `source_rights_reference` identifies the separately reviewed collection/private-retention authority; `reviewers` must be `['Lead', 'Trader']`. These declarations do not authenticate the human, source facts or paid entitlements. Lead must independently release the exact files before actual use.
- `runtime_sha256` must equal the exact file-byte hashes returned by `ingest.private_forecast_pipeline.runtime_hashes()`. It binds this module/CLI and the existing collector/store/secure transport/core/refresh/exporter paths listed in `RUNTIME_PATHS`. Configuration presence is not proof that a live run happened.

Only the existing supervised worker opens credential material and uses the existing secure loader/transport. The parent validates private locator references without printing them; no credentials or provider bodies appear in operation summaries.

## Finite Execution and Receipts

The complete original plans are validated before dispatch. The wrapper uses their exact ordered jobs as single-job derived plans so pacing and stop-on-first-failure work without changing the collector. It records original plan/job hashes alongside each unique capture ID. At most one provider attempt per job, zero retries, unchanged100-bar unadjusted requests. Every actual supervisor dispatch is counted, including a later worker/storage failure.

Minimum start spacing is enforced against actual supervisor starts, with bounded waits and repeated monotonic/wall/deadline checks. Each plan gets at most300seconds and the operation at most600seconds, including pacing. Expired budgets or reversed clocks prevent later dispatch. Each worker keeps the existing20second/2second bounds and process-group cleanup. Failure, rate limit, empty/insufficient history, finality, cleanup, clock or integrity problems stop later requests. No retry-after resubmission or quota expansion occurs.

These limits bound waiting and worker dispatch/cleanup. Existing synchronous raw/SQLite I/O is not preemptible; arbitrary disk stalls can exceed a wall-clock budget. The wrapper checks budgets before further workers/preparation/export and does not claim a hard process kill of disk I/O.

A store-wide `.collector.lock` excludes concurrent use by this wrapper. Other clients do not honor that lock; exclusive provider windows remain an operator obligation, not distributed quota coordination. An exclusive claim under `receipt_parent` is retained after failures. Never delete a consumed claim simply to rerun an uncertain release.

An exclusive `receipt_parent/run_prefix/` operation directory contains `started.json`, `collection.json`, `captured-config.json`, and on successful preparation `candidate-review.json`/`completed.json`. Failed operations retain bounded failure/unattempted records and a safe50-identity missing ledger where possible. Raw capture data stays in the existing store. A claim or partially written operation may remain after a crash; it is not a successful generation.

Successful preparation uses the existing exporter to create a new immutable `forecasts.csv`, `private-audit.json` and `manifest.json` under the fixed50 output parent. The private candidate receipt is returned separately as `review_path`; the summary returns `csv_path`, `resume_config`, `receipt_path`, current cutoff/counts and `next_action`. The completed summary hash-binds the collection receipt, captured config, candidate review, CSV, private audit and generation manifest by exact file bytes. No old generation is overwritten. A same-second output collision fails. A failure after writing an individual artifact can leave an incomplete operation; missing `completed.json` must never be treated as success.

## Status and Acceptance

- Exit0, `ready`: at least35 current generated non-demo rows across the exact50 identities under matching reviews. This is a mechanical result; independent actual-source/currentness/rights acceptance remains required.
- Exit2, `insufficient_coverage`: valid current50-row export below35 eligible rows. `next_action` is `review_required` for missing exact admissions, otherwise `resolve_inputs`. Fixtures stay demo and never meet the actual35 gate.
- Exit1, `collection_failed`: a bounded online failure with actual attempts, unattempted jobs and sanitized failure receipt; no numerical export is presented as a successful result.
- Exit1, `failed`/`private-pipeline-unavailable`: fatal arguments/private setup/release/integrity/write problem. No raw provider body, credential, private input or old CSV fallback is returned.

`provider_refreshed: true` online means the explicitly **planned subset** completed capture, not that all50 names were refreshed or financially admitted. Check `planned_jobs`, `attempted_jobs`, `refreshed_codes`, counts and source timestamps. Offline always reports false. Currentness must be recomputed on every later invocation. A mocked or insufficient run does not complete PRSG-141-D4 or the PRSG-135 actual35 release gate. Full50, full100, strong-model validation and public-use rights remain separate.
