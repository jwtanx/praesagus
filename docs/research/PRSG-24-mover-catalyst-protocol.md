# PRSG-24 — Prior-session mover and catalyst replay protocol

Prepared 2026-10-01 MYT by Consultant. Status: proposed, research only; independent Lead review pending. Reuses technical-trend-analysis, daily-market-brief, praesagus-trading-orchestrator and skill-template. No real-market experiment, measured improvement, training or skill change was performed.

## TLDR

- Keep two datasets: retrospective explanations and forecasts made from demonstrably available pre-decision evidence. A convincing explanation is not predictive skill or causal proof.
- Measure gaps, returns, range and volume separately. Compare corporate-action-consistent prices and earlier-session baselines; never select only successful movers.
- Preserve all eligible watchlist sessions, both directions, nonmovers, unmatched news and unexplained moves. Report missing coverage rather than inventing catalysts.
- Use chronological, event-grouped, overlap-purged replay. Human-reviewed candidate corrections must improve untouched evidence cases without weakening rejection safeguards.
- Next boundary: offline deterministic calculations and evidence joins, after Lead freezes parameters and Researcher clears rights/coverage. PRSG-25's evidence-store implementation is separate; this document neither changes nor accepts its scope.

## 1. Evidence and decisions

Official [NYSE hours/calendar](https://www.nyse.com/trade/hours-calendars) distinguishes core sessions, holidays and early closes. Resolve each instrument's actual venue calendar, not a generic weekday calendar. US session timestamps require DST-aware conversion; MY instruments require their own verified exchange schedule. A MY public holiday alone does not establish a market closure. No Bursa calendar was verified in this assignment; acquiring and versioning it is a pilot prerequisite.

[TimeSeriesSplit documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) describes ordered splits and a sample-count gap. Inference: that gap alone does not implement multi-instrument event grouping or interval-based outcome purging; these require explicit checks. [Calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) requires separation of fitting and calibration data and explains that Brier loss combines more than calibration. Do not interpret a sentiment/class score as the probability of a future positive return.

These primary pages were retrieved on 2026-10-01. The [Moomoo historical-bar reference](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html) timed out during this assignment; adjustment, historical coverage, entitlement and redistribution claims are not independently verified here and remain PRSG-23 dependencies. Thresholds and schema below are Consultant proposals, not sourced performance findings or frozen policy.

## 2. Sessions, bars and comparable measurements

At report cutoff T, S is the latest completed regular exchange session with a complete bar actually available by T. P is the immediately preceding scheduled session. Do not silently replace a missing S bar with an older bar; mark missing or stale. At 08:00 MYT, US and MY session dates can differ. Store session open/close in UTC and venue timezone, calendar version, cutoff, actual bar availability and ingestion time. Early closes are complete sessions with a shortened-session flag; extended-hours bars are a separate dataset.

For S, use O/H/L/C/V and preceding close C_P on one disclosed comparable basis:

| Metric | Formula | Interpretation |
| --- | --- | --- |
| Overnight gap | O / C_P - 1 | Previous close to opening price, not the full daily move |
| Close return | C / C_P - 1 | Close-to-close price change |
| Intraday return | C / O - 1 | Open-to-close change, not maximum excursion |
| Daily range | (H - L) / C_P | Nondirectional dispersion, not a signed return |
| Relative volume | V / median(V of previous 20 sessions) | Activity against an earlier-only baseline |

Store returns as fractions and display percentages. Validate finite positive prices, nonnegative volume, H >= max(O,C), L <= min(O,C), H >= L and unique instrument/session/basis records. Reject inconsistent or incomplete bars; null is not zero. A zero volume denominator is unavailable. Daily OHLCV cannot show whether a price move happened before or after an intraday article.

Retain raw bars plus versioned adjustments and corporate-action evidence. A split requires consistent price bases and reciprocal share-volume treatment; do not apply a split twice. Distinguish price returns from dividend-inclusive total returns: ex-dividend gaps are not automatically bearish catalysts. Rights issues, spin-offs, mergers, symbol changes and currency redenomination need explicit handling or exclusion. Historical adjustment revisions discovered later cannot become earlier forecast inputs without a vintage record.

Measure listing-currency returns first. An investor-currency return, if requested, is (1 + local return) * (1 + matched FX return) - 1, with FX direction, timestamps and source disclosed. Never rank nominal USD and MYR prices together. Quarantine bad ticks, stale quotes, suspensions, halts and reopening sessions; preserve their rows and reasons rather than silently deleting difficult outcomes. ETFs and inverse/leveraged ETFs need separate strata; daily-reset exposures are not simple multi-day negations of an underlying return.

## 3. Proposed screening parameters — Lead must freeze before replay

Use a point-in-time watchlist with membership history, including removed/delisted names where licensed data exists. A fixed shortlist supports watchlist coverage only, not market-wide top-mover claims.

Proposed feasibility defaults:

- Return history: previous 60 scheduled sessions, minimum 40 valid comparable observations. Estimate robust scale separately for close returns and gaps as 1.4826 * median absolute deviation around the median. No current-session input; zero scale uses the absolute floor and is flagged.
- Price flag: abs(close return) >= max(3%, 2.5 * close-return scale); gap flag: abs(gap) >= max(2%, 2.5 * gap scale). Record direction separately. These arbitrary starting floors reduce tiny-move noise; they are not validated US/MY signal thresholds.
- Volume flag: relative volume >= 2, minimum 15 valid observations in the previous 20 sessions. Preserve volume-only and price-only flags rather than requiring both. Range is descriptive initially; no fitted range trigger.
- Compare only within market, instrument type and pre-decision liquidity strata. Proposed eligibility: prior 20-session median daily turnover >= USD 1 million for US or MYR 1 million for MY; at least 15 valid turnover observations. These unequal local floors are operational proposals, not equivalent economic liquidity. Missing turnover cannot establish eligibility. Record spreads when available; turnover does not prove executable fills.
- Shortened sessions and halt/reopening days form separate flagged strata; do not compare their raw volume to a normal full-session baseline as if exposure time were identical.

Freeze these parameters, windows, rounding rules and exclusions in a versioned configuration before inspecting held-out outcomes. Lead may choose different floors from development-only evidence. Publish counts and missingness by market/stratum and rerun predeclared sensitivity variants on development data only. New listings or thin names lacking history remain insufficient-data controls, not falsely classified ordinary nonmovers.

Minimum sample proposal: initial annotation feasibility requires 20 distinct event clusters per intended class, including negative controls. This is not sufficient proof of accuracy. Reserve at least 20 independent clusters per evaluated class in each reported held-out block or label its class result exploratory/insufficient; report numerator, denominator and event-cluster uncertainty. Rare classes may remain unrated. Lead must set a precision/power requirement based on observed development variability and dependence before a performance claim; no universal sample count proves an edge.

## 4. News linkage and information availability

Store publication time, provider-available time if evidenced, first workflow observation, retrieval and ingestion separately. Preserve original timezone and timestamp precision. Date-only news cannot establish within-session ordering. Backfilled articles are retrospective evidence; an old publication timestamp does not prove the system possessed them then. Retain revisions/content hashes and use only the revision available at the decision cutoff.

Two explicit modes:

1. **Retrospective explanation:** news discovered at review may describe S, but its later discovery stays visible. It cannot justify an earlier forecast.
2. **Prospective workflow replay:** every evidence item and derived feature must have demonstrable workflow availability <= decision cutoff. Provider historical availability without workflow ingestion supports only a separately labeled hypothetical provider replay, never an actual system forecast.

Proposed fixed windows, resolved from exchange timestamps:

| Window | Allowed interpretation |
| --- | --- |
| After P close through S open | Candidate overnight-gap association if timestamp precision establishes pre-open availability |
| After S open through S close | Candidate session association; daily bars alone cannot establish intraday reaction sequence |
| Earlier five completed sessions through P close | Prior context/already-known information; not automatically a new S catalyst |
| After S close through review cutoff | Later explanation, never a cause of the completed S move on timing evidence alone |

An item exactly on an auction boundary with insufficient timing precision is boundary-ambiguous. For prospective inputs, cutoff availability overrides these explanatory windows. For a forecast made after S closes, S bars may be inputs to a future horizon, not predictions of S itself.

Deduplicate provider IDs, URLs, content and underlying event lineage. Maintain syndicated copies and corrections for provenance, but count one event cluster, including cross-company macro stories. Prefer issuer filings, exchange/regulator notices and official releases; vendor/social evidence remains labeled. Match entities by stable IDs, listing and affected exposure, not ticker substrings alone.

Human annotation has separate axes: event category/relevance from the source text; timing eligibility; and attribution assessed with price/context evidence. Preserve disagreement. Attribution labels:

- **Plausible catalyst:** specific mechanism, relevant entity, credible source and compatible timing; association only, not causal proof.
- **Context/correlation:** broad market/sector movement, old information or coincident news without specific attribution evidence.
- **Contradictory:** substantive evidence conflicts with the proposed explanation or expected direction; do not hide it or force sentiment to match returns.
- **Unknown:** coverage/timing/mechanism insufficient or no matched item in the searched sources. “No matched news” is not proof that no catalyst existed.

Retain multiple hypotheses and strongest disconfirmation. Compare same-session benchmark and sector returns on comparable bases. Simple excess return (asset minus benchmark) is descriptive, not a causal residual; any beta model must be fit only on earlier data with missingness disclosed. Rates, FX, commodity shocks, index rebalancing, options expiry, dividends and earnings overlap are confounders. Positive news with falling prices is not automatically a false headline: expectations, pricing-in and wider shocks can differ.

## 5. Cohorts and frozen case schema

Retain every eligible instrument-session and rejected row with its reason. Cohorts include upward/downward movers, volume-only movers, ordinary nonmovers, relevant news without a mover, movers without matched news and data-quality exclusions. Controls are selected by earlier-known market/sector/liquidity/history attributes, never by future outcome. If sampled for annotation, freeze sampling probabilities and report weighted population metrics; all eligible rows remain in the scan ledger.

Proposed case contract (not implemented):

| Group | Required fields |
| --- | --- |
| Identity/version | case_id, dataset_mode, instrument_id, venue, currency, membership_version, protocol/config/taxonomy/schema versions |
| Session/input | S/P IDs, timezone, session open/close, calendar_version, as_of, bar IDs/hashes, availability/ingestion, raw/adjusted basis, action factors/vintage |
| Measurements | O/H/L/C/V/turnover, prior close, historical row IDs, gap/close/intraday/range/RVOL, thresholds, eligibility, rejection reasons, market/sector context |
| Evidence | news IDs, URLs/source tier, publication/availability/first_observed/retrieval/ingestion timestamps, timestamp precision, hash/revision, event_cluster_id, window, missing-coverage notes |
| Annotation | cohort, event category, relevance, timing eligibility, attribution label, alternatives/disconfirmation, annotator IDs/disagreement/adjudication, label version |
| Forecast | nullable forecast_id, frozen decision/reference price and source, direction/probability/target/range if justified, horizon start/end, invalidation, skill/prompt/model versions, input hash |
| Outcome/replay | separate actual-price records and source/availability, matured_at, scorer/version, split/group IDs, purge reason, review timestamp and acceptance status |

Null unsupported probabilities/targets. Do not insert future outcomes into the input payload. Store immutable forecast and evidence snapshots; append outcome/review revisions. Proposed horizons: next regular-session close and fifth subsequent regular-session close, separately scored; “week-end” needs its own explicit calendar endpoint and must not be conflated with five sessions. Reference price must already be available at decision time. These are observation returns, not realizable entry/fill returns.

## 6. Worked synthetic acceptance/rejection cases

All identifiers, prices, volumes and times below are invented fixtures, not market observations. Assume verified calendars, comparable bases and sufficient history unless stated. “Accept” means retain a research/regression case, never approve a trade.

| Case | Inputs and calculation | Expected result and regression assertion |
| --- | --- | --- |
| SYN-01 future news | C_P=100, O=104, C=106: gap +4%, close +6%. Forecast cutoff 08:00 UTC; article published/first observed 09:00 UTC. | Reject article from that forecast even if it plausibly explains a later move. Accept an explanation-only record with later availability. Assert zero future evidence in forecast inputs. |
| SYN-02 syndication | C_P=100, O=100, C=95: close -5%. Five syndicated copies of one official pre-session warning; V=2m, prior median=1m, RVOL=2. | Accept one plausible event cluster with five provenance links, not five confirmations. Negative mover remains captured. Assert dedup count=1 and RVOL=2. |
| SYN-03 split gap | Raw C_P=100, O=50, C=51 after documented 2:1 split. Comparable C_P=50: raw gap -50%, comparable gap 0%, close +2%. | Reject split-induced bearish catalyst and raw-return trigger. Accept corporate-action regression; volume comparison needs consistent share units. Assert no price-mover flag under default floors when earlier scale does not lower those floors. |
| SYN-04 unexplained mover | C_P=100, O=100, C=108: +8%; RVOL=3. Search finds no relevant item; feed covers only one provider. | Accept mover with attribution unknown and explicit coverage limitation. Reject invented takeover/big-buyer narrative. Assert no matched news is not encoded as proven absence. |
| SYN-05 missed catalyst | Official warning available before cutoff is labeled irrelevant by a candidate classifier. Later C_P=100 to C=94 (-6%). Human text-only relevance annotation identifies affected issuer. | Accept classification false-negative regression based on adjudicated relevance, not the negative return alone. Keep return in outcome/explanation channel; prediction value remains unproven. |
| SYN-06 false positive/nonmover | Unrelated issuer article is matched by ticker substring. C_P=100, C=100.5 (+0.5%), RVOL=1. | Reject entity match; retain false-positive control. Separately retain correctly matched official relevant news with the same small move as news-without-move: relevance is not equivalent to price impact. |
| SYN-07 macro confounder | Asset close return +5%; sector +6%, market +4%. Only a broad macro release is matched. Asset-minus-sector=-1 percentage point. | Accept context/correlation, not asserted issuer-specific causal alpha. Assert contrary sector comparison is visible and macro cluster cannot straddle folds. |
| SYN-08 insufficient/ambiguous data | New listing has 8 prior bars, median volume 0, article date only, bar crosses a halt. | Retain quarantined row; scale/RVOL unavailable, timing ambiguous. Reject normal-baseline screen and precise causal/forecast probability. Assert missing is not converted to zero. |

These are specification cases, not executed tests. Engineer would need deterministic fixtures/assertions in a separately accepted ticket.

## 7. Evaluation without hindsight leakage

Freeze data hashes, label versions, universe membership and cutoff first. Use ordered development/train, later calibration, then untouched test blocks with published calendar boundaries. Assign all instruments/syndications of one event cluster to one fold. If a cluster spans a boundary, quarantine it from that boundary's evaluation rather than move later evidence into training. Group common macro shocks and repeated revisions; report remaining dependence by issuer/session.

For every sample define information cutoff and label interval [horizon_start, horizon_end]. Purge earlier training/calibration rows whose outcome intervals overlap the next block or whose outcomes were unavailable at that block's fitting cutoff. Include maximum frozen horizon plus documented reporting delay in a conservative boundary embargo; verify interval overlap directly, not just row count. Fit preprocessing, feature selection and thresholds on training/development only, calibration on its separate block, and never tune on test. External pretrained models may contain later knowledge; record checkpoint provenance and do not claim historical point-in-time replay where that cannot be established.

Evaluate classification separately from forecasting:

- Classification: relevance/event-class precision, recall, macro-F1, confusion counts, missed relevant catalysts, false matches, unknown/abstention coverage, and metrics including rejected/abstained rows. Report class and event-cluster counts, market/language breakdown and coverage denominator.
- Attribution: blinded human adjudication, disagreement rate, provenance/timing violations and unsupported-causality count. A plausible-label agreement score does not establish economic causality.
- Forecasts: only matured actual prices at an explicit review time; separate horizons, directional hit rate with sample counts, error/range coverage when issued, and Brier only for justified probability forecasts. Missing actuals remain pending, not losses or wins. Reuse existing harness/forecast_review.py within its validated contract; additional metrics need their own accepted implementation.
- Baselines: unchanged current skill on identical inputs, simple no-change/directional historical base-rate forecast and relevant market benchmark, defined before evaluation. A hypothetical return strategy requires spreads, fees, slippage, delays and feasible fills before any trading-performance claim.
- Operations: accepted-case count, rejected/missing count, annotation time, total token/API cost including failures, and p95 latency. No cost or accuracy claims without measurements.

Use event-cluster-resampled uncertainty where sample size supports it; report dependence and instability rather than treating correlated copies as independent. Repeatedly inspected test sets become development sets. Promotion requires a fresh later holdout, adequate per-class support, no safeguard regressions and a Lead-frozen improvement/uncertainty criterion. This assignment sets no invented accuracy target.

## 8. Human-reviewed skill-candidate loop

Frozen failure case → Consultant identifies a narrow instruction defect → candidate change and rationale recorded separately → Lead approves evaluation scope → replay unchanged vs candidate on identical frozen evidence plus fresh chronological holdout → Consultant checks disconfirmation/rejections → Lead/human accepts or rejects → versioned change in a later authorized ticket.

No automatic rewriting or daily training. Do not reward confident storytelling, mover-only accuracy or abstention-only accuracy. Keep the original failure, unsuccessful candidates and measured tradeoffs. Prompt/model/risk-policy changes require explicit human review; deployment and live execution are outside this loop. Missing evidence means research only/unrated or NO TRADE, not fabricated precision.

## 9. Smallest next implementation and stop conditions

After Lead integrates PRSG-23 and reviews PRSG-25, a separately frozen Engineer ticket can consume authorized immutable local bars/news and output deterministic session metrics, eligibility reasons, event joins and review JSON. No collector, model training, order path, public database or skill editor is necessary for this first scan. Use synthetic fixtures before any licensed pilot; do not modify PRSG-25 files under this assignment.

Required future checks: calendar/DST/early close, missing scheduled bar, malformed OHLCV/zero denominator, split/dividend vintages, duplicate event/entity collision, future publication and later first observation, boundary ambiguity, controls in both directions, fold-group integrity and overlapping-label purge. Fixture tests must not need credentials or place orders.

Stop/reduce scope on unresolved data rights, missing MY calendar/adjustment coverage, unverifiable availability, systematic news-language gaps or inadequate independent class samples. Keep raw/license-restricted evidence private; any sanitized publication requires explicit redistribution review. Lead must freeze thresholds, cohorts, horizons, availability mode, schema, taxonomy, split boundaries and promotion criteria before pilot evaluation. Completion remains pending independent Lead review; documentation is not implementation or proof of improved predictions.
