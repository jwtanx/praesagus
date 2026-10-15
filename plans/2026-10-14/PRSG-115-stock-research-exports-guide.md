# PRSG-115 — stock research exports guide

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Timestamped CSV/XLSX bundles, safe output paths, zero-argument defaults and reproducible dummy preview.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `d7e739a0bf17ba15759b0ff9b6f07ff0c28546ee` (initial implementation base0fc637f retained in manifest). Allowed paths:

- `scripts/stock-research/export.py`
- `scripts/stock-research/run.py`
- `scripts/stock-research/demo.py`
- `scripts/stock-research/README.md`
- `scripts/stock-research/examples/`
- `.gitignore`
- `tests/test_stock_research_exports.py`
- `plans/2026-10-14/PRSG-115-stock-research-exports-guide.md`
- `plans/2026-10-14/PRSG-115.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-115-D1: Master/horizons/top20/ranking/sector/ETF/speculative/evaluation exports reconcile with typed values and safe workbook formatting.
- [x] PRSG-115-D2: Zero-arg/demo/offline workflows, immutable timestamp collisions and Git exclusion proven; actual bundle verified separately.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Integration review — one immutable run bundle

Planning refinement from the delivered PRSG-111/112/113 interfaces; this section does not release additional implementation paths. Before PRSG-115 implementation, Lead will freeze the minimal supporting paths and checks with Engineer and AI Engineer.

`run.py` must finalize exactly one generation for collection, forecasts, evaluation and exports. It must not append to an already finalized manifest, mutate an earlier collection, or create separate sibling output generations for one user run. Training remains an explicit separate generation; a prediction bundle references the trusted existing model by version/hash rather than copying a mutable model pointer.

A compatible integration option is an externally supplied, still-open `Generation` for collection, with standalone collection retaining its current behavior. The run orchestrator owns finalization. Selection-only CSV writing must be deferrable so the final speculative forecast view can be written once without overwriting the collector's shorter selection view. Collection sidecars, calendar and canonical history remain unchanged. A versioned, allowlisted manifest component declaration can make a combined bundle discoverable both as collection state and as prediction history; existing single-purpose manifests remain valid. Review exact support scope before implementation; do not weaken artifact integrity checks or silently reinterpret arbitrary manifest kinds.

The exporter accepts typed instrument rows, long-form forecasts, evaluation results and coverage. It does not fit models, assign financial actions, fetch data, repair forecasts or fill missing metrics. Forecast keys include exact security binding, reference session, horizon/session window, original issue time and model/data version. Model and matched baseline values remain distinct. Windows already started are visible but excluded from fresh-entry ranking.

Master uses one row per unique admitted main instrument and separately named columns for each horizon's median low/high, outer quantiles, terminal return, reference/start/end dates and forecast status. Native bullish/bearish counts remain nullable with capability reason/timeframe/source; locally computed votes cannot populate native columns. Current quote/today range carry their own observation time, separate from the completed-session reference. All unavailable numeric fields are blank, with a status/reason column, never zero or the string `N/A` in numeric cells. Financial metrics keep their period and source limitations.

Summary and `top20.csv` show at most 20 genuinely eligible ranked rows, without force filling or inventing BUY/SELL. When no model qualifies, show the validation limitation prominently; WATCH/research-only rows may be shown only as a separately identified diagnostic view, not as validated candidates. Keep the canonical action text sortable; color is supplementary. Speculative rows remain disjoint from main and top20.

Workbook order: Summary, Master, Winners, Losers, Volume, sectors, ETFs, Speculative, Coverage; add Forecast review for per-forecast/cumulative evaluation if needed. Freeze identity columns/header, apply filters, readable widths and numeric formats, and green BUY/red SELL/amber WATCH/gray NO TRADE. Emit literal text safely (including provider names beginning with `=`, `+`, `-` or `@`) without turning valid negative numeric values into text. Stable sector filenames/sheet names must prevent path traversal and handle truncation/case collisions. Historical OHLCV exports retain the canonical training schema and are not widened with predicted prices.

Acceptance must reconcile every CSV/workbook view with its typed source, verify row/cap counts, blank-versus-zero behavior, numeric cell types, exact dates, action fills, filters/frozen panes, no formula injection, sector-name collisions and a representative visual preview. A collision or partial failure cannot overwrite a prior generation or produce a success manifest. Demo fixtures carry `is_demo=true` everywhere and fictional symbols only; they do not count as actual forecast or model-performance evidence.

## Lead display decision — validated candidates and visible research

Trader's six-case financial boundary review was independently reconciled on 2026-10-15. The numerical thresholds and promotion gates are unchanged. Missing required cost is NO TRADE, never cost zero; unvalidated model/baseline forecasts remain WATCH/research-only when inputs otherwise pass. Failed data/tradability takes precedence.

`top20.csv` and Summary's primary candidate table contain up to 20 validated BUY/SELL candidates that pass data/tradability, required metadata, cost, diversity and unstarted-window checks. Do not fill the table with unvalidated forecasts or force a BUY/SELL balance. A run without a qualifying promoted model reports zero validated candidates. Preserve all available numeric research forecasts in Master/Forecasts and a separately labeled WATCH/research diagnostic table in Summary, with model status, validation blocker and reasons. Diagnostic rows do not count toward the primary top20; do not imply missing forecasts or hide usable research merely because promotion is blocked. This is an output distinction, not a new financial policy or evidence of predictive accuracy.

## Accepted supporting architecture and artifact ownership

The Engineer's bounded integration review is accepted. Extend only the explicitly frozen paths: storage.py, collect.py, data.py (collection selector only), their universe/data regression files, and the existing export/run/demo/README/examples/gitignore/export-test paths. AGENTS.md may receive one factual standalone-tool capability paragraph only; do not change role, safety or delivery instructions. Engineer must not edit active AI-owned inference.py, predict.py, evaluation.py, ranking.py or inference tests. The AI owner adopts component discovery in a separately coordinated follow-up.

Preserve standalone run_collection -> Path and its finalization behavior. Add collect_into(open Generation) -> CollectionResult with the same handle, current selection/state/quotes, canonical rows and an attributable identity/calendar/metadata receipt built from written artifact hashes; do not invent a final manifest hash for an open generation. Validate parent/policy/as-of/artifact vacancy before provider calls. Optional selection-CSV deferral prevents overwriting speculative.csv. run.py owns exactly one collection call and one finalization. Training stays explicit/separate, and offline mode forbids provider/LLM calls.

Add an explicit manifests(component=collection|prediction|exports) selector while kind= stays an exact physical-kind filter. Recognize only allowlisted legacy kinds or stock-research-run with components_schema_version1 and validated known component declarations. Reject unsupported versions, missing required local artifact links, bad status/compatibility and path/hash/size/permission violations; capability pilots, demo records and incomplete folders cannot become actual collection/prediction history. Verify every referenced artifact, including unused XLSX. latest_state and data.read_generations use collection component; forecast-symbol retention and AI history readers use prediction component. Preserve canonical OHLC schema and root collection compatibility/as-of/calendar/adjustment receipt semantics; no dataset/feature/label-policy change.

Collection owns history.csv, history_revisions.csv, state.json, metadata_input.json, identity_bindings.json, calendar.json, universe.json and coverage.json. It may write selection universe.csv/speculative.csv only in its standalone mode. AI owns predictions.json and outcomes.json, with actual issue/as-of cutoff, typed stock ID, panel, exact windows, model/baseline axes and versioned trusted model lineage. Export owns master.csv, forecasts.csv, top20.csv, winners.csv, losers.csv, volume.csv, etfs.csv, rich speculative.csv, stable sector CSVs, per-forecast and cumulative evaluation CSVs, export_coverage.json and research.xlsx. The run orchestrator alone owns final manifest.json. No stage overwrites another stage's file or finalizes success in finally. Fatal failures leave an incomplete undiscoverable folder; expected unavailable results remain visibly partial.

Extend Generation.write with .xlsx bytes only, preserving O_EXCL0600/flat-path/size/hash/closed-state guards. Use the already approved Python openpyxl dependency for the user-runnable export script; no new package, runtime service or paid access. Keep machine-readable numeric CSV types/blank missingness separate from formula-safe literal text; stock IDs become literal strings in the workbook so long IDs retain precision. All forecasts and decisions are supplied by AI payloads, not recomputed or repaired by the exporter. Joins require exact code and typed security ID; current financial/quote/provenance fields remain current-only. Current UI bull/bear counts stay blank with capability reason when unsupported.

Provide a deterministic fictional demo/template with is_demo=true on all rows, authored illustrative prices and no implied model-performance evidence. README must cover install, private credential-locator references, initial history bootstrap/metadata gaps, explicit train/save, daily run, offline replay, SQLite/CSV inputs, interpreting prices/actions/uncertainty/evaluation, no-model/partial-data failures and optional sentiment auto/explicit off. A missing trusted model is a setup failure or explicit unavailable result, never silent training. Default enrichment auto attempts only a configured later extension and cannot alter price-only features. Until PRSG-116 exists, label sentiment unavailable/not configured; do not build a fake connection check or scrape subscription tokens.

Acceptance includes a real generated fictional CSV/XLSX bundle read back for all requested tabs, dates/numeric values, sort/filter/freeze/fills, literal-text injection safety, null-versus-zero, negative numerics, sector-name collisions, exact-ID mismatch rejection and no second collect/finalize. Verify a representative visual preview. Existing collector/storage/data/model/inference regressions remain mandatory; no passing fixture proves actual-source coverage or trained-model quality. The actual-data/strong-model gate remains separately open in PRSG-113/109.

## Summary visibility clarification

Available numerical forecasts with NO TRADE actions (for example missing required cost or identity evidence) remain visible in the secondary main-panel research diagnostics alongside WATCH rows, retaining their actual action and reasons. They never enter the primary validated top20 and are never relabeled WATCH to hide an input failure. Keep speculative rows in their separate panel. Display counts distinguish available numerical forecasts from validated candidates. ETF issuer/security proof remains required as in PRSG-111; stock share-class deduplication does not impose an additional ETF-manager concentration cap.

Implementation released at reviewed source-fix dependency 0fc637f80372610b44d45db9536b63e79d8086fb. Engineer owns the listed implementation/support paths; Lead owns ticket records. AI PRSG-114 files remain protected and their early versioned Python payload/API is the integration contract. No new provider or model code is released here.

## Component consumer integration — 16 October 2026 MYT

Lead reviewed the stable support API and independently replayed101 universe/data tests in2.86s. Within this mixed export ticket, AI Engineer exclusively owns bounded component-selector adoption in `evaluation.py`, `predict.py` and existing `tests/test_stock_research_inference.py`. Engineer retains all other accepted implementation paths; Lead retains records. Only replace saved-prediction discovery with explicit prediction component and cached-collection discovery with explicit collection component, retaining exact model-kind discovery, cutoff filtering, typed identity and verify-all integrity semantics. Regressions cover legacy/composite parity, excluded demo/incomplete/unrelated generations, unused-artifact corruption and offline CLI collection selection with mocked model boundary. No forecast/model/financial-policy change, live calls, fitting or silent fallback is authorized. This integration follows accepted114; overall115 acceptance remains pending.

## Integration progress — 16 October 2026 MYT

Lead independently replayed support universe/data regressions:101passed2.86s. The stable storage/collection/data interface was reviewed for explicit component discovery, exact legacy kinds, private immutable artifacts, strict artifact-key/path/hash/size validation and pre-provider shared-generation checks. AI Engineer completed the separately owned two selector replacements and compatibility regressions; Lead reviewed all three changed paths and independently replayed inference/model/data:122passed6.61s. The first owner test run failed one new exception-alias assertion after module reload; the import binding was corrected without weakening the expected corruption rejection, and the final owner replay passed122in6.93s. Existing model regression tests use fictional fits; new consumer tests mock the model boundary and make no provider calls. These are partial integration checks. Export/run/README/demo and final workbook/CSV/visual checks remain unaccepted; no actual-data or strong-model completion is claimed.

## Lead acceptance — 16 October 2026 MYT

Lead independently reviewed full scoped implementation;135universe/data/export tests passed10.36s;122inference/model/data passed6.61s. Fictional025753 workbook verified13tabs/20authoredforecasts/0validatedcandidates; alltabviews rendered and finalSummary visually reviewed. No actual-source/model-quality/nativeExcel acceptance.

The final output uses correct exchange windows and logarithmic terminal-return conversion, exact typed quote/security joins, blank unavailable numeric columns, literal long IDs/formula-looking text, explicit optional sentiment mode and one immutable shared generation. Nonempty fixture-model and missing-model runs exercise the real inference/export path with one collection and finalization; no silent training occurs. README covers private setup, explicit CSV/SQLite training, saved-model selection and offline replay. All13tab views and four-window price columns were visually reviewed, with a separate finalSummary rerender after its readable reasons/action legend update. Initial failed test-order evidence and the ignored-parent fixture correction remain in private receipts/history; final135passed10.36s. This closes export implementation/fictional workflow acceptance only. Actual-source bundles and ongoing real outcomes remain PRSG-109-D4; strong empirical model/hardware evidence remains PRSG-113-D2. No live calls, credentials, deployment or model promotion occurred.
