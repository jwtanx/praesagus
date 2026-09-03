---
name: praesagus-trading-orchestrator
description: >-
  Bind Praesagus investment, research, signal, market, Moomoo, and risk skills
  into one evidence-first workflow. Use when the user asks for a stock analysis,
  investment thesis, trade setup, portfolio action, event analysis, or recommendation.
license: MIT
metadata:
  author: praesagus
  version: "1.0"
  category: orchestration
  tags: [orchestration, evidence, risk, trading, research]
---

# Praesagus Trading Orchestrator

## Purpose
Coordinate specialist skills into one auditable decision. Specialist skills produce bounded evidence; this skill selects them, normalizes outputs, rejects unsafe conclusions, and emits one decision memo. It does not place orders.

## Skill map

1. Core decision: `market-analysis`, `earnings-quality`, `valuation-momentum`, `corporate-governance`, `issuer-credit-quality`.
2. Quantitative signals: `alpha-signal-engine`, `smart-beta-factor`, `sector-rotation`, `securities-arbitrage`.
3. Macro and external risk: `global-macro-cycle`, `quantitative-macro`, `geopolitics-risk`, `regulation-policy`, `regulatory-event-driven`, `inflation-opportunity`, `commodity-insights`.
4. Theme and demand: `ai-investment-thesis`, `tech-disruption`, `venture-to-public`, `consumer-behavior-signals`, `retail-consumer-growth`, `daily-necessity-forecasting`, `supply-chain-analytics`, `esg-investment-framework`, `alternative-assets`, `hidden-gem-finder`.
5. Data inputs: Moomoo news, digest, sentiment, technical anomaly, capital anomaly, and derivatives anomaly skills. These never independently establish a trade.
6. Risk and execution: `portfolio-resilience`, `swing-trading-for-idiots`, plus the shared contract in `skill-template`.

## Workflow

1. Parse asset identifier, asset class, region, decision, horizon, portfolio context, risk budget, and requested action. Ask when missing information changes the decision.
2. Freeze decision timestamp, timezone, market session, data vintage, and corporate-action basis. Reject future-dated or stale inputs.
3. Select only relevant specialist skills. Always include core analysis, disconfirming evidence, and portfolio/liquidity risk for actionable requests.
4. Gather primary evidence first. Record source URL, source tier, publication time, data period, extraction time, and limitation.
5. Normalize every result to: direction, horizon, thesis, evidence, regime, expected return, risk, confidence, invalidation, and provenance.
6. Deduplicate events and correlated evidence. News, sentiment, price, volume, capital flow, and derivatives may describe one event; do not count them as independent confirmations.
7. Reconcile conflicts by source quality, timestamp, horizon, regime, and measurement error. Lower conviction when conflict remains. State what new evidence would resolve it.
8. Run bias checks: look-ahead leakage, hindsight framing, confirmation seeking, survivorship bias, cherry-picked windows, multiple testing, and narrative overfitting.
9. For signals or strategies, require sample size, benchmark, walk-forward or out-of-sample validation, costs, spread, slippage, delay, turnover, capacity, drawdown, and kill-switch thresholds.
10. For trades, define executable entry, exit, stop, time stop, expected value, maximum loss, risk-based size, liquidity, borrow/funding, event risk, correlation, and concentration.
11. Classify result as `research only`, `watchlist`, `paper trade`, `human approval required`, `execution-ready`, or `NO TRADE`. `Execution-ready` requires all gates and human approval.
12. Emit monitoring triggers, review date, forecast assumptions, and ex-post scorecard fields so future results cannot rewrite the original thesis.

## Trader-method guardrails

The current Sneaky Pivot method is a candidate setup, not validated truth. Preserve its simplicity, but reject any setup with undefined “meaningful level,” “big buyer,” “big seller,” or candle-cross condition. Require numerical pivot, entry, stop, target, cancellation, spread, liquidity, volatility, gap/news filter, execution cost, risk-per-trade, daily loss limit, and out-of-sample expectancy. One 15-minute chart may generate the setup; higher-timeframe regime and event checks remain mandatory. `NO TRADE` is valid.

Moomoo data is discovery input. Never treat sentiment as fundamentals, technical anomaly as direction, capital flow as informed certainty, derivatives activity as directional certainty, recency as information advantage, or repeated syndicated stories as independent confirmation. Check whether information is already priced in.

## Canonical output

```yaml
decision:
classification:
asset:
asset_class:
horizon:
as_of:
data_available_at:
regime:
thesis:
evidence_grade:
primary_evidence:
disconfirming_evidence:
bull_case:
base_case:
bear_case:
probabilities:
expected_return:
expected_loss:
entry_rule:
exit_rule:
stop_rule:
time_stop:
position_size:
max_loss:
liquidity_and_costs:
portfolio_interaction:
confidence:
invalidation_trigger:
review_date:
backtest_status:
out_of_sample_status:
approval_required:
data_gaps:
provenance:
```

## Hard rejection gates

Reject or mark `NO TRADE` when data is missing, future-dated, stale, duplicated, or unverifiable; entry/exit/stop is undefined; maximum loss or position size is absent; liquidity, costs, borrow, or event risk is ignored; validation fails; contradictory signals are hidden; or live execution lacks human approval.
