# PRSG-129 — Explicit Malaysia History Dialect

Type: feature · Modules: financial-data · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high — test a declared interpretation for the observed100-row Malaysia metadata discrepancy without altering existing data semantics.

## Why the ticket is created?

The separately released BMS.1155 count diagnostic returned100 hours-only matches,0 minute matches,0 neither and0 uncheckable; all rows remain rejected. This supports a hypothesis, not proof of vendor units or actual offsets. The current pipeline has no explicit opt-in research dialect for evaluating it.

## Approach

Add optional closed history job/plan item key normalization_dialect=bms1155_hours_hypothesis_v1 only for literal BMS.1155, existing end-only raw daily100 request. Bind dialect into job digest/context but keep HTTP bytes unchanged. Missing token preserves default minute semantics. Introduce normalization5 exclusively for explicit dialect; US/current4 and legacy3/4 remain unchanged. Reject unknown/cross-market tokens, version downgrade/substitution and legacy-frame replay of opt-in jobs.

Normalization5 reuses closed envelope/secret screen and all date/end/future/duplicate/finite-price gates. Preserve raw time_key/date/time_zone unchanged. Under explicit dialect only, validate integer hours in[-12,14] and effective offset within existing minute bounds, compute separate effective_offset_minutes=raw_zone*60, then require exact date relation. No fallback or automatic choice between interpretations, even if both match. Store explicit dialect/unit_basis=operator_selected_hypothesis_not_vendor_confirmed, raw-unit label, effective offset and inference-quality flag in hashed metadata/payload; integrity replay must apply the same version/context, never reinterpret old records.

## Choices

Keep frame3 shape, worker input1, database schema1 and receipt envelope1 where compatible. Bind norm5 iff explicit dialect through encoder/parser/parent/store; old frames1/2 may replay only old jobs. Extend existing count-only diagnostic eligibility to norm5 without changing its schema1/2 meaning. Return a concrete scope/version finding before expansion. No provider query, CLI or numerical/public path changes.

## Findings

Official history documentation describes offset minutes; the new counts only show that a competing hours arithmetic matches dates for100 rows. Actual offsets were discarded. Normalization success under a declared hypothesis does not establish actual source units, correct instrument/currency/calendar/session-finality/actions/rights or forecast suitability. All remain separate actual-source admission obligations.

## Tradeoffs

An explicit opt-in/versioned transformation is narrower than a new raw quarantine/projector and avoids silently weakening existing checks. A trusted date-plus-venue-close projection would instead require independent source session-label proof and a new quarantine path. This ticket uses mocked fixtures only; no actual capture or admission is released.

## Frozen scope

Base f0a201b07bb45874c00c5193a796cdbd848ad813. Engineer exclusively writes ingest/market_collector.py, ingest/private_market_store.py, connectors/moomoo_rest.py and their three test files. Lead owns records. Protect connectors/signing/credentials, scripts, model/forecast code, artifacts, dependencies and unrelated.DS_Store. No provider requests, extra raw rejection retention, automatic evidence projection, source permission assertion or model promotion.

## When it's considered done

- [x] PRSG-129-D1: Explicit opt-in/version5 hours-hypothesis mechanics and hashed store replay pass; missing opt-in/default minute behavior and all previous versions/US tests remain unchanged.
- [x] PRSG-129-D2: Negative offsets/limits, malformed/future/end/duplicate/secret failures, cross-job/version/token substitution and count-only failure diagnostics pass; Lead independently reviews and delivers. Actual capture and source admission remain separate.

## Scope amendment — repeated connector validation

First mocked run587passed/2failed: an accidental snapshot quality branching regression was repaired; the remaining worker success failure revealed an independent minute-only check in MoomooRESTConnector.history_kline. Lead authorizes exactly connectors/moomoo_rest.py and tests/test_moomoo_rest.py in addition to the four original paths. Add optional normalization_dialect keyword defaultNone, accepted only for the same explicit BMS.1155 raw daily100 contract. Worker passes it only for opted-in jobs. Keep default behavior, signing/HTTP bytes and raw result fields unchanged; apply the same explicit hours-hypothesis relation when selected. No swallowing connector errors or bypassing its validation. Secure transport remains protected. Final configured checks include connector regressions.

## Lead acceptance — 18 October

Independent six-path review and final configured tests: 793 passed in 3.49s; Engineer793 passed3.51s. Scope amendment and initial587pass/2fail retained above. Explicit opt-in token is digest/version-bound at worker/parser/parent/store; default minute semantics and old versions remain. New version5 retains raw metadata plus separate inferred-unit labels/effective offset and quality flag; replay recomputes matching context. Connector receives keyword only for opt-in; HTTP/signing bytes and default auxiliary checks remain. Frozen handoff patch SHA256 63458d5e3d2a050b7f37f7bfb2526a6470ffceb2e6e513e9ea92e4c38a78321e. Actual capture, unit confirmation, source-use permission, source financial admission and forecasts remain unfulfilled/separate; no model promotion. Required delivery hooks apply.
