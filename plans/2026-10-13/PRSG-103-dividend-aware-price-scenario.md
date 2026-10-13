# PRSG-103 Dividend-aware research price scenario

Type: feature | Modules: financial-data,market-research | Owner: Engineer | Priority: P1 | Effort: S 1–2person-days | Impact: high

## Accepted purpose

Human requires report target price/range and next-session predicted movement, continuing existing precision direction. Lead accepts Trader’s bounded cash-return research variant; no predictive promotion. Existing action-free SPY method remains unchanged and rejects dividends. Actual source capture/admission and publication remain separately reviewed.

## Frozen scope

Seven paths/base in matching manifest. Protected collector/connectors/artifacts/projection/skills/harness untouched. No provider/credential calls, source approval, report publication or generic action engine. Engineer proposes exact closed keys/types/interfaces here before code; Lead confirms exact contract.

## Financial contract

Exactly21 consecutive split-free raw USD SPY closes ending latest completed reference,20 adjacent returns, sample SDddof1,h1,z1.959964. New fixed method identity; cash-return r_i=log(C_i+D_i)-log(C_previous). D_i is verified grossUSD cash per share on EX-date, positive finite; zero only with complete reviewed event coverage. Original cash event/source/known-at evidence preserved and hash-bound, with future-known information excluded. Payment date cannot substitute ex-date. Ambiguous/noncash/split events and any target distribution/basis-change withhold. Current raw USD reference C_ref anchors median C_ref*exp(mu) and range C_ref*exp(mu +/-z*s). Historical cash adjustment is an authored end-session reinvestment proxy, not vendor adjusted-series equivalence. Direction sign(mu), no indicator/count/quote dependency. Low qualitative confidence, uncalibrated range, no accuracy claim. Preserve all existing seven input gates and admission/fixture safeguards.

Extend exact forecast overlay/time linkage and mapper to recognize the two frozen methods while preserving old behavior and evidence binding; no permissive model-string bypass. Fixture output cannot be published. Generated actual overlay still requires independently accepted evidence and report validation. First source amount independently verifiedUSD1.888834 on18Sep2026, but complete actions/current21closes still unavailable; tests use authored fixtures only.

## When it is considered done

- [x] PRSG-103-D1: Lead accepts exact interface/source-event binding.
- [x] PRSG-103-D2: Exact cash-affected return corrected; wrong-date/unit/future/unknown/split/target events withheld; original method regressions retained.
- [x] PRSG-103-D3: Independent Lead review and delivery with actual readiness separately stated.

## Checks

ApprovedPython -m pytest -q tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py. Preserve actual existing JS chip guard replay and public venue-time validation. New exact return/formula tests plus altered admission/event tamper/unknown amount/completeness/sourcepublication/known-at/DST/gap-preservation/fixture-refusal controls. Full hooks at delivery.

## Lead scope amendment

Added existing validate_report_json.py and tests/test_daily_report.py to seven allowed paths so exact second method/time-contract identity is recognized; preserve legacy/original guards. No collector/projection/artifact changes.

## Frozen exact interface (Lead confirmed 2026-10-13)

V1 evidence, admission, raw method and audit shape remain unchanged. V2 evidence/admission retain the closed top-level and seven-gate keys; only exact method `spy_cash_return_drift_lognormal_h1_v1` is accepted. All original method parameters remain fixed. Public model is `Cash-return drift/lognormal median scenario v1 (uncalibrated)`. V2 private audit adds `method_id`; time contract remains schema1 with exact corresponding method identity. Public validator recognizes exactly the two frozen models after linked-time validation.

V2 events have exactly `event_id`, `effective_date`, `kind`, `amount`, `currency`, `unit`, `source_url`, `source_sha256`, `source_publication_at`, `retrieved_at`, `ingested_at`, `known_at`. Effective date means EX-date, never payment date; kind is cash_distribution; amount is positive finite gross USD per share, excludes bool; currency USD and unit gross_cash_per_share. Unique ASCII event IDs, safe source URLs/digests and accepted calendar session dates required. Publication may be null; if supplied it must be aware and <=retrieved. Actual retrieved<=ingested<=known<=coverage-known<=review<=issuance is required. No publication time is invented.

Whole evidence and action gate bind original events/timestamps. Complete means independently reviewed AS-OF declared-event coverage, not guaranteed absence of future/unexpected events. External admission references retain review procedure/window/sources/failures/limitations. Missing coverage/unknown amount/noncash/split/basis/target-session events withhold. First-close EX-date events remain validated/bound but contribute no return because preceding close is outside window. Distinct same-date events sum deterministically. V2 scenario states end-session reinvestment proxy and residual source-index/revision/unexpected-event risk. No new source calls, acceptance or numeric report issuance.

## Engineer evidence

Lead confirmed exact v2 contract and nullable publication on 2026-10-13; seven-path amendment accepted. Focused checks: approved Python3.11 `-m pytest -q tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py`: **311 passed in1.23s**, no skips; existing Node viewer guard executed for both methods. `git diff --check` passed. Initial new unrated test retained numeric targets and hit earlier null-target guard (1failed/310passed); fixture corrected without changing or weakening production guards, then full focused set rerun passed. Original260 regressions passed before new tests. Authored fixtures only; actual current eligible history/target and report generator integration remain unavailable. Independent Lead review/full hooks pending; do not mark complete.

## Lead independent acceptance

Lead independently reviewed seven owned paths and exact cash/event/time/mapper behavior;311focused passed1.21s, actual Node guard for both methods. No real history capture or current report issuance claimed.
