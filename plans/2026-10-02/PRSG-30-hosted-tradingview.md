# PRSG-30 Hosted TradingView charts for dated watchlists

Type: feature · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days, estimate) · Impact: medium

## Why the ticket is created?

Human requested this to make the static research site easier to navigate and understand.

## Approach

Add a TA chart view using date-selected report tickers as horizontal rounded keyboard/touch chips with explicit direction emoji/text. Clicking a mapped US symbol remounts the official hosted Advanced Chart; no OHLCV ingestion. Preserve TradingView attribution, distinguish current/delayed chart from historical watchlist, and use explicit Bursa external-link fallback instead of claiming unsupported embed coverage.

## Options and tradeoffs

Reuse existing static assets and hosted widgets rather than add a build system or ingest chart prices. External charts require third-party connectivity and may be delayed; vendor coverage is not guaranteed. No backend/credential changes.

## Findings and references

Existing Pages serves artifacts directly. TradingView research established historical date selection selects a watchlist, not a frozen historical chart. References: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/ and https://www.tradingview.com/widget-docs/tutorials/iframe/build-page/dynamic-symbols/

## Frozen scope and validation

Base: 775e8a151a620644caa0d21dae765072069f4f24. Only manifest allowed_paths may change. Preserve unrelated .DS_Store and other ticket edits. Date changes replace the watchlist without stale loads; up/down/flat/unrated chips are accessible; safe curated exchange mapping rejects unknown symbols; rapid switching cleans up embeds; missing/failed external widget always has a safe link; reduced-motion and mobile overflow covered. Mock scripts/network; never include private portfolio or secrets.

## When it's considered done

- [x] PRSG-30-D1: Implement behavior with deterministic regressions and independent Lead review.

## Progress

Accepted for implementation. No test or deployment claimed yet.



## Engineer handoff evidence

Added a Technical analysis view, addressable with `?view=technical`, using the existing selected report date and public forecasts. Date changes clear old ticker chips/embed immediately; accepted report responses replace the watchlist, stale report loads remain excluded by existing request guards. Chips are one horizontal rounded colored strip, native keyboard/touch buttons with recorded Up/Down/Flat/Unrated emoji/text and pressed state. Arrow/Home/End traverse chips; reduced motion uses auto scroll. Chart prices are explicitly current/delayed, not frozen to the report date; direction is a recorded scenario, not a live signal.

Official Advanced Chart configuration and attribution reused from https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/ and https://www.tradingview.com/widget-docs/tutorials/iframe/build-page/dynamic-symbols/ . Fixed external script URL and constant widget settings transmit only the selected mapped public symbol, not report date/scenarios/private holdings. Seven initial verified mappings: NASDAQ AAPL/MSFT/NVDA/QQQ, AMEX SPY/IWM, NYSE JPM. Verified against official TradingView `/symbols/EXCHANGE-TICKER/` pages on October2. Unmapped US listings intentionally do not embed or guess exchange; use TradingView symbol-directory fallback. Valid Bursa codes use an external MYX chart link explicitly labelled coverage unverified; no Bursa embedding assertion.

Navigation/date/symbol changes remove old embed DOM, observers and timers; generation guards reject stale error callbacks. Script errors and a15-second no-frame timeout display fallback and clear embed. Detecting a frame does not establish usable/live data; status says frame added and vendor determines availability/delay. Cross-origin internal chart/data errors are not inspectable here; safe external link remains visible. Removing a script cannot guarantee cancelling an already-running vendor request/script. Attribution remains both in widget markup and persistent view footer.

Frozen command `node tests/tradingview_checks.cjs`: **passed**, with external scripts/network mocked,1280/390 fixtures, direction/safety/date-race/lifecycle/error/timeout/keyboard/reduced-motion and missing states. It also successfully replays the existing daily report DOM checks. No live hosted rendering, vendor entitlement/coverage test or browser visual QA claimed. All five exact owned paths validated; whitespace clean. Frozen scope/base/check definitions and all Lead review/acceptance gates retained. No staging/commit/push/dependency/backend/watchlist-API edits. PRSG-29 landing/ticket changes are Lead-owned and preserved, as is .DS_Store. These five owned paths are handed back to Lead; acceptance remains pending.

## Lead acceptance

Lead independently inspected implementation and reran node tests/tradingview_checks.cjs (including existing viewer replay), node tests/pages_branding_checks.cjs and node tests/ticket_dashboard_checks.cjs: all passed. PRSG29 independent review identified skip stacking and anchor offsets; fixed single final skip rule z30 and measured ResizeObserver offset, regressions pass. PRSG30 external scripts mocked; live rendering/entitlements and visual browser QA not verified. No credentials/private data/backend changed.
