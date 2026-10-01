# PRSG-27 — Offline session metrics

Type: feature · Modules: financial-data, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium-high

Created2026-10-01 MYT. Frozen base e9ffeda962ec289dab6adb0070a358a5ffd205fd. Lead accepts synthetic-only deterministic metric scope from PRSG-24; no acceptance of predictive thresholds or live rights.

## Objective and boundary
Implement pure standard-library calculations in harness/session_metrics.py with tests/test_session_metrics.py and harness/SESSION_METRICS.md. No provider/store integration yet; preserve evidence_store.py and forecast_review.py. Input explicitly synthetic, one stable instrument/venue/currency and comparable adjustment basis, explicit source-vintage selection by caller, ordered unique completed regular-session daily bars, aware availability/known timestamps and decision cutoff. Caller supplies an ordered expected-session list; it is fixture data, not a verified exchange calendar.

Compute gap=open/priorclose-1, close_return=close/priorclose-1, intraday=close/open-1, range=(high-low)/priorclose and relative_volume=currentvolume/median(previous20sessions). Fractions not percentages. Volume requires at least15 valid previous observations in the20 scheduled sessions; zero median -> unavailable. Missing history stays unknown with reason. No inferred stale replacement for missing immediately prior expected session. No current/future rows enter historical baseline.

Input contracts: finite positive OHLC with valid ordering, finite nonnegative volume; completed/regular explicit. Reject duplicate/conflicting versions and multiple source vintages per session rather than max(ingestionrevision). Reject unavailable/future rows at cutoff. Preserve every supplied target/control session with status/reason, not only movers. Currency/basis/instrument mismatch rejected. Split/dividend/other-action uncertainty, shortened session and halt/reopening flags quarantine the affected calculation rather than applying guessed adjustment; already comparable caller-supplied clear-action fixtures may calculate. No return forecasts, mover thresholds, annualization, causality, entity matching, classifiers, network, databases, deps, skill edits or public data.

## API and tests
Document one pure function accepting validated fixture envelope, returning versioned result rows with input provenance references, metric values nullable, status and reasons. Malformed envelope rejects visibly; per-session unavailable/quarantined states remain rows. Exact API details Engineer chooses within scope.
Run python3 -m pytest -q tests/test_session_metrics.py tests/test_evidence_store.py tests/test_forecast_review.py.
Tests: SYNfixture priorclose100 open104 close106 yieldsgap.04 closereturn.06; intraday106/104-1, range(high-low)/100. Falling and ordinary controls preserved. RVOL2 fromcurrent200/prior median100 excludescurrent. Minimumhistory/zero-volume, missing prior scheduled session, duplicate/out-of-order source revisions, future availability/knowledge, missing/naive time, NaN/invalidOHLC, currencies/basis mismatch, split/uncertain action and shortened/halted fixtures quarantined. All values synthetic, no exchangecoverage claim.

## Frozen scope and handoff
Allowed:this spec/manifest,harness/session_metrics.py,harness/SESSION_METRICS.md,tests/test_session_metrics.py. Preserve all other files. No commits/push by Engineer; update test/progress evidence and return exact diff/results. Gate/base/scope changes require Lead. Lead reviews and integrates separately.

## When it's considered done

- [x] PRSG-27-D1: Pure metrics, provenance and unavailable/quarantine states pass deterministic fixture tests and independent Lead review.

## Progress

Lead accepted2026-10-01 MYT after full code/docs/fixture inspection,160 focused tests and383 fullsuite tests (5 existingwarnings). No provider/calendar/vintage attestation or predictive performance implied. Earlier pending/handoff statements retain checkpoint history; current acceptance is complete.
Lead accepted bounded scope; implementation/checks pending.


## Engineer handoff evidence

Implemented pure `calculate_session_metrics(fixture)` with versioned rows for every explicit target/control session. Stable instrument/venue/currency/basis and caller vintage selection are required; duplicate/conflicting/out-of-order session versions reject instead of guessing authoritative truth. Gap/close return/intraday/range are fractions. RVOL uses only eligible previous 20 expected slots, minimum 15, excluding current/later/quarantined/unavailable history. Missing immediate prior never substitutes a stale observed close. Missing target rows, incomplete/future data and action/session quarantine remain explicit with nullable values/reasons/provenance. Current quarantine conservatively blocks all metrics; prior quarantine blocks dependent price comparisons while independent intraday/volume may remain. No provider/store/calendar/action-adjustment integration added.

Frozen command `python3 -m pytest -q tests/test_session_metrics.py tests/test_evidence_store.py tests/test_forecast_review.py`: **160 passed in 0.45s**. Includes deterministic formula/control, history count/window/zero-median, missing prior/target, future knowledge/availability, malformed OHLCV/time, currency/basis mismatch, duplicate/source-vintage order, split/dividend/uncertain/shortened/halted/reopening and synthetic MY timezone cases. Documented example replay passed. Full suite not run; integration scope unchanged. Both protected evidence/forecast modules unchanged from frozen base.

All five exact owned paths validated, whitespace clean; frozen base/scope/check definitions and acceptance gates unchanged. No staging, commit or push. Independent Lead review and acceptance remain pending. Synthetic expected-session lists, action-clear/comparable-basis and source-vintage selection are caller declarations, not exchange/source attestation. No mover threshold, causality, forecasting, live provider or entitlement claim.
