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
