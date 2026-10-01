# Synthetic offline session metrics

`calculate_session_metrics(fixture)` in `harness/session_metrics.py` is pure
standard-library computation. It reads no files, databases, providers or network,
mutates no inputs, and selects no movers or forecasts. It does not integrate with
EvidenceStore, attest an exchange calendar, adjust corporate actions or verify
market-data rights. All examples/tests use invented instruments and dates.

## Envelope schema 1

Required fields:

- `schema_version`: integer 1; `origin`: literal `synthetic`.
- `instrument`, `venue`, `currency`, `adjustment_basis`: nonempty text, identical
  on every bar. An adjustment label does not prove actual comparability.
- `exchange_timezone`: IANA timezone used only to check the declared completed
  session date; it does not verify an exchange's session hours.
- `decision_cutoff`: aware ISO timestamp. Comparisons use actual instants.
- `source_vintage_selection`: object with nonempty `method` and `reference`.
  The caller must resolve authoritative source vintages before calling. This
  declaration is retained, not independently verified. Ingestion revision order
  is not source authority, and this function never chooses `max(revision)`.
- `expected_sessions`: nonempty, strictly ordered unique `YYYY-MM-DD` fixture
  list. It defines immediate predecessors and the volume window. It is **not a
  verified exchange calendar**; completeness is the caller's responsibility.
- `target_sessions`: nonempty ordered unique subset of expected sessions.
  Every target/control is returned, including missing, normal and rejected rows.
- `bars`: explicit list, possibly empty, ordered uniquely by session. Bars may
  omit expected sessions but cannot include unlisted sessions, duplicates or
  conflicting/source-vintage alternatives for a session.

Each bar requires matching identity fields and `session`, `interval: 1d`,
`session_type: regular`, boolean `completed`, finite positive numeric
`open/high/low/close`, finite nonnegative numeric `volume`, nonempty `source_version`
and `provenance_ref`, aware `completed_at/available_at/known_at`, `action_status`
(`clear`, `uncertain`, `split`, `dividend`, `other`) and explicit boolean
`shortened_session/halted/reopening`. Numeric strings and booleans are not prices.
OHLC must satisfy `low <= open/close <= high`. Completed time's exchange-local
calendar date must equal session. `known_at` must represent system knowledge,
including ingestion, rather than publication/provider availability alone.

Malformed envelopes, missing/naive times, invalid OHLCV, snapshots, extended
sessions, currency/basis mismatches and duplicate/out-of-order vintages raise
`ValueError`. No rows are silently dropped to repair malformed input. An explicit
incomplete bar, invalid completion <= availability <= knowledge order, or any of
those instants after cutoff instead produces an unavailable row and cannot enter
a baseline. These states retain input references; references do not imply the
rejected evidence was usable at cutoff.

## Calculations

Values are fractions/ratios, **not percentages**:

| Metric | Formula |
| --- | --- |
| `gap` | current open / immediately prior expected close − 1 |
| `close_return` | current close / immediately prior expected close − 1 |
| `intraday` | current close / current open − 1 |
| `range` | (current high − current low) / immediately prior expected close |
| `relative_volume` | current volume / median eligible volumes in previous 20 expected sessions |

Price comparisons never substitute an older observed close when the immediately
prior expected session is missing, unavailable or quarantined. Intraday remains
independent of the prior close. Volume requires at least 15 eligible prior bars in
the last 20 scheduled slots; missing slots do not expand the window further back.
Current/later sessions and unavailable/quarantined history are excluded. A zero
median is unavailable. A finite-input calculation overflowing to infinity is
unavailable, never emitted as an infinite metric. No annualization, return targets,
mover thresholds or causal claims are produced.

Current action uncertainty/split/dividend/other flags or shortened/halted/reopening
flags conservatively quarantine all current metrics. A quarantined prior session
blocks the three prior-close comparisons; independent intraday and an otherwise
valid volume baseline may remain available. Quarantined history is excluded from
volume. No guessed split/dividend adjustment is applied. Comparable adjusted
fixtures may calculate only when the caller supplies matching basis and explicit
clear-action flags. These declarations are not action-calendar verification.

## Result schema 1

Result retains synthetic origin, identity, cutoff, exchange timezone and caller's
source-vintage selection. `rows` follows target order. Each row contains:

- `session`, current `source_version`, `prior_expected_session`.
- `metrics`: five nullable numbers; `reasons`: per-metric lists of reason codes.
- `status`: `ok` (all metrics available), `partial` (some available),
  `unavailable` (none), or `quarantined` (current/prior comparison flags).
  A quarantined row can retain independent safe metrics; inspect reasons/values.
- `provenance`: current and immediate prior references, plus the ordered references
  actually used for the volume baseline. Missing references are null.
- `volume_baseline`: preceding scheduled slots, valid count and median when the
  minimum history requirement is met. Unavailable/quarantined current rows have
  zero valid count and null median because no baseline calculation was attempted.

Reason codes include `missing_target_bar`, `no_prior_expected_session`,
`missing_prior_expected_session`, `incomplete_bar`, `invalid_temporal_order`,
`future_completion/availability/knowledge`, `action_uncertain/split/dividend/other`,
`shortened_session/halted/reopening`, `insufficient_volume_history`,
`zero_median_volume`, `nonfinite_calculation`. Prior failures use `prior_` prefixes.
Reason codes report calculation eligibility, not evidence of market events.

## Minimal runnable synthetic example

These three consecutive dates are artificial expected-session slots, not exchange
coverage. With fewer than 15 prior slots, relative volume is intentionally null.

```python
from harness.session_metrics import calculate_session_metrics

identity = dict(instrument='SYNTH', venue='TEST', currency='USD',
                adjustment_basis='unadjusted')
sessions = ['2026-09-01', '2026-09-02', '2026-09-03']
bars = []
for session in sessions:
    bars.append(dict(**identity, session=session, interval='1d',
        session_type='regular', completed=True, completed_at=session+'T16:00:00Z',
        available_at=session+'T16:01:00Z', known_at=session+'T16:02:00Z',
        open=100, high=108, low=98, close=100, volume=100,
        source_version='fixture-v1', provenance_ref='fixture:'+session,
        action_status='clear', shortened_session=False, halted=False, reopening=False))
bars[-1].update(open=104, close=106)
result = calculate_session_metrics(dict(schema_version=1, origin='synthetic',
    **identity, exchange_timezone='UTC', decision_cutoff='2026-09-04T00:00:00Z',
    source_vintage_selection=dict(method='caller-selected fixture', reference='fixture:selection'),
    expected_sessions=sessions, target_sessions=[sessions[-1]], bars=bars))
row = result['rows'][0]
assert abs(row['metrics']['gap'] - 0.04) < 1e-12
assert abs(row['metrics']['close_return'] - 0.06) < 1e-12
assert row['metrics']['relative_volume'] is None
```

Run frozen offline checks:

```sh
python3 -m pytest -q tests/test_session_metrics.py tests/test_evidence_store.py tests/test_forecast_review.py
```

Live providers, authoritative vintage resolution, calendar coverage, real action
adjustments, movers, forecasts and production consumers require separately accepted
work. Passing synthetic calculations establishes formula/rejection behavior only.
