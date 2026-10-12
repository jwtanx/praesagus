# PRSG-99 Synthetic precision scorer

Type: feature · Modules: harness, financial-data · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days) · Impact: medium-high

Accepted implementation13October under human direction1+2. Outcome: deterministic stdlib arithmetic on explicitly authored synthetic cohorts; no real-data admission, model construction, forecast generation or predictive-performance claim. Existing evaluators, collectors and reports remain protected.

Proposed interface: score_cohort(packet, review_at=explicit UTC timestamp). Exact synthetic schema; authored due-only schedule with strict ID membership; immutable forecast bindings separate from outcomes; derived pending/mature-missing/scored states. Whole invalid packets suppress counts/metrics. Limits: 1000 opportunities, depth 8, 250000 visited values, string length 128, positive numeric domain 1e-100 through 1e100; fixed validation order and finite intermediates. Lead froze the reviewed exact contract appended below before implementation; its limits override earlier provisional wording.

Metrics: matched log-return point loss versus reference baseline, unit MAE/RMSE, authored interval coverage/normalized width/interval score at alpha .05, and individual/matched up/down hit counts. Zero realized return is a miss for up/down. Flat/abstain excludes direction only. Coverage is eligible/scored (0 when scored>0 and eligible=0); hit fraction null at zero eligible. Missing/ineligible mature outcomes remain operational completion failures. Prior-sign baseline derives from frozen prior_close; authored candidate direction is independent of candidate_point. Intervals are authored, construction unverified, and nominal level is not calibrated coverage.

Tests must cover hand-computable losses/ties/interval endpoints, all-abstain and zero-intersection direction, missing/ineligible/late outcomes, due membership, altered bindings, distinct vintages/common scale, bounded numerical extremes, unknown keys/types/bools, deterministic ordering and input/output isolation. No provider/credential/network calls.

## When it's considered done

- [x] PRSG-99-D1: Freeze reviewed exact contract and accepted scope before implementation.
- [x] PRSG-99-D2: Implement synthetic-only scorer with meaningful deterministic regressions.
- [x] PRSG-99-D3: Lead reviews full scope, legacy regressions and authorized delivery.

Registered Engineer produced the exact private proposed contract; Trader accepted synthetic conventions with coverage correction, incorporated by Lead. The exact contract appended below accompanies accepted implementation; this summary alone is insufficient implementation authority. Current source remains separately no-go pending attributable structural/price-basis/finality/rights evidence. Effort is an estimate, not accuracy lift.

## Frozen exact contract

The following exact text originated as a planning proposal. Lead accepted it for PRSG-99 implementation on13October with the reviewed amendments below. Historical planning-only/remaining-decision statements in the quoted contract describe its authoring stage; the explicit Lead acceptance and reviewed amendments govern current scope.

# Proposed exact synthetic scorer contract — 2026-10-12 MYT

Planning deliverable only. Lead has not accepted implementation. Registered Trader must decide the financial items in section 9. This is a proposed standalone stdlib component, not an amendment to the legacy CSV evaluator or outcome metadata v2. No repository implementation, tests, provider calls or secret access occurred. The source plan is `scorer.md` in this folder; PRSG-97 supplies the reviewed research metric/tie policy.

## 1. Interface, types and hard limits

`score_cohort(packet, *, review_at)` returns a newly allocated JSON-compatible dict. No I/O, CLI, persistence, provider/store imports, clock reads, calendar engine, fitting or generation. Review time is an explicit argument.

Only built-in dict/list/str/int/float/bool/None are accepted, with exact types (no subclasses). All objects have exactly the keys below; unknown or missing keys invalidate the whole packet. Nullable fields must be present as null. Dict keys must be strings. Unknown versions are rejected, never interpreted as outcome-v1/v2. No bytes or JSON parser in this MVP.

Limits: 1,000 scheduled opportunities; nesting depth at most 8; at most 250,000 total visited values including keys; every string at most 128 characters. Identity/version fields are nonempty ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}`. Currency is `[A-Z]{3}`; MIC is four uppercase letters/digits. SHA256 is 64 lowercase hex characters. Dates are valid `YYYY-MM-DD`. Instants, including review_at, are UTC strings exactly `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-MM-DDTHH:MM:SS.sssZ`; leap seconds are unsupported. Compare parsed aware instants, not strings. Other nonzero timezone offsets are outside this first schema. Equivalent millisecond representations may compare equally, but original strings remain hash inputs.

Integers are exact int, never bool. Price/series numbers are exact int or float, never bool, positive finite and within `[1e-100, 1e100]`; integer-to-float conversion must also be finite. This deliberately restricted synthetic domain keeps derived price errors, squared errors, interval widths/penalties and normalized widths bounded. Values outside it produce `numeric_domain`, not clipping or imputation. Root alpha is finite numeric exactly 0.05. Horizon is integer exactly 1. No arbitrary numeric fields are accepted elsewhere.

## 2. Root and cohort contract

Exact root keys:

| Key | Type/constraint |
| --- | --- |
| schema_version | int, exactly 1 |
| synthetic | bool, exactly true |
| classification | str, exactly `synthetic_only` |
| contract | exact object below |
| scheduled_total | int, 0–1000 |
| schedule | list of exact scheduled objects |
| opportunities | dict keyed by scheduled opportunity ID |
| forecast_bindings | dict: issued opportunity ID → SHA256 |
| outcome_bindings | dict: eligible outcome opportunity ID → SHA256 |

Contract exact keys: `cohort_id`, `instrument_id`, `market`, `mic`, `currency`, `unit`, `basis`, `value_semantics`, `scale_id`, `calendar_version`, `instrument_version`, `method_id`, `method_version`, `interval_baseline_id`, `horizon_sessions`, `alpha`.

IDs/versions follow the identifier rule. `market` is exactly `US`; `unit` is `price_unit` or `series_unit`; `basis` is `unadjusted`, `split_adjusted` or `total_return_adjusted`. `value_semantics` is `traded_close_series` for the first two bases and `total_return_series` for the last. Total-return basis requires series_unit; it never becomes an executable price target. `scale_id` binds all values to the same authored normalization scale; it is not a source authenticity claim. Versions are caller-authored frozen labels, not independent calendar/rights validation. `interval_baseline_id` is exactly `authored_zero_drift_interval_v1`. Candidate method/version are identifiers frozen once per cohort; the scorer validates no model formula.

Contract digest is SHA256 of canonical UTF-8 JSON of this exact contract: `json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)`. Canonicalization does not round, coerce or normalize numeric/time representations. A changed float/int representation can change the digest. Bindings establish authored object consistency, not historical possession or provider provenance.

## 3. Due-only scheduled identities

Each schedule object has exactly `opportunity_id`, `target_session`, `target_close_at`, `scheduled_at`. ID/date/time types follow section 1. The contract instrument/horizon plus target_session form the canonical identity. Reject duplicate identity or ID regardless of differing time strings. All scheduled_at instants must be ≤review_at and strictly before target_close_at. Future scheduled opportunities are rejected as `schedule_not_due`, not counted as failed issuance. Empty schedule is valid only with scheduled_total=0 and all four maps empty.

Require scheduled_total=len(schedule), and exact ID-set equality between schedule and opportunities. This checks the authored due-set only; it cannot detect a real omitted scheduler run. The caller supplies session/close/calendar mapping. This scorer does not prove h=1 is the next exchange session, nor that the close is genuine/final. No timezone inference from target_session.

## 4. Opportunity disposition and frozen forecast

Each opportunity object has exactly `disposition`, `decision_at`, `reason_code`, `forecast`, `outcome`.

`disposition` is `source_gate_abstention`, `issuance_failure` or `issued`. `decision_at` must satisfy scheduled_at≤decision_at≤review_at. For issued, it must also be strictly before target_close_at. For the two failure dispositions, forecast/outcome are null and reason_code is respectively `synthetic_source_blocked` or `synthetic_issuance_failed`. Their state remains that disposition even after target maturity. For issued, reason_code is null and forecast is the exact object below. Opportunity disposition never claims real source eligibility.

Forecast exact keys:

| Key | Type/meaning |
| --- | --- |
| opportunity_id, contract_sha256 | exact scheduled ID / computed contract digest |
| issued_at | UTC instant equal in time to decision_at |
| forecast_vintage | identifier, authored immutable issuance vintage |
| reference_session | valid date strictly earlier than target_session |
| reference_close_at | UTC instant strictly before target_close_at |
| reference_known_at | reference_close_at≤known≤issued_at |
| prior_close_at | UTC instant strictly before reference_close_at |
| prior_known_at | prior_close_at≤known≤issued_at |
| reference, prior_close, candidate_point | positive domain numbers |
| candidate_direction, baseline_direction | enum `up`, `down`, `flat`, `abstain` |
| candidate_interval, baseline_interval | exact objects `{low, high}` of domain numbers, low≤high |
| interval_construction | exactly `authored_not_verified` |

All reference/prior/candidate/interval numbers use contract units/basis/scale. Point baseline is internally derived as reference; there is no caller-supplied baseline point. Baseline direction must equal sign(reference−prior_close): up/down; equal values require abstain (not flat). Candidate direction is frozen authored input: no threshold inferred or consistency with candidate_point required. The missing prior-return/direction problem is resolved by requiring prior_close for every issued fixture.

Intervals remain caller-authored. This MVP verifies endpoints/binding and scores them; it does not prove baseline bounds came from identical sigma or zero drift. That is why the fixed ID and construction label explicitly say authored/not verified. Trader must accept this arithmetic-only limitation or require a separately specified volatility/construction-validation scope before implementation. No sigma fitting/model generation is added implicitly.

Require forecast_bindings keys to equal issued opportunity IDs exactly. Each value matches the canonical digest of its forecast object. No digest rebuilding or packet resealing inside the scorer. Recomputing a tampered packet and its digest externally is undetectable; docs/output must say so.

## 5. Outcomes, maturity and separate bindings

Issued outcome is either null, an exact unavailable object, or an exact eligible object. No outcome object may be provided while review_at<target_close_at.

Unavailable object exact keys: `kind`=`unavailable`, `reason_code`=`absent` or `ineligible`, `known_at` UTC with target_close_at≤known_at≤review_at. No numeric payload is retained. Null means no submitted outcome and becomes absent at maturity.

Eligible object exact keys: `kind`=`eligible`, `opportunity_id`, `contract_sha256`, `forecast_sha256`, `outcome_vintage`, `scale_id`, `close_at`, `available_at`, `known_at`, `actual`. ID and digests match the scheduled identity, contract and forecast binding. Outcome vintage is an independent identifier; it need not equal forecast_vintage. scale_id must equal contract scale_id. close_at equals target_close_at as an instant; close_at≤available_at≤known_at≤review_at. Actual is a positive domain number in contract units/basis/scale. Eligible here means eligible authored arithmetic, never approved source. Unknown availability cannot be replaced by close_at; caller must use unavailable/ineligible instead.

Require outcome_bindings keys to equal eligible outcome IDs exactly, with digest of each complete eligible object. Forecast binding contains no outcome fields, so adding future outcome data cannot alter the forecast digest. Outcome binding includes forecast digest and distinct outcome vintage. No revision preference, rebasing, conversion or overwrite is implemented: caller supplies one primary authored outcome per opportunity; wrong identity/scale/bindings invalidate the whole packet.

Derived issued state: review<target close → issued_pending; review≥target close and null/unavailable → mature_missing_outcome; review≥target close and eligible outcome → scored. Equality at target/availability/review boundaries is allowed, while issuance at target is forbidden. Callers supply no scored/pending status label. Mature missing rows retain absent/ineligible reason. Bad numeric/temporal/binding evidence is packet-invalid, not silently reclassified as missing.

## 6. Arithmetic and deterministic aggregation

Score candidate and point-baseline losses on exactly the scored rows. Compute log return `100*(log(value)−log(reference))`, avoiding raw ratio overflow/underflow. For near-equal numbers, use the fixed implementation rule using `log1p((value−reference)/reference)` when reference/2≤value≤2*reference; use the same rule everywhere. Primary row delta is absolute candidate log-return error minus absolute baseline log-return error. Negative means smaller authored synthetic loss only.

Price/series-unit row errors: abs(candidate_point−actual) and abs(reference−actual). MAE is mean error; RMSE is sqrt(mean squared error). Input domain and row-count limits bound all intermediates, but every computed intermediate/final metric must still be finite; otherwise invalidate with `numeric_overflow`. No saturation, silent row drop or partial summary.

For each candidate/baseline interval: inclusive coverage; lower miss iff actual<low; upper miss iff actual>high; width/reference; interval score `(high−low)+40*(low−actual)` for lower miss, or `+40*(actual−high)` for upper miss. Width/score are both reported. Scores/MAE/RMSE have contract units; normalized width is dimensionless; primary delta is log-return percentage points. No Brier/calibration/significance/promotion calculation.

Direction is assessed from actual compared with reference, using exact value comparison. Up/down predictions enter denominator; flat/abstain are excluded. Realized equal-to-reference is a miss for up/down, retained in denominator and tie count. Report each direction's coverage and hits; matched comparison includes only rows where both directions are up/down. Baseline abstention stays visible, never becomes flat.

Canonical row order is `(target_session, opportunity_id)` because instrument/horizon are fixed; never mutate the input list. Aggregate using math.fsum over this order, then divide by explicit count. Output rows use the same order. Binding keys also emitted in sorted order. Repeated calls/reordered packet maps/lists produce equal output for unchanged field representations. Numeric oracle tolerance is `math.isclose(rel_tol=1e-12, abs_tol=1e-10)`; timestamps/counts/booleans/statuses are exact. Scale invariance applies to primary log loss/normalized width, not unit-valued losses/scores.

## 7. Exact output shape

Always exact root keys: `schema_version`=1, `synthetic_only`=true, `classification`=`synthetic_only`, `source_eligibility`=`not_assessed`, `rights_status`=`unverified`, `invalid` bool, `review_at` (validated input or null), `contract` (new copy or null), `reasons` list of fixed codes, `counts`, `operational`, `metrics`, `rows`, `limitations`.

Invalid packet: contract/counts/operational/metrics null; rows=[]; sorted unique fixed reasons; no performance or partial counts. Valid packet: reasons=[]; copied contract; counts exactly `{scheduled, source_gate_abstention, issuance_failure, issued_pending, mature_missing_outcome, scored, issued, mature_issued}`. Partition: scheduled=abstention+failure+issued; issued=pending+missing+scored; mature_issued=missing+scored. `operational` exactly `{issuance_coverage, outcome_completion}`, each `{numerator, denominator, fraction}`. Coverage=issued/scheduled; completion=scored/mature_issued; zero denominator → null fraction.

`metrics` exactly `{point, direction, interval}`. Point exactly `{paired_count, candidate_log_mae, baseline_log_mae, mean_log_loss_delta, candidate_mae, baseline_mae, candidate_rmse, baseline_rmse}`; zero paired_count means all seven metrics null. Direction exactly `{candidate, baseline, matched}`, each `{eligible_count, hits, realized_zero_count, hit_fraction, coverage_fraction}`; individual coverage denominator=scored; matched coverage denominator=scored, and hits for matched is exact object `{candidate, baseline}` with hit_fraction same object; zero eligible yields null hit fractions (matched hit_fraction null, not object of zeroes); coverage is 0.0 when scored>0 and eligible=0, and null only when scored=0. Interval exactly `{paired_count, candidate, baseline}`; each method has `{covered, lower_misses, upper_misses, coverage_fraction, mean_normalized_width, mean_interval_score}`; zero paired_count means counts0 and fraction/means null. Candidate/baseline always share point/interval paired count.

Each row exactly `{opportunity_id, target_session, state, missing_reason, forecast_sha256, outcome_sha256, losses}`. Missing reason absent/ineligible only for mature_missing, otherwise null. Forecast digest null only for nonissued; outcome digest null except scored. Losses null except scored. Scored losses exactly `{candidate_log_absolute, baseline_log_absolute, log_loss_delta, candidate_absolute, baseline_absolute, candidate_direction_hit, baseline_direction_hit, realized_zero, candidate_interval, baseline_interval}`. Direction hits are bool or null when excluded; realized_zero bool; interval objects exactly `{covered, lower_miss, upper_miss, normalized_width, interval_score}`.

Limitations is a fixed ordered list: synthetic arithmetic only; no scheduler completeness/calendar/source/rights verification; hashes do not prove historical possession; authored interval construction not verified; direction authored independently of candidate_point; no calibration/significance/promotion; adjusted series is not an executable target. Returned dicts/lists must not alias any input object. Successful JSON encoding with allow_nan=False is an output acceptance check, not a file write.

## 8. Validation order and required checks

Use deterministic stages: budget/types/schema → root synthetic/version → contract/date/time/domain → schedule identity/due-set → opportunity disposition/forecast → outcome/bindings → arithmetic/output. At the first failing stage return sorted unique codes collected within that stage only, independent of input order. Codes are fixed: `resource_limit`, `schema`, `unsupported_version`, `not_synthetic`, `contract`, `timestamp`, `numeric_domain`, `schedule_identity`, `schedule_not_due`, `schedule_membership`, `opportunity_state`, `forecast_time`, `forecast_binding`, `baseline_direction`, `outcome_time`, `outcome_binding`, `outcome_scale`, `numeric_overflow`. No input strings, exception messages, paths or provider errors in reasons.

Focused regression scope: hand-computable paired losses, up/down/zero/flat/abstain, inclusive intervals and penalties, empty/zero-scored cohorts; due-only/failure/pending/exact-close/mature-missing/late-available states; omitted/duplicate scheduled identities; false prior sign; altered forecast/outcome digests; separate outcome vintage; scale mismatch; input/output aliasing; near-equal/extreme/domain-boundary values; wrong types/unknown keys/booleans/nonfinite/size/depth/huge ints; deterministic reorder. Legacy forecast and outcome_v2 tests run unchanged after separately accepted implementation. No test has been run for this planning document.

Exact proposed implementation paths remain new precision_scoring.py, tests/test_precision_scoring.py, PRECISION_SCORING.md and one Lead-assigned dated spec/PRSG-N.harness.json. Use existing importlib file loading for the hyphenated directory; no package/dependency/policy changes. All existing files protected. Lead must freeze base/paths/checks and review this contract before implementation.

## 9. Remaining decisions for Trader and Lead

Trader: accept the arithmetic-only authored zero-drift interval label/limitation, or require a separately specified construction validator; accept proposed 0.05 nominal level and candidate direction as predeclared authored enum without threshold validation; approve common scale/units/basis wording and outcome availability convention for synthetic fixtures. The existing reviewed zero-realized-return miss/flat exclusion policy is preserved. None of these decisions accepts real data, source semantics or a new production financial policy.

Lead: approve due-only set, proposed numeric domain/resource limits, exact schemas/bindings/output and invalid-whole-packet policy; allocate ticket and freeze accepted implementation scope only after human sees plans. Real issuance schedule, source onboarding, corpus/effect/sample/stopping/uncertainty policy remain outside this synthetic arithmetic MVP.

## Lead/Trader reviewed amendments

Planning-only financial acceptance returned. Direction coverage is eligible_count/scored: 0.0 when scored>0 and eligible_count=0; null only when scored=0. Hit fractions remain null at eligible_count=0. Matched zero hits remain the candidate/baseline count object. Add all-flat/abstain and empty-intersection oracles. Fixed limitations disclose direction independence from candidate_point and unverified interval construction. Use the specified log1p region consistently as a fixed rule, not an option. Alpha 0.05 and authored interval arithmetic accepted for synthetic fixtures only; no real-source/model approval.


## Engineer implementation handoff — 2026-10-13 08:10 MYT

Implemented the standalone pure stdlib scorer, authored synthetic tests and versioned documentation within the five accepted paths. Existing forecast_review.py/outcome_v2.py APIs, implementations and their tests are unchanged. The scorer derives maturity, binds frozen forecasts separately from later outcomes, validates a due-only scheduled identity set and suppresses all summaries for invalid packets. Root/output remain synthetic-only with source eligibility not assessed and rights unverified. There is no parser, CLI, persistence, provider/store import, calendar engine, dependency, forecast generation or model promotion.

Trader's coverage correction is implemented: directional coverage0.0 when scored>0/eligible=0, hit fractionnull at zeroeligible; matched hits retain the two-method count object. The fixed log1p region is used exactly. Prior-sign is checked from frozen prior_close; candidate direction and interval construction remain authored/unverified. The iterative resource walk bounds pending work and gives resource exhaustion precedence over structural reporting, making that first-stage rejection deterministic. Positive domain and final finite/output encoding controls retain bounded arithmetic.

Exact final executed check (cwd: /Users/jwtan/.codex/worktrees/prsg89-prediction-chip/praesagus):

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' /Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_precision_scoring.py tests/test_forecast_review.py tests/test_outcome_v2.py
263 passed in0.42s; exit0
```

Earlier focused iterations passed250,256 and262 tests; additional meaningful oracles and serialized-output ordering were added before the final263 run. No failing test run occurred. Coverage includes hand-computable paired point MAE/RMSE/log deltas; direction ties/flat/abstention/empty intersection; interval endpoints and penalties; operational partitions and exact target/availability boundaries; due/identity omissions; altered bindings and distinct vintages/common scale; representation-preserving hashes; bounded extremes and resource limits; ordering, strict schema/types and input/output isolation. Existing legacy regressions were included unchanged. These are synthetic arithmetic checks, not predictive-performance or real-source validation.

D2 is demonstrated; D3 remains pending Lead independent scope/review and delivery. No commit/push/provider/credential/private-store access. Complete five-path scope/whitespace and documentation-link checks accompany the returned handoff; manual check evidence is not automatic ticket-runner verification. Primary protected projection hash remains b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f.

Final complete actual Git scope (tracked diff from frozen base plus all untracked files) is exactly the five allowed paths. Manifest validator, existing diff check, per-new-file no-index whitespace checks and documentation spec-link resolution passed. No tracked file differs from frozen base, including both existing evaluator implementations and legacy tests. Hooks remain configured as .githooks. Lead review/delivery D3 stays pending.

## Lead independent acceptance

Lead reviewed all five new files and independently ran pytest on precision_scoring, forecast_review and outcome_v2:263passed0.50s. Explicit scope amendment:250000 visited values accepted to support the declared1000 full opportunities; the earlier50000 limit was inconsistent with that cohort capacity. This is a Lead-approved bounded resource choice, not pre-existing authorization. Exact1000-row regression passes; no input/resource guard removed. Source/model/calibration limits preserved. Delivery verification follows commit/push; no live performance claim.
