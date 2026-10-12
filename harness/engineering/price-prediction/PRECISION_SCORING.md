# Synthetic precision scoring v1

`precision_scoring.py` implements a pure stdlib `score_cohort(packet, *, review_at)`
function for **authored synthetic arithmetic only**. It has no parser, CLI, storage,
provider imports, calendar engine, forecast generation or model fitting. It does
not accept real source evidence, certify predictive skill, or replace the legacy
CSV evaluator or synthetic outcome-v2 metadata assessor.

The exact accepted field/type/output contract is frozen in
[PRSG-99](../../../plans/2026-10-12/PRSG-99-synthetic-precision-scorer.md#frozen-exact-contract).
Schema version 1 here is a separate namespace from either existing evaluator.
No public report, forecast ledger or collector is modified by this component.

## Input and validation

The root explicitly declares `synthetic=true`, `classification=synthetic_only`,
a single instrument/horizon/unit/basis/scale cohort, a due-only schedule, exact
opportunity membership, and separate forecast/outcome digest bindings. All
nested key sets are closed. Built-in types only; booleans are not numbers or
integer versions. Unknown availability stays missing/ineligible, never an
inferred timestamp. Dates and explicit review/known/close/issuance instants
follow the frozen UTC-only syntax; no clock is consulted.

Resource limits are 1,000 opportunities, depth 8, 250,000 visited values including
keys, and 128 characters per string. The iterative resource walk also bounds
pending work and rejects cycles through the depth limit. Resource exhaustion
precedes structural/type reporting; inputs within budget collect deterministic
schema errors. Subsequent stages are synthetic/version, contract/time/domain,
schedule, forecast/disposition, outcome/bindings, arithmetic/output. The first
failed stage returns sorted fixed reasons, with no input text or exception data.

Positive price/series numbers are restricted to `[1e-100, 1e100]`. Alpha is exactly
0.05 and horizon is exactly one authored session. Nonfinite values, oversized
integers and unsupported magnitudes are rejected, not clipped. All computed
intermediates/final metrics must remain finite. Invalid packets return no partial
counts, metrics or rows, so malformed opportunities cannot disappear into an
otherwise favorable summary.

Canonical digests are SHA256 of stdlib JSON with sorted keys, compact separators,
ASCII escaping and `allow_nan=False`. Numeric/time representations are not
rounded or normalized before hashing. An altered fixture with an unchanged
binding fails; independently recomputing both externally is undetectable. Hashes
prove object consistency only, never historical possession or provider authenticity.

## States and denominators

The caller declares source-gate abstention, issuance failure or issued disposition;
it does not supply a scored/pending label. Issued rows derive their state at the
explicit review instant:

- Before target close: `issued_pending`, with no submitted outcome.
- At/after target close without an eligible authored outcome:
  `mature_missing_outcome`, retaining `absent` or `ineligible`.
- At/after target close with bound comparable outcome available/known by review:
  `scored`.

Issuance must precede target close strictly. Availability at target close or review
is permitted. Outcome vintage is independent from forecast vintage; the outcome
binds the forecast digest and common scale. No revision selection, rebasing or
conversion occurs. Source abstention and issuance failure remain visible after
maturity. Every due scheduled opportunity must appear exactly once. The supplied
schedule is not independently checked against real scheduler runs or an exchange.

`scheduled = source_gate_abstention + issuance_failure + issued`;
`issued = issued_pending + mature_missing_outcome + scored`;
`mature_issued = mature_missing_outcome + scored`.
Issuance coverage is issued/scheduled and outcome completion is scored/mature_issued.
Zero denominators yield null fractions. These operational ratios are separate
from conditional numerical losses.

## Arithmetic

For value `P` and reference `R`, log-return percentage points use a fixed rule:
`100*log1p((P-R)/R)` for `R/2 <= P <= 2*R`; otherwise
`100*(log(P)-log(R))`. This avoids direct-ratio overflow/underflow and improves
near-equal numerical behavior. Candidate and zero-return point baseline use
identical scored rows; baseline point is derived as reference. Primary delta is
candidate absolute log-return loss minus baseline loss. Negative means smaller
**synthetic** error, not demonstrated market improvement. Unit MAE and RMSE are
also reported. Sorted `(target_session, opportunity_id)` order and `math.fsum`
make aggregation independent of input ordering. Oracle tolerance is relative
1e-12/absolute 1e-10; counts, states and booleans are exact.

Direction is independently authored for the candidate, never inferred from its
point. Prior-sign baseline is validated from frozen reference/prior close; a zero
prior return requires abstain. Only up/down predictions enter hit denominators;
realized zero is a miss and separately counted. Flat/abstain excludes direction
only. Individual and matched up/down comparisons retain their own counts.
Directional coverage is eligible/scored: it is **0.0** for zero eligible when
scored>0, and null only for scored=0. Hit fraction is null whenever eligible=0.
Matched hits remain a candidate/baseline count object even with no intersection.

Intervals are authored and their construction is explicitly unverified. Inclusive
coverage, lower/upper misses, normalized width `(U-L)/R` and proper interval score
are reported for candidate and baseline on the same rows. At alpha=.05, interval
score is width plus `40*(L-y)` for lower misses or `40*(y-U)` for upper misses.
Normalized width is reported alongside coverage; nominal 95% is not calibrated confidence.
Log loss/normalized width are scale-invariant; MAE/RMSE/interval score scale with
units. Adjusted/total-return series values are not executable traded-price targets.

## Verification and limits

Tests use only in-memory authored fixtures and hand-computable oracles. They
cover ties, interval endpoints/penalties, operational state boundaries, missing
and delayed outcomes, malformed schemas/bindings, distinct vintages/common scale,
bounded extremes, resource limits, ordering and input/output isolation. Legacy
forecast and outcome-v2 regression tests run unchanged with the new tests.

Every output is newly allocated, JSON-compatible and explicitly synthetic-only,
source eligibility not assessed and rights unverified. No Brier/calibration,
uncertainty/significance, financial promotion, source rights verification,
calendar completeness, or historical possession claim is made. Real source
onboarding and human-reviewed financial acceptance remain separate requirements.
