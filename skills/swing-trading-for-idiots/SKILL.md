---
name: swing-trading-for-idiots
description: >-
  Generate straightforward swing and short-term trading guidance using the
  "Sneaky Pivot" framework: one 15-minute chart, four key price levels, and a
  disciplined three-candlestick entry process.
disable-model-invocation: true
metadata:
  author: praesagus
  version: "1.0"
  category: swing-trading
  tags: [swing trading, day trading, price action, simple strategy, pivot]
---

# Swing Trading for Idiots Skill

## Objective
Provide a simple swing/day trading workflow that trades the market using the
Sneaky Pivot ruleset. The skill should help the agent identify the right price
levels, define a three-bar entry setup, set protective stops, and choose target
zones while minimizing complexity.

## Use when
- The user wants a low-friction short-term trading plan for liquid equities,
  ETFs, or futures.
- The user is trading a single 15-minute chart and wants a rule-based approach.
- The user needs a simple, repeatable entry and risk-management framework.

## Inputs
- Required:
  - Asset ticker or symbol.
  - Time frame: 15-minute chart.
  - Previous trading day high and low.
  - Recent swing high and swing low beyond the prior day range.
- Optional:
  - Current market context (trend, gap, earnings, macro events).
  - Preferred risk per trade or stop distance.

## Outputs
- A concise trade plan that includes:
  - Buy or sell bias based on the Sneaky Pivot price bands.
  - Entry condition using the three-candle framework.
  - Stop-loss placement below the big buyer or above the big seller.
  - Target zone aligned to the opposite pivot band.
  - A brief risk/reward assessment.

## Trading rules
1. Use exactly one chart and one timeframe: 15-minute bars only.
2. Identify four magic lines:
   - Range High = previous day high.
   - Range Low = previous day low.
   - Swing High = next meaningful level above Range High.
   - Swing Low = next meaningful level below Range Low.
3. Only trade when price interacts with these lines.
   - Sell at the upper two lines.
   - Buy at the lower two lines.
4. Use the three-candle setup:
   - Candle 1: Opening Range Candle — the first 15-minute bar of the day.
   - Candle 2: Sneaky Candle — confirms legitimacy and direction.
   - Candle 3: Entry Candle — enter when price crosses the Sneaky Candle.
5. Place the stop-loss just below the big buyer or above the big seller.
6. Be patient: wait for the market to ping-pong between the range lines before
   trading.

## Validation and safety gates
- Sneaky Pivot is a hypothesis, not a proven edge. Define “meaningful level,” “big buyer,” “big seller,” and “crosses” numerically before backtesting.
- Add higher-timeframe regime, volatility, spread, liquidity, gap, halt, earnings/news, session, slippage, and execution-delay checks.
- Require risk-per-trade, maximum daily loss, consecutive-loss limit, target, time stop, expected value, sample size, walk-forward validation, and out-of-sample results.
- Reject setup as `NO TRADE` when any gate fails. Never claim one 15-minute chart predicts direction without evidence.

## Output structure
- Trade idea type: Buy or Sell.
- Setup: exact pivot line, entry condition, and relevant candle.
- Stop: protective level and rationale.
- Target: appropriate profit zone along the pivot levels.
- Notes: market context, timing, and execution confidence.

## Research rules
- Keep the strategy simple and avoid adding indicators.
- Do not trade outside the defined four pivot lines.
- Prioritize risk control over market anticipation.
- If the trade does not meet the three-candle criteria, do not take it.
- Distinguish between ideal textbook entries and real-world execution; accept
  that some details will be approximate.

## References
- Use the Sneaky Pivot concept from the provided video summary.
- Frame the logic for swing/day trading across equities, ETFs, or futures.
- Emphasize that good trades are often simple, disciplined, and level-based.
