# Forecast outcome and quality scorecard

`scripts/stock-research/quality_scorecard.py` reviews existing forecasts offline. It
does not collect data, load an estimator, fit, predict, trade, schedule work or
promote a model. Output is private, descriptive evidence. A successful execution
does not mean forecasts are accurate or qualified.

## Run

Use the repository's configured Python 3.11 environment and absolute paths:

```sh
python3.11 -I -B /absolute/checkout/scripts/stock-research/quality_scorecard.py \
  --bundle /private/research/scorecard-inputs.json \
  --bundle-sha256 EXACT_SHA256 \
  --output-parent /private/research/scorecards
```

The output parent must already exist with mode `0700`, outside the repository.
Input files require mode `0600` and immediate parents `0700`, current-user
ownership, regular files and no symlinks. Each explicitly supplied reference has
exactly `path`, `sha256`, and `bytes`. There is no input-directory discovery or
recursive following of paths found inside historical JSON.

The command creates `scorecard-<bundle hash prefix>/` exclusively, containing:

- `scorecard.html`: readable summaries, original rows and financial limitations;
- `scorecard.json`: rows, market/horizon/instrument groups and metric provenance;
- `scorecard.csv`: flat rows with reasons and unavailable numerical cells blank;
- `provenance.json`: exact input references and implementation/evaluator hashes.

The HTML starts with readable status cards, scored/mature-generated denominators,
scope warnings and the descriptive paired comparison. The table shows original
predictions beside actuals and exact missing/failed reasons. Local labelled search,
status, horizon and target-semantics filters use only static escaped DOM content;
there are no remote assets or requests. CSV/JSON/provenance downloads sit above the
cohorts. Raw summaries and financial detail are secondary disclosures. Withheld
identities remain in the table but do not increase valid target sample counts.

Existing output is never overwritten. Reproduce in a different clean output
parent. The same bound inputs and code produce identical artifact bytes. No
current wall-clock timestamp is inserted into report bytes. Workflow time is used
only to reject a future review cutoff or future workflow approval. Original input
bytes are rechecked before writing outputs. A late write failure can leave a
partial, unapproved output directory; preserve it and use another output parent.

## Explicit contract

The outer bundle has exactly:

```json
{
  "schema_version": 1,
  "kind": "quality-scorecard-inputs",
  "analysis": {"path": "/private/research/analysis.json", "sha256": "...", "bytes": 123},
  "financial_review": {"path": "/private/research/financial.json", "sha256": "...", "bytes": 456}
}
```

Analysis requires `schema_version: 1`, an aware `review_at`,
`qualification_policy: null`, and a nonempty `cohorts` list. Recognized descriptive
metadata is `status`, `qualification_disposition`, and `interface_notes`; it grants
no authority. Unknown fields are rejected. A changed cohort, baseline or cutoff
requires a new immutable analysis and financial binding; retain earlier editions.

The financial review has exactly `schema_version`,
`kind: "quality-scorecard-financial-review"`, `analysis_sha256`, `reviewer: "Trader"`,
`reviewed_at`, `decision: "accepted"`, `cohorts`, and `limitations`. Each reviewed
cohort specifies `cohort_id`, `forecasts_sha256`, `target_semantics`,
`accepted_outcome_review_sha256`, and `limitations`. The exact analysis/cohort and
actual-review hash sets must match. This is a supplied reviewed contract, not
cryptographic authentication of a reviewer or provider. A standalone approval
boolean cannot bypass source, issue, target, currency or hash checks.

The later financial workflow review can occur after the frozen outcome cutoff;
it does not make later observations available earlier. Retained outcome-review,
settlement and actual-availability timestamps must meet the outcome cutoff.

Bounds: 16 cohorts, 10,000 combined forecast rows, 256 distinct files, 32 MiB per
file, 10 MiB per decoded JSON, 128 MiB aggregate input and 32 MiB aggregate output.
Calendar spans are limited to 3,660 days before library allocation.
Inputs are explicit private CSV/JSON only. Runtime helper imports are fixed
repository evaluators, never executable paths or serialized estimators from data.

## Terminal-close adapter

A `terminal_close_csv` cohort contains exactly `cohort_id`, `kind`, `forecasts`,
`original_batch`, `outcome_reviews`, `outcome_acceptance`, and `baseline`. It reads
the existing private export's original 34-column schema, not a newly generated
forecast. Every original row remains visible, including withheld rows and
generated rows lacking accepted actuals. Leading-zero identities remain strings.

An eligible actual must bind the original CSV and canonical row, evidence,
admission and result hashes; exact security, nominal currency, unadjusted close
field, session and retained source observation; target-close/settlement/availability
ordering; and the retained financial comparability checks and acceptance. This
does not independently reauthenticate a provider response. Missing reviews yield
`missing_actual`; inconsistent or rejected reviews yield an invalid affected row.

Direction and inclusive terminal-range hits use
`harness.forecast_review.evaluate_row`. The wrapper adds original terminal point
absolute error, error/reference fraction and range width. These display metrics
use original CSV display precision. Probability/Brier is unavailable when the
original export did not supply a probability. No probability is inferred from
interval width.

Terminal closing intervals are **not** intraday-low/high endpoint forecasts or
whole-window containment. Those metric cells remain unavailable. Financial scope
also identifies intraday-issued closing forecasts; they must not be described as
pre-open full-session forecasts merely because the method has one-session lead.

### Original origin-time baseline

`baseline: null` means no baseline was supplied to this contract, not that none
exists anywhere. Never reconstruct one after observing outcomes.

The original export audit can supply an existing baseline through:

```json
{
  "kind": "original_audit",
  "audit": {"path": "/private/research/private-audit.json", "sha256": "...", "bytes": 123},
  "manifest": {"path": "/private/research/manifest.json", "sha256": "...", "bytes": 456},
  "precision": "original_unrounded_both"
}
```

The original manifest must bind CSV and audit bytes. Each audit result must match
the original row's identity, evidence/admission/result hashes, method, reference,
target, issue time and original display estimates. Both paired model point/low/high
and baseline point/low/high come from the original **unrounded** saved estimates.
The code extracts those numbers; it does not generate a new baseline forecast.
CSV display-rounded diagnostics remain separately labelled. A bad per-row baseline
binding makes its comparison unavailable while preserving an otherwise valid
descriptive actual score. Tampered files or manifest bindings block the run.

An alternative existing baseline CSV uses `forecasts` and `origin_review` refs.
The receipt must bind its hash with `kind: "origin-frozen-baseline"` and actual
`known_at` no later than the original forecast issue. Identity, reference, target,
method and horizon must match. This path supplies point-error comparison only;
it does not imply unrounded audit precision or a newly authenticated source.

## Saved OHLC adapter

A `saved_ohlc` cohort contains exactly `cohort_id`, `kind`, `forecasts`, `actuals`,
`calendar`, and `baseline: "embedded-original-only"`. Calendar has exactly `name`,
`start`, `end`, and `version` and must match the existing calendar implementation.

Reuse `evaluation.review_forecasts` and its existing forecast-ID, calendar,
identity, price conversion, adjustment-vintage and availability checks. Complete
reviewed OHLC windows can produce separate low/high/terminal errors, quantile
pinball, endpoint coverage/width and joint envelope containment. Embedded model
and baseline quantiles remain the original issued values. Evaluation imports
numerical code but never deserializes an estimator or calls fit/predict.

`actuals: null` keeps future full windows pending. After maturity it exposes a
missing-actual reason; time passing is not a successful outcome. No terminal
closing price is substituted for a window's extrema.

Explicit actuals, when available, have four refs: `history_csv`, `receipt`,
`basis_evidence`, and `review`. The financial contract must accept that review
hash. Its exact fields are `kind: "reviewed-ohlc-actuals"`, `decision: "accepted"`,
`known_at`, `forecasts_sha256`, `inputs_sha256` for the three data refs, `calendar`,
and `targets: ["low_return", "high_return", "terminal_logreturn"]`. The existing
canonical reader/evaluator still checks the actual rows; the review is no bypass.

## Interpretation and checks

Scoring states distinguish scored, pending, missing actual, withheld, unscored and
invalid inputs. Quality states are separate: pending, insufficient or failed.
With this version's frozen null policy, no row can become qualified for review.
A missed direction/range is a visible measured outcome, not automatic invalidity
or an invented promotion threshold. Existing PRSG-113 promotion gates are unchanged.

Report issuance count, distinct instrument-targets and distinct origin dates.
Repeated editions are flagged as correlated. Display-metric aggregation averages
issuances within instrument/horizon/origin, horizons within instruments, instruments
within dates, then dates. Target semantics are never pooled together. Native price
errors are row-specific; normalized fractions and terminal logreturns are labelled.
Paired audit summaries are descriptive cross-sectional pairs, not confidence
intervals or independent chronological performance evidence. Paired errors and
range-hit rates use the same grouped weighting. Raw pair/hit/win counts remain
labelled diagnostic issuance counts; paired distinct-date and instrument-target
denominators are shown separately. Unknown original statuses are rejected as
failed inputs, never silently converted to withheld rows.

Focused checks:

```sh
/path/to/configured/python -m pytest -q tests/test_quality_scorecard.py
```

Fixtures prove implementation behavior only. An actual retained-cohort report
requires the exact reviewed private packet and independent financial/integration
review. Provider truth, public rights, profitability, calibration and deployment
are not established by passing tests or writing a report. Missing timing/RSS
telemetry is explicitly null, not an estimated measurement.
