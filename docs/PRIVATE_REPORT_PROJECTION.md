# Private observed-quote report draft (PRSG-39)

This manual workflow overlays selected private snapshot observations onto an
explicitly accepted schema3 report template. It does not collect data, schedule a
run, publish a report, update Pages/index files, or generate forecasts.

## Inputs and boundaries

`project_report(store, template, universe, run_id=..., cutoff=..., expected_codes=...)`
deep-copies the template and requests the existing complete run-specific snapshot
selection. The explicit unique US code list must exactly match the supplied
five-name universe: 50 instruments across ten groups, currently US and MY. All rows
and accepted narrative remain present. MY quote collection is unsupported.

The template's aware `metadata.as_of` must equal the explicit cutoff, and its date
must match that cutoff's MYT date. It cannot relabel a later report as an earlier
information set. This checks the quote integration, **not arbitrary narrative
cutoff safety**: the caller must supply an accepted, nonprivate narrative/template.
The CLI validates the report/universe and its shared calendar before and after
projection. Projected rows must already have unknown direction, unavailable
forecast/confidence, and null numeric targets; unsupported forecasts are rejected.
Identity, group/classification, scenario, targets and chip direction are not inferred
from prices. No quote confidence, change, last close, turnover or RVOL is generated.

## Optional observed quote contract

Selected positive-price observations appear in optional `observed_quote`, separate
from listing-currency price fields. Legacy `current_price_value` remains null and
`quote_status` remains `missing` (the verified reference-price slot is missing).
The legacy display says `Unavailable`. A selected provider point may still be
visible in the independent observed-quote slot. Missing, conflicted, ineligible,
failed or unsupported points have `observed_quote: null` and explicit data gaps;
there is no previous-report/other-run fallback.

The strict observed point includes price, provider volume (zero preserved), source,
observation, ingestion, known and cutoff timestamps, origin, four explicit null
reference fields (currency/session/adjustment/prior close), bounded gaps and
allowlisted provenance. Source <= observation <= ingestion <= known <= cutoff is
required. All times use the store's lexical validator with at most six fractional
digits. Known time preserves the store's conservative millisecond fence. Provenance
retains only provider/connector, unverified authenticity, unconfirmed rights, run
identifier and attempt/raw/semantic hashes. Hashes are private evidence references,
not raw bodies, file paths or authenticated provider proof. Arbitrary dictionaries,
authentication headers and account fields are not copied from selection output.

The viewer labels structured points **Observed last — report cutoff**, shows source
age relative to the frozen cutoff, receipt/ingestion/known times, and says
**Quote currency/session unverified** and **Provider volume · unit/session
unverified**. Reference gaps remain visible. Synthetic origin is explicitly labeled
**Synthetic draft observation**. These values never enter nominal USD/MYR price
sorting. Legacy schema2/schema3 reports remain supported. No freshness, live data,
regular-session, stale-price or last-close policy is implied by elapsed age.

## Manual CLI

Use the existing project Python environment; no credentials or network are needed.
The store must already exist. Template/calendar/universe files are accepted inputs;
expected codes are a nonsecret JSON list such as `["US.SPY", ...]`, with the full
exact US universe, not a partial quote list.

```sh
python3 scripts/daily-market-brief/project_private_quotes.py \
  --root /absolute/private/store \
  --template /absolute/input/daily-market-brief/2026-10-02.json \
  --universe /absolute/input/watchlist-universe-five.json \
  --run-id approved-run \
  --cutoff 2026-10-02T08:00:00+08:00 \
  --expected-codes /absolute/input/expected-us-codes.json \
  --output /absolute/private-drafts/2026-10-02.json
```

Paths/run identifier are placeholders. The destination must be canonical, outside
the repository and conventional public roots, within an existing owned `0700`
directory. Symlinks, existing files and unsafe directories are rejected. A private
temporary file is flushed/fsynced, set `0400`, and atomically linked without clobber;
the directory is fsynced and the temporary name removed. A competing destination
wins without being overwritten. Filesystem failure after linking can leave a
complete destination despite a reported failure; inspect it privately, never
silently retry with overwrite. Permission/path checks are not a sandbox against
malicious same-user races and cannot discover custom web-serving configurations.
The operator must keep this directory private. Successful stdout reports only
`private_draft_written: true`; failures omit private paths and provider details.

Real data stays private in this ticket. Public redistribution/export requires a
separate accepted policy. The draft marker is not an export guard by itself; do not
copy private drafts into `artifacts/` or update `reports.json`. This workflow does
not establish live entitlement, real collection, operational daily delivery or
better forecast accuracy.

## Offline validation

```sh
python3 -m pytest -q tests/test_daily_report_projection.py tests/test_daily_report.py tests/test_private_market_selection.py
node tests/daily_report_viewer_checks.cjs
```

Reuse the existing isolated Python/DOM runtimes; no dependency installation is
performed. Synthetic tests cover cutoff/universe/symbol preservation, missing and
conflicted points, reference gaps, forecast rejection, provenance allowlisting,
input immutability, private no-clobber and races, strict optional validation, DOM
escaping, frozen age, zero volume, nominal sorting exclusion and legacy rendering.
