# PRSG-145 — Bounded Malaysian Adjusted History Capture

Type: feature · Modules: financial-data, connectors, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 estimated person-days) · Impact: high — tests the specific adjusted-history capability needed by the Malaysian model input path.

## Why the ticket is created?

The human requests both prediction products by 28 October and continued work until they operate. PRSG-143 supplies offline MYR/XKLS model interfaces, but actual adjusted Malaysian OHLCV is not admitted. PRSG-144 verified a documented adjustment parameter and an already observed BMS.1155 route. Implement a narrow capture path, then independently decide its actual one-request result; do not claim model readiness from endpoint success.

## Approach

Permit only a new explicit local capability qualifier/version for GET /api/v1.0/quote/BMS.1155/history-kline with end=2026-10-23, ktype=2, autype=1, num=100 for the first live canary. The only API change from the known raw request is documented autype0 to1. Runtime support may accept a valid explicit end date, but no start, paging, count expansion, other BMS symbol or adjustment mode is authorized. Preserve ordinary raw defaults, US behavior, versions3–6 and all secure loader/TLS/worker/error-screening behavior.

Use a distinct normalization version7 and explicit BMS1155 adjusted-capability hours-hypothesis qualifier. Record requested adjustment separately from verified basis. Preserve raw body/hash, semantic/attempt bindings and original observed/ingested/known times. Keep timezone interpretation qualified; do not certify native currency, adjustment factors, price/volume units, finality or training rights. A new quality marker must not call requested autype1 unadjusted. Existing raw projections and the fixed50 baseline must not consume this capture as raw admitted history. No database rewrite or model/training interface change.

Engineer implements and tests only. Before an actual call Lead reviews the exact source-use/private-retention evidence, no-paid-access condition, runtime pins, closed job, quarantine store, credential references, process limits and exclusive IP window. The actual call is NOT released by this specification. Proposed budget is one GET, at most100 bars, zero retries/follow-ups,20-second worker plus2-second cleanup,60-second operation and at least3-second spacing from other requests. Any denied entitlement, rate limit, malformed/empty response or uncertain attempt stops; do not retry or contact anyone. Use the existing secure collector CLI and worker, not a lower-level bypass.

## Frozen scope

Base is the full current HEAD in the manifest. Engineer owns connectors/moomoo_rest.py, connectors/moomoo_rest_live.py, ingest/market_collector.py, ingest/private_market_store.py and the matching four existing test files. Lead owns these two records plus integration of the already reviewed PRSG-144 decision records. Protect all stock-research model code,141/140 forecast orchestration, reports, public data, credentials, schemas and unrelated .DS_Store/PRSG-138 edits. No dependencies, endpoints, authentication changes, purchases, schedules, model fitting, source admission or publication. If an additional path is necessary, return a concrete scope extension before editing it.

## Choices

A single known-symbol capture tests capability with a small bounded cost. Keep it quarantined and unadmitted. Do not broaden all Malaysian requests, invent a MY security alias, relabel unadjusted data, or turn a successful HTTP response into adjustment certification. Retained raw OHLCV can support separate offline QA but cannot meet the unchanged long-history/basis contract.

## Findings

The official dictionary describes autype1 as forward excluding dividends. Current BMS guards accept end-only daily raw100-bar requests; all four layers reject the proposed adjusted request. Actual retained BMS raw captures use a qualified hours interpretation although public history documentation describes minutes. Those unknowns remain after this narrow implementation. One hundred bars cannot establish three years or point-in-time model evidence.

## Tradeoffs

An empirical result can establish acceptance/rejection and returned shape for this exact request; it cannot establish accuracy, profitability, factors, training rights or broader market support. A failed or unavailable capability result is retained honestly. Full50/full100/strong-model and actual35 release gates remain open independently.

## When it's considered done

- [x] PRSG-145-D1: Narrow explicit BMS.1155 adjusted capture is implemented through all existing secure guard/collector/store layers; raw defaults and incompatible requests remain rejected.
- [x] PRSG-145-D2: Focused success, failure, replay, qualifier/basis, hostile-input and legacy compatibility regressions pass; Lead independently reviews exact changed scope and runtime pins.
- [x] PRSG-145-D3: One separately released actual canary is independently reviewed against exact count/deadline/cleanup/raw-time bindings, with success/rejection/unknown semantics recorded and no model admission inferred.

## Validation and delivery

Run the four manifest test suites; cover wrong symbol/mode/start/count/qualifier, secure transport allowlist, one-job frame/version behavior, failed and empty captures, replay integrity, existing v3–6 raw history and baseline exclusion. No credentials or provider values in fixtures/logs/Git. Validate every changed path; required hooks run on commit. Actual evidence stays private. D3 cannot be satisfied by authored fixtures or code checks.

## Lead acceptance — 26 October 2026 MYT

Lead matched all eight file hashes, reviewed the secure request marker and version7 isolation, and independently ran the four focused suites: **1157 passed in 4.08s**. Engineer additionally reported338 related integration tests passing in10.04s.

The separately released actual canary succeeded: one BMS.1155 request,100 returned bars spanning29May–23October, zero provider retries,1.58seconds, child reaped and no cleanup failure. Lead independently verified the single stored attempt, raw hash, replay, actual observation/ingestion/known times and every non-admission label. Private raw data remains quarantined; no provider values or credentials enter Git. Initial CLI setup failed before collection because the quarantine store was absent; that launch and deterministic zero-provider failure were retained, then the empty store was initialized before the first actual provider attempt.

Private release/supervisor/review evidence is under `/Users/jwtan/.codex/lead-state/PRSG145/lead/`. Requested autype1 is still unverified adjusted basis. Currency, native units, factors, finality, training rights and historical point-in-time availability remain unverified. This completes the bounded capability ticket, not the prediction coverage or stronger-model outcome. Required commit hooks and delivery state are reported separately.
