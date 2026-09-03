---
name: alpha-signal-engine
description: >-
  Create a signal-engineering research framework that defines alpha signals,
  validates factor performance, and recommends a signal mix for alpha-oriented
  portfolios.
disable-model-invocation: true
---

# Alpha Signal Engine Skill

## Objective
Develop a systematic alpha generation framework by defining signals, testing
their predictive power, and combining them into a diversified alpha engine for
investable strategies.

## Outputs
- Signal taxonomy and definitions
- Historical and cross-sectional evidence
- Signal correlation and diversification analysis
- Portfolio construction and risk budgeting
- Implementation recommendations

## Required Sections
1. Executive summary
2. Signal universe and rationale
3. Empirical evidence and backtest assumptions
4. Signal interaction and correlation
5. Construction and weighting rules
6. Risk management and capacity analysis
7. Recommendation and monitoring plan

## Research Rules
- Define signals precisely: mean reversion, momentum, quality, earnings revision,
  sentiment, macro, or alternative data.
- Use historical evidence, regime analysis, and cross-sectional validation.
- Quantify correlation and risk to avoid concentrated signal exposure.
- Include practical considerations: turnover, transaction costs, capacity, and
  crowding.
- Provide a monitoring plan for when signals degrade or market regimes shift.
- Require sample size, benchmark, train/test or walk-forward split, out-of-sample result, transaction costs, spread, slippage, execution delay, turnover, capacity, drawdown, survivorship-bias and look-ahead-bias checks.
- Define kill-switch thresholds before reviewing results. Do not promote an unvalidated signal to trade-ready.

## Output Template
- Signal set: primary and supporting signals.
- Expected alpha: directional / relative / opportunistic.
- Suggested allocation: core / satellite / tactical overlay.
- Performance guardrails: risk budget, turnover limits, drawdown control.
