# PRSG-22 — Overall market-learning plan

Type: docs · Modules: market-research, financial-data, harness · Owner: Lead · Priority: P1 · Effort: S (0.3–0.5 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Base: bb0d302bd4384482e628e5e1e58630e0d68396f4. Impact hypothesis: better evidence quality and reproducible research, not guaranteed returns.

## Objective and baseline
Build a research-only feedback loop from licensed price/volume observations and timestamped news. PRSG-21 user approval authorizes further library investigation and pilot planning, not proof of model performance. Existing forecast_review.py scores frozen forecasts; reuse it rather than replacing it. There is no persistent OHLCV/news collector or automatic skill-learning runtime.

## Delivery sequence
1. PRSG-23 Researcher: current OSS/API reuse and data-rights audit.
2. PRSG-24 Consultant: market labels, catalyst attribution and frozen evaluation protocol.
3. Lead integrates both findings and freezes measurable gates, selected versions and accepted implementation scope.
4. Engineer follow-up ticket: local immutable raw batches + SQLite normalized daily bars/news, idempotency and bounded retry tests. Estimate M, 3–5 person-days.
5. Engineer follow-up ticket: deterministic prior-session mover scan and evidence joins with a review report. Estimate M, 2–4 person-days.
6. Offline classifier replay: scikit-learn baseline, SetFit challenger; Laya only after maturity/license/compatibility review. Estimate M, 3–5 person-days excluding annotation.
7. Consultant reviews candidate regression cases; Lead/human approves any skill/model change after untouched replay. Estimate S, 1–2 person-days per initial review cycle.
Future implementation tickets are not yet allocated or delegated. Initial engineering estimate 9–16 person-days, excludes live entitlements, historical licensing and labeling. Impact: auditable evidence and measured classification quality, not assured investment ROI.

## Dataset and calculation contract
T-1 means previous completed regular exchange session per instrument, not yesterday MYT. US and MY close at different times; include exchange timezone, DST and holidays. Store provider instrument IDs, venue, currency, adjustment/session basis, bar completion/availability, ingestion time, original/revised batches and checksums.
Separate overnight gap = open(T-1)/close(T-2)-1, close return = close(T-1)/close(T-2)-1, intraday return = close/open-1 and range=(high-low)/prior close. Comparable corporate-action-adjusted bases required; splits, dividends, halts and bad ticks must not masquerade as catalysts. Relative volume uses only earlier completed sessions; baseline window and threshold frozen before evaluation. Daily bars cannot locate an intraday news reaction.
Capture all eligible watchlist observations, ordinary moves, false alarms and news with no move, not only winners. A small watchlist proves coverage only within that watchlist, not a market-wide top-mover service.

## Evidence and attribution
News records retain provider ID, canonical URL, raw publication timestamp/timezone, provider availability if known, first observed/retrieved time, ingestion time, source tier, content hash, event cluster and revisions. Historical news fetched today is not evidence our system knew it yesterday. Earliest observed source is not necessarily earliest publication.
Maintain two datasets: retrospective mover explanations and pre-decision evidence for prospective forecasting. News after the forecast cutoff is explanation-only. Label plausible catalyst, correlated/contextual, contradictory or unknown; never claim price causation solely from a time match. Preserve no-news cases and disconfirming market/sector explanations.

## Evaluation and reinforcement
Version taxonomy, labels, cases, model/checkpoint/license, preprocessing, skill/prompt and data hashes. Freeze event-grouped chronological train/calibration/test windows with overlapping-outcome purge. Report relevance recall/macro-F1, catalyst misses, abstention/coverage, task calibration, total accepted-case cost and p95. Forecast outcomes separately use real matured closes, Brier/coverage and baseline comparisons. Numeric returns/time ordering remain code, not Jev judgments.
Starting from zero means accumulation and review, not daily automatic training. Improvements are candidate changes evaluated against frozen regressions and fresh chronological holdouts, with human approval; no autonomous production-skill rewrite, trades or unverified precise confidence.

## Dependencies and stop conditions
US/MY requested; pilot English-first with explicit multilingual unknowns pending research. OpenD login/entitlements and redistribution rights unresolved. Local SQLite private; GitHub Pages only receives sanitized permitted JSON, never database/credentials. No paid enrollment or installation now.
Stop or reduce scope on unresolved license/rights, unavailable timestamps/adjustments, inadequate per-class samples, unreliable market coverage or no held-out benefit. Thresholds/horizons must be selected before outcome inspection; no fabricated accuracy target or savings claim.

## Sources verified by Lead
- https://scikit-learn.org/stable/modules/feature_extraction.html — reusable text feature extraction.
- https://huggingface.co/docs/setfit/index — reusable classification framework.
- https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html — historical candles rather than snapshots.
Primary pages checked 2026-10-01; version/security/rights research remains PRSG-23.

## Assignments and scope
Lead owns this plan. PRSG-23 and PRSG-24 have disjoint documentation paths. No Engineer implementation until research returns and scope is accepted. No commit/push performed in this planning pass; ticket-by-ticket commits required later.

## When it's considered done

- [x] PRSG-22-D1: Overall phased plan, risks and role assignments reviewed by Lead.

## Progress

Planning recorded; findings/review pending. No implemented feature or measured improvement.

## Lead acceptance — 2026-10-05 MYT

Lead review2026-10-05MYT: phased documentation-only plan accepted; repository forecast_review functions inspected, future collection/model/skill runtime remains absent. Three linked official docs reopened successfully. Leakage/session/provenance/rights/sample/cost/abstention gates reviewed; estimates unmeasured; PRSG23/24 research dependencies and human evaluation approval remain prerequisites. Historical owners retained; future financial judgment routes to verified Trader. No implementation or model performance accepted.

Historical Researcher/Consultant assignments above retain original ownership. Future source comparisons use bounded temporary research; financial judgment and review route to the verified Trader. No successor implementation is allocated by this acceptance. Before any pilot, PRSG-23/PRSG-24 findings must be independently accepted and a new frozen implementation manifest must select versions, rights, sample/window boundaries and measurable thresholds. No installed model, persistent collector or measured accuracy/ROI claimed. Official references rechecked: [scikit-learn feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html), [SetFit](https://huggingface.co/docs/setfit/index), [Moomoo historical candles](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html). They establish available library/API interfaces only, not entitlement or investment validity.
