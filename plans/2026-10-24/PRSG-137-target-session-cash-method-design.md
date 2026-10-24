# PRSG-137 — Target-Session Cash Method Decision

Type: spike · Modules: market-research, financial-data, harness · Owner: AI Engineer · Priority: P1 · Effort: XS (0.1–0.25 person-days, estimate) · Impact: medium

## Objective

Answer one design question within a 45-minute analysis timebox: can the existing private one-session terminal-price scenario handle an already-known ordinary cash dividend on its target session without changing its estimand silently or weakening evidence gates? Deliver a reviewed decision, not implementation or model promotion. This is supporting design inside the accepted manual-CSV/MVP program, not a new strategy or live-trading direction.

## Findings

`ingest/forecast_scenario.py` currently uses cash-inclusive historical log returns for the generic cash method, but its action gate explicitly rejects `day == target[0]`. This is intentional fail-closed behavior, not a defect to delete. Retained financial review for the next US edition conditionally moves PG cash into the historical window, while a CAT target-date cash event remains held. Thus thirty US plus five MY is not established by capture alone. Facts, inferred record/ex-date convention, target-price method and predictive performance are separate evidence gates. Canonical dependencies: PRSG-124, PRSG-135 and PRSG-113; existing source/rights and model-promotion requirements remain binding.

## Choices

1. Retain target-event abstention. No new financial assumptions; coverage may remain below the MVP target.
2. A separately versioned cash-inclusive-return/terminal-ex-cash transformation. Define its mathematical assumptions, cash timing, price direction, quantiles, low-price rejection and limitations before considering code.
3. A separately versioned reference/escrowed-dividend approximation. Explain discounting/reinvestment assumptions and how it differs from option 2. Reject any option inconsistent with the historical estimand or requiring unavailable inputs.

These are candidates, not accepted formulas. Use only authored numerical examples clearly labeled fictional; they are algebra/contract checks, not empirical performance. No recommendation of an actual trade.

## Approach

AI Engineer owns the bounded mathematical/contract decision brief, with independent Trader financial judgment. Lead owns prioritization, final design review and canonical integration. Freeze base SHA shown in the manifest. Only the two ticket record paths may change in Git; worker analysis stays private. Protect implementation, tests, public reports, original financial evidence, all prior forecasts/models, skills and unrelated edits. No production/experimental method code, provider calls, fitting, inference, CSV generation, source permission grants, fees or external contacts from this spike. Do not change accepted requirements, methods or source dates to obtain 35 rows.

## Required Analysis

Specify the terminal traded-price estimand versus total shareholder return, native gross cash per ordinary unit, exact ex-session and record-date inference qualifications, target/issue chronology, known-at provenance, private/public source rights and unchanged complete-history gates. Compare formulas for median, bounds and raw-price direction, including a zero-cash equivalence case. Address double counting, multiple same-session cash events, special/uncertain dividends, capital actions, taxes, FX, discounting/reinvestment assumptions, non-positive adjusted inputs/results, extreme cash, rounding and unknown current terms. Never fill a price hole or treat a payment date as an ex-date. Preserve inclusive calendar/action bounds and exclusive instrument end-date semantics.

Use a small frozen worked-case table: zero cash; eligible known ordinary target cash; historical and target cash together; duplicate events; unknown/inferred or contradictory ex-date; cash known after issuance; wrong unit/currency; unsupported split/special event; non-positive or extreme adjusted result; already-expired target; absent rights or a historical close. Explicitly say which cases must withhold. No target-cash evidence becomes an earlier known signal through this analysis.

## When It Is Considered Done

- [x] PRSG-137-D1: Existing rejection, exact financial trigger and source-date/estimand distinctions documented from implementation and retained evidence.
- [ ] PRSG-137-D2: Three viable options compared or rejected with equations, assumptions and frozen authored cases; no implementation or accuracy claim.
- [ ] PRSG-137-D3: Trader independently reviews financial semantics and exact admission/rejection conditions; differences and unresolved questions retained.
- [ ] PRSG-137-D4: Lead accepts a decision-ready brief, explicit next implementation boundary and required human method-promotion decision; original MVP/full-program gates stay open.

## Acceptance And Promotion Boundary

Spike completion means a reviewed answer, including abstention if the evidence is insufficient. Any subsequent method change needs separately frozen implementation paths/tests, versioned evidence and result contracts, chronology/source rejection regressions and independent review. AGENTS.md requires human review before model/prompt/risk-policy promotion; this spike neither supplies that human decision nor authorizes production/public use. Current CAT hold remains until a valid alternative is explicitly accepted and every source gate passes.

## Tradeoffs

Measured outcome is a reproducible design decision with all worked-case outcomes stated, not a promised coverage or accuracy increase. The medium impact estimate reflects one observed coverage bottleneck; other fifteen MY and full100/strong-model obligations are unchanged. Stop at 45 minutes or missing financial facts; return the exact unresolved dependency rather than inventing cash dates, discount rates or validation evidence.

## Baseline Review Evidence

24 October: Lead inspected the existing historical-cash log-return calculation and explicit target-session rejection. Trader independently confirmed that the retained CAT event intersects26October under the qualified ordinary-business-record convention, while PG23October can only conditionally enter the historical window after fresh data checks. The financial recommendation favors retaining a terminal raw-price estimand and considering an explicitly qualified cum-entitlement-wealth/terminal-cash translation; it does not approve a formula, code, source admission or promotion. AI Engineer comparison and final independent financial review remain pending.

Retaining abstention preserves the current financial contract but cannot remedy this coverage bottleneck. A terminal-cash transformation is transparent about the ex-cash price but needs explicit receivable-value and tail assumptions; an escrowed-reference approximation preserves positive lognormal support at the cost of a different cash-growth assumption. Neither mathematical convenience nor a 35-row target resolves the missing method and source decisions.
