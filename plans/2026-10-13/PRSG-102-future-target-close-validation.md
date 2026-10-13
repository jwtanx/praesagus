# PRSG-102 Future target close validation

Type: bug | Modules: financial-data,market-research | Owner: Engineer | Priority: P1 | Effort: S 1–2person-days | Impact: high

## Problem and expected behavior

The compact validator rejects a future US close on the same calendar date as issuance. Do not shift issuance or invent another target date. Use a frozen venue close instant only for the accepted raw-close SPY/h1 method; preserve legacy date-only guards for all other methods. Human authorized continuing actual price-target delivery; Lead accepts this bounded integration repair.

## Frozen scope and exact contract

Base and seven owned paths are in the matching manifest; all other paths protected, including dirty daily_report_projection.py. No artifacts, provider requests, new source/method, current forecast issuance or renderer changes.

Add forecast_time_basis to scenario report_fields (null when withheld). Generated value has exactly schema_version:int1, method_id:spy_raw_close_drift_lognormal_h1_v1, venue_timezone:IANA, calendar_version:accepted calendar version, reference_close_at:aware instant, target_close_at:aware instant. Derive from the existing reviewed calendar; preserve existing seven-key forecast_basis. Include timezone/calendar_version in private audit and validate mapper consistency. No private IDs/hashes/raw evidence in this public contract.

For the exact existing scenario MODEL only, require this complete contract and existing positive observations20/horizon1/next_session. Validate reference_close_at<=issuance<=report cutoff and target_close_at>issuance; reference and target venue-local dates match existing reference_close_date and target_date, reference session before target session. Calendar version nonempty bounded ASCII ID, valid IANA zone, exact types/keys and aware timestamps. This verifies internal linkage, not authenticity/calendar completeness; those remain reviewed-source gates. Reject injected/malformed time contracts on any other method; preserve legacy date-only behavior when absent. Do not weaken public snapshot, secret/provenance, target ordering or other guards.

## When it is considered done

- [x] PRSG-102-D1: Exact time contract implemented and reviewed.
- [x] PRSG-102-D2: Same-date future close passes, past/equal closes and malformed/mismatched contracts fail; legacy regressions remain.
- [x] PRSG-102-D3: Lead independently reviews complete scope and delivers with real-input readiness separately stated.

## Checks

ApprovedPython -m pytest -q tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py. Cover offset representations, venue-local dates/DST/early close, unknown zone/calendar version, contract tampering, future reference, target equality/past, cutoff, wrong method and absent contract. Actual viewer replay must still accept numeric target/range. Tests authored only; no real forecast/performance claim. Full hooks at delivery.


## Engineer frozen implementation detail — 2026-10-13 MYT

Reuse the accepted six-field public time contract exactly, plus venue_timezone/calendar_version in the private audit. Shared pure validate_forecast_time_basis(row, report_cutoff) in the scenario module checks the exact MODEL,20observations/h1/next_session, closed keys/builtin types/IANA/ASCII version and linked aware close instants/venue dates. The compact validator calls it before rated-row skipping, so nonnull injected contracts on other methods are rejected even on Unrated rows; null withheld contracts behave as absent. Existing reference/source/numeric/public guards remain. Only the accepted MODEL skips the legacy target-calendar-date rule after passing this linked-instant check. Existing cutoff datetime from the validator preserves its precision; public close strings follow the scenario's aware millisecond-or-less syntax. Mapper cross-checks public zone/version/instants against private audit, without exposing private IDs or hashes. No authenticity/completeness claim follows internal linkage.


## Engineer tested handoff — 2026-10-13 MYT

Implemented the exact six-key forecast_time_basis and private timezone/calendar-version audit linkage. Shared pure validation reserves nonnull contracts for exact raw-close SPY/USD MODEL with20observations/h1/next_session; malformed linkage rejects before rated skipping and in full/noncompact report validation. Same-date targets pass only with future venue-close instants; legacy models retain their date-only rule. Mapper verifies public time/zone/version against private audit and preserves all other row fields. No timestamp shifting, source approval or protected projection/renderer change.

Exact executed command (cwd /Users/jwtan/.codex/worktrees/prsg89-prediction-chip/praesagus):

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' /Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py
260 passed in1.04s; exit0; no skips
```

Earlier258 run passed; added noncompact bypass regressions before final260. No failing test run for this ticket. Actual existing JS predictionState replay still executed and accepts generated direction/target/range. Full authored compact scenario with same-date/future-close passes; equal/past target, future/mismatched reference, malformed/extra/bool/version/unknown-zone/calendar/offset/naive/method/count/horizon/cutoff contracts fail. Legacy date-only and private/public snapshot guards remain tested. Mapper public/private tampering rejects; equivalent aware offset representations pass. Prior venue-local DST/early-close and all source-calculator rejection regressions run unchanged.

Tests are authored fixtures, not actual history intake, current prediction issuance, live browser rendering or public delivery. Internal time linkage does not prove provider authenticity/calendar completeness. Real-source readiness remains separate. D3 pending Lead independent review/integration/push. Complete actual seven-path scope, manifest/whitespace/doc-link checks accompany returned handoff. No commit or push.

## Lead acceptance

Lead independent seven-path review:260focused passed1.08s including actual Node viewer. Time linkage accepted; no real history/source admission or current report issuance claimed.
