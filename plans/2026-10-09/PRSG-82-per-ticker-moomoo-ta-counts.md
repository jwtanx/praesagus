# PRSG-82 — Show per-ticker Moomoo TA signal counts

Type: feature · Modules: financial-data, market-research, frontend · Owner: Engineer · Priority: P2 · Effort: M (3–5 person-days, estimate) · Impact: medium-high — lets report readers inspect the balance of rule-triggered technical indicator observations per ticker; adoption and usefulness are not yet measured.

Created 2026-10-09 MYT. Frozen planning base: `ba7c01480616ab0f4bca576c1be97d5a4961c9e9`.

## Objective

Add an optional per-ticker display such as `Bullish 2 · Bearish 1` for eligible, discrete Moomoo technical-analysis outputs, with an expandable/tappable explanation of each rule hit. Keep these counts visibly separate from the report's forecast direction, target, confidence and price prediction. Counts are observations, not probabilities, recommendations or an aggregate predictive score.

## Current baseline and interfaces

- `ingest/market_collector.py` and `ingest/private_market_store.py` already collect and retain Moomoo snapshot and daily history records, but the history collector currently validates `US.*` codes only.
- `ingest/daily_report_projection.py` projects quote-vs-provider-previous-close direction and SMA-5/SMA-20 trend. These fields do not compute KDJ, MACD or Bollinger rules.
- The shared viewer at `artifacts/daily-market-brief/index.html` already renders Moomoo detail text in each ticker row. Report validation and forecast schemas must be inspected before accepting an output shape.
- Moomoo technical-anomaly instructions and a CLI exist for ad hoc anomalies, but that is not the daily-report's persisted, timestamped per-ticker count contract.

## Proposed MVP and rule semantics

Use completed daily bars, one documented timeframe, and fixed/versioned parameters. Store individual indicator outputs with ticker, indicator, rule/version, direction (`bullish`, `bearish`, `neutral`), observed value/state, bar end/source time, retrieval/known time, and explicit unavailable reason. Compute counts only from eligible directional outputs; show neutral and unavailable separately so missing indicators never look bearish or disappear into the denominator.

- **KDJ:** directional only on a K/D crossover (bullish when K crosses above D; bearish when K crosses below D) on the completed bar. Record J and whether the crossover occurred below 20 or above 80 as context; oversold/overbought alone is not directional.
- **MACD:** directional only on MACD-line/signal-line crossover (bullish up-cross, bearish down-cross) on the completed bar. Record MACD, signal and histogram; histogram sign alone is not the MVP directional trigger.
- **Bollinger Bands:** directional only on a completed close re-entering inside the lower band after closing below it (bullish mean-reversion event), or re-entering inside the upper band after closing above it (bearish mean-reversion event). Record close and band values. A band touch, proximity or breakout alone is not a directional call.

The per-ticker summary may show per-indicator counts and a combined count across the three fixed indicator families, with a clear denominator and data coverage. Do not collapse repeated same-indicator events into an unbounded vote; count at most one current state per indicator per ticker and timeframe. If current/complete history, parameter metadata or timestamp provenance is missing, render unavailable with its reason.

## Frozen planning boundary

Planning only; no implementation is authorized by this ticket yet. Proposed Engineer write set if Lead accepts a follow-on delivery: `ingest/daily_report_projection.py`, `artifacts/daily-market-brief/index.html`, `scripts/daily-market-brief/validate_report_json.py`, focused projector/viewer/validator tests, and a separate dated report-skill edit only after the report schema and operational flow are accepted. Keep Moomoo data fields governed by the existing normal dated-report flow and the user's current report instructions. Do not change historical reports, forecast targets/directions/confidence, forecast model, report schedule, private raw storage, API credentials, rights/publication guidance, or trader financial judgment.

## When it's considered done

- [ ] PRSG-82-D1: Accept a provenance-backed schema and exact, versioned rules for at most one current directional event per indicator, ticker and timeframe.
- [ ] PRSG-82-D2: Demonstrate deterministic bullish/bearish and rejection/missing cases for all three indicators using frozen local bars.
- [ ] PRSG-82-D3: Display per-ticker per-indicator counts with accessible details and explicit coverage, independently from forecast direction/targets/confidence.
- [ ] PRSG-82-D4: Record coverage and usability evidence; keep any predictive use out of scope until separately evaluated.
- [ ] PRSG-82-D5: Lead independently reviews complete scoped diff and test evidence.

## Dependencies and risks

Confirm via a bounded prototype/research step whether the approved local/private data path has enough reliable, completed daily bars and supports the chosen markets. Current Moomoo history path is US-only and past saved data had failed history requests; this feature may initially show many unavailable rows. Verify indicator formulas/parameters against Moomoo's documented conventions before implementing; do not silently claim identical vendor calculations if locally calculated. Market-data terms and current report handling remain governed by the normal report flow. This feature has no validated forecast edge and must not change price predictions.

## Measurement

At first manual preview, record the share of report tickers with all three eligible signals and whether a reader can identify the rule and timestamp for a displayed count within one interaction. No existing analytics baseline is available. Continue only if coverage is sufficient for the intended market and a user review confirms the details help interpretation.
