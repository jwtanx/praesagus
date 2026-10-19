# PRSG-131 — Isolate Invalid Snapshot Rows

Type: bug · Modules: financial-data, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-days, estimate) · Impact: high — one invalid row currently prevents all healthy current quotes from the approved standalone discovery prerequisite being retained.

## Why the ticket is created?

At base e1eea779ff3a02876bde2df58835ad7492f6dbbf, ResearchProvider._codes normalizes each snapshot inside one batch loop and lets any invalid-numeric-field abort the entire batch. The separately released exact300 snapshot diagnostic returned300 rows in one713858-byte response, then invalid-numeric-field. Aggregate rejects were high_price zero5, low_price zero5, open_price zero4; other numeric checks reported0 rejects. Their individual overlap/union is UNKNOWN. Do not infer14 affected names or286 healthy rows. No raw numeric values or per-name private IDs were retained by the diagnostic.

Actual discovery evidence: one completed five-call300-candidate run counted1500 raw rows but retained0 normalized quotes although900 screen and300 basic-info rows succeeded. A bad optional OHLC field does not justify accepting zero as a price, nor losing otherwise valid snapshot rows.

## Reproduction / expected behavior

Author a two-code snapshot fixture: both identities/timestamps are valid; the first has positive finite quotes, and the second has open_price=0 (repeat for high/low and last price). Current snapshots() raises invalid-numeric-field and returns no Batch. Expected: unchanged strict normalize_snapshot rejects the bad row, valid row survives in Batch.rows, status=partial, explicit rejection evidence/counts is returned and persisted. All-rejected rows remain partial/rejected, distinguishable from provider-absent rows. Missing optional numeric fields retain their current None semantics; signed negative financial ratios remain accepted. No field is repaired, zero-filled, coerced, nulled to bypass validation or reinterpreted.

## Approach

1. Preserve contracts.normalize_snapshot and numeric/signed_numeric unchanged. Scope row isolation to snapshot normalizer ContractError(kind=invalid-numeric-field) ONLY. Other row errors and unexpected exceptions remain fatal; basic-info and history behavior is unchanged.
2. Reuse Batch metadata, as existing screen row rejection does. Before numeric row processing, preflight ALL returned identities, source timestamp/date and suspension/equity_valid/trust_valid flags; reject duplicate/unrequested/invalid codes, so a rejected row cannot hide later identity failures. Existing envelope/row-shape/budget/JSON/nonfinite/privacy/source-request gates remain fatal. Raw counts include rejected rows and existing request budgets/signing behavior remain unchanged.
3. Proposed closed snapshot metadata: schema_version=1, raw_rows_received, accepted_rows, rejected_row_count, rejected_rows, missing_row_count, requested_codes_count, source_payload_hash. Rejection rows contain exactly code, ordinal, reason=invalid-numeric-field, source=moomoo-rest-snapshot, source_payload_hash, row_sha256 (canonical parsed row hash, not raw-body byte claim), requested_at_ms, retrieved_at_ms and known_at_ms. Keep original source timestamps/vintage; known_at equals actual retrieval. No raw values, full responses, credentials, stock/account IDs or exception text in rejections. Rejected rows <=400 (existing request cap) and serialized rejection list <=256KiB; overflow fails visibly, never silently truncates.
4. Snapshot Batch.missing_codes keeps its existing meaning: requested codes absent from provider response ONLY; rejected-but-returned codes are separately counted. Status partial if any reject or missing; reason snapshot-rows-rejected when any reject, otherwise existing requested-codes-missing. All valid complete response stays success. All-rejected is partial/snapshot-rows-rejected with rows=(), not successful empty or source absence. raw_rows_received = accepted_rows + rejected_row_count; absent count is separate.
5. Collector persists returned snapshot dispositions in state.snapshot_dispositions and coverage.snapshot_dispositions, with bounded collection_issues recording row rejections. Process valid rows normally, without marking the whole provider fatal for visible numeric-row rejection. Remove cached quote entries for rejected OR provider-missing codes in the current requested chunk before fresh updates, so a stale quote cannot masquerade as this run's accepted snapshot. Historical immutable generations stay unchanged; other cached symbols remain. Key snapshot_dispositions by SHA256 of the canonical requested chunk-code list. Snapshot disposition map resets for an online run, remains attributable cached evidence offline. Do not change selection, history release or eligibility policy.

## Choices

Quarantine the entire numerically invalid row instead of weakening optional-price validation. Provider-only isolation would lose rejection metadata in collect_into and permit stale quote fallback, so the smallest complete proposed implementation is four source/test files. No need for a new exception hierarchy, registry, client, dependency, CLI, artifact type or numerical policy. The generic numeric reason intentionally does not invent a field-level diagnosis absent an existing normalizer signal; the separate aggregate diagnostic supplies the observed field counts. Passing fixtures or retaining more quotes does not prove currency, currentness, units, ETF classification, valid100universe, training quality or profitability. No new provider request/retry is authorized by this ticket.

## Frozen scope — accepted by Lead before coding

Base e1eea779ff3a02876bde2df58835ad7492f6dbbf. Engineer owns only scripts/stock-research/provider.py, scripts/stock-research/collect.py, tests/test_stock_research_provider.py and tests/test_stock_research_universe.py. Lead reviews these two ticket records before accepting the implementation scope. Lead explicitly accepted the four-file implementation scope after the specification and path validation passed; no provider call or integration release follows by implication. Protect all connectors/credentials/signing/TLS, ingest, public artifacts, strict contracts.py, config/storage/universe policy, model/train/data/features and unrelated.DS_Store. No provider/network/credential/history/discovery/model/trading work. Focused checks are recorded below.

Actual source pointer (private, not committed raw data): forecast-report-20261019/snapshot-counts-221736/intakes/2026-10-19_222009_052040 under private Lead state. This ticket records only aggregate observations supplied by Lead; no private code-to-failure mapping is invented.

## When it's considered done

- [x] PRSG-131-D1: Mixed/all-valid/all-rejected/absent snapshot fixtures preserve strict numeric rejection, healthy rows, source hashes, counted budgets and separate bounded dispositions; basic/history and signed-value behavior unchanged.
- [x] PRSG-131-D2: Collector state/coverage/issues retain rejection evidence and remove rejected/missing current-chunk cached quotes; unaffected symbols and immutable prior generations survive. Fatal envelope/JSON/nonfinite/privacy/shape/duplicate/unrequested errors still abort with no partial accepted Batch escaping; no extra request/retry/signing.
- [x] PRSG-131-D3: Lead independently reviews complete diff, focused regressions, source privacy and required delivery hooks before integration. No actual100universe/model/public-source readiness inferred.

Regression cases include bad row first/middle/last, zero optionalOHLC/last, negative/type/bool quote, missing optional accepted, signed negative financial accepted, overlapping invalid fields counted once per row, all-rejected versus all-absent, valid300+bad rows within requested cap, duplicate/unrequested later than a bad row, nonfinite envelope, malformed date/time/flags, rejection-byte overflow, current-chunk stale cache clearing and offline provenance. New tests assert rejection rather than weakening old invalid-value expectations.

## Engineer verification — pending independent Lead review

The four-file implementation preserves strict normalizers, catches only snapshot invalid-numeric-field ContractError, preflights identities/time/date/flags before quarantine, persists bounded dispositions and removes rejected/missing current-chunk stale quotes. First focused run265passed; final adds first/middle/last positioning and later-row source-fatal regressions. Final269passed; exact timing and frozen hashes are in private handoff. No initial test failure or provider call. D3 remains pending.

## Lead acceptance

Independently reviewed the final frozen six-path scope and complete diff;269 focused tests passed in3.20s. Strict numeric validation, source/time/flag/identity fatal preflight, rejected versus absent accounting, bounded provenance, stale-cache removal and offline/immutable-generation behavior accepted. Mandatory commit/push hooks gate delivery; their actual results remain in the private delivery receipt. No actual followup provider capture,100-name eligibility or model promotion is claimed.

## Findings

The one-call actual diagnostic examined300rows and found zero open/high/low values in4/5/5 rows respectively; overlap is unknown. The prior normalizer aborted the full batch. Independent269 regression checks passed in3.20s, including strict rejection and cached-quote removal. The first full commit hook reported3433passed and one brief-quality failure; this authored decision context repairs that failure without changing tests.

## Tradeoffs

Rejecting an entire invalid row preserves strict quote semantics but leaves explicit coverage gaps. Keeping valid rows improves usable coverage without establishing source eligibility, twenty ETF coverage or model quality. A provider-only fix would leave silent stale-cache fallback, so collector provenance and cleanup are required too.
