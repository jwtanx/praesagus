# Reviewed-evidence SPY price scenario

`ingest.forecast_scenario.build_forecast_scenario(evidence, *, admission, issued_at,
report_cutoff)` verifies seven reviewed input gates and calculates a research-only
raw-close SPY next-session model median and **uncalibrated** range. It performs no
intake, file writes, model fitting, source approval or report publication.

The closed input/output contract is recorded in the accepted
[PRSG-101 spec](../plans/2026-10-13/PRSG-101-first-supported-price-scenario.md).
A separate reviewed admission binds the entire structured evidence, method and
seven evidence subsets. The calculator checks those hashes and temporal/technical
consistency. It does not authenticate reviewers, provider bytes, event completeness
or licensing: the trusted Lead/Trader workflow must independently establish those
claims. Hashes and `reviewed_real` labels cannot turn fabricated evidence into a
valid real forecast. Authored reviewed-real-shaped tests prove plumbing only.

Required gates are identity/USD traded units; accepted venue calendar and exactly
21 consecutive completed closes ending at the latest completed reference; bar
provenance and knowledge by issuance; accepted close settlement convention; raw
basis and complete action-free coverage through target; separate collection,
private research/retention and derived-publication rights; and frozen method.
Vendor regular close is not described as an exchange-certified close. Unknown
publication stays null. Settlement may be an explicitly reviewed operational
revision cutoff. No stale reference, future evidence, arbitrary adjustment or
calendar inference is accepted.

The fixed method uses20 chronological log returns, arithmetic mean, sample standard
deviation(ddof1), h1 and z1.959964. Point is reference*exp(mu); bounds are
reference*exp(mu±z*s). Private audit retains full precision and zero-drift matched
baselines. The point is a model median, not fair value/validated expected return.
Up/down follows sign(mu), flat only exactzero before display rounding. No forced
threshold, indicator/quote direction or inferred news input is used.

Public field overlay uses existing target/range/method/horizon/reference fields
and the existing seven-key forecast_basis. USD amounts use2decimal HALF_UP
rounding, with numeric fields matching displayed amounts. Range text is
`USD <low>–USD <high>` without spaces around the dash, matching the existing
viewer amount parser; no renderer change is needed. Unsupported arithmetic
or unsafe rounding withholds Unrated/nulls. Low confidence is a qualitative method
limitation, not a probability. Nominal95% is a model assumption, not empirical
coverage. Assumption/disconfirming text is clearly method-based, not fabricated
fundamental news.

`apply_scenario_to_row(row, result)` is a separate pure mapper. It requires a US
SPY/USD row and an exact valid result. It deep-copies the row and forecast overlay,
preserving every existing instrument/quote/current-price/source/indicator/universe
field and existing data_gaps. Withheld reasons append fixed readable gap strings
without duplicates. It refuses generated authored_fixture results and malformed
results with a fixed ScenarioValidationError; no caller input or exception text
is exposed. Generated reviewed_real results remain subject to independent source
acceptance, complete-report validation and separate publication authority.

The current compact report validator rejects a target on the issuance calendar
date even if its venue close is future. This ticket does not alter that validator
or protected daily_report_projection.py. Tests demonstrate successful generated
mapping when the target date follows issuance, and the same-date/future-close
rejection. No issuance timestamp shift or publication workaround is used. A
separate accepted venue-close time-contract amendment is required for that case.

Tests use authored in-memory evidence only and the unchanged report validators.
They cover formula/baselines/rounding, matching-row mapping and isolation,
fixture refusal, withheld gap preservation, missing/future/stale/session/unit/
action/rights/method/nonfinite failures and the current time-contract limitation.
No eligible current history or actual public numeric issuance is established by
passing these tests.
