---
name: technical-trend-analysis
description: >-
  Analyze timestamped OHLCV or chart data for market structure, trend, relative
  strength, volatility, and conditional levels across stated timeframes. Use for
  technical trend reviews and as a specialist input to event or daily briefs.
license: MIT
metadata:
  author: praesagus
  version: "1.0"
  category: market-research
  tags: [technical-analysis, trend, price-action, risk]
---

# Technical Trend Analysis

## Purpose

Describe the trend and observable price structure from supplied or verifiable market data. Technical patterns and indicators describe historical prices; they do not establish fundamentals, investor intent, or future direction.

## Use when

- The user asks for a technical trend, support/resistance, chart, or indicator review.
- The user needs a technical view alongside dated news, catalysts, or a broader market brief.
- Moomoo technical-anomaly output needs checking against price context.

## Inputs

- Required: instrument/venue, data source, observation window, bar interval, and `as_of` timestamp with timezone.
- Optional: adjusted/unadjusted basis, benchmark, session, volume, volatility, and named indicators or levels to evaluate.
- If only a chart image or partial series is supplied, describe the visible scope and limitations. Do not infer missing bars or corporate-action adjustments.

## Workflow

1. Freeze the decision timestamp and identify whether inputs are intraday, delayed, end-of-day, adjusted, or incomplete.
2. Summarize higher-timeframe and requested-timeframe structure separately: swing sequence, range, gaps, realized volatility, and relative performance when comparable data exists.
3. Calculate or inspect only indicators supported by the inputs. State the window, formula/convention when material, and whether a signal is observed or inferred.
4. Mark support/resistance as zones derived from disclosed pivots, ranges, or repeated reactions. Avoid false precision and claims that a level is defended by a particular participant unless evidence identifies that participant.
5. Compare price/volume behavior with relevant event timestamps. Treat timing alignment as association unless a causal link is independently supported.
6. Give conditional scenarios: what price/data behavior would strengthen or weaken each read. Include the strongest contrary technical evidence.
7. If a trade setup is requested, hand off to `praesagus-trading-orchestrator`; classify an unvalidated setup as `research only`, `watchlist`, `paper trade`, or `NO TRADE` as appropriate.

## Output

- **As of / data** — source, timestamp, timezone, interval, adjustment basis, and coverage.
- **Trend** — direction/structure by timeframe and relative strength if available.
- **Key zones** — derivation and conditions that would invalidate them.
- **Momentum / volatility** — indicator values or observed behavior, with calculation limits.
- **Scenarios** — conditional continuation and reversal evidence, including the strongest disconfirmation.
- **Event context** — dated overlap with catalysts, without asserting causality from timing alone.
- **Confidence and gaps** — distinguish data quality from directional confidence.
- **Action class** — research only / watchlist / paper trade / human approval required / NO TRADE.

## Moomoo technical anomaly inputs

Report the provider's anomaly and timestamp faithfully, then interpret it as a signal to inspect. A technical-anomaly alert is not a standalone trend conclusion or trade trigger. Validate the underlying price series, market/session, indicator definition, and broader timeframe. If the underlying series or alert provenance is unavailable, state that limitation.

## Boundaries

- Do not claim predictive accuracy without a defined, reproducible out-of-sample test including costs and execution assumptions.
- Do not call a setup execution-ready based on chart structure alone.
- Do not imply continuous quotes, streaming, or automated monitoring from a request-scoped snapshot.
