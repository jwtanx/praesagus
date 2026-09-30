# Praesagus delivery plans

Planning baseline: 1 October 2026 (Asia/Kuala_Lumpur). Lead owns prioritization and acceptance; Engineer owns implementation; Researcher resolves provider/product uncertainty; Consultant reviews market semantics. Plans describe future behavior until implementation and tests establish completion.

## Ordered backlog

| Order | Spec | State | Engineering effort | Expected impact | Confidence |
|---|---|---|---|---|---|
| 1 | [Company catalyst inbox](001-catalyst-inbox.md) | Selected; delegated to Engineer | 3–5 person-days | High: connects four existing datasets into one research workflow | Medium-high: data/interfaces exist; user value unmeasured |
| 2 | [Connector freshness](002-connector-freshness.md) | Planned | 3–5 person-days | High: makes stale data and failed runs visible | High for reliability need; moderate for delivery estimate |
| 3 | [Filing evidence detail](003-filing-evidence.md) | Planned | 2–4 person-days | Medium-high: faster verification of filing facts | Medium: metric attribution needs audit |
| 4 | [Watchlist management](004-watchlist-management.md) | Planned | 3–5 person-days | Medium: removes manual configuration work | Medium: shared ownership/concurrency need design |
| 5 | [Durable alert delivery](005-alert-outbox.md) | Planned | 4–7 person-days | High for alert-dependent users; otherwise medium | Medium: receiver delivery semantics vary |

Estimates include focused tests, documentation, and Lead review for one engineer familiar with the repository. One person-day means roughly six focused engineering hours; these are planning ranges, not calendar promises. API/provider onboarding and user-testing recruitment are excluded. Parallel tasks may reduce elapsed time without reducing effort. Impact is a hypothesis about user friction or reliability, not a financial ROI or trading-return estimate.

## Decision and baseline

The inbox wins first because `backend/financial_services.py` and `frontend/src/pages/Financial.tsx` already expose the four datasets separately. New joins and presentation can be tested offline. Freshness instrumentation follows so users can judge dataset coverage. The forecast evaluator in `harness/forecast_review.py` is implemented separately; the broader answer harness YAML remains design-only.

This sequence refines the existing [implementation roadmap](../docs/IMPLEMENTATION_ROADMAP.md). It does not supersede current implementation evidence or authorize all backlog items to run at once. Only item 001 is assigned now. Keep provider integrations, persistent Moomoo collection, model-backed answers, and trade execution outside these MVPs.

## Delivery record

- Engineer session: `01a0f1ee-92bc-7ba0-add1-02a5023a6dad`.
- Researcher session: `01a0f1ec-b056-7a53-904e-46b944471262`.
- Consultant session: `01a0f21f-8fee-7ed2-aa49-04a7c7a8645b`.
- Lead writes these plans; Engineer edits only the accepted implementation scope. Confirm thread identity before messaging if sessions are replaced.
- Each completion updates its spec with changed files, exact validation results, known limitations, and release commit. Do not mark completion from a passing build alone.
- Lead reviews and integrates changes before publication. Preserve concurrent report, ledger, and skill edits.

For each future item, confirm scope against current code before starting, record estimate changes and reasons, and retain a measurable outcome check. No production analytics collector exists yet; initial user metrics can be measured in a recorded manual usability session.
