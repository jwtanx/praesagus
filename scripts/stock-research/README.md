# Local stock research

This on-demand tool creates a private timestamped bundle of canonical history, research forecasts, evaluation results, CSV views and a formatted workbook. Training is explicit and separate. A numerical forecast is not evidence of accuracy or trade execution; unpromoted models remain research-only.

## Installation and fictional preview

Use Python 3.11 or later in a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r scripts/stock-research/requirements.txt
python scripts/stock-research/demo.py
```

The demo needs no credentials, provider, saved model or fitting. It uses authored fictional symbols and prices at an explicit October 2026 reference; every exported row and the manifest carry `is_demo=true`. It shows zero validated candidates and separate WATCH/NO TRADE numerical research. It is a layout/template example, not fresh market data or model-performance evidence. The old template and every later generation are preserved.

Default output is `~/Documents/stock-research-data/YYYY-MM-DD_HHMMSS/`. `demo.py --output-dir /absolute/private/parent` selects another parent. A timestamp collision fails without overwriting. Store actual data outside Git. The optional repository-root `stock-research-data/` parent is entirely ignored; any other in-repository parent must also be entirely Git-ignored and outside code directories. Generated workbooks, data and models never belong in examples or commits.

## Private setup and initial history

Copy `config.example.toml` to your private configuration location. The provider request/page/row settings are local budgets, not verified entitlements or provider quotas. No paid-access or trading changes are made.

Online collection requires an existing private credential locator: an absolute JSON file outside the repository with owner-only `0600` permissions. It contains the existing loader's `directory` and `app_key_name` references, not credential contents. Set `collection.credential_locator_file` in private config or `PRSG_MOOMOO_CREDENTIAL_LOCATOR` to that locator's path. Keep keys, passphrases, tokens, account data and private locator contents out of this repository and terminal output. The reviewed secure loader handles credentials only when an explicitly invoked online collection executes.

```sh
python scripts/stock-research/collect.py --config /absolute/private/config.toml
python scripts/stock-research/collect.py --offline --state-dir /absolute/private/data
```

The first online collection discovers names from market screens; portfolios, report names and the ETF registry do not seed discovery. Bounded runs backfill and revise canonical history incrementally. Missing entitlements, exhausted budgets, first upstream failures and missing symbols remain coverage issues. Offline mode loads compatible hash-verified state without credentials or provider/LLM calls; a missing cache produces honest empty coverage.

Actual eligibility needs reviewed listing/security, sector crosswalk, issuer/ETF, currency-by-endpoint-field and comparable adjustment evidence. A US prefix alone does not establish USD; a website/name does not establish issuer or sector identity. Provider classifications are current observations, not historical membership. Currency, timezone units, provider finality and adjustment vintages must retain their limitations. Do not fabricate metadata to fill selection quotas. Canonical `history.csv` remains the training schema; predicted prices never enter historical OHLC columns.

## Optional Independent ETF Directory Cohort

An optional **reviewed local pair** of official NasdaqTrader symbol directories can enumerate a separate `etf_directory` cohort. This does not download files, add a provider filter or seed discovery from the 49-name classification registry. Without this option, the existing three stock pools, speculative rules and compatibility hash are unchanged.

```toml
[collection]
etf_directory_manifest = "/absolute/private/directory-pair.json"
etf_directory_candidates_per_run = 40
```

Use this in the existing private collection config alongside its provider settings, then invoke the existing `collect.py --config /absolute/private/config.toml` command. Directory input alone does not authorize an online run or supply credentials. `--offline` performs no provider/credential work, still validates the local pair at its cutoff, and does not advance the enrichment cursor.

The manifest and both source files must be regular owner-only0600/0400 files under owner0700 parents outside Git/public paths, without symlink components. The exact schema is documented in [API_CONTRACTS.md](API_CONTRACTS.md#local-official-directory-pair-contract). Both official files must be complete, nonempty, hash/byte-bound, with the expected headers and creation footer. Actual retrieval must be no more than24hours old at cutoff, inclusive; retrieval and known times cannot be future or reversed. Preserve the footer verbatim with unknown timezone. A later import or review never makes an old capture fresh. Reviewer/source declarations and hashes do not independently authenticate a source or grant use rights.

All ETF=Y/TestIssue=N rows are enumerated first. Simple, unambiguous symbols map exactly to `US.<same-symbol>`; punctuation/namespace differences need explicit reviewed aliases, and duplicate/conflicting listings stay UNKNOWN. No root matching or first-match choice is used. Each candidate retains its source URL/hash, file/row, original retrieval/known times and alias review. Membership first-seen records the collection observation, not historical membership inferred from a footer.

Enrichment visits a deterministic lexicographic slice, default40 and maximum400, independent of the stock `max_candidates`. This is a work queue, **not selection of the first20 or an activity ranking**. Original stock/retained-forecast work runs first; the directory slice uses only the remaining shared provider request/row/timeout budgets. There is no extra quota. Partial or interrupted work stays pending for a later explicit run; source absence is retained visibly. The checkpoint binds the complete pair, manifest/aliases and slice option. Changed bindings create a new compatibility generation rather than reusing stale membership; old outputs remain immutable. An unchanged complete walk may be refreshed in later bounded runs.

Coverage/state retain the complete enumeration, rejected aliases, checkpoint, pending/unvisited/completed counts and separate origin. Directory-only nonfund/unverified candidates cannot enter company or speculative stock selection; genuine overlaps retain both origins without duplicate enrichment. Current cached field observations retain their actual timestamps within the compatible pair; a stale pair fails even offline. Shortfalls and partially explored cohorts remain explicit.

An ETF flag is not fund admission. Existing typed identity, listing/status, comparable USD fields,252-session/latest20 coverage, median20 turnover>=25M, price>=5, issuer mandate/leverage/reset, exposure-family cap and12/2/2/2/1/1 quotas remain unchanged. The registry classifies only discovered names; an unregistered fund remains unverified. Current-only enumeration does not establish historical membership, a ready100-name universe, source rights or model quality. All acceptance evidence for this optional importer is offline and fictional until a separate reviewed live-source release.

## Explicit training and saved models

```sh
python scripts/stock-research/train.py
python scripts/stock-research/train.py --state-dir /absolute/private/data --model-dir /absolute/private/models
python scripts/stock-research/train.py --csv-dir /absolute/private/csvs --receipt /absolute/private/receipt.json --model-dir /absolute/private/models
python scripts/stock-research/train.py --sqlite /absolute/private/source.sqlite --table ohlcv --receipt /absolute/private/receipt.json --model-dir /absolute/private/models
```

Training defaults to configured collection generations. Standalone CSV/SQLite inputs require their attributable identity/calendar/availability receipt; SQLite opens read-only. Use explicit date/fold options described by `train.py --help` when overriding chronological defaults. The tool freezes inputs, uses chronological splits and saves a new timestamped model generation with hashes, runtime contract, forecasts and evaluation. It does not overwrite a current-model pointer. Training can reject insufficient/purged data; a present-day backfill cannot invent historical availability.

Strict availability is the default. A research-retrospective policy requires explicit declarations of membership, delisting, adjustment-vintage and first-availability gaps. It does not promote a model or make later information available at an earlier forecast. Missing historical identity/mandate evidence, costs, coverage and validation remain real blockers.

## Everyday run and offline replay

```sh
python scripts/stock-research/run.py
python scripts/stock-research/run.py --config /absolute/private/config.toml
python scripts/stock-research/run.py --offline --state-dir /absolute/private/data
python scripts/stock-research/run.py --offline --state-dir /absolute/private/data --model-dir /absolute/private/models --model-folder /absolute/private/models/YYYY-MM-DD_HHMMSS
python scripts/stock-research/predict.py --offline --state-dir /absolute/private/data --model-dir /absolute/private/models
```

All entrypoints have defaults; first use still requires the setup/data prerequisites. `run.py` performs one collection, saved-model inference and evaluation, then exports into one open generation and finalizes one manifest. It never trains, recalibrates, promotes or collects again through the prediction CLI. `predict.py` remains independently usable. A missing trusted model yields explicit unavailable forecasts and blank numeric cells, not silent training or a fabricated baseline. An invalid trusted artifact/setup fails visibly, leaving an incomplete folder that state discovery ignores. Old generations and original predictions remain immutable.

Use `--costs /absolute/private/costs.json` for explicit per-code nonnegative roundtrip fee/spread/slippage fractions. Unknown cost is not zero: available numerical forecasts remain visible with their actual NO TRADE reason, outside validated candidates. `--dated-metadata` and `--basis-evidence` accept explicit attributable evidence inputs; they do not waive identity or training policy. Current quotes/financials require exact typed security binding; absent quote IDs leave those fields blank with a reason. Integer and string security IDs are never silently equated. Model versions/hashes reference existing trusted artifacts rather than mutable model pointers.

Default `--sentiment auto` is explicitly unavailable/not configured until the later sentiment extension exists. `--sentiment off` records off. Neither mode performs a fake connection check, reads subscription tokens, invokes an LLM or changes numerical features. `--offline` prohibits all provider and LLM calls.

## Reading the bundle

- `master.csv`: one main instrument per row, front-loaded identity/action/reference/current range and four median low/high windows, followed by uncertainty/status/provenance. `forecasts.csv` preserves immutable per-window model and matched-baseline results separately.
- `top20.csv` and Summary's primary table contain at most 20 genuinely validated BUY/SELL candidates. They may be empty. Numerical WATCH and NO TRADE research remains visible in Summary's separate diagnostic table and Master; it is never relabeled or counted as validated. Speculative names are disjoint and use `speculative.csv`/their own tab.
- Winners, Losers and Volume retain supplied pool order. ETF and stable hashed sector views are separate. Issuer/security/exposure constraints come from the accepted selection/ranking stages; exports do not invent new actions, scores, mappings or an ETF-manager cap.
- `research.xlsx`: Summary, Master, Winners, Losers, Volume, sector tabs, ETFs, Speculative, Coverage, Forecast review, Cumulative review and Forecasts. Headers have filters and frozen identity columns; BUY is green, SELL red, WATCH amber, NO TRADE gray. IDs are literal strings to preserve long-ID precision; negative metrics remain numeric. Missing numbers are blank with status/reasons; zero remains zero. Formula-looking source text stays literal. CSV text with formula prefixes or leading apostrophe gets one leading apostrophe; remove exactly one when decoding such text. Numeric negatives are never escaped.
- All four horizons use the same completed reference per instrument. Today/current ranges have separate observation times. Median whole-window extrema, outer quantiles and terminal return differ; a forecast interval need not contain the reference. Windows already started remain visible but cannot enter fresh-entry ranking.
- `predictions.json` preserves original forecast IDs, issue/as-of/reference/window times, typed security IDs and model/data versions. `outcomes.json`, `evaluation.csv` and `evaluation_cumulative.csv` preserve per-forecast outcome revisions and horizon/class/leverage diagnostics. Only fully ended windows with compatible actual OHLC visible at review time score; pending/missing/incompatible actuals stay unscored. Exited names remain tracked for actuals. Model accuracy, realized P&L and profitability are distinct questions.
- Collection owns canonical history/state/calendar/identity/metadata/universe/coverage sidecars. Shared runs defer selection-only CSVs so the richer final speculative view is written once. `export_coverage.json` reports export/model/input limitations separately. Manifest components explicitly distinguish collection, prediction and exports; legacy single-purpose generations remain compatible, while pilots/demo/incomplete generations cannot seed actual state/history.

No actual-source bundle, trained-model promotion, full-universe coverage or native Excel application behavior is established by the fictional preview or fixture tests. Review the manifest and coverage before interpreting any output.

Screening excludes a well-typed nonpositive price per instrument, with code, original response rank, reason, typed-value hash and source/knowledge times in collection state and coverage. The field validator still raises; malformed fields elsewhere in that row remain fatal. Every received row counts against paging/row budgets, including exclusions. A source traversal may finish with zero accepted rows; this differs from an empty source or a page-budget shortfall and does not establish eligibility. Refill uses only the existing bounded cursor traversal.

The provider accepts the unchanged US-only query or explicit `screen_queries_for_price_floor(1|5)` presets. These use the [official REST range shape](https://open.moomoo.com/zh-cn/api/quote/screening/stock-screen) and [documented 2201 scaling](https://open.moomoo.com/mcp-docs/available-tools): inclusive raw bounds 1000/5000. They filter reported-price units, not proven USD denomination. Collection defaults stay US-only; a separate main-only intake may request floor 5, while speculative discovery must retain its independent floor-1 rules. No turnover average substitutes for the required completed-history median, and no listing/status/issuer/currency gate is waived. Actual server filter behavior still needs a separately approved bounded live check.
