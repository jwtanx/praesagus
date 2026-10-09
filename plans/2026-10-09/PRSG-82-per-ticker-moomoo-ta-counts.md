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

## Provider API feasibility review (2026-10-09)

Official OpenD documentation describes two distinct possible data contracts:

1. **Provider pattern events:** Stock Screening V2 exposes named pattern filters such as `KDJ_GOLD_CROSS`, MACD crosses, and Bollinger patterns. These are Moomoo-defined screening patterns, not a generic complete event feed. A missing ticker from a filtered screener response does not by itself prove a neutral/no-event state; neutral requires a successful response contract that demonstrates evaluation coverage for the ticker, pattern set, timeframe and completed session.
2. **Provider-calculated indicator values:** `get_indicator_list` returns indicator input/output metadata; `request_indicator_calc_async` accepts bars and optional input overrides and returns a `calc_id`; `push-indicator-calc` delivers output metadata and rows with bar timestamps. These are provider-calculated values, not provider-issued bullish/bearish recommendations. Any cross or re-entry derived from them remains a Praesagus event rule and must be labeled accordingly.

Primary references: [Moomoo indicator list](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-indicator-list.html), [async indicator calculation](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-indicator-calc.html), [timestamped calculation results](https://openapi.moomoo.com/moomoo-api-doc/en/quote/push-indicator-calc.html), and [Stock Screening V2 patterns](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-stock-screen.html).

The repository does not currently use those APIs. `connectors/moomoo_opend.py` calls close-only `request_history_kline`, and creates/closes a connection per request; `pyproject.toml` declares `moomoo-api = "*"` with no version lock establishing SDK method availability. Implementing async calculations requires a managed callback lifetime and bounded correlation/timeout by `calc_id`; neither API support in the installed SDK nor local OpenD access, market entitlement, exact indicator parameters, output mapping, or rights has been verified. No provider call was made for this review.

**Lead decision: do not mix provider patterns and locally derived events in one count.** Stock Screening V2 returns matching stocks and `all_count`, not an evaluated response row for every requested ticker. Therefore omission cannot establish a no-pattern result. The preferred next feasibility step is the provider-calculated timestamped indicator series with explicitly labeled Praesagus event rules; this is a local event derived from Moomoo-calculated values, not a Moomoo-issued signal. Keep native pattern outputs as a separate source class, and do not use them for a complete per-ticker count unless Moomoo documents or demonstrates explicit complete per-symbol coverage including non-matches. In either path, missing, partial, stale, unsupported or permission-denied results are `unavailable`, never neutral. Keep public JSON excluded absent the user's specified current operator-provisioned rights evidence.

**Scope consequence:** PRSG-82 remains planning-only and provisional. This read-only review does not authorize connector edits, OpenD calls, private-store reads/writes, data backfills, or viewer/public-report changes. A new frozen private-only implementation scope must first choose one data contract, verify completion/coverage semantics and SDK feasibility, and explicitly include any connector lifecycle/schema changes. Do not implement the candidate locally calculated rules below as a substitute for vendor pattern events.

## Candidate fallback rules — locally calculated events, not vendor signals

Trader's read-only review found that Moomoo's documented native patterns have their own definitions and may differ from these formulas. These formulas are retained only as a possible **locally calculated event from Moomoo-calculated values or Moomoo-sourced bars** contract if explicitly selected later; they are not Moomoo-issued signals. D1 remains unaccepted.

Shared event behavior: use one completed daily bar per exchange-local session. Each indicator emits one of `bullish_event`, `bearish_event`, `neutral`, or `unavailable`. Directional events are one-session pulses and expire on the next completed bar; do not carry a prior cross forward. An eligible latest bar with no new trigger is `neutral`; missing, invalid, stale, conflicting, or insufficiently warmed-up data is `unavailable` with a reason. Counts include only current-bar directional events; expose neutral/unavailable counts and coverage separately. These related price-derived events are observations, not independent votes, probabilities, forecasts or recommendations.

- **KDJ(9,3,3):** `RSV_t = 100 × (C_t−LL9_t)/(HH9_t−LL9_t)` using the current and prior eight completed bars; a zero range is unavailable. Seed K and D at 50 on the first valid RSV, then `K_t = (2/3)K_(t−1)+(1/3)RSV_t`, `D_t = (2/3)D_(t−1)+(1/3)K_t`, and `J_t=3K_t−2D_t`. Need 11 contiguous completed bars to evaluate the first cross. Bullish iff prior `K<=D` and current `K>D`; bearish iff prior `K>=D` and current `K<D`. K's current value below 20 or above 80 is context only; J is descriptive. Neither extreme alone creates an event.
- **MACD(12,26,9):** use adjusted close with `EMA_n` seeded by the arithmetic mean of the first n values, then `EMA_t = 2/(n+1)×x_t + (1−2/(n+1))×EMA_(t−1)`. MACD is EMA12 minus EMA26. The signal EMA9 is seeded from the first nine valid MACD values: with these seeds, MACD first exists at close 26, the signal first exists at close 34, and the earliest prior/current crossover comparison is close 35. Bullish iff prior MACD `<=` prior signal and current MACD `>` current signal; bearish iff prior MACD `>=` prior signal and current MACD `<` current signal. Equality on the current bar is not a cross. Histogram is descriptive only.
- **Bollinger(20,2):** middle band is SMA20; standard deviation is population SD (`ddof=0`) over the same 20 closes; upper/lower are middle ±2 SD. Need 21 contiguous completed bars for prior and current band comparisons. Bullish re-entry iff prior close is strictly below its lower band and current close is at or above its lower band while at or below its upper band. Bearish re-entry is the symmetric strict prior close above upper band followed by current close at or below upper and at or above lower. A touch without prior outside close, continued outside close, or inside-to-inside movement is neutral. This is a chosen mean-reversion display rule, not a universal directional interpretation.

History requirements: finite positive OHLC, `low <= open/close <= high`, unique ordered exchange-session dates, one adjustment basis, enough contiguous bars for each warm-up, and a latest completed bar whose age is within a Lead-frozen maximum number of expected trading sessions. Source bar time, retrieval/availability time, known-at time, report cutoff, exchange calendar and completed-session decision must be preserved. Require all evidence times no later than cutoff; exclude in-progress and after-hours bars, and handle holidays and early closes. A gap, adjustment-basis change, duplicate/conflict or invalid value must not be silently bridged.

Proposed private-draft object: top-level schema/method version, timeframe, source and adjustment basis; last completed session date; source/retrieval/known/cutoff timestamps; expected/available/eligible coverage; per-indicator parameters, rule version, prior/current values used, status, direction and unavailable reason; plus bullish, bearish, neutral and unavailable counts with an explicit denominator. Do not include raw provider responses, account details or private identifiers. No Moomoo-derived fields may be written into public JSON without the user's specified current operator-provisioned rights evidence for the exact market, fields, public display and redistribution; a private draft purpose does not supply those rights.

The current history normalizer exposes close but not OHLC. Engineer's readiness review recommends a new normalization version for new captures, preserving version-3 reads unchanged. Any replay of old raw payloads needs a separate immutable re-normalization design preserving hashes, runs and original timestamps; it is not silently a new capture. Current projector's fixed wall-clock cutoff does not verify exchange-calendar completeness or maximum stale-session age. Resolve those before implementation. Current stored rights/authenticity are unconfirmed and checked-in history evidence shows failed requests and zero eligible bars; real counts therefore remain unavailable until evidence is captured and passes these checks. Synthetic fixtures can verify rule math but cannot establish live coverage or provider equivalence.

## Frozen planning boundary

Planning only; no implementation is authorized by this ticket yet. A first, private-only follow-on would need Lead to freeze the schema and session/freshness decisions, then expand the allowed path list for a new OHLC normalizer version, collector version selection, an isolated private TA projector, private-draft runner integration, and focused storage/collector/projector/runner checks. Preserve legacy version-3 reads and the existing unrelated edit in `ingest/daily_report_projection.py`; use a new module rather than editing that path. Keep public report JSON, historical reports, viewer, report skill, forecast fields/confidence, model, schedule, credentials, and publication guidance outside this private phase. Any public display is a distinct follow-on requiring the user's specified rights evidence and separately frozen schema/viewer paths. No current live data coverage is demonstrated.

## When it's considered done

- [ ] PRSG-82-D1: Accept a provenance-backed schema and exact, versioned rules for at most one current directional event per indicator, ticker and timeframe.
- [ ] PRSG-82-D2: Demonstrate deterministic bullish/bearish and rejection/missing cases for all three indicators using frozen local bars.
- [ ] PRSG-82-D3: Display per-ticker per-indicator counts with accessible details and explicit coverage, independently from forecast direction/targets/confidence.
- [ ] PRSG-82-D4: Record coverage and usability evidence; keep any predictive use out of scope until separately evaluated.
- [ ] PRSG-82-D5: Lead independently reviews complete scoped diff and test evidence.

## Dependencies and risks

Confirm via a bounded prototype/research step whether the approved local/private data path has enough reliable, completed daily bars and supports the chosen markets. Current Moomoo history path is US-only and past saved data had failed history requests; this feature may initially show many unavailable rows. Verify indicator formulas/parameters against Moomoo's documented conventions before implementing; do not silently claim identical vendor calculations if locally calculated. Market-data terms and current report handling remain governed by the normal report flow. This feature has no validated forecast edge and must not change price predictions.

Trader's review notes that Moomoo's official [screener documentation](https://www.moomoo.com/us/support/topic3_68) describes screener timeframes and signal vocabulary, but does not verify the formulas, seeds or parameters proposed here. Treat the equations above as an explicitly local display convention unless exact vendor equivalence is independently established.

## Measurement

At first manual preview, record the share of report tickers with all three eligible signals and whether a reader can identify the rule and timestamp for a displayed count within one interaction. No existing analytics baseline is available. Continue only if coverage is sufficient for the intended market and a user review confirms the details help interpretation.
