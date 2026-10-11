# PRSG-94 — Add safe history diagnostic stages

Type: feature · Modules: financial-data, connectors, docs · Owner: Engineer · Priority: P1 · Effort: S (0.5–1.0 person-day estimate) · Impact: medium-high — make future rejected history intake actionable without retaining rejected responses; no predictive improvement established.

Created 2026-10-12 MYT. Status: in progress; accepted continuation of bounded forecast-input readiness. Frozen base: 0c90de58912f0c45f7742320de67a58183cb5dae. Lead owns independent review/integration. Reuse implementation skill and the independently accepted PRSG-93 decision.

## Problem and outcome

The existing collector reports invalid-response but discards rejected response bodies. Preserve that privacy boundary and failure semantics while attaching a trusted fixed validation stage to future history rejections. This cannot reconstruct PRSG-90 or establish authentication, entitlements, rights or forecast eligibility.

## Frozen implementation contract

Implement PRSG-93's reviewed contract exactly: fixed ASCII stages decode-screen, envelope, provider-rejection, history-rows, metadata-missing, metadata-invalid, date-relation, core-validation, unknown. Annotate the original trusted guard once, keep generic MarketStoreError text, accept annotations only from controlled errors and exact allowlist. Combine syntax/security failures, never expose actual input keys/values, row indices, messages/codes, identifiers, paths or exception text. Preserve rejection order and all existing metadata/date/row/pagination requirements. No second decoding/screening, fallback metadata or salvage.

Encoder emits exact v2 eight-key frames; parser accepts exact v1 seven-key legacy frames with null stage and strict v2. Nonnull stage only for history + HTTP200 + invalid-response + empty body; v2 such rejection requires an allowlisted stage. Other cases null. Malformed/unknown/unhashable/oversized/contradictory stage frames fail as bad-frame/null; preserve digest, sizes, time, retry and parent success-body validation. Append default fields after existing positional fields. Validate injected supervisor replies too. Clear stage on cleanup/storage/clock replacement; retain only its own invalid-response outcome when current run-budget precedence permits. Atomic worker/parent rollout; old parents reject v2.

Default CLI output remains exact current keys/exit semantics. Add explicit --diagnostics yielding private schema_version 2 with nullable stage per outcome. Diagnostics remain ephemeral, no automatic persistence/store DDL/version change. Document compatibility and limits. Current public reports, forecast labels/targets/confidence, financial methods and report consumer behavior unchanged.

## Scope and ownership

Engineer edits only the four production/docs and two test files in the manifest, plus evidence in these two ticket files. Work in the existing isolated managed checkout; preserve primary unrelated projection. All paths outside the allowlist are protected. No core connector edit, new dependency/client/script, credentials/Keychain/private store/provider/network requests, live fixtures, actual secrets, subagents or further probe. Ask Lead before widening scope. Lead handles commits/push and completion acceptance; return uncommitted review-ready patch.

## Verification

Use invented privacy canaries and deterministic mocks; replay all 27 authored PRSG-93 matrix requirements. Cover trusted guard precedence, malformed/security bodies, absent/invalid/date metadata, row/core rejection, legacy/v2 framing, forged/unhashable stages, parent body revalidation and injected replies, storage/clock/cleanup/run-budget precedence, default/opt-in CLI shapes/exit codes, no rejected archive/rows/raw_hash, and positional/report compatibility. Assert canaries absent in bytes/repr/stdout/stderr. Matrix is a requirement, not previous passing evidence.

Exact focused check (cwd repository): PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider" /Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_private_market_store.py tests/test_market_collector.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py tests/test_daily_quote_report.py. Preserve three unedited regression files. Validate manifest against every complete diff path. Required hooks remain enabled.

## When it's considered done

- [ ] PRSG-94-D1: Trusted fixed diagnostics preserve failure/privacy/acceptance boundaries and strict legacy/v2 compatibility.
- [ ] PRSG-94-D2: Meaningful deterministic privacy, framing, propagation and CLI regressions pass; docs accurately describe ephemeral limits.
- [ ] PRSG-94-D3: Lead independently reviews all owned paths, preservation, test evidence and authorized commit/push delivery.

## Next gate

No live request in this ticket. After independent review, a future Trader probe needs a separately frozen single-job plan and fresh resources. Keep unsupported targets Unrated. No performance or precise earlier failure claim.
