---
name: daily-market-brief
description: >-
  Turn timestamped market, company, macro, and news inputs into a concise
  decision-time research brief. Use for daily market reviews, catalyst tracking,
  event interpretation, and cross-sector or cross-asset impact mapping.
license: MIT
metadata:
  author: praesagus
  version: "1.2"
  category: market-research
  tags: [daily-brief, catalysts, news, provenance, market-research]
---

# Daily Market Brief

## Purpose

Synthesize a defined set of market and news inputs into a dated, evidence-linked brief. The brief explains what changed, what may matter next, and what evidence could disconfirm the read. It is research support, not an order or personalized investment recommendation.

## Use when

- The user provides daily news, market data, a watchlist, or asks for a market/catalyst recap.
- The task connects an event to affected companies, sectors, commodities, rates, currencies, or indices.
- Timestamped Moomoo news, sentiment, quote, or anomaly outputs need contextual interpretation.

## Inputs

- Required: the question or decision context and an `as_of` cutoff with timezone. If the user supplies a dated batch, use its latest stated availability time as the cutoff unless they specify otherwise.
- Optional: instruments/watchlist, market session, horizon, portfolio context, prior thesis, and source material.
- For each item, capture source/provider, source URL when available, publication time, retrieval/availability time, timezone, period covered, and any known limitation.

If the cutoff, market, or instrument ambiguity could change the result, state the ambiguity and ask only the necessary question. Otherwise state the working assumption.

## Workflow

1. Freeze the decision-time information set: cutoff, timezone, market session, and date range. Exclude later information from the contemporaneous read; label it separately if the user asks for hindsight review.
2. Inventory and deduplicate items by underlying event and source lineage. Syndicated copies, reposts, sentiment, price moves, and flow/anomaly outputs tied to one catalyst are not independent confirmations.
3. Rank evidence by directness: regulator/exchange/filing/official release and official statistics first, company statements next, reputable reporting/vendor data after that, then social or anecdotal material. Preserve contradictory accounts.
4. Separate each material statement into observed data, source-reported claim, interpretation, or scenario inference. Do not turn correlation or a market move into proof of causality, intent, manipulation, or informed positioning.
5. For cross-market implications, show each causal link and label it `observed`, `sourced`, or `scenario inference` (for example: conflict → shipping disruption → delivered energy prices → inflation expectations → exposed sectors). Mark unsupported or broken links.
6. Assess what is new versus already known or potentially priced in. Use only supplied or verifiable price/context data; do not invent price reaction, consensus, probabilities, or freshness.
7. Present bull and bear evidence, strongest disconfirmation, uncertainty/data gaps, and a measurable trigger that would change the view.
8. Assign a proportionate action class: `research only`, `watchlist`, `paper trade`, `human approval required`, or `NO TRADE`. Do not use `execution-ready` as a substitute for the orchestrator's full validation gates.

## Output

Use a concise brief with:

- **As of** — cutoff, timezone, session, and input window.
- **What changed** — key developments ranked by evidence and likely relevance.
- **Catalyst chain** — explicit links labeled `observed`, `sourced`, or `scenario inference`.
- **Affected assets/sectors** — exposure mechanism and time horizon; state when the link is uncertain.
- **Bull / bear evidence** — include the strongest disconfirming item.
- **What would change the view** — measurable invalidation or follow-up trigger.
- **Data limits and provenance** — missing timestamps, stale inputs, source quality, duplicate coverage, and URLs.
- **Action class** — research only / watchlist / paper trade / human approval required / NO TRADE, with a short reason.

## Daily market brief artifact

When the user asks for a daily or week-ahead market brief, use `artifacts/daily-market-brief/template.html` and save a dated report as `artifacts/daily-market-brief/YYYY-MM-DD.html`. Preserve the template's section slider/action bar and include a TL;DR. Treat ticker direction as conditional scenario analysis, not a promise or personalized instruction. Include the exact reference close, target date, and horizon for every scored directional forecast; distinguish a next-session (T-1 to T) evaluation from a week-end forecast.

At each new report, check the prior report for forecasts whose target date has matured. Append actuals and scoring fields to `harness/engineering/price-prediction/forecast-ledger.csv`; never rewrite the original forecast or score an unexpired horizon. If there is no eligible prior forecast or actual data is missing, record that plainly and do not invent a success rate. The accompanying harness README defines this manual, proposed workflow; it is not runtime-enforced or an automated scheduler. Preserve report snapshot and source provenance so scoring uses only the forecast-time information set.

### GitHub Pages publishing

The HTML report and template are self-contained (inline CSS/JavaScript, no build step). To publish them, enable GitHub Pages for the repository with the `artifacts` directory as the published static site source (or configure a Pages workflow that copies `artifacts/` into the deployment root). Keep `artifacts/daily-market-brief/YYYY-MM-DD.html` and `artifacts/daily-market-brief/template.html` in the published tree; relative assets/links should remain within that tree. The dated report path will then be `/daily-market-brief/YYYY-MM-DD.html` under the Pages site URL. Check the mobile viewport and slider/navigation on the deployed page after publication. A committed report alone does not publish Pages; repository Pages settings/workflow and a successful deployment are required. Do not enable Pages, change repository settings, or claim a public URL unless explicitly configured and verified.

This skill describes how the active Codex task/agent generates a report when invoked. It does not create an 8:00 a.m. MYT schedule, run autonomously every day, or assign report generation to the `Researcher` chat. Researcher may provide a one-time research task when asked, but daily generation requires an explicitly configured automation or external scheduler and an available market-data/news workflow.

## Moomoo inputs

Moomoo news and anomaly outputs are discovery inputs. Verify material claims against primary sources where possible. Treat sentiment as a sampled discussion measure; technical anomalies as indicators rather than direction; and capital-flow, derivatives, or broker activity as ambiguous evidence. Check source timestamps, entitlement/coverage limits, liquidity, event overlap, and whether the item may already be priced in. Do not describe repository Moomoo routes as a push feed or trading interface: the implemented Praesagus adapter is read-only and request/response.

## Boundaries

- Do not imply that this skill monitors markets continuously or runs on a schedule.
- Do not provide personalized allocations, order instructions, or certainty unsupported by evidence.
- Do not call suspected manipulation established fact without documented evidence; explain plausible mechanisms and competing explanations separately.
- For a full investment or trade decision, use `praesagus-trading-orchestrator` and the shared requirements in `skill-template`.
