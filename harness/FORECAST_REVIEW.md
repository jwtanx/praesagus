# Offline forecast review

The forecast evaluator validates frozen CSV forecast records and computes supplied outcomes at an explicit review time. It uses Python's standard library, requires no network or market credentials, and does not change the ledger. The proposed answer harness in `research_harness.yaml` remains design-only.

From the repository root:

```bash
poetry run python -m harness.forecast_review \
  --ledger harness/engineering/price-prediction/forecast-ledger.csv \
  --as-of 2026-10-01T03:00:00+08:00

# A later review can save a JSON summary to a separate file.
poetry run python -m harness.forecast_review \
  --ledger harness/engineering/price-prediction/forecast-ledger.csv \
  --as-of 2026-10-10T23:00:00+08:00 \
  --output /tmp/praesagus-forecast-review.json

poetry run python -m pytest -q tests/test_forecast_review.py
```

Exit code 0 means supplied rows passed validation; it does not mean outcomes are available or forecasts were accurate. Exit code 1 reports invalid input, and malformed command arguments return a nonzero exit code. The JSON includes row results, validation errors, aggregate counts, and separate horizon summaries. Zero-denominator metrics are null.

## Input and scoring rules

Use the ledger header as the forecast schema. Preserve original forecasts and evidence snapshots; write corrections as documented new vintages. Numeric prices and complete range pairs must be finite and positive. Probabilities, when supplied, must be between 0 and 1. Forecast timestamps include a timezone and cannot follow the review timestamp. Normally the target date must follow both the report date and the forecast's local date. For a same-calendar-day target, include the optional `forecast_target_close_at` CSV field: it must be a timezone-aware ISO datetime whose own local date equals `forecast_target_date`, and the frozen `as_of` must be strictly before that close. When supplied, the close timestamp must also be later than the forecast issuance time.

To score an outcome, provide `actual_close_date`, `actual_close`, and `actual_source` together. Keep `actual_close_date` equal to `forecast_target_date`. Add an `actual_available_at` CSV column with the timezone-aware timestamp when that close became available. Its absence leaves a complete outcome unscored because availability cannot be verified. When `forecast_target_close_at` is present, `actual_available_at` must be at or after that close. A future outcome or mismatched target date fails validation. Supplied timestamps are validated, but their underlying source truth still requires review.

| Result | Meaning |
|---|---|
| `pending` | Target has not matured and no outcome is supplied. With `forecast_target_close_at`, it remains pending until the review timestamp reaches that venue-local close; without it, the existing review-calendar-date rule applies. |
| `not_scored` | Outcome is missing, availability is unverified, or baseline comparability is ambiguous. |
| `abstain` / `data_unavailable` | No eligible forecast; excluded from scoring. |
| `scored` | Comparable outcome inputs pass the evaluator's checks. |
| `invalid` | Row violates the input contract; excluded from metrics and causes nonzero exit. |

Return is `(actual / reference - 1) * 100`. Direction hits use strict positive/negative returns for up/down calls; unchanged prices miss both. Flat and sideways calls have no direction score. Range hits include endpoints and use a separate denominator. Brier scores are available for supplied positive-return probabilities; zero-return outcomes are excluded under this initial scoring policy.

Repeated issuances for one instrument, horizon, and target remain separate records and are flagged as correlated vintages. Aggregates are descriptive, not independent-sample accuracy estimates. Do not select a favorable issuance after seeing the outcome. Coverage uses scored versus mature unscored rows; abstentions and invalid input counts remain visible separately.

## Evidence limits

Historical rows include intraday snapshots in a column named `reference_close`. The evaluator conservatively withholds scoring when notes mark the reference as intraday or a snapshot, including ambiguous mixed-market notes. It does not replace these records with invented closing prices. Future collection should record a structured baseline type, timestamp, quote currency, venue, adjustment basis, and source availability.

The evaluator does not fetch prices, verify source URLs, authenticate frozen forecast history, or calculate exchange holidays/session closes. Currency, corporate actions, adjustment basis, target-session selection, and source validity require provider or human checks. Date-only maturity classification follows the review timezone; scoring additionally requires actual availability. Small samples, repeated vintages, and manually set ranges cannot establish predictive skill. This build provides repeatable offline checks; it does not update skills or prompts automatically.

## Separate synthetic v2 metadata assessment

`engineering/price-prediction/outcome_v2.py` exposes
`assess_outcome(record, *, fixtures, review_at)`. It is a pure standard-library
function accepting in-memory objects, separate from the v1 CSV and scoring API.
Inline examples and synthetic fixtures are in `tests/test_outcome_v2.py`; the
authored holiday and early close there are simulations, not exchange calendars.

The schema-2 record must declare `synthetic: true`, US market, frozen
`forecast_id`/`ledger_revision`, listing identity, forecast cutoff, reference and
target session dates, `horizon_kind: trading_sessions` and a positive count.
Count excludes the reference session and includes the target. Version references
are `ledger_version`, `instruments_version`, `calendar_version` and `mic_version`.
Each `reference`/`actual` object supplies listing ID, ticker, MIC, currency,
session date/timezone, exact UTC `close_at`, `observed_at`, `available_at`,
`retrieved_at`, source and series semantics. Reference observation, availability
and retrieval cannot follow forecast cutoff; actual times cannot follow review.
Observation must equal the fixture's final regular-session close; availability
must follow observation and retrieval must follow availability. Null availability
requires `availability_status: unknown` and `availability_fallback: none` and
always blocks assessment. It is never inferred from retrieval.

Fixtures contain explicitly synthetic, versioned `ledger`, `instruments` and
`calendar` objects plus an `evidence` ID-to-bytes mapping. The ledger fixture
binds forecast metadata and its frozen `reference_metadata`. Listing intervals
are inclusive at `effective_from` and exclusive at `effective_to`; exactly one
listing mapping must match at each endpoint. This first contract conservatively
requires identical ticker/listing identity at both endpoints. The calendar
declares complete coverage, a MIC, IANA timezone and session-date-to-final-close
mapping. UTC closes must map to their declared local session date. The caller's
synthetic declarations are validated for consistency, never authenticated.

Both endpoints require `source_claim: simulated`. Supported `source_class`
declarations are `vendor_reported_bar` and `exchange_certified_close`; these are
simulated provenance labels, not evidence grades or actual certification.
Only `observation_kind: final_regular_session_close` and `price_field: close`
are accepted. Intraday, last-trade, extended-hours and provisional closes block.
Adjustment basis must be `unadjusted`, `split_adjusted` or `total_return_adjusted`,
with matching immutable `series_vintage` and explicit matching
`corporate_action_treatment`. Unknown treatment blocks. Total-return adjustment
requires `value_semantics: total_return_series`; the others require
`traded_close_series`. This preserves the distinction and never substitutes a
total-return series for a traded close. No prices or returns are evaluated.

Evidence bytes must decode to the exact synthetic schema/forecast/revision and
endpoint objects, without duplicate JSON keys. `evidence_fixture_id` and
`evidence_sha256` bind those supplied bytes only; matching bytes do not establish
source authenticity, price accuracy, licensing or entitlement.

The result separately reports `maturity`, `provenance_status`, `rights_status`,
`review_status`, `assessment_status` and sorted deterministic `reasons`.
`rights_declaration: synthetic_only` plus `review_state: requested` can permit
`ready_for_human_review` when every metadata gate passes. Rights remain
`unverified`, and requested review is never approval. Missing/unverified/denied
rights declarations, pending/denied review and future targets remain `blocked`.
Schema-1 records return `legacy_unverifiable` without dispatching to v1 scoring.
There is no persistence, provider access, outcome scoring or permission to score
real observations; the historical ledger and v1 evaluator remain unchanged.

```bash
python3 -m pytest -q tests/test_outcome_v2.py tests/test_forecast_review.py
```
