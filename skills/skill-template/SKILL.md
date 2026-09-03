---
name: skill-template
description: Template for a Praesagus skill. Use when adding new investment, research, or signal skills to ensure consistent metadata, activation guidance, inputs, outputs, and workflow structure.
license: MIT
compatibility: Works with Agent Skills-compatible environments; no special runtime required unless referenced scripts exist.
metadata:
  author: praesagus
  version: "1.0"
  category: skill-template
  tags: [template, skill, research, finance]
---

# Praesagus Skill Template

## Overview
Summarize the skill purpose, the domain it covers, and the type of problem it solves.

## Use when
- The user asks for ...
- The task requires ...
- The output must do ...

## Clarify first
Before executing, ask for any missing or ambiguous information:
- What is the exact decision or use case?
- What asset class, sector, region, or time horizon is in scope?
- Which inputs are required versus optional?
- What level of confidence is needed?

## Inputs
- Required inputs:
  - ...
- Optional inputs:
  - ...
- Data sources and expectations:
  - ...
- Assumptions and scope boundaries:
  - ...

## Outputs
Describe the expected deliverable and structure.
- Executive summary
- Key conclusions
- Supporting evidence and analysis
- Risks / downside factors
- Recommendation and suggested action
- Assumptions and caveats

## Workflow
1. Define the objective and decision context.
2. Collect and validate data.
3. Analyze the opportunity or risk.
4. Build the narrative and evidence.
5. Summarize recommendation, conviction, and horizon.
6. List assumptions and follow-up questions.

## Research rules
- Use reliable public sources and validate calculations.
- Do not fabricate numbers or precise metrics without supporting evidence.
- Clearly label assumptions and confidence levels.
- Treat model outputs as drafts unless verified.

## Shared evidence and risk contract
- Record `as_of`, publication time, data-available time, timezone, and data period for every material claim.
- Prefer Tier 1 sources (filings, regulators, exchanges, central banks, official statistics), then Tier 2 company disclosures and verified transactions, Tier 3 reputable vendors, Tier 4 news and analyst commentary, Tier 5 social or anecdotal evidence.
- Separate facts, interpretation, and recommendation. Link every material claim to source URL, source tier, publication date, limitation, and extraction date.
- Never use information published after the decision timestamp in an ex-ante thesis or backtest.
- Mark missing, stale, revised, proxy, model-generated, and conflicting data. Do not fill gaps with plausible numbers.
- Treat news, sentiment, capital flow, derivatives, and technical anomalies as supporting evidence until independently validated; deduplicate shared events and sources.
- Every directional output must include bull case, bear case, strongest disconfirming evidence, invalidation trigger, review date, and `NO TRADE` condition.
- Actionable outputs must include entry, exit, stop, time stop, expected value, maximum loss, risk-based position size, liquidity/slippage/fees, borrow or funding risk, and portfolio concentration.
- Backtests must state sample size, benchmark, train/test or walk-forward split, corporate-action handling, transaction costs, spread, slippage, execution delay, survivorship bias, look-ahead leakage, turnover, capacity, drawdown, and out-of-sample result.
- Confidence must distinguish evidence grade, directional confidence, timing confidence, and magnitude confidence. Confidence never replaces missing validation.
- Default classification: `research only`, `watchlist`, `paper trade`, `human approval required`, or `execution-ready`. Live execution always requires human approval and independent risk checks.

## Output template
- Decision: buy / hold / reduce / avoid / short / hedge / monitor / `NO TRADE`
- Classification: research only / watchlist / paper trade / human approval required / execution-ready
- Evidence grade: A / B / C / D
- Directional / timing / magnitude confidence: 0–100% each
- Time horizon: intraday / swing / event-driven / 3–12 months / structural
- Primary drivers: ...
- Bull / base / bear cases and probabilities: ...
- Strongest disconfirming evidence: ...
- Key risks: ...
- Entry / exit / stop / time stop: ...
- Expected return / maximum loss / position size: ...
- Liquidity, cost, correlation, and approval checks: ...
- Invalidation and next review date: ...

## References
- Use `references/` for deeper guidance, examples, formulas, or data definitions.
- Use `scripts/` for reusable calculation tools or validation helpers.
- Keep `SKILL.md` focused; move lengthy reference material into supporting files.
