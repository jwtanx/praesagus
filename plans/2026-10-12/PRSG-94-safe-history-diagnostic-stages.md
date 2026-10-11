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

- [x] PRSG-94-D1: Trusted fixed diagnostics preserve failure/privacy/acceptance boundaries and strict legacy/v2 compatibility.
- [x] PRSG-94-D2: Meaningful deterministic privacy, framing, propagation and CLI regressions pass; docs accurately describe ephemeral limits.
- [ ] PRSG-94-D3: Lead independently reviews all owned paths, preservation, test evidence and authorized commit/push delivery.

## Next gate

No live request in this ticket. After independent review, a future Trader probe needs a separately frozen single-job plan and fresh resources. Keep unsupported targets Unrated. No performance or precise earlier failure claim.


## Engineer evidence — 2026-10-12 MYT, uncommitted patch

Implemented nine trusted fixed stages using original normalization guards. Generic error text, failure categories, rejected-body disposal, store DDL/version/reasons, public output and report behavior remain intact. Stage extraction requires the exact controlled error type and allowlist; arbitrary attributes/subclasses are ignored. Decode/security failures share one stage. New replies use exact v2; exact legacy v1 parses with null stage. Invalid stage/frame combinations become bad-frame/null, including injected supervisor replies. Cleanup stops and clears stage; storage/clock replacements clear it; run-budget precedence retains only the earlier rejected job's stage. CLI default keys are unchanged; --diagnostics adds explicit private schema_version 2 and nullable per-outcome stage. No automatic persistence.

Exact focused command from Verification: **675 passed in 4.27s**, exit 0, approved Python 3.11 with bytecode/cache writes disabled. Baseline after initial production patch: 527 existing tests passed; final suite adds 148 parameter-expanded regressions. The three protected core/live/report test files were not edited. No actual provider, Keychain, credential or private market-store access; only invented mocks/fixtures and temporary synthetic stores. Tests are offline behavior evidence, not live success/authentication/entitlement or PRSG-90 cause evidence.

### PRSG-93 authored matrix replay mapping

These requirements now map to executed checks (test function names are in the two accepted test files, except existing unedited core/report checks):

| Matrix requirement | Executed coverage |
|---|---|
| 1 Bad UTF-8/JSON/duplicate/nonfinite | diagnostic_cases; test_history_trusted_stages_generic_errors_and_store_disposal |
| 2 Nested/URL/PEM/known secret | Same cases; test_stage_worker_discards_body_and_propagates_private_outcome |
| 3 Bad envelope/types/outer keys | diagnostic_cases; unchanged strict envelope guards |
| 4 Nonzero typed code with private message | test_stage_worker_discards_body_and_propagates_private_outcome |
| 5 Nonzero code before invalid data | diagnostic_cases with ret_code 1234567/data null |
| 6 Bad history container/unknown key/pagination scalar | diagnostic_cases; no allowlist expansion |
| 7 Bad list/count/scalar row | diagnostic_cases and worker stage cases |
| 8 Missing metadata individually/combined | diagnostic_cases |
| 9 Invalid/null/bool/string/bounds/calendar/overflow | diagnostic_cases |
| 10 Date/offset mismatch | store and worker stage cases |
| 11 Offset/day-edge/nonmidnight positives | test_history_diagnostic_local_boundaries_remain_accepted; existing PRSG-92 edges |
| 12 Range/duplicates/missing/nonpositive close | diagnostic_cases; existing history checks |
| 13 Core-only negative volume/optional OHLC | test_stage_worker_discards_body_and_propagates_private_outcome |
| 14 Empty valid history | test_stage_success_empty_nonhistory_and_http_null |
| 15 Unknown/forged exception | test_stage_unknown_exception_never_trusts_arbitrary_attributes |
| 16 Nonhistory/HTTP/transport/credentials | test_stage_success_empty_nonhistory_and_http_null; existing sanitization checks |
| 17 Legacy v1 success/failure | test_stage_frame_all_fixed_values_and_v1_legacy; test_stage_legacy_success_frame_and_positional_dataclasses |
| 18 Every v2 fixed stage | test_stage_frame_all_fixed_values_and_v1_legacy |
| 19 Unknown/unhashable/oversized/version/key/header | test_stage_frame_mutations_fail_closed_and_supervisor_clears; test_stage_missing_key_duplicate_header_body_and_parent_screening |
| 20 Contradictory/missing stage/nonempty failure body | Same parser tests; test_stage_encoder_rejects_impossible_contract |
| 21 Framing/digest/size/UTC/retry | Existing test_frame_fail_closed plus v2 mutation tests |
| 22 Parent successful-body screening | test_stage_missing_key_duplicate_header_body_and_parent_screening; existing unsafe-body checks |
| 23 Injected stage/failure/type inconsistencies | test_stage_injected_supervisor_unknown_stage_becomes_bad_frame; test_stage_injected_supervisor_contradictions; test_stage_injected_reply_bounded_types |
| 24 Storage/clock/cleanup/run-budget precedence | test_stage_replacement_precedence_and_no_leak_to_later_jobs; existing stopping/budget checks |
| 25 Default/opt-in CLI and missing synthetic credentials | test_stage_cli_opt_in_shapes_exit_codes_and_privacy; parameterized real CLI subprocess missing-credential check |
| 26 Store re-query and positional/report consumers | test_history_trusted_stages_generic_errors_and_store_disposal; positional dataclass check; unedited tests/test_daily_quote_report.py |
| 27 First trusted guard/no additional diagnostic decode | test_history_stage_first_guard_and_single_decode; worker unknown test counts one screening call |

Extra bounded-body and legacy-injected checks cover bytes/empty/oversize responses and null-stage legacy collection. Invented canaries are asserted absent from rejected IPC, repr and CLI stdout/stderr. Rejected attempts have zero history rows, null raw_hash and no archive. Secret and malformed decode errors share a stage.

Complete diff contains only the six accepted implementation/docs/test files and two PRSG-94 evidence files, including Lead's prior scope commit. Protected primary projection SHA256 remains b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f. Hooks remain configured as .githooks and praesagus.testPython uses the approved venv. Engineer has not committed or pushed. Lead independent review/delivery PRSG-94-D3 remains pending; no live request authorized.
