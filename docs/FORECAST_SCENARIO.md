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

Generated fields now include a closed forecast_time_basis: schema1, fixed method
ID, venue IANA timezone, calendar version and reference/target close instants.
Those zone/version values are also retained in private audit and mapper-linked
to the public contract; private evidence IDs/hashes remain private. The seven-key
forecast_basis is unchanged. Withheld time contracts are null.

The report validator requires the complete linked time contract only for this
exact SPY/USD method, observations20/h1/next_session. It checks venue-local
reference/target dates, reference close<=issuance<=report cutoff and future target
close>issuance. A same-calendar-date target can therefore pass without shifting
issuance. Equal/past targets, malformed linkage and injected contracts on other
methods reject, including Unrated/noncompact rows. Other methods with no contract
retain legacy date-only behavior. Existing public/provenance/numeric guards and
protected daily_report_projection.py remain unchanged. These checks establish
internal linkage, not source authenticity or calendar completeness.

Tests use authored in-memory evidence only and the current report validators.
They cover formula/baselines/rounding, matching-row mapping and isolation,
fixture refusal, withheld gap preservation, missing/future/stale/session/unit/
action/rights/method/nonfinite failures and future-close/legacy time-contract regressions.
No eligible current history or actual public numeric issuance is established by
passing these tests.

## Cash-return variant

PRSG-103 adds closed evidence/admission schema2 and exact method
`spy_cash_return_drift_lognormal_h1_v1`. The original schema1/raw method and audit
shape are unchanged. The public model is `Cash-return drift/lognormal median
scenario v1 (uncalibrated)`. V2 audit adds method_id; six-key time linkage keeps
schema1 and binds the exact selected method. Validators recognize exactly these
two models; other method strings retain prior reserved-contract/date guards.

V2 corporate-action events contain exactly event_id, effective_date, kind, amount,
currency, unit, source_url, source_sha256, source_publication_at, retrieved_at,
ingested_at and known_at. Effective_date is the EX-date, kind cash_distribution,
currency USD and unit gross_cash_per_share. Amount must be positive finite and
not bool. IDs are unique; original source/timestamps/events are evidence/hash
bound. Publication may be null; if present it must be aware and <=retrieval.
Actual retrieval<=ingestion<=known<=coverage-known<=review<=issuance is required.
Unknown amounts and incorrect units/dates/events withhold instead of becoming zero.

Complete action coverage is an externally reviewed **as-of declared-event**
convention across the entire close window and target, not a future-event guarantee.
The external admission evidence reference must preserve the review procedure,
window, sources, failures and limitations. This calculator cannot authenticate
that review. Residual source-index, revisions and unexpected-event risk remains.
No forecast is generated from the current missing history by this implementation.

For return positions1..20, r_i=log(C_i+D_i)-log(C_previous), with distinct gross
cash events aggregated on their verified session EX-date. Zero cash requires
complete admitted coverage. First-window-close events are retained/validated but
have no return contribution. Target-session events, noncash/split/basis changes,
incomplete or future-known evidence withhold. Historical reinvestment is an
authored end-session proxy, not vendor adjusted-series equivalence. Current raw
USD close remains the target/range anchor; mean, sampleSD(ddof1), h1, z1.959964,
low qualitative confidence and uncalibrated range remain unchanged. This module
still has no collection, report-generator CLI, scheduler or publication behavior.
