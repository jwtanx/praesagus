# Private observed-quote report draft (PRSG-39)

> Scope: this document describes the optional private-draft projection CLI only. It is not the normal dated report/dashboard workflow. Do not apply its `--public-output` procedure or restrictions to reports generated through `skills/daily-market-brief/SKILL.md` and the shared dated viewer.

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

## PRSG-61 direct REST snapshot workflow

The separate manual direct-REST collector is `scripts/market_collect.py`. At the
existing Trader report workflow, first invoke it with the explicitly configured
private store root, credential-directory locator, AppKeyID filename, approved
30-US-symbol plan, SPY/QQQ English news queries and a unique run ID. The
credential directory and Keychain passphrase setup are operator-managed. Reuse
the configured locators; do not search for, copy, or read secret contents to
discover them. If a locator was not supplied to this workflow, report that
locator as unavailable and preserve data gaps. The collector does not schedule
itself and this ticket does not change the 08:00 schedule.

After collection, run `scripts/daily-market-brief/publish_market_snapshot.py`
with the same private store and run ID. Only after collection has completed,
freeze one timezone-aware report cutoff at or after its completion/retrieval time.
Use that identical cutoff for private projection and the report's
`metadata.as_of`; never backdate it to the scheduled start or to before a
retrieval completed. Late or unavailable results remain explicit gaps.
Its `--private-output`
mode can supply a private analysis snapshot to Trader judgment. The Trader then
authors the existing SPY/QQQ report forecasts manually with a frozen reference,
horizon, linked evidence, visible qualitative confidence, bull/bear cases and
invalidation; unsupported views remain explicit abstentions. Forecast content
is separate from publishing vendor quote/news fields.

Its `--public-output` mode requires an explicit operator-provisioned rights
record outside the repository. That record must cover the US market, every
exported field and both public website display and redistribution, with a
current authoritative evidence URL and verifier/timestamps. The publisher fails
closed when the record is missing, expired or incomplete. No live permission is
asserted by implementation fixtures. Until the applicable field/market rights
are independently verified, do not publish live Moomoo quote/news snapshots to
Pages. The static viewer accepts only same-origin, validated dated artifacts;
forecast reports can still show Trader-authored evidence/abstention without a
public market snapshot.

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

## One-command pre-cutoff collection (PRSG-40)

`scripts/daily-market-brief/run_private_quote_report.py` joins the existing
collector, selection, projection, validator and private draft writer. It is an
explicit manual operation, not a schedule or publication bridge. It derives the
approved 30 US codes from the supplied five-name universe and makes one
snapshot-only collector invocation. Every 50-row draft retains the 20 unsupported
MY names and unknown/unrated forecasts. It adds no storage, credential discovery,
reference-data inference or broker watchlist mutation.

Prepare an accepted schema3 narrative/template whose information `as_of` equals
the intended future cutoff. Its sources must already be reviewed as compatible
with that information set; this command does not write or certify the narrative.
Choose a declared pre-cutoff window and invoke within it:

```sh
python3 scripts/daily-market-brief/run_private_quote_report.py \
  --root /absolute/private/store \
  --template /absolute/input/daily-market-brief/2026-10-04.json \
  --universe /absolute/input/watchlist-universe-five.json \
  --credential-directory /absolute/private/credentials \
  --app-key-name app-key-id \
  --run-id unique-approved-daily-run \
  --window-start 2026-10-04T07:55:00+08:00 \
  --cutoff 2026-10-04T08:00:00+08:00 \
  --output /absolute/private-drafts/2026-10-04.json
```

The example times and paths illustrate a future planned invocation; they are not
an active schedule or a claim the service can deliver at those times. Existing
store/private credentials must be configured through their separate approved
workflows. Running with real credentials makes real read-only network requests
inside the existing worker, subject to entitlement and transport failures.
The coordinator only passes the locator; it never reads credential values.

Preflight validates the private destination/collision, accepted report/calendar,
universe/taxonomy/forecast constraints, existing store, locator syntax and unused
run identifier before calling the collector. An identifier-only read of the
existing runs table also rejects an old run whose attempts are all post-cutoff;
it does not bypass quote validation or disclose private data. Supply a globally
unique run identifier per invocation and do not overlap invocations. Preflight is
not an atomic run reservation or distributed lock. A competing output creation
still cannot be overwritten because the final writer is atomic no-clobber.

Current wall time must be within `window_start <= now < cutoff`, checked initially
and again immediately before collection. Starting at/after cutoff, clock rollback
or inconsistent template time fails closed; no captures are backdated. Collection
can finish after cutoff: actual late ingestion remains in private history but is
excluded from the draft. The worker retains its 20-second deadline/2-second cleanup
and 300-second admission/accounting budget; filesystem latency is not a hard total
deadline. The command has no automatic retry, previous-run fallback or guaranteed
08:00 delivery. Never use new captures to fill a past report's earlier cutoff.

Stdout contains only the private-draft flag, coverage status, expected/selected/
unselected/conflicted US counts, unsupported MY count and available attempt status
counts. It never prints prices, provider bodies, credentials or private paths.
`us-coverage-complete` and exit0 require all 30 US points selected and a successful
collector outcome. This is **US selected-point coverage**, not verified units,
freshness, source authentication, MY coverage or complete useful report evidence.
Any failed/partial/all-missing/unattempted outcome, late ingestion or insufficient
selection produces an honest private draft with `degraded` and exit1 when storage
remains safely queryable. Missing coverage is not entitlement proof. Storage,
integrity, cleanup or clock-order failures stop without writing a draft, with a
sanitized error and no retry. Actual collector attempt evidence stays in storage.

Lead separately reported that a single SPY probe succeeded while the approved
30-code batch returned a transport failure/no valid response. That diagnostic
does not establish provider entitlement or individual symbol coverage. Engineering
regressions use injected synthetic collection only; no live retry or connector
scope expansion is performed here.

Focused offline check:

```sh
python3 -m pytest -q tests/test_daily_quote_report.py tests/test_market_collector.py tests/test_daily_report_projection.py tests/test_private_market_selection.py
```

The daily workflow's activation and any reviewed public projection remain
separate gates. Do not copy private drafts wholesale into `artifacts/`.
