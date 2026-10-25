# Manual Private Forecast CSV

Run this checked-in launcher with a **separately reviewed private batch** and an existing private output parent:

```sh
sh scripts/daily-market-brief/run_private_forecast.sh \
  --batch "/absolute/private/reviewed-batch.json" \
  --output-parent "/absolute/private/forecast-exports"
```

Run from the checkout, or use the launcher's absolute path from another directory. Paths containing spaces are supported. `--help` shows usage. The launcher uses this checkout's `praesagus.testPython` Git setting, or `python3` on PATH if unset; Python 3.11 or newer is required. A configured missing or unsupported interpreter fails visibly. Set the interpreter with one executable path, not a shell command:

```sh
git config --local praesagus.testPython "/absolute/path/to/environment/bin/python"
```

The launcher samples actual UTC time once and uses that same value for issuance and cutoff. It calls the existing private exporter's reader, calculator and writer. It never fetches data, trains, creates admission, changes inputs or rolls targets forward. Old inputs can produce withheld rows or fail; rerunning them does not establish fresh evidence. Fresh issuance is not a claim that a whole forecast window has yet to open.

The batch schema, reviewed evidence/admission requirements and numerical limitations are in [Private Forecast CSV](PRIVATE_FORECAST_CSV.md). Inputs must be owner-only 0600 or 0400 with no symlink components. The existing parent must be owned by the current user, mode 0700, outside Git checkouts and public paths. The exporter enforces these rules. Missing evidence/admission within a valid batch yields withheld rows; a missing file or malformed batch fails. Do not manufacture admission to obtain numbers.

On success the launcher prints one JSON summary, for example:

```json
{"status":"prepared","counts":{"total":2,"generated":1,"withheld":1,"is_demo":0},"csv_path":"/absolute/private/forecast-exports/YYYY-MM-DD_HHMMSS/forecasts.csv"}
```

These illustrative counts and the path placeholder are not an actual run. `csv_path` identifies the exact file returned by the writer, not a guessed timestamp. Keep this local output private. The original `prepare_private_forecast.py` CLI continues to omit private paths from its stdout.

Each new UTC generation contains `forecasts.csv`, `private-audit.json` and `manifest.json`. Creation time is sampled by the existing writer separately from issuance/cutoff. Existing generations are never replaced; a same-second collision fails without retry. All-withheld and empty valid batches still write bundles, return zero and report `status: withheld`; inspect counts and CSV reasons. Errors return nonzero with a sanitized failure reason. A generated row alone does not establish source authenticity or forecast quality. Authored fixtures retain their demo classification.

**Private research only.** These uncalibrated next-close ranges are not whole-window intraday extrema, measured 95% coverage or executable prices. Public rights and publication remain separate.

## Collection Is a Separate Operation

The launcher consumes reviewed inputs. It does not run the collector or turn a raw capture into source admission. The existing collector's separate command has this form:

```sh
"/absolute/path/to/approved/python" scripts/market_collect.py \
  --root "/absolute/private/market-store" \
  --plan "/absolute/private/released-collection-plan.json" \
  --credential-directory "/absolute/private/credential-directory" \
  --app-key-name "CONFIGURED_APP_KEY_FILENAME" \
  --run-id "NEW_RELEASED_RUN_ID" \
  --diagnostics \
  --diagnostic-receipt "/absolute/private/new-diagnostic-receipt.json"
```

The placeholders contain no credentials. This syntax example is not a collection release: use the separately approved plan, pacing/deadlines, finite request budget and source/financial review. Do not combine capture and export by assuming a successful response grants admission.

For the broader collection, saved-model inference, evaluation and CSV/XLSX program, see [stock research](../scripts/stock-research/README.md) and [run.py](../scripts/stock-research/run.py). Training is separate. Missing trusted models, source coverage or eligibility remain explicit limitations; this launcher does not establish that a 100-name universe is ready.

## Prepare a Current Fixed50 Batch From the Verified Store

Use this separate command after permitted history has been collected and current venue/source inputs have been reviewed:

```sh
"/absolute/path/to/approved/python" \
  "/absolute/path/to/praesagus/scripts/daily-market-brief/refresh_private_forecast.py" \
  --offline --config "/absolute/private/fixed50-config.json"
```

Python>=3.11 is required. The absolute script path works from another working directory, including paths with spaces. This command does **offline store preparation**: it performs no network calls, credential loading, collection, training, financial approval, public export or scheduling. Its JSON always says `mode: offline_store` and `provider_refreshed: false`. Existing store observations can remain current over a weekend if their reviewed venue schedule, latest completed reference, target and action coverage still apply. Otherwise collect through a separately released finite plan and renew the affected reviewed inputs before invoking again. There is no online mode in this adapter.

The fixed50 baseline requires no trained model. The standalone100 saved-model runner remains a separate workflow. This command cannot guarantee35 numbers when source eligibility or matching reviews are missing.

### Private Config Contract

Config JSON must be an owner0600/0400 regular file under an owner0700 private parent outside Git/public paths, with no symlink components. Reuse these permissions for review files. Store root, review directory and output parent must already exist and satisfy the existing private path checks. The store must pass `PrivateMarketStore` schema/raw integrity verification. Limits remain2MiB per JSON/CSV, depth12 for config, and50 unique ordered items. Unknown keys are rejected.

The top-level object has exactly these keys:

| Key | Value |
| --- | --- |
| `schema_version` | Integer `1` |
| `mode` | Literal `offline_store` |
| `store_root` | Absolute path to the existing private market store |
| `review_directory` | Absolute path to a private directory of exact admissions |
| `output_parent` | Absolute path to an existing private output parent |
| `items` | Exactly50 separately approved ordered identity entries; order is preserved |

Each item has exactly `ticker`, `market`, `currency`, `code`, `run_id`, `normalization_version`, `normalization_dialect`, `template`, `finality`:

- Identity is the reviewed fixed universe, unique by ticker/market, with US/USD or MY/MYR. `code` is exactly `US.<ticker>` or `BMS.<ticker>`. Config does not discover names or substitute missing names. Lead must independently check the actual fixed50 identities at release.
- `run_id` is an explicit finite existing capture selector, or `null` when no selector exists; it is never a mutable latest pointer. A null selector yields `history_unavailable` before any history query for that row. A run is queried once at actual issuance, capped at5000 rows. A query returning5000 is rejected to avoid silent truncation. Use bounded cohort run IDs; old/revised rows also consume the query cap. Missing/failed/empty captures supply no history, not a cached numerical fallback.
- `normalization_version` is the exact integer3/4/5/6 expected in the store, and `normalization_dialect` is its exact string or `null`. When the template or capture selector is missing, normalization version may also be `null`; no source semantics need be invented for withholding. Retain reviewed MY hours-hypothesis limitations. Changing a dialect does not approve its semantics.
- `template` is `null` for unavailable evidence, yielding `template_missing`, or the exact schema3 scenario evidence object **without `bars`**. Non-null templates retain all validation requirements. It contains `schema_version: 3`, `classification`, `instrument`, `source`, `calendar`, `corporate_actions`, `rights`, `method`, `narrative`, with the existing closed keysets defined in `ingest/forecast_scenario.py`. Instrument identity must match the entry. Source provider must be `moomoo-rest`, basis `unadjusted`; method must equal `GENERIC_METHOD` or `GENERIC_CASH_METHOD` exactly. Reuse independently reviewed identity/units, source-field/finality convention, current corporate-action coverage/events, private rights and issuer-specific bull/bear/invalidation. The adapter supplies no accepted decisions. A synthetic store observation forces `authored_fixture` even if the template says `reviewed_real`.
- `calendar` inside the template is the separately reviewed complete venue schedule: original source/version/MIC/timezone/known time, bounded coverage containing issuance, all completed sessions needed for the21-close window, and at least one future target close. Sessions must be unique, ordered and in the declared venue local date. No weekdays or new calendars are inferred. An exhausted, incomplete or out-of-range schedule withholds the row. Exceptional venue changes remain a reviewer responsibility.
- `finality` may be `null` when `template` is null; otherwise it maps ISO session dates to their explicitly reviewed aware settlement/revision-cutoff timestamps. Every required session needs an entry at/after that regular close and at/before the **original retrieval**. A later invocation never turns an early retrieval into settled evidence. There is no default cutoff, waiting-based retimestamp or settlement inference.

The mapper selects exactly the latest21 completed scheduled sessions and the next scheduled close at issuance. Each bar binds original raw hash, source URL, observed retrieval and ingestion; known time preserves the original stored `known_ms` exactly as UTC milliseconds, including its rounding boundary, after checking retrieval<=ingestion<=knowledge<=issuance. It is never shifted earlier to ingestion or replaced by invocation time. Provider publication time is explicitly `null` because the stored history endpoint does not establish it. Full original observation metadata, source milliseconds, normalization quality, revisions and semantic hashes are retained in the private review receipt. Identical replay observations use a deterministic earliest original binding; conflicting semantic versions within the selected run withhold rather than guessing a revision. Never fill missing20/19-bar windows.

Unsupported names stay in their exact ordered slots with `template: null` and, when no capture exists, `run_id: null`. These rows need no fabricated calendar, action, rights, source or fixture facts. For example, this is a single unavailable item within the required50-entry config (not a complete runnable config):

```json
{"ticker":"0166","market":"MY","currency":"MYR","code":"BMS.0166","run_id":null,"normalization_version":null,"normalization_dialect":null,"template":null,"finality":null}
```

Such a row produces blank numeric cells, null candidate hash/reference/target, and `template_missing`/`history_unavailable` in the review ledger and CSV reasons. Only non-null selectors for non-null templates are queried; an unused selector is never queried just to withhold a missing template. Missing template/selector is a per-row state; malformed non-null values still fail config validation. Exact50 identity/code/currency/order validation remains mandatory.

### Exact Review Handoff

Run without admissions first to obtain candidate evidence and hashes in `refresh-review.json`. This may yield50 withheld rows and exit2. Each complete candidate is the exact evidence reviewers must inspect, alongside original observation bindings; hashes do not authenticate the source. The receipt deduplicates original observation metadata by `observation_sha256`, referenced from each candidate's `store_bindings`.

An independently prepared admission is read only from:

```text
<review_directory>/<candidate-evidence-sha256>.json
```

It must satisfy the existing schema3 private-purpose contract: exact evidence/method hashes, classification, reviewed time no earlier than input knowledge and no later than issuance, reviewers `Lead`/`Trader`, and all seven accepted evidence-bound decisions. The command never creates or renews these approvals. Missing or mismatched admissions yield `review_required` and blank numeric cells; denied rights, unsupported action terms or other underlying core gates still withhold even with a matching hash. A malformed/insecure review file is a fatal private-input error. New bars or changed calendar/action/rights/template inputs normally change the candidate hash and need a new matching review. Keep old reviews and forecast editions immutable.

### Output and Exit Dispositions

A new immutable UTC generation contains the existing `forecasts.csv`, `private-audit.json`, `manifest.json`, plus owner0600 `refresh-review.json`. The added receipt contains candidate evidence, original store bindings/observations, config digest, row reasons/reference/target dates and disposition. It is private research material; do not publish it. The existing manifest hashes the CSV and private audit; the added review receipt is a separate artifact. Ordinary receipt-write errors roll back this new generation; a process crash can leave an incomplete folder. A same-second collision fails and preserves existing bytes.

The JSON summary returns exact `csv_path`, `review_path`, actual UTC `cutoff`, per-identity reference/target sessions, mode and counts:

- Exit0, `ready`: exactly50 identities with at least35 currently generated **non-demo** rows under the supplied exact reviews. This is a mechanical eligibility count, still subject to independent Lead actual-source release acceptance under PRSG135.
- Exit2, `insufficient_coverage`: a valid50-row bundle with fewer than35 eligible generated rows. Inspect `generated`, `withheld`, `is_demo`, `eligible_generated`, `review_required`, CSV reasons and the private review receipt. Generated fixture rows remain demo and never count toward35. Insufficient output does not constitute release success.
- Exit1, `failed`: setup, integrity, malformed/private input, bounds or output failure, with sanitized `private-refresh-unavailable`. No raw provider body, credentials or private evidence appears in the error. No old edition is returned as a fallback.

The CSV keeps core failure reasons plus preparation reasons such as `history_missing_or_stale`, `history_conflict`, `history_basis_or_time_unavailable`, `finality_unavailable`, `calendar_or_input_unavailable`, `template_missing`, `history_unavailable` and `review_required`. A bad venue/history input can withhold its intended identity while other supported rows proceed; global config/store-integrity failures abort. Existing issued forecasts and outcome ledgers are never rewritten or rescored by this command. Public rights, full50 coverage, full100 coverage and predictive validation remain independent gates.
