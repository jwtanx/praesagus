# PRSG-93 — Define safe history rejection diagnostics

Type: spike · Modules: financial-data, connectors, docs · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.2 person-day, estimate) · Impact: medium-high — makes the observed intake blocker actionable without retaining untrusted responses; no coverage or predictive gain is established.

Created 2026-10-12 MYT. Status: complete, independently accepted by Lead under the human's continuation of forecast-input readiness. Frozen base: `74fc1c36a66c2880a0bc38949b3afe8ebb7cff16`. Engineer performed bounded read-only technical review; Lead owns this ticket and acceptance. Repository write scope is only this spec and its manifest.

## Question and timebox

Within 15–20 minutes, define the smallest replayable diagnostic contract that can distinguish a future history rejection's validation stage using only trusted fixed categories. PRSG-90 persisted a failed attempt but discarded the screened body; PRSG-91 found unresolved example/envelope ambiguities, and PRSG-92 fixed a separate date-consistency guard. None identifies the actual earlier rejection. A repeated request with the same broad failure would add little evidence. No new live request is authorized by this spike.

## Accepted read-only scope

Inspect the existing store normalization errors, collector worker frame/parse/outcome/CLI serialization, core errors and consumers/tests. Compare: extending fixed failure categories versus a separate bounded stage enum while retaining existing failure semantics. Explain framing/version/compatibility, bounded serialization, malformed-frame handling, CLI consumers, rejected-body disposal and whether persistence needs any change. Prefer no existing-store migration and no public report/schema change. Every returned category must come from an explicit allowlist; unknown errors stay generic.

Distinguish malformed JSON/envelope, logical provider rejection, missing required history metadata, bad date/offset relationship, invalid rows and later core validation only where the checked code can establish the stage. Do not expose provider return-message/code values, field names taken from input, row values, identifiers, exception strings, response bodies, credentials or operational paths. Category precision must not imply authentication/entitlement assurance or a particular cause in PRSG-90.

Engineer returns a concrete proposed contract, exact minimal implementation/consumer/test paths, compatibility implications and authored failure-case matrix. Private in-memory deterministic design examples are allowed; label them synthetic. No repository implementation/test changes, credentials/Keychain/private store/provider access, ad hoc client, additional data request, schema weakening, inferred metadata/pagination whitelist, forecast/method/confidence/ledger/report changes or subagents. Existing privacy/security/temporal/quota controls remain binding.

## When it's considered done

- [x] PRSG-93-D1: Review current error/frame/output consumers and compare bounded diagnostic alternatives with exact compatibility and privacy limits.
- [x] PRSG-93-D2: Return a fixed-category contract and meaningful malformed/secret/unknown/history-stage replay matrix, plus exact proposed implementation/test paths.
- [x] PRSG-93-D3: Lead independently accepts a concrete next scope or blocker and verifies protected files unchanged; no live request or repair occurs in this spike.

## Delivery and next gate

Checks are contract review, failure-matrix review, preservation and Lead decision. Engineer's repository write set is empty; sanitized findings belong in the approved private Lead context. Lead alone updates these two ticket files. Any implementation requires its own accepted frozen scope. After implementation and independent privacy/regression review, any future data probe needs a separately frozen single-job plan and fresh resources using the existing collector; this ticket grants none. Completed diagnostics still do not establish comparable completed prices, source availability, rights or forecast eligibility.

## Independently reviewed decision

Lead inspected the current exact version-1 seven-key frame, parser, worker exception mapping, outcome constructors and CLI/report consumers. Extending failure strings would alter operational semantics and still break old parsers. Accept a separate nullable `diagnostic_stage`, preserving existing failure/status/exit behavior and store schema. Producer and parent changes must roll out together; old parents deliberately reject new frames.

The fixed history stage allowlist is `decode-screen`, `envelope`, `provider-rejection`, `history-rows`, `metadata-missing`, `metadata-invalid`, `date-relation`, `core-validation`, `unknown`. Assign at existing trusted checks once; do not re-decode or salvage rejected bodies. Syntax and privacy-screen rejection share `decode-screen` to avoid a secret-specific oracle. No provider return-code/message, input field name/value, row index, identifier, path or exception string is returned. Unknown internal errors remain generic. Guard order and handling of multiple defects must be explicit and tested.

New exact version-2 worker headers add one stage field. New parsing accepts exact legacy version-1 frames with null stage, and exact version-2 frames with strict types/allowlist. A nonnull stage is valid only for history + HTTP200 + invalid-response + empty body. New version-2 history rejection requires a known stage; `unknown` is the internal fallback. Received unknown or contradictory stages fail closed as bad-frame without propagation. Success/non-history/other failures have null stages. Preserve all framing/size/digest/time/retry/body-validation constraints and positional constructors. Supervisor injection and storage/clock/cleanup precedence require separate safeguards.

The default CLI JSON remains byte-structure compatible with its current keys and exit semantics. An explicit `--diagnostics` mode would produce a private schema-version-2 summary with nullable stage fields. Diagnostics are ephemeral unless a future accepted probe saves its sanitized summary privately; no automatic persistence, store migration/normalization-version change or public projection/schema change. This does not reconstruct old failures.

Engineer supplied a 27-row authored matrix covering malformed JSON/security canaries, provider logical rejection, missing/invalid/date metadata, row/core failures, old/new frame versions, forged/unhashable/oversized/contradictory stages, parent replacements, store disposal and default/opt-in CLI compatibility. Lead reviewed the matrix against existing boundaries. These are **proposed regression requirements, not executed tests**; no runtime quality claim follows from this design review.

Lead independently verified protected tracked implementation/tests/reports/ledger/calendar paths are unchanged against the frozen base. The primary unrelated projection retains its original hash. No tests, real credentials/Keychain/store/provider/network calls or code changes were made for this spike.

Accept the bounded next implementation candidate: `ingest/private_market_store.py`, `ingest/market_collector.py`, `scripts/market_collect.py`, `docs/PRIVATE_MARKET_COLLECTOR.md`, and focused store/collector tests. Existing core/live/report-consumer tests must also run without edits unless Lead reviews a scope change. Missing metadata and pagination remain fail-closed. A separate frozen implementation ticket must demonstrate privacy and compatibility before any separately accepted live diagnostic probe. PRSG-90's cause, entitlement and forecast readiness remain unknown/blocked.
