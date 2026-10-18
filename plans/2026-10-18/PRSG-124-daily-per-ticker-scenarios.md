# PRSG-124 — Daily Per-Ticker Research Scenarios

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: M (2–4 person-days) · Impact: high — support the human's daily50-ticker prediction requirement instead of a SPY-only overlay.

## Why the ticket is created?

The human requested a prediction for every daily-report ticker and explicitly required making that path work. The current calculator, result validator/mapper and preparation overlay hardcode SPY/US/USD; actual daily coverage remains0/50. This fixed50-name task is separate from PRSG-109 market-wide100-name discovery and trained whole-window extrema forecasting.

## Approach

Generalize the existing uncalibrated21-completed-close/20-logreturn, ddof1, z1.959964, next-venue-session research scenario with exact per-instrument evidence and identity-bound results. Preserve legacy SPY raw/cash schemas and existing source/calendar/availability/action/admission gates. AI owns numerical core; Engineer owns bounded batch overlay/CLI. Trader supplies actual financial/source admission separately.

## Choices

Add generic schema3 raw/cash method IDs and explicit closed identity-bearing keysets; preserve legacy schema1/2 and method IDs. Keep current raw and cash-return arithmetic; no fitted model or adjusted-series algorithm. Generic public research estimates display2decimals HALF_UP for USD/MYR, retaining continuous private values and declared display policy; they are not executable quotes and do not claim compliance with exchange tick ladders. Do not add an exchange-tick gate to continuous research forecasts.

Batch schema1 items contain exact ticker/market/currency/evidence/admission fields, at most50 unique matching report rows,2MiB total/depth12 specifically for batch (legacy bounds remain unchanged). New --batch is mutually exclusive with legacy singleton evidence/admission. Missing entries withhold the intended ticker and clear old numeric fields; malformed/duplicate/unknown/cross-bound identities reject before writes. Separate per-row audits/counts and immutable issuance remain mandatory.

## Findings

The current core also hardcodes identity in output validation/time-basis/row mapping, so loosening only its input test is insufficient. Existing immutable private-output handling and public/compact validation can be reused. Fixture success establishes plumbing, not source admission, real forecasts or predictive quality. Actual latest histories, quote currency/basis/actions, venue calendars and source-use evidence remain required upstream work.

## Tradeoffs

A transparent research baseline is the shortest existing numerical path; it does not meet the standalone strong-model requirement or demonstrate calibrated interval coverage/profitability. Retain low qualitative confidence, issuer-specific reviewed bull/bear/invalidation and precise missing-input reasons. Rounded unchanged prices do not redefine the unrounded directional sign. No 252-session/liquidity discovery gate is imposed on this fixed shortlist.

## Frozen scope

Implementation base f0182039fe2cc4ec8875943da41f878f84ac94c8. AI Engineer exclusively writes ingest/forecast_scenario.py and tests/test_forecast_scenario.py in primary. Engineer later exclusively writes ingest/report_forecast.py, scripts/daily-market-brief/prepare_forecast_report.py and tests/test_report_forecast.py after core API review. Lead owns these two records and integration. Disjoint reviewed commit fast-forwards may occur while work runs; never overwrite another owner's edits. Protected: projection/PRSG-123, viewer/report/calendar/ledger artifacts, stock-research/model/provider/credential clients and dependencies. No provider/history/network/fitting/model-promotion release in this ticket. If a validator/public-schema dependency needs edits, return exact finding for scope extension before writing it.

## When it's considered done

- [x] PRSG-124-D1: Generic raw/cash core, strict identity-safe results/mapping and legacy compatibility pass focused fixtures and Lead review.
- [x] PRSG-124-D2: Bounded per-ticker batch overlay/CLI, distinct US/MY calendars, partial/missing/error behavior and immutable output/public validation pass focused review.
- [ ] PRSG-124-D3: All50 actual ticker predictions have admitted current inputs and frozen numeric outputs; coverage/limitations and delivery independently verified. Fixtures or0/50 do not satisfy this item.

## Lead review — 18 October

D1 accepted after independent inspection of both frozen core files and a combined core/legacy-overlay/ticket-brief run: 274 passed in 1.57s. Core SHA256 515ec709e72b5174694e82a7e5591579aadf215c080054d414fa1e32c65efc22; tests ec8c5367e0bba63533a105e125be0e536edecaf754ba767b3081b8d5411fbf43. This check ran in primary before the new overlay handoff and establishes fixture compatibility only. D2 remains under Engineer implementation; D3 actual coverage remains 0/50. No model promotion or actual source admission is inferred.

D1 integrated as 1f6a47f; mandatory commit gate 2,937 passed, 41 warnings in 56.82s. D2 accepted after independent frozen three-file review and combined overlay/core/projection checks: 355 passed in 2.69s. Frozen handoff hashes: overlay 8da93734648833a96f6141f3e09d2f624fb9ff6b2cab0a5be7af9bc984ee347b; CLI 36640da3d92d89cba3af09700fb195722af199a410dc68434ee78b0195dacca6; tests 4de7475c73609a7621cd1a1891cc85df1f4c6f858b6965b0c28c6bd1b3eba56f. Missing rows clear previous numbers; duplicate/unknown/cross-bound batches reject; legacy flow remains covered. D3 remains pending: one actual SPY capture succeeded with 100 bars and all 21 required sessions, but source admission and actual numeric issuance remain unfulfilled.

## Actual private delivery — 19 October

Lead independently verified six actual next-close research forecasts (SPY and five company stocks) in a private timestamped combined CSV, with audit/manifest hashes, owner-only permissions, original data/store bindings and arithmetic checked. Coverage is6/50private and0/50public; D3 remains pending. These are uncalibrated numerical baselines, not the standalone trained whole-window requirement. No private generated artifacts, raw values or account attestations are committed. All30US histories have since been captured at100bars each; source/event review for remaining names is in progress. Original partial and earlier editions remain immutable.

Lead subsequently verified the additional23-name cohort and a separately sourced QQQcash supplement, then issued a new combined30-name US private CSV. All30US predictions are now generated;20MY and publicnumeric publication remain unfinished. Across cohorts,630actual closes plus provenance bindings and independent raw/cash arithmetic were checked; artifact hashes/bytes and immutable editions verified. D3 stays pending. No full100-name trained multi-window result or performance claim follows.
