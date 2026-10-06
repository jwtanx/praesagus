# PRSG-64 — Select explainable SPY/QQQ descriptive metrics

Type: spike · Modules: financial-data, market-research · Owner: Trader · Priority: P2 · Effort: XS (0.1–0.25 person-days; capped at 2 hours) · Impact: medium; could make the existing SPY/QQQ capture trend easier to interpret, but user value and predictive value are unmeasured. Created 2026-10-06 MYT.

## Decision question and status

Which small set of explainable, timestamp-safe **descriptive** metrics, if any, should accompany the existing SPY/QQQ observed-price trend, and what provider/rights evidence must exist before public display? This is a completed research spike, not an implementation authorization. Lead accepted this planning scope on 2026-10-06; `implementation_authorized=false` remains in effect.

Draft finding: the formulas below are simple enough to explain, but no public-use data source/rights package or actual eligible historical-bar feed was verified in this spike. Therefore publish no new market values or metric now. If Lead later accepts a separate implementation scope and a provider confirms coverage, adjustment basis, availability, cost, and public display/derived-data rights in writing, the smallest candidate set is 20-session price return plus 20-session realized volatility. The moving-average spread is a lower-priority optional regime description. These metrics do not produce or validate a forecast.

## Baseline and boundary

The existing PRSG-61 viewer plots up to five report-date public quote snapshots for SPY and QQQ, requires at least three valid dated observations, and labels them as MYT capture observations rather than official session closes. It has no historical bar/indicator contract. PRSG-61 separately gates Pages publication on verified market- and field-specific public redistribution rights; its delivery record says no live public market snapshot was present. This spike does not change those behaviors.

Covered instruments are only SPY and QQQ (USD listings). State Street identifies SPY as NYSE Arca/USD; QQQ is the Nasdaq-100 ETF, but the exact current primary listing market should be confirmed from an issuer/exchange security master before venue-specific procurement. Do not infer source currency, close definition, session, or corporate-action adjustment from a vendor field name.

## Candidate comparison

All candidates use completed regular-session daily closes `C_t` in one verified, consistent price basis and session calendar. They are snapshots of what happened through the latest eligible close, not expected returns. Daily refresh is sufficient for the existing daily brief; the bar must be available by the frozen report cutoff. For a 08:00 MYT report, use the most recent completed US session that the provider has actually made available by cutoff, retaining exchange session date, source timestamp, provider retrieval/availability timestamp, local retrieval time, known-at time, timezone, currency, correction/revision state, and cutoff separately.

| Candidate | Exact definition | Value / tradeoff | Inputs, gaps, and failure behavior |
|---|---|---|---|
| 20-session price return | `100 * (C_t / C_(t-20) - 1)`; two closes exactly 20 completed US trading intervals apart (21 closes). | Directly summarizes recent realized price movement. Easy to explain; endpoint-sensitive and not a forecast. Use unadjusted close for quoted-price movement only if split/corporate-action handling is separately validated; ETF distributions can make price-only return differ from total return. | Daily close history, correct exchange calendar, verified USD, and explicit split/dividend adjustment policy. Missing either endpoint, a correction, inconsistent basis, or any unresolved session gap => null/unavailable with named dates; never bridge a gap silently. Stale if the latest eligible session bar is absent at cutoff. |
| 20-session realized volatility | `100 * stdev_sample(ln(C_i/C_(i-1)), i=t-19..t) * sqrt(252)`; 20 daily close-to-close log returns from 21 consecutive completed-session closes. | Context on recent realized variation, not direction. Formula is explainable but annualization convention is a presentation assumption; can be misread as a forward volatility forecast. Label “historical, annualized (252-session convention)” and do not imply expected future volatility. | Same close history plus validated calendar/adjustment basis. Any missing return, nonpositive price, stale endpoint, or basis change => unavailable/null with gap reason. Does not establish risk, cause, or future range. |
| 20/50-session moving-average spread | `100 * (SMA_20(C_t) / SMA_50(C_t) - 1)` using the last 20 and 50 completed-session closes. | Describes a short-vs-long realized price regime; more resistant to one endpoint but lags and needs 50 closes. Avoid redundant chart clutter if the 20-session return already appears. | At least 50 valid consecutive-session closes under one declared adjustment basis. Any missing bar/basis discontinuity => unavailable/null; do not forward-fill. Not a crossover or directional forecast unless separately defined and validated. |

**Recommendation:** do not publish any new metric until source and rights gates are resolved. For a later bounded display experiment, prefer 20-session price return and 20-session realized volatility, with the latter labeled explicitly as backward-looking; add SMA20/50 only if the user test shows a need for a slower regime reference. This is a choice of descriptive presentation, not evidence that either improves predictive accuracy.

## Source and operational comparison

The data source is a separate decision from the formulas. Nasdaq Data Link publicly describes a Bars API with real-time, delayed, and historical OHLCV for US-listed securities and says subscribers can access 10+ years; this appears to cover both US-listed ETFs in principle, but the actual subscription's SPY/QQQ symbol entitlement, daily interval, adjustment policy, delivery timing, price, and order form were not verified. Its posted license says usage is internal unless a written Order Form provides other rights, limits derived-data distribution, and incorporates third-party terms. Treat public Pages display of raw close or derived values as unapproved until the executed terms explicitly cover it. The site announces updated terms apply 2026-11-01, after this plan date; re-review terms before any future procurement/use.

NYSE TAQ Closing Prices publishes daily Open/High/Low/Last, volume and closing bid/ask for NYSE Group listings, with history from 2001; official State Street listing data places SPY on NYSE Arca, so this is a plausible SPY close candidate after symbol/file verification. It does not state coverage of Nasdaq-listed QQQ, so it is not a single-source pair solution. The current NYSE product catalog links order/purchase and pricing/policy terms. An older client specification describes file availability around 4:30 PM Eastern for Arca; this timing is inherited from an old spec and is not claimed freshly verified for current DST, product version, or account. NYSE states external redistribution can incur fees; confirm current field-specific and derived-data rights and current cost with the provider.

NYSE Daily TAQ is a third, broader fallback: its catalog says it contains prior-day trades/quotes for NYSE, Nasdaq, and regional markets and all US equities. It is far more granular than daily closes, requiring reconstruction/quality controls, and its purchase/terms/cost are not established here. It is not recommended for this two-instrument descriptive chart absent an existing licensed entitlement.

Official references (reviewed 2026-10-06 UTC; no vendor API or credential calls):

- State Street SPY listing facts: https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy
- Nasdaq Data Link Bars coverage/product: https://www.nasdaq.com/products/data/data-link/api
- Nasdaq Data Link terms and Order Form / derived-data restrictions: https://data.nasdaq.com/terms
- NYSE TAQ Closing Prices scope/history: https://www.nyse.com/data-products/catalog/taq-nyse-closing-prices
- NYSE older TAQ Closing Prices client specification (timing caveat above): https://www.nyse.com/publicdocs/nyse/data/TAQ_NYSE_Closing_Prices_Client_Spec.pdf
- NYSE Daily TAQ all-US-equities coverage: https://www.nyse.com/data-products/catalog/daily-taq
- NYSE market data policy/pricing index: https://www.nyse.com/market-data/pricing-policies-contracts-guidelines
- NYSE external redistribution FAQ: https://www.nyse.com/contact/nyse-market-data/pricing

## Data quality, interpretation, and forecast boundary

- Treat a source bar as a vendor observation until its security, venue, currency, units, session, close definition, adjustment basis, completeness, correction behavior, and timestamps are verified. Never merge unlike bases or silently use a proxy/provider fallback.
- For both instruments, require the latest scheduled regular session that is eligible by cutoff. If only an earlier bar is available, show the exact stale session/time or suppress the metric; do not present an older close as current. If a market holiday explains no session, retain the exchange calendar evidence separately from a data failure.
- Keep observed trend separate from any forward prediction. A return/average/volatility reading may frame scenarios only. Any later forecast would separately need a frozen target date/horizon/reference price, point-in-time evidence, explicit method, bull and bear cases, measurable disconfirmation/invalidation, and confidence with reason. No probabilities or performance claims absent frozen chronological out-of-sample evaluation with leakage controls and realistic costs.
- Suggested interpretation template: **Observed:** formula output and exact end session/source. **Bull case:** evidence that could support continuation. **Bear/disconfirmation:** counter-evidence or condition that breaks that reading. **Trigger:** measurable next observation to revisit it. **Action class:** research only/watchlist. Do not let a metric itself supply bull/bear evidence or a trigger.
- Missing or stale history => null values, explicit status and date-specific `data_gaps`; no invented price, direction, target, or confidence. Capture/retrieval timestamps do not prove provider authenticity or public redistribution rights.

## Dependencies, cost, and effort

- Operator/provider must identify one eligible US daily-bar product and produce current written rights evidence covering SPY and QQQ, daily close fields, adjustment basis, internal storage/derived calculations, public display/redistribution of those fields and metrics, retention, and any attribution. Until then, public values are prohibited by this plan.
- Provider must confirm total price/minimum term, back-history cost, API/file quotas, refresh SLA/actual availability, corrections, support, and required contracts. Nasdaq Data Link price is contact/order-form dependent on the reviewed public materials; NYSE product terms/pricing require a current quote/order check. This spike purchases nothing and starts no trial.
- Later engineering estimate cannot be frozen from this spike; rough planning only: a single daily close fetch plus deterministic formulas appears XS/S after source normalization and licensing, but data onboarding, field validation, rights review, historical backfill and tests may dominate. Lead should re-estimate after an eligible sample file and signed terms exist.
- Before any later display, test holiday/no-session, delayed/missing/stale bars, vendor correction after cutoff, split/dividend adjustment discontinuity, invalid/zero values, timezone/DST boundary, and inconsistent SPY/QQQ session availability. Point-in-time replay must not leak later corrections into earlier snapshots.

## Value test and stop condition

No baseline exists for whether readers understand the current five-capture trend; no user-test evidence or metric-accuracy baseline is claimed. If a separate implementation is later accepted, a small manually reviewed usability check can ask whether viewers correctly distinguish the selected descriptive metrics from forecasts and identify the bar end session and missing/stale state. Stop if users interpret a historical statistic as a prediction, if rights cannot be documented, or if the pair lacks consistent licensed history. Forecast quality is out of scope.

## Non-goals and write boundary

- No implementation, tests against live providers, Moomoo/OpenD/API calls, paid service, credential access, trades, deployment, or public market values.
- Do not edit daily reports, report indexes, dashboard/viewer, source code, skills, calendar, forecast ledger, provider configuration, or existing PRSG-60/61/62/63 work.
- Only these two new ticket planning files may be created/edited in this task. A later implementation needs a separate Lead-reviewed accepted scope, rights proof, source contract and exact test plan.
- Implementation authorization: **false**. No personalized allocations or order instructions.

## Checks and review status

- Primary-source comparison: completed by Trader from the linked official issuer, Nasdaq Data Link, and NYSE pages as retrieved 2026-10-06 UTC. No Moomoo page/API used. These public pages do not substitute for a current executed license or an entitled sample bar.
- Ticket manifest/path validation: passed for the manifest and both declared paths with `python3 scripts/planning/validate_ticket.py plans/2026-10-06/PRSG-64.harness.json --changed-file plans/2026-10-06/PRSG-64-spy-qqq-descriptive-metric-selection.md --changed-file plans/2026-10-06/PRSG-64.harness.json`; `git diff --check` was clean (2026-10-06 MYT). This validates declared/supplied paths, not completeness of a Git diff.
- Lead review: accepted 2026-10-06. Lead independently verified the two-file-only scope, unique key against origin/main/history, formulas and gap behavior, source/rights caveats, forecast boundary, validator success, and `implementation_authorized=false`. No market values were published; acceptance does not authorize implementation.

## When it's considered done

- [x] PRSG-64-D1: Compare no more than three exact, interpretable descriptive metrics with formulas, window, coverage, cadence/as-of, missing/stale behavior, costs/rights uncertainties and forecast limitations.
- [x] PRSG-64-D2: Record a source-backed recommendation or abstention and explicit data/rights/operator dependencies without publishing market data or authorizing implementation.
- [x] PRSG-64-D3: Lead reviews the unique PRSG-64 key, two-file-only scope, cited evidence, open questions, and implementation_authorized=false; retain any unresolved source/rights issues.
