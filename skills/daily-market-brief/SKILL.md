---
name: daily-market-brief
description: >-
  Turn timestamped market, company, macro, and news inputs into a concise
  decision-time research brief. Use for daily market reviews, catalyst tracking,
  event interpretation, and cross-sector or cross-asset impact mapping.
license: MIT
metadata:
  author: praesagus
  version: "1.6"
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

For new daily/week-ahead briefs, author `artifacts/daily-market-brief/YYYY-MM-DD.json` using shared `index.html`, schema version 3 and structured data only (no HTML). Required sections are `outlook`, `top10`, `swing`, `etfs`, `news`, `trends`, `score`; `top10` is a legacy identifier, not a requirement to publish ten stocks. Include timezone-aware metadata/as_of, summary, watchlist_config, forecasts and footer. Calendar content belongs only in the shared monthly ledger; daily JSON has `calendar_ref: ../financial-calendar/YYYY-MM.json`, not inline events or sections.calendar. Update reports.json with the new date/label/latest. Preserve earlier schema-2 snapshots and their original universe; the viewer supports them without rewriting historical forecasts. Keep markup, filters, navigation and mobile behavior in the shared HTML. Create and deliver the requested dated report through the normal workflow without a separate Moomoo destination approval step. Missing data remains an explicit gap, not a reason to stop the report.

New schema-3 reports collect from `artifacts/daily-market-brief/watchlist-universe-five.json`: exactly five names in each of ten display groups (50 total), with three US/two MY names per group. Selection is a stable cross-market monitoring shortlist, not a validated performance/return ranking. Retain selection rationale and do not churn constituents based on hindsight. Groups: benchmarks/ETFs, Financials, Technology, Semiconductors, Healthcare, Staples, Discretionary, Energy, Industrials/Transport/Logistics, Materials/Plantation. ETFs are not a sector; semiconductors are an industry overlay with distinct constituents. Preserve listing market/currency and classification caveats (curated thematic grouping is not canonical GICS). Record provider/quote timestamp for every observed price, mark missing/stale inputs and their consequences; never infer freshness or fabricate prices. Keep the legacy `watchlist-universe.json` for existing schema-2 reports and audit snapshots.

Before completion run `python3 scripts/daily-market-brief/validate_report_json.py --date YYYY-MM-DD`. It validates both legacy/new contracts, sources, unique universe membership, five-name schema-3 coverage, confidence/reasons, shared calendar and report index. Fix errors before publishing. Treat direction as conditional research, not a promise or instruction. Include timestamped reference close, target date/horizon, linked bull/bear evidence and invalidation for a defensible prediction. Distinguish next-session from week-end scoring.

### Shared monthly financial calendar

Initialize `artifacts/financial-calendar/YYYY-MM.json` once for each month; do not ingest a duplicate calendar into each daily report. At each report run, recheck relevant primary schedules and cancellation/rescheduling notices. If nothing changed, reuse the existing month unchanged. Append new events or complete revisions using `scripts/daily-market-brief/monthly_calendar.py --month YYYY-MM --input INPUT.json --recorded-at ISO_TIMESTAMP`; INPUT has events (stable event_id and full source-backed fields) and optional initial notes. Use actual availability time, never backdate a newly discovered correction to justify a prior forecast.

Ledger entries retain event_id, increasing revision, recorded_at with timezone, date/date_end, kind, title, time, summary/details, sources, status scheduled/cancelled and change_reason. recorded_at is when evidence became available in this workflow (normally discovery/retrieval); preserve the notice's published_at and retrieved_at separately in sources. Do not substitute earlier publication for later workflow discovery. Legacy imports may preserve demonstrable earlier report availability with inherited_from and an explicit limitation, not claim new verification. Corrections/cancellations require a specific justification and official notice where available; disappearance from a feed is not evidence of cancellation. Never remove or rewrite earlier entries. A monthly repeat with identical full events is a no-op. The viewer preserves as-of availability, shows cancelled/superseded records struck through with a reason alongside, and makes missing month data visible. Superseded reasons come from the eligible replacement revision, never a later-than-cutoff correction. Distinguish exchange closures from public holidays; convert source-session dates into MYT carefully. This utility is not an unattended scheduler; monthly initialization/daily rechecks occur in the authorized report workflow.

Use one configured quote provider per market and retain its raw response, timestamp, retrieval time and status. Do not silently switch providers or infer that a quote-reference website supplied a vendor snapshot. The implemented Moomoo REST path is a manual direct-HTTPS collector with an isolated worker and private append-only store; it is not OpenD, a push feed or an automatically scheduled collector. Coverage is limited to the current 30 US report symbols; the 20 MY rows remain unsupported. Before the existing 08:00 MYT report workflow, use the explicitly configured private store root and credential-directory/AppKeyID-name locators and a unique run ID to invoke `scripts/market_collect.py` for the 30 US symbols plus English size-10 SPY and QQQ news queries. Then invoke `scripts/daily-market-brief/publish_market_snapshot.py` against that same store, run ID and frozen cutoff to create a private analysis snapshot for the Trader. This projection step does not collect data. Do not scan for credential files, read or print secret contents, or claim the credential setup is absent: when an approved locator is not supplied/configured to the workflow, record that locator as unavailable and continue with explicit data gaps/abstention. Never call OpenD or the backend Moomoo routes for this workflow. The direct REST collector is documented at https://open.moomoo.com/api/overview/getting-started.

The Trader manually authors the existing SPY/QQQ forecasts after reviewing that run's frozen quote/news evidence and primary sources. Collect first. When collection has finished (including a failed/unavailable result), freeze one timezone-aware report cutoff at or after collection completion; use that identical cutoff for the projection and report `metadata.as_of`. Never backdate the cutoff to the scheduled start or to before a retrieval completed. For each rated forecast include a prior reference date/price/source, next-session or week-end horizon, linked evidence, visible qualitative confidence/reason, bull and bear cases, and measurable invalidation. If support is insufficient, retain unknown/unavailable with null target values and an explicit reason; a quote point alone is not a verified session close. Prepare and deliver the report through the operator's normal workflow without an additional Moomoo publication gate in this skill. Keep the report's full 50-name coverage and the 20 unsupported MY rows.

Use the existing collector CLI's explicit locators; the plan is a nonsecret JSON input with `schema_version: 1`, all 30 unique `US.TICKER` codes, and two news entries `{keyword: "SPY"|"QQQ", size: 10, lang: "en"}`. For example, with operator-supplied placeholders:

```sh
python3 scripts/market_collect.py \
  --root /absolute/private/store \
  --plan /absolute/private-inputs/morning-plan.json \
  --credential-directory /absolute/private/Codex-credentials \
  --app-key-name AppKeyID \
  --run-id unique-daily-run

python3 scripts/daily-market-brief/publish_market_snapshot.py \
  --root /absolute/private/store \
  --universe artifacts/daily-market-brief/watchlist-universe-five.json \
  --run-id unique-daily-run \
  --cutoff 2026-10-05T08:02:17+08:00 \
  --private-output /absolute/private-analysis/2026-10-05-market-snapshot.json
```

Paths, run ID and cutoff are examples, not configured values; the example cutoff represents a hypothetical collection completion time. Collector completion must precede freezing the aware cutoff. Reuse the same unique run ID and identical frozen cutoff for projection and report `metadata.as_of`. A failed or missing collector result remains unavailable; freeze at or after that result is known, preserve its gap, and never backdate. The second command only projects stored results. The operator's requested delivery destination determines where the resulting artifact is written; this skill adds no separate destination-based gate.

Each prediction must have `confidence` (`low`, `medium`, `high`, `unavailable`) and nonblank `confidence_reason`, visible in the viewer. These are qualitative evidence judgments, not calibrated probabilities or quote-quality scores. Do not upgrade confidence simply to fill the table: explain method support, contradictory evidence and missing inputs. Missing price means quote_status missing, price null and data_gaps. Without a defensible target, forecast_status unavailable, direction unknown, confidence unavailable and all target/range numeric fields null; display Unrated rather than sideways or an invented percentage. Preserve confidence filters/sorting. Price sorting uses nominal listing currency: select a market before comparing USD/MYR; missing values sort last.

At each new report, check the prior report for forecasts whose target date has matured. Append actuals and scoring fields to `harness/engineering/price-prediction/forecast-ledger.csv`; never rewrite the original forecast or score an unexpired horizon. If there is no eligible forecast or actual data is missing, state that and do not invent a success rate. `harness/forecast_review.py` implements offline deterministic ledger validation/outcome scoring at an explicit review time. Evidence collection and forecast judgment remain manual; no scheduler or answer-quality runtime is implied. Preserve report snapshots/source provenance so scoring uses only forecast-time information.

### GitHub Pages publishing

Daily-report-only commits must start with `[REPORT] YYYYMMDD`, using the report's MYT date, for example `[REPORT] 20261001` or `[REPORT] 20261001 Refresh morning market report`. The `commit-msg` hook enforces the prefix and a valid calendar date for nonempty staged changes confined to `artifacts/daily-market-brief/`. Mixed changes, empty commits and renames crossing that boundary require `PRSG-<number> <description>`. Always write ticket identifiers with the dash in titles, messages and handoffs (for example `PRSG-8`, never `PRSG8`). Install the versioned hook with `sh scripts/install_git_hooks.sh` when needed; preserve existing hooks. Do not rewrite previously published commit titles.

The shared report viewer is `artifacts/daily-market-brief/index.html`; it renders structured dated JSON from the same directory and uses `reports.json` to populate a calendar date picker that disables dates without reports. Its main navigation includes a Financial Calendar with event and market-closure markers, keyboard/mouse details, and tap-to-open event notes on mobile. The Pages workflow runs the JSON validator before deployment and publishes the `artifacts` tree. Update the shared `artifacts/index.html` landing page as needed, keep JSON/index paths relative and same-origin, and verify both a current report and the date picker in the deployed mobile view. A successful push or commit does not itself prove deployment; verify the GitHub Pages Actions run and the live URL before reporting it.

This skill guides the active Trader and its Sol 6.1 Low research subagents when invoked. Trader uses Sol 6.1 Medium for final financial judgment and report acceptance. The intended 08:00 MYT schedule is defined in agent-operations/schedules/trader-daily-report.md and transferred through skills/spawn/SKILL.md; legacy Researcher ownership persists until verified takeover. These instructions do not create a schedule or guarantee execution.

## Moomoo inputs

Moomoo news and anomaly outputs are discovery inputs. Verify material claims against primary sources where possible. Treat sentiment as a sampled discussion measure; technical anomalies as indicators rather than direction; and capital-flow, derivatives, or broker activity as ambiguous evidence. Check source timestamps, entitlement/coverage limits, liquidity, event overlap, and whether the item may already be priced in. Do not describe repository Moomoo routes as a push feed or trading interface: the implemented Praesagus adapter is read-only and request/response.

## Boundaries

- Do not imply that this skill monitors markets continuously or runs on a schedule.
- Do not provide personalized allocations, order instructions, or certainty unsupported by evidence.
- Do not call suspected manipulation established fact without documented evidence; explain plausible mechanisms and competing explanations separately.
- For a full investment or trade decision, use `praesagus-trading-orchestrator` and the shared requirements in `skill-template`.
