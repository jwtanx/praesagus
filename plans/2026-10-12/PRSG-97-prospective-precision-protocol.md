# PRSG-97 Prospective precision evaluation protocol

Type: docs · Modules: harness, market-research, financial-data · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.4 days) · Impact: medium-high

Created 2026-10-12 MYT. Scope: deliver a reviewed source-independent research protocol; no runtime/model promotion.

Status: reviewed research planning contract, not accepted production policy. Classification: research only. Registered Trader owns financial-method acceptance; Lead owns scope and integration. No provider calls, credentials, private-store inspection, numeric forecasts, scoring, repository edits or promotion occurred in preparing this document.

## Decision and reuse

Freeze one SPY, next-trading-session prospective cohort after a viable source passes onboarding. This adds an operational preregistration decision packet to completed PRSG-81/83 findings, rather than repeating their experiment. PRSG-81 already recommended no promotion of drift or Chronos-2. PRSG-95 accepted zero history bars; this protocol does not cure intake, source semantics or rights.

Three paths considered: (1) repeat historical model replay — excluded because completed PRSG-81 and later-retrieved revised data cannot become prospective evidence; (2) single-SPY/h=1 operational cohort — recommended bounded first step conditional on source gates; (3) immediate multi-ticker/multi-horizon comparison — defer until the first source/issuance/outcome path is accepted, to avoid mixing incompatible inputs and expanding multiple testing. A single SPY cohort supports conclusions only about its instrument, method, horizon and observed period.

## A. Source gate before any numeric issuance

Trader/Lead must independently accept instrument/listing/MIC mapping at reference and target, price currency/unit, source identity, exact close field, final regular-session semantics, adjustment/corporate-action formula and vintage, source availability convention, permitted collection/retention/research/derived-publication uses, and versioned venue calendar. A successful HTTP response or positive close does not meet these gates. Unknown source first-publication time remains null. Actual workflow receipt/known time may establish when THIS workflow possessed data if separately accepted, never historical provider publication or a backfilled cutoff.

For the existing 20-log-return method, require 21 consecutive completed eligible session closes ending at the reference; identical declared source/basis and immutable evidence vintage throughout. Derive dates from the accepted calendar at the new reference; do not reuse September 11–October 9 as a generic window. Source corrections are new versions, not overwrites. Never retroactively certify the legacy 120-row cohort or use later data to justify an old issuance.

The adjusted baseline and fixed autype0 unadjusted collector are incompatible until a specific basis decision is accepted. Dividend-inclusive total-return series and traded-close series are different targets. If source only supports raw closes, defining a new raw-close method/target is a separately accepted method scope, not a silent repair of adjusted historical forecasts.

## B. Freeze before first target outcome

Store a signed-off preregistration and immutable issuance/evidence packet containing:

- Cohort ID, instrument/listing/MIC/currency and calendar/listing/source versions.
- Exact daily issuance schedule and cutoff timezone; one canonical issuance per instrument/target/horizon. Missing scheduled runs and data failures remain recorded abstentions, not omitted dates.
- Reference session, finalized close value/field, event-close instant, provider bar label, actual receipt/retrieval/ingestion/known times and provider availability if known, each with its own meaning.
- Horizon h=1, counting sessions after reference through target inclusive; explicit target session and close instant, including holiday, early-close and DST handling.
- Exact method/version/dependency hash, 20-return lookback, ddof=1, formulas, rounding and direction thresholds. No retrospective threshold or horizon selection.
- Interval nominal level and declared Gaussian assumptions/uncalibrated status; original input bytes/hash and immutable vintage; evidence of availability by cutoff.
- Preregistered baselines, metrics, denominator/tie policies, chronological development/holdout boundaries, review dates, stopping rules and evidence threshold.

Illustrative formula specification for retaining the existing candidate, subject to Trader acceptance: r_i=log(P_i/P_(i-1)); mu=mean(last 20 r); s=sample standard deviation; point=P_ref exp(h mu); nominal 95% bounds=P_ref exp(h mu ± 1.959964 s sqrt(h)). This is a candidate formula, not evidence its band is calibrated. If adjusted values are not traded prices, do not render their point estimate as an executable target price without an explicit accepted mapping.

## C. Frozen matched baselines

1. Zero-return point: P_hat=P_ref, evaluated by point loss, never directional hit rate.
2. Prior-session sign direction: sign of the last eligible close-to-close return. Zero prior return is an abstention for this direction comparison. Optional training-only majority sign is an alternative that must be chosen before holdout, not the better result afterward.
3. Zero-drift range: same eligible 20-return volatility, horizon and nominal level as candidate, centered at zero return. This isolates the drift contribution.

All comparisons use matched valid instrument-target-vintage observations. Publish paired denominator and losses; also publish each method's individual availability/abstention counts. Preserve unfavorable rows and do not choose favorable duplicate vintages. No technical-indicator counts, quote-versus-close observations or chip colors enter method inputs.

## D. Metrics and denominators

Primary endpoint proposal: paired mean absolute error difference, candidate minus zero-return baseline, in cumulative log-return percentage points. Negative is improvement. Also report price-unit MAE and RMSE with currency/basis labels; do not combine unlike currencies or horizons.

Direction: up/down hit fraction only. Trader accepted policy: zero realized returns are misses for up/down and remain in the directional denominator; report tie counts separately. Flat predictions are excluded. Preserve the current v1 tie policy; matched directional comparisons and per-method coverage remain explicit.

Range: inclusive coverage, mean width normalized by reference, lower/upper miss counts and proper interval score at declared alpha. In the declared scoring units, IS_alpha=(U-L)+(2/alpha)(L-y) when y<L, +(2/alpha)(y-U) when y>U. Always report width alongside coverage, so widening does not masquerade as improvement. Nominal 95% is an assumption; empirical coverage is not established beforehand.

Operational denominator: every scheduled cohort opportunity; partition issued, source-gate abstention, other issuance failure, pending outcome, mature missing/ineligible outcome, and scored. Report issuance eligibility and outcome completion separately from conditional error. No probability_up supplied means no Brier score or probability calibration claim. Sideways needs a fixed economically/statistically justified threshold to become a tested categorical target; otherwise exclude it from directional accuracy and retain point/range metrics.

## E. Chronological evaluation and source vintage

Development/training comes first, validation follows, and future untouched target-date holdout follows that. Exact boundary dates depend on source readiness and accepted sampling plan; do not invent dates now. Every training label must have actually been available before its forecast origin. Freeze model and hyperparameters before the holdout; no random row split and no tuning on future results.

For h=1 consecutive close-to-close target intervals do not overlap internally, but label availability may be delayed and dependencies/regime persistence remain. Exclude training records whose outcome interval overlaps validation/test intervals, and exclude labels not available at fold origin. For later h>1 scopes purge overlapping labels and use an embargo determined by actual horizon/availability, not an arbitrary fixed day count. Original source vintages remain the issuance inputs; later-revised history is a separate retrospective sensitivity analysis.

Paired uncertainty must respect time dependence. Preregister a time-block method and block-length sensitivity on development data; one-SPY samples have target-date clusters, not a cross-sectional independent sample. If later expanded to several tickers, keep common target-date shocks and instrument dependence together; duplicate vintages are not independent observations. A pretrained-model comparison additionally requires pinned weights, software and known training-data cutoff; release date alone cannot prove an unseen-data test.

## F. Sample planning and decision rule

Before collecting the confirmatory cohort, Trader/Lead choose the smallest worthwhile MAE reduction, interval-score/coverage guardrails and uncertainty level, then estimate paired loss variance/dependence from an eligible DEVELOPMENT series or a transparent conservative planning assumption. Define the required target-date count and fixed review/stopping plan from those inputs. There is no defensible generic N=20 or N=100 sufficiency. If variance/effect assumptions cannot be justified, the first cohort is operational/descriptive only, with no promotion decision.

No promotion merely because a point estimate is better. Require the predeclared uncertainty criterion and materially meaningful effect versus matched baseline, adequate completion/abstention behavior and no unacceptable range degradation, independently reviewed. Multiple exploratory methods/horizons remain labeled exploratory or require an accepted multiple-testing policy. Do not stop early on a favorable metric. Forecast-error success is not trading profitability.

## G. Outcome and costs

After target finalization, collect the comparable close under the accepted source convention, recording event time, true receipt/availability and immutable outcome vintage; all evidence must precede the explicit review time. Target basis/currency/field must match the frozen reference semantics. Revisions append new outcome vintages and preserve the original primary evaluation policy. Missing outcomes remain visible.

Separate any strategy-utility experiment: freeze entry/exit timing that could actually be executed after information becomes known, spread, fees, slippage, delay, turnover/capacity and risk limits. A finalized close observed after close cannot be assumed tradable at that same close. No execution instructions or live trades are part of this protocol.

## Existing implementation limits

harness/forecast_review.py validates supplied CSV and scores its own narrow supplied-outcome contract; it does not verify data, venue calendars or rights, and currently lacks this proposed paired point/interval-score protocol. Its valid/exit0 is not source eligibility. outcome_v2.py is synthetic-only in-memory metadata assessment, no numeric scoring/persistence and at most ready_for_human_review. Its observed_at==final-close rule cannot be met by renaming actual retrieval or provider bar-label times. Preserve both contracts; real-data admission and scoring require an accepted new implementation scope.

## Acceptance decisions still needed

1. Trader: exact source/basis/availability/rights path and whether adjusted-series output can legitimately represent the requested price target.
2. Trader: retain the drift candidate for operational comparison or accept a different preregistered method; direction threshold and zero-return tie policy; nominal range level.
3. Lead/Trader: issuance timing, definitive primary metric, worthwhile effect and interval/availability guardrails, development/validation/holdout dates and sample/uncertainty/stopping plan.
4. Lead: separately freeze any real evidence admission/record/scoring implementation; current synthetic harness must not be promoted by removing synthetic guards.

Recommended next deliverable: record those decisions in one dated accepted protocol ticket only after source readiness is demonstrable; before then retain this as a reviewable conditional packet. No new market capture is authorized by this document.

## Evidence inspected

Repository evidence only: plans/2026-10-09/PRSG-81-forecast-model-precision.md; plans/2026-10-09/PRSG-83-forward-outcome-eligibility-harness.md; plans/2026-10-12/PRSG-95-single-history-diagnostic-readiness.md; harness/FORECAST_REVIEW.md; harness/forecast_review.py; harness/engineering/price-prediction/outcome_v2.py. Trader's completed read-only gap assessment supplied by Lead was reused. Proposed choices above are planning judgments, not new measured performance. No tests rerun because no implementation changed.

## Registered Trader review
Conditional planning acceptance returned 2026-10-12. Source-independent decisions accepted; source/basis/rights, issuance timing, sample/effect/uncertainty plan remain gates. Adjusted series cannot be rendered as traded-price targets without accepted mapping. Freeze issuance scale/vintage and reviewed outcome conversion policy; independently rebased endpoints are incomparable. No production policy promotion or capture permission.

## When it is considered done

- [x] PRSG-97-D1: Record a concrete prospective protocol reusing PRSG-81/83, with matched metrics and no retrospective certification.
- [x] PRSG-97-D2: Registered Trader reviews financial semantics and tie policy; Lead incorporates corrections and preserves source/sample gates.
- [x] PRSG-97-D3: Lead validates complete two-file scope and commits the reviewed planning contract.

## Lead decision

Freeze source-independent choices described above as the next research planning contract. No source, live capture, adapter, score implementation or production forecasting is accepted by this ticket. The first usable cohort remains descriptive until the effect/sample/uncertainty plan is justified and frozen. Source comparison is separate onboarding input: existing provider unresolved; alternative providers require separate entitlement, basis and rights review. No purchase or account creation authorized.

Lead accepted the complete two-file planning scope; manifest validation passed. Commitment is recorded by Git history, not evidence of runtime delivery or performance.
