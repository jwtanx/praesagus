# PRSG-127 — Private Forecast CSV Export

Type: feature · Modules: financial-data · Owner: Engineer · Priority: P1 · Effort: S (0.5–1.5 person-days) · Impact: high — provide the requested local numeric CSV through the reviewed private-purpose calculation API.

## Why the ticket is created?

The private-only numerical API in PRSG-126 is ready for Lead integration. The user still has no numeric CSV. This supporting CLI turns separately admitted private research inputs into an immutable local bundle; it does not resolve actual source-use permission or publish a report.

## Approach

Add one small CLI using build_private_forecast_scenario and reuse existing secure private JSON/path/directory readers from prepare_forecast_report. Accept either --evidence plus --admission or --batch, mutually exclusive before reads. Batch exact schema1/items, at most50 unique exact ticker/market/currency/evidence/admission entries and2MiB/depth12 bound; reject unknown/duplicate/cross-bound identities before writes. Legacy schema1/2 SPY and generic schema3 identities must bind exactly. Missing pair members yield explicit withheld rows, never invented numbers.

Require explicit --issued-at, --cutoff and --output-parent; parent is existing owner-only0700 outside Git/public paths. Generate one new YYYY-MM-DD_HHMMSS UTC folder, fail on collision, no overwrites. Save forecasts.csv, private-audit.json and manifest.json with owner-only files, original input/result hashes, timestamp, purpose and model/source status. Preserve safe rollback on write error; do not claim crash-atomic multi-file commits. No raw payload copied or credentials read.

## Choices

CSV columns include identity, status/reasons/classification/is_demo, currency, reference/target/issuance dates and prices, point/low/high, direction, uncalibrated method/observations, evidence/admission hashes and private-only purpose. State prominently that the next-close model range is not whole-window intraday extrema or measured95percent coverage. Preserve raw precision in private audit and numeric display values in CSV; prevent spreadsheet-formula injection in text fields. Include a short guide with exact singleton/batch commands and unavailable-data behavior.

## Findings

Existing public preparation helpers already enforce private no-symlink/path/permissions/finiteJSON constraints. Private outputs intentionally cannot enter public row mapping. Export must consume the private API directly, preserve unknown public rights and never copy a public result or fabricate admission.

## Tradeoffs

A bounded local CSV proves export mechanics without adding providers, models, LLM or publication. It is one part of the daily report; standalone100-name trained whole-window forecasts remain unfulfilled. Fixtures are fictional and cannot establish actual-use rights or numerical quality.

## Frozen scope

Base 6f289ce7a730f43de05852b80cfb92dfd4b8306c. Dependency PRSG-126 reviewed pure API (in primary, integration active). Engineer writes only the new script, new test and guide listed in manifest. Lead owns records. Protect126core/tests,125ingestion, existing public scripts/report/ledger/artifacts/dependencies/provider clients and unrelated.DSStore. No actualsource calls/admission creation/real export release in this implementation ticket.

## When it's considered done

- [x] PRSG-127-D1: Singleton/batch private API exports immutable bounded private CSV/audit/manifest with correct numbers, hashes and withheld states; malformed/bypass/path/collision/rollback regressions pass.
- [x] PRSG-127-D2: Lead independently reviews and delivers the script/tests/guide through mandatory hooks. Actual private CSV delivery remains a separately verified source-admission obligation.

## Lead acceptance — 18 October

Independent exact three-file review and combined export/core/public-overlay run: 388 passed in 2.91s. Engineer focused50 passed0.53s and final export/core275 passed1.13s. Initial43passed/7failed retained: output-parent Git marker hole fixed; invalid provider formula fixtures corrected to accepted private rights text without relaxing core. Script SHA256 5e369ed719c74a7fea35a5991cb2b3350837a103678d79643b98a4457a908a14; tests16f2eedd67f82d63ec77986e2f6fc6201fb36b1392c2646583ce51ab39df7e6d; guide637810fc691064ebc3923146c1d394e6e15eab3f46daec5a7b5c20332686f534. Private-only UTC bundles, source/input hashes, formula escaping, no-overwrite and ordinary rollback reviewed; not crash-atomic. Actual source permission and numeric CSV remain pending, not satisfied by fixtures. Required delivery hooks apply.
