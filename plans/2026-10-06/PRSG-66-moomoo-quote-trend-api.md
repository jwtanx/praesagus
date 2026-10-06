# PRSG-66 — Read-only Moomoo quote trend labels

Type: feature · Modules: backend, connectors, financial-data, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high; supplies a reproducible directional context label for each requested quote without pretending a point quote is a forecast. Created 2026-10-06 MYT.

## Objective

Add a bounded batch API that returns one transparent descriptive trend label for each requested US Moomoo symbol, using Moomoo OpenD daily K-line history. Users need per-quote bullish/bearish context in the API. The current quote response contains snapshots, not a native directional recommendation. Moomoo's official strategy sample derives bull/bear from fast and slow moving averages; this ticket applies that idea as a read-only indicator.

## Frozen scope

Lead accepted this user-requested implementation on 2026-10-06 MYT. Base SHA: `e45050f6957e045800c3a45121b68176ded64463`.

**Allowed paths**

- `backend/main.py`
- `tests/test_moomoo_api.py`
- `plans/2026-10-06/PRSG-66-moomoo-quote-trend-api.md`
- `plans/2026-10-06/PRSG-66.harness.json`

**Protected paths**

- all other paths, especially `connectors/moomoo_opend.py`, `frontend/`, `artifacts/`, `agent-operations/`, report snapshots, publication projection, and credentials/configuration.

The endpoint reuses the existing read-only `get_history` connector. Do not add dependencies, network implementations, indicators from unverified quote fields, order/trade APIs, persistence, scheduling, or report publication. Do not call live OpenD in tests.

## API behavior

Add `GET /api/v1/moomoo/trends?codes=US.AAPL&codes=US.MSFT` with a hard limit of 20 unique market-qualified `US.*` symbols and the standard optional API-key dependency. Deduplicate codes and reject malformed/non-US codes before calling the connector. Fetch enough history for 20 completed daily closes (request the existing three-month bounded history window, max 100 rows). For each symbol calculate simple means over the latest 5 and 20 returned positive, finite daily closes:

- `bullish` when SMA-5 > SMA-20.
- `bearish` when SMA-5 < SMA-20.
- `neutral` when equal.
- `unavailable` with an explicit reason when fewer than 20 usable daily bars exist or history is unavailable for that symbol.

Return per-symbol `code`, `status`, `method`, `fast_window`, `slow_window`, `fast_sma`, `slow_sma`, `spread_pct`, `latest_bar_date`, `retrieved_at`, and `reason` where applicable, plus top-level `count`, `window`, `adjustment: QFQ`, provider/method note, and request retrieval timestamp. Values are descriptive calculations from Moomoo history, not provider-issued recommendations or predictions. The response must say so. Never map unavailable to neutral or bearish. Preserve input symbols in the result even if individual history calls fail; surface bounded per-symbol unavailability instead of dropping the symbol. Keep the endpoint read-only and use the existing connector's documented Moomoo/OpenD behavior.

## Verification

- Mocked API tests cover positive/negative/equal MA spread, 19-row warmup, malformed/nonpositive/nonfinite bars, case normalization/deduplication, invalid symbol rejection before provider calls, batch bound, per-symbol connector failure, API-key enforcement, and request provenance.
- Run `python3 -m pytest -q tests/test_moomoo_api.py tests/test_moomoo_opend.py` and relevant broader checks if needed.
- Run `python3 scripts/planning/validate_ticket.py plans/2026-10-06/PRSG-66.harness.json --changed-file plans/2026-10-06/PRSG-66-moomoo-quote-trend-api.md --changed-file plans/2026-10-06/PRSG-66.harness.json` and `git diff --check`.
- No live Moomoo account, credential, or market request is part of acceptance.

## When it's considered done

- [x] PRSG-66-D1: Batch trends endpoint validates/deduplicates at most 20 US symbols and returns one explicit row per input symbol. Evidence: `tests/test_moomoo_api.py` covers normalization, deduplication, invalid-symbol rejection before connector calls, the 20-symbol bound, and per-symbol result retention.
- [x] PRSG-66-D2: SMA-5/SMA-20 trend status is computed from validated Moomoo daily bars with null/unavailable behavior for insufficient or failed history. Evidence: mocked tests cover bullish, bearish, neutral, 19-bar warmup, malformed/nonpositive/nonfinite bars, current-date-bar exclusion, and per-symbol OpenD failure.
- [x] PRSG-66-D3: Response exposes method, QFQ basis, latest bar date and retrieval timestamp, and labels the indicator as descriptive rather than a forecast/recommendation. Evidence: response-contract assertions cover per-row SMA windows/values/latest date/retrieval time and top-level QFQ, provider, method and non-forecast note.
- [x] PRSG-66-D4: Focused mock tests, ticket validation, scope review and `git diff --check` pass; no live requests or protected-path changes occur. Evidence: focused Moomoo API/OpenD suite passed 49 tests against current HEAD `25941ad596a1193a6f4e32d43bbdb75f8f48b2ff`; ticket validator accepted all four scoped paths; diff/whitespace checks passed; PRSG-66 working-tree changes are confined to allowed files. User-confirmed concurrent PRSG-67 commit `25941ad596a1193a6f4e32d43bbdb75f8f48b2ff` was preserved while the frozen base remains `e45050f6957e045800c3a45121b68176ded64463`. No live request was made. Lead review remains pending.

## Evidence

- Moomoo's official [strategy sample](https://openapi.moomoo.com/moomoo-api-doc/en/quick/strategy-sample.html) demonstrates a bull/bear classification using fast and slow moving averages calculated from returned K-line close values. This ticket adapts the calculation to a read-only batch API and does not copy the strategy's order-execution behavior.
- Moomoo's official [historical candlestick API](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html) documents daily K-line history and adjustment-type parameters.
- The repository already has a bounded OpenD history connector and read-only `/api/v1/moomoo/history` route. No native bullish/bearish recommendation field has been verified in the existing quote response.

## Lead review and delivery

2026-10-06 MYT: Lead independently accepted the scoped read-only implementation. Commit `df4d420945fe5fa481683bac8efc1712fe67d46d` was pushed to `main`; GitHub Pages deployment [37465466939](https://github.com/jwtanx/praesagus/actions/runs/37465466939) succeeded for the report site. The full pre-commit suite passed 1,206 tests and the focused Moomoo suite passed 49 tests. Repository CI run [37465466849](https://github.com/jwtanx/praesagus/actions/runs/37465466849) was still in progress when recorded. Pages success does not establish backend hosting. A local API probe returned `opend_unavailable`; no live Moomoo trend data or report refresh was claimed.
