# PRSG-92 — Reject contradictory daily-history dates

Type: bug · Modules: connectors, financial-data · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-day, estimate) · Impact: medium-high — prevents contradictory temporal input from being accepted; no prediction or live-coverage gain is established.

Created 2026-10-11 MYT. Status: in progress, Lead accepted. Frozen base: `6ad50954ab9a8d8c0d98b34f90d0a08738dff512`. This is the narrowly scoped guard correction identified by the accepted PRSG-91 review, within the selected forecast-input readiness direction.

## Reproduction and expected behavior

Existing store normalization accepts timestamp1779249600000, explicit offset-240 and date20260521, although that timestamp's local date is20May. Core history validation lacks the same relationship check. Existing positive fixtures also contain inconsistent date/timestamp combinations. Expected: both boundaries accept only rows whose declared daily date equals the local calendar date obtained from the supplied millisecond timestamp and explicit minute offset. Contradictory or unrepresentable inputs produce existing bounded rejection categories. Do not infer missing offset/date, require midnight timestamps or claim regular-session finality from this relation.

## Accepted implementation scope

Engineer may change only `connectors/moomoo_rest.py`, `ingest/private_market_store.py`, the existing four focused REST/live/collector/store test files, and this ticket's spec/manifest. Lead owns scope/review/integration. Use the existing interfaces and error vocabulary; handle timestamp conversion overflow/platform limits without leaking exceptions. Preserve exact millisecond/date boundary behavior without avoidable floating-point rounding. Keep offset and date scalar/type/range checks, positive finite close, duplicates, start/end, cutoff, secret rejection and request/signature/quota controls intact.

Correct only contradictory positive history fixtures; preserve request-signing timestamps and unrelated snapshot/news semantics. Add meaningful core/store mismatch regressions, consistent non-midnight cases, explicit-offset local day rollover at valid offset bounds and unrepresentable timestamp rejection. Collector-level malformed capture must remain bounded and yield no accepted history. Do not weaken or remove tests to make the stricter check pass.

No credential/Keychain/private-store/provider access, live sample, new client/script/dependency, pagination/metadata compatibility expansion or diagnostics-schema change. No report/ledger/calendar/method/target/confidence change. This fix does not establish the cause of PRSG-90's discarded response or resolve forecast readiness.

## When it's considered done

- [x] PRSG-92-D1: Both core and store enforce supplied timestamp/offset/date agreement with controlled mismatch/overflow rejection.
- [x] PRSG-92-D2: Focused positive, mismatch, rollover, overflow and collector failure regressions pass; existing safety controls remain covered.
- [ ] PRSG-92-D3: Lead independently reviews all owned paths and preservation, validates ticket evidence and verifies authorized commit/push delivery.

## Validation and ownership

Run approved Python `-m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py`; mandatory hooks provide the repository-wide checks at delivery. Lead replays targeted evidence and verifies the full changed-path set, including new/deleted/rename endpoints. Protected paths include all reports/ledger/calendar, other implementation, scripts, skills, agent operations and the unrelated primary projection edit. Isolated accepted checkout: `/Users/jwtan/.codex/worktrees/prsg89-prediction-chip/praesagus`. Engineer returns uncommitted reviewed patch/check evidence; Lead commits and integrates.

Primary contract: [official history endpoint](https://open.moomoo.com/api/quote/basic-data/history-kline.md), reviewed in PRSG-91. The relation is mathematical consistency using explicit supplied metadata, not provider authenticity, timezone entitlement, exchange-calendar certification or forecast eligibility.

## Engineer implementation evidence — 2026-10-11T19:47:53+08:00

Both boundaries now compare declared daily date against an exact integer local-day calculation using only the supplied millisecond timestamp and explicit minute offset. Calendar conversion overflow remains a controlled rejection. No midnight requirement, metadata fallback, envelope expansion, new dependency or source-finality inference was added. Store replays apply the same stricter relation; no stored data was inspected or migrated.

Exact focused check: `PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' /Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_market_collector.py tests/test_private_market_store.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py` — **491 passed in 2.82s**, exit 0. Thirty new cases exercise consistent nonmidnight bars, explicit-offset day rollovers at -720/+840, one millisecond before/at midnight, UTC rollover, epoch offset rollover, contradictory dates, unrepresentable 64-bit timestamp and collector failure with no retained body/raw/history rows. Existing history-positive fixtures were corrected independently of signing clocks; the existing future-date case now has a consistent future timestamp so the end-date guard remains exercised. Unrelated snapshot/news fixtures and request/signature expectations remain intact.

`git diff --check` passed. Only the six frozen implementation/test paths plus this evidence spec/manifest changed. All protected paths match the frozen base. The primary unrelated projection remains SHA256 `b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f`. Lead independent review, complete scope/preservation acceptance, full delivery hooks and commit/push remain pending (D3). No live request, credentials/Keychain/private-store access, new client/script/subagent, forecast/method/report changes or commits/pushes performed. The fix does not identify PRSG-90's live cause or establish forecast readiness.

## Independent Lead review

Lead inspected all eight owned paths and independently ran the exact focused test set: 491 passed in2.98s. Integer arithmetic preserves explicit-offset millisecond boundaries and controlled overflow rejection;30newcases retain valid non-midnight rows and test mismatches/rollovers/worker zero-row failures. Full scope and protected-path preservation passed. Implementation accepted; commit/push delivery remains pending. No live request or new target.
