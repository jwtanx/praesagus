---
name: daily-market-brief
description: >-
  Turn timestamped market, company, macro, and news inputs into a concise
  decision-time research brief. Use for daily market reviews, catalyst tracking,
  event interpretation, and cross-sector or cross-asset impact mapping.
license: MIT
metadata:
  author: praesagus
  version: "2.3"
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

For new daily/week-ahead briefs, author `artifacts/daily-market-brief/YYYY-MM-DD.json` using shared `index.html`, schema version 3 and structured data only (no HTML). Required sections are `outlook`, `top10`, `swing`, `etfs`, `news`, `trends`, `score`; `top10` is a legacy identifier, not a requirement to publish ten stocks. Include timezone-aware metadata/as_of, summary, watchlist_config, forecasts and footer. Calendar content belongs only in the shared monthly ledger; daily JSON has `calendar_ref: ../financial-calendar/YYYY-MM.json`, not inline events or sections.calendar. Update reports.json with the new date/label/latest. Preserve earlier schema-2 snapshots and their original universe; the viewer supports them without rewriting historical forecasts. Keep markup, filters, navigation and mobile behavior in the shared HTML.

Use the October 8 report's concise reading format for new reports: set `metadata.presentation_profile` to `compact-v1` and read [the compact report contract](references/compact-report.md) before authoring or revising one. Keep prices, separate native Moomoo bullish/bearish observation chips and the independent Forecast chip visible; retain detailed provenance and the complete forecast audit behind closed expandable controls. Native signal coverage is currently unavailable; price comparisons and calculated SMA trends cannot substitute for native signals. Keep missing coverage and a short forecast blocker visible. Presentation must not turn an observed signal into a rated forecast. Historical reports without this profile retain their original presentation.

Use the dated report artifact as the normal analysis and dashboard-export flow. Do not route ordinary dashboard generation through the separate private-draft workflow. For each available snapshot, place only the allowlisted price-only point in that report row's `public_snapshot` using `ingest.daily_report_projection.map_public_snapshot`; preserve source, observation, ingestion, known and cutoff times plus explicit unknown-reference fields. Include available schema-compatible snapshot data in the public dated JSON. Keep raw captures, private IDs, account details, credentials and full provider responses out of public output. Validate new compact reports with `python3 scripts/daily-market-brief/validate_report_json.py --date YYYY-MM-DD --public --compact` before publication.

New schema-3 reports collect from `artifacts/daily-market-brief/watchlist-universe-five.json`: exactly five names in each of ten display groups (50 total), with three US/two MY names per group. Selection is a stable cross-market monitoring shortlist, not a validated performance/return ranking. Retain selection rationale and do not churn constituents based on hindsight. Groups: benchmarks/ETFs, Financials, Technology, Semiconductors, Healthcare, Staples, Discretionary, Energy, Industrials/Transport/Logistics, Materials/Plantation. ETFs are not a sector; semiconductors are an industry overlay with distinct constituents. Preserve listing market/currency and classification caveats (curated thematic grouping is not canonical GICS). Record provider/quote timestamp for every observed price, mark missing/stale inputs and their consequences; never infer freshness or fabricate prices. Keep the legacy `watchlist-universe.json` for existing schema-2 reports and audit snapshots.

After the final write for every generated or edited report, run the committed local validator `python3 scripts/daily-market-brief/validate_report_json.py --date YYYY-MM-DD`; add `--public` for a report intended for the public Pages viewer. It validates both legacy/new contracts, sources, unique universe membership, five-name schema-3 coverage, confidence/reasons, shared calendar and report index. Treat validator failure as a stop condition: fix errors and rerun before delivery, commit or publication. The committed validator is the local report-component check; Pages CI also runs it before deployment. Treat direction as conditional research, not a promise or instruction. Include timestamped reference close, target date/horizon, linked bull/bear evidence and invalidation for a defensible prediction. Distinguish next-session from week-end scoring.

For new reports and compact presentation revisions, also pass `--compact` in that same final command. It checks the visible text budgets, collapsed long tables, declared price/signal/reference coverage and support for every rated row. Run it after the last write, including a repair; a prior pass is insufficient. Do not create a second validator or a replacement provider script. Passing these checks establishes declared consistency, not source authenticity or predictive performance. Preserve historical reports without the compact profile when checking the archive.

### Reuse the committed REST collector at each report run

Use `scripts/market_collect.py` for provider intake. Do not generate a new fetch,
signing, Keychain or transport script on each 08:00 run. Reuse the provisioned
AppKey file, encrypted private key and configured Keychain passphrase through
the existing loader; see [safe access guidance](../../README.md#moomoo-rest-access-for-agents)
and [collector contract](../../docs/PRIVATE_MARKET_COLLECTOR.md). Read private
operational locator metadata only from the authorized role context, never copy
actual paths/identifiers or credential values into public reports.

1. Verify the approved Python >=3.11 collector environment (including cryptography),
   existing owned private store and approved nonsecret plan before collection.
   The system `python3` may be older; use the privately verified interpreter.
   A missing store, locator, runtime or plan is a concrete setup blocker, not
   permission to create new credentials, initialize a store or improvise a client.
2. Derive the plan from the existing five-name universe: the 30 supported US codes,
   approved history entries `{code,end}` and bounded news queries when needed.
   The committed plan validator controls supported fields and job limits. History
   jobs use daily `ktype=2`, unadjusted `autype=0`, `num=100` and omit start; use
   the intended completed-session end, not an inferred final close. MY remains
   explicitly unsupported by this collector. Reuse the plan structure; only
   authorized universe/date/query inputs and the unique run ID change.
3. Invoke the existing CLI from the repository root using private operational
   locators. The example below contains placeholders, not credential values:

   ```sh
   /absolute/path/to/approved/python scripts/market_collect.py \
     --root /absolute/private/store \
     --plan /absolute/private/nonsecret-plan.json \
     --credential-directory /absolute/private/credentials \
     --app-key-name configured-appkey-filename \
     --run-id unique-approved-report-run
   ```

   Jobs are serial, with a 20-second worker deadline and a 300-second admission
   budget; a full snapshot/history/news plan is not guaranteed to finish in that
   budget. Keep CLI summaries (which include private run/attempt IDs) in private
   operational evidence; public diagnostics contain only controlled status and
   coverage counts. Record exit/status/failure, including partial, empty and
   missing results. Do not retry indefinitely or dump worker credentials,
   private IDs, provider bodies or prices into diagnostics.
4. Freeze the report cutoff honestly. Intake received/ingested after it is
   unavailable for that cutoff; never backdate collection to 08:00. If this
   08:00 invocation is the first intake, use its actual later as-of time and state
   the delay. Only use prior captures when their recorded times, freshness and
   source contract actually qualify. An already elapsed pre-cutoff window is not
   satisfied by starting the collector late.
5. Reuse `PrivateMarketStore` and
   `ingest.daily_report_projection.project_public_market_snapshot` in memory to
   select same-run eligible points for the existing universe. Copy only each
   matching row's allowlisted `public_snapshot` into the normal dated report; the
   projector already uses `map_public_snapshot`. Preserve null prices and explicit
   gaps for unavailable rows. Do not publish the whole private store/projection
   object, and do not route normal report generation through
   `run_private_quote_report.py` or `project_private_quotes.py`. No committed CLI
   currently authors the full normal narrative report automatically; authoring
   that report remains Trader's task, not a reason to rewrite provider intake.
6. Continue the existing narrative/calendar/forecast workflow and, after the final
   dated report/index write, run the committed public report validator with
   `--compact` for the new compact report. Collection
   success alone establishes neither financial eligibility nor publication rights.

### Shared monthly financial calendar

Initialize `artifacts/financial-calendar/YYYY-MM.json` once for each month; do not ingest a duplicate calendar into each daily report. At each report run, recheck relevant primary schedules and cancellation/rescheduling notices. If nothing changed, reuse the existing month unchanged. Append new events or complete revisions using `scripts/daily-market-brief/monthly_calendar.py --month YYYY-MM --input INPUT.json --recorded-at ISO_TIMESTAMP`; INPUT has events (stable event_id and full source-backed fields) and optional initial notes. Use actual availability time, never backdate a newly discovered correction to justify a prior forecast.

Ledger entries retain event_id, increasing revision, recorded_at with timezone, date/date_end, kind, title, time, summary/details, sources, status scheduled/cancelled and change_reason. recorded_at is when evidence became available in this workflow (normally discovery/retrieval); preserve the notice's published_at and retrieved_at separately in sources. Do not substitute earlier publication for later workflow discovery. Legacy imports may preserve demonstrable earlier report availability with inherited_from and an explicit limitation, not claim new verification. Corrections/cancellations require a specific justification and official notice where available; disappearance from a feed is not evidence of cancellation. Never remove or rewrite earlier entries. A monthly repeat with identical full events is a no-op. The viewer preserves as-of availability, shows cancelled/superseded records struck through with a reason alongside, and makes missing month data visible. Superseded reasons come from the eligible replacement revision, never a later-than-cutoff correction. Distinguish exchange closures from public holidays; convert source-session dates into MYT carefully. This utility is not an unattended scheduler; monthly initialization/daily rechecks occur in the authorized report workflow.

Use one configured quote provider per market and retain its response, timestamp, currency, adjustment basis, retrieval time, and status. Do not silently switch providers or infer that a quote-reference website supplied a vendor snapshot. A trend marker is a time-sensitive observation, not a durable recommendation. Use available Moomoo snapshot data in the normal dated dashboard report and label source, timestamps, coverage and limitations. Proceed through report validation and export with available allowlisted snapshots. The direct Moomoo REST adapter and manual collector are implemented; reuse the committed collector described above for scheduled intake. Bounded authenticated REST history was verified on 2026-10-11 MYT, which does not guarantee future coverage, entitlements or complete report-universe intake. The collector does not schedule itself. If configured intake is unavailable, keep the provider failure and coverage gaps visible; do not silently substitute ad hoc web quotes. Official exchanges/regulators/issuer releases remain the source for calendars, filings and catalysts; forecasts are separate research output.

The existing `moomoo_session_direction` (latest quote versus provider previous close) and `moomoo_trend` (SMA-5 versus SMA-20 over completed daily bars) are calculated proxies retained in raw provenance. Do not display them as native Moomoo bullish/bearish signals or force their agreement into forecast direction. Native KDJ/MACD/Bollinger observations require actual provider output under an accepted intake scope; expand their chips to show each native indicator/pattern, exact rule and parameters, timeframe, signal, source, observation/availability times and coverage. Preserve unknown fields explicitly. Missing, failed, unsupported or unverified coverage is unavailable, never zero or neutral; an empty successful screener response alone does not prove no signal. Deduplicate native matches; screener totals count matching securities, not per-ticker events. Keep counts separate from forecast direction and confidence: observations are not probabilities or numeric targets. Assess forecasts independently using the existing supported method, frozen reference/horizon, bull/bear evidence and invalidation; withhold unsupported targets and explain the gap. See the compact contract for native coverage limits and delivery replays.

Each prediction must have `confidence` (`low`, `medium`, `high`, `unavailable`) and nonblank `confidence_reason`, visible in the viewer. These are qualitative evidence judgments, not calibrated probabilities or quote-quality scores. Do not upgrade confidence simply to fill the table: explain method support, contradictory evidence and missing inputs. Missing price means quote_status missing, price null and data_gaps. Without a defensible target, forecast_status unavailable, direction unknown, confidence unavailable and all target/range numeric fields null; display Unrated rather than sideways or an invented percentage. Preserve confidence filters/sorting. Price sorting uses nominal listing currency: select a market before comparing USD/MYR; missing values sort last.

At publication, immediately freeze every rated report prediction in `harness/engineering/price-prediction/forecast-ledger.csv`, before its target outcome is observable. Copy the original report date and forecast timestamp, market/venue/ticker, horizon, reference close date/value/source, target date, direction, range, confidence and thesis/confirmation/invalidation exactly; assign a unique `forecast_id`, leave actual fields blank and set status to pending. Keep an `actual_available_at` column for the timezone-aware time the close became available to this workflow. Do not revise a frozen signal or reconstruct its values from later data. At each later report, reconcile the previous report's rated rows against the ledger and restore any missing issuance from the preserved report snapshot without treating it as a new forecast.

Score a forecast only after its target venue session has closed and a comparable final close is available. Append the target-date close, source and URL, currency/adjustment basis, and timezone-aware `actual_available_at`, then run `harness/forecast_review.py` at an explicit review timestamp. A target date arriving on the calendar does not prove that the venue has closed; if the close is still in the future or unavailable, leave the outcome pending and say why. For direction scoring, Bullish/`up` is a hit only when actual close exceeds the reference close; Bearish/`down` is a hit only when it is lower. Sideways/`flat` is excluded from directional hit/miss counts. Score a range hit only when the close is inside the frozen inclusive bounds. Report the scored denominator, pending/unavailable rows and range coverage separately; do not claim accuracy from unscored, correlated or small cohorts. `harness/forecast_review.py` implements offline deterministic ledger validation/outcome scoring at an explicit review time; it does not fetch or verify prices.

**Required daily forecast follow-through (Trader):** At every scheduled daily report run, audit the full ledger for pending forecasts whose target venue session has closed, including older unresolved rows rather than only yesterday's report. Resolve each eligible row from a verified source with comparable final-close data; retain source URL, venue/listing currency, adjustment basis and timezone-aware `actual_available_at`, then run the evaluator at the report cutoff. Never infer a close from an intraday snapshot or silently treat a missing source as a completed review. If a matured row cannot be verified, surface the exact unresolved count, affected cohort/venues, concrete source or data blocker, and next scheduled recheck in the delivered report findings. The run is complete only when each matured row is either scored or explicitly listed as blocked; do not wait for the human to ask for a follow-up. When targets have not yet closed, state the next venue-close/review timing. Preserve report snapshots/source provenance so scoring uses only forecast-time information. This is a scheduled workflow instruction, not a price-feed runtime; the evaluator remains offline and deterministic.

### GitHub Pages publishing

Daily-report-only commits must start with `[REPORT] YYYYMMDD`, using the report's MYT date, for example `[REPORT] 20261001` or `[REPORT] 20261001 Refresh morning market report`. The `commit-msg` hook enforces the prefix and a valid calendar date for nonempty staged changes confined to `artifacts/daily-market-brief/`. Mixed changes, empty commits and renames crossing that boundary require `PRSG-<number> <description>`. Always write ticket identifiers with the dash in titles, messages and handoffs (for example `PRSG-8`, never `PRSG8`). Install the versioned hook with `sh scripts/install_git_hooks.sh` when needed; preserve existing hooks. Do not rewrite previously published commit titles.

The shared report viewer is `artifacts/daily-market-brief/index.html`; it renders structured dated JSON from the same directory and uses `reports.json` to populate a calendar date picker that disables dates without reports. Its main navigation includes a Financial Calendar with event and market-closure markers, keyboard/mouse details, and tap-to-open event notes on mobile. The Pages workflow runs the JSON validator before deployment and publishes the `artifacts` tree. Update the shared `artifacts/index.html` landing page as needed, keep JSON/index paths relative and same-origin, and verify both a current report and the date picker in the deployed mobile view. A successful push or commit does not itself prove deployment; verify the GitHub Pages Actions run and the live URL before reporting it.

This skill guides the active Trader and its bounded research support. Sol 6.1 Low subagents and Sol 6.1 Medium for Trader synthesis are preferred settings, not prerequisites; use the current supported runtime/model if they are unavailable or cannot be verified, and do not delay report generation for model checks. The intended 08:00 MYT schedule is defined in agent-operations/schedules/trader-daily-report.md and transferred through skills/spawn/SKILL.md; legacy Researcher ownership persists until verified takeover. These instructions do not create a schedule or guarantee execution.

## Moomoo inputs

Moomoo news and anomaly outputs are discovery inputs. Verify material claims against primary sources where possible. Treat sentiment as a sampled discussion measure; technical anomalies as indicators rather than direction; and capital-flow, derivatives, or broker activity as ambiguous evidence. Check source timestamps, entitlement/coverage limits, liquidity, event overlap, and whether the item may already be priced in. Do not describe repository Moomoo routes as a push feed or trading interface: the implemented Praesagus adapter is read-only and request/response.

## Boundaries

- Do not imply that this skill monitors markets continuously or runs on a schedule.
- Do not provide personalized allocations, order instructions, or certainty unsupported by evidence.
- Do not call suspected manipulation established fact without documented evidence; explain plausible mechanisms and competing explanations separately.
- For a full investment or trade decision, use `praesagus-trading-orchestrator` and the shared requirements in `skill-template`.
