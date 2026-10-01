# Praesagus delivery plans

Planning baseline: 1 October 2026 (Asia/Kuala_Lumpur). Lead owns prioritization and acceptance; Engineer owns implementation; Researcher resolves provider/product uncertainty; Consultant reviews market semantics. Plans describe future behavior until implementation and tests establish completion.

## Ordered backlog

Active corrective delivery: [PRSG-7 — daily report navigation, shared monthly calendar and five-name coverage](2026-10-01/PRSG-7-daily-report-workflow.md). Type feature; modules frontend/financial-data/skills; Lead accountable, Engineer viewer implementation, Researcher artifact migration; P1; S (1–2 person-days estimated); high usability/maintenance impact. PRSG-6 is reserved for the earlier report-research assignment, not reused.

| Order | Spec | State | Engineering effort | Expected impact | Confidence |
|---|---|---|---|---|---|
| PRSG-1 | [Company catalyst inbox](2026-10-01/PRSG-1-catalyst-inbox.md) | In progress; Engineer delivery pending Lead review | 3–5 person-days | High: connects four existing datasets into one research workflow | Medium-high: data/interfaces exist; user value unmeasured |
| PRSG-2 | [Connector freshness](2026-10-01/PRSG-2-connector-freshness.md) | Planned | 3–5 person-days | High: makes stale data and failed runs visible | High for reliability need; moderate for delivery estimate |
| PRSG-3 | [Filing evidence detail](2026-10-01/PRSG-3-filing-evidence.md) | Planned | 2–4 person-days | Medium-high: faster verification of filing facts | Medium: metric attribution needs audit |
| PRSG-4 | [Watchlist management](2026-10-01/PRSG-4-watchlist-management.md) | Planned | 3–5 person-days | Medium: removes manual configuration work | Medium: shared ownership/concurrency need design |
| PRSG-5 | [Durable alert delivery](2026-10-01/PRSG-5-alert-outbox.md) | Planned | 4–7 person-days | High for alert-dependent users; otherwise medium | Medium: receiver delivery semantics vary |

Estimates include focused tests, documentation, and Lead review for one engineer familiar with the repository. One person-day means roughly six focused engineering hours; these are planning ranges, not calendar promises. API/provider onboarding and user-testing recruitment are excluded. Parallel tasks may reduce elapsed time without reducing effort. Impact is a hypothesis about user friction or reliability, not a financial ROI or trading-return estimate.

## Quick-glance routing tags

| Ticket | Type | Modules | Owner | Priority | Effort | Impact |
|---|---|---|---|---|---|---|
| PRSG-1 | feature | backend, frontend, connectors | Engineer | P1 | M: 3–5 days | high |
| PRSG-2 | feature | backend, frontend, connectors, observability | Engineer | P2 | M: 3–5 days | high |
| PRSG-3 | feature | backend, frontend, financial-data | Engineer | P2 | M: 2–4 days | medium-high |
| PRSG-4 | feature | backend, frontend, connectors | Engineer | P2 | M: 3–5 days | medium |
| PRSG-5 | feature | backend, frontend, alerting | Engineer | P2 | M: 4–7 days | high |

Future research/feasibility tickets use `spike` and Researcher ownership; market-analysis spikes use Consultant ownership. Bugs include reproduction, severity and regression coverage. The planning skill defines all tag values and routing rules.

## Decision rationale

The inbox wins first because `backend/financial_services.py` and `frontend/src/pages/Financial.tsx` already expose the four datasets separately. New joins and presentation can be tested offline. Freshness instrumentation follows so users can judge dataset coverage. The forecast evaluator in `harness/forecast_review.py` is implemented separately; the broader answer harness YAML remains design-only.

This sequence refines the existing [implementation roadmap](../docs/IMPLEMENTATION_ROADMAP.md). It does not supersede current implementation evidence or authorize all backlog items to run at once. Only PRSG-1 is assigned now. Keep provider integrations, persistent Moomoo collection, model-backed answers, and trade execution outside these MVPs.

## Ticket convention and harness

### Searchable audit and completion history

Open the [ticket dashboard](https://jwtanx.github.io/praesagus/tickets/) to search title/description/key, filter tags/status/owner, sort records and review each committed progress snapshot with its commit link. CSV download is for spreadsheet sorting/export; JSON preserves nested checks, acceptance evidence and the full timeline. Keep progress in the ticket spec and `.harness.json`, commit checkpoints, and mark complete only after accepted evidence/review. PRSG-prefixed delivery commits are linked without silently changing acceptance state; PRSG-0 without a manifest is activity-only. Deleted manifests remain in the audit.

Build locally with `python3 scripts/planning/build_ticket_audit.py`, then serve `artifacts/` via `python3 -m http.server 8000 --directory artifacts` and open `/tickets/`. The generated audit is `artifacts/tickets/audit.json` (Git-ignored, downloadable from Pages). It is rebuilt from full first-parent history in every main-branch Pages deployment; committed specs/manifests and Git are the source of truth, not a manually synchronized spreadsheet. Every committed checkpoint is recorded; uncommitted activity and hidden branch-only history are not. A deployment snapshot is not a tamper-proof compliance archive, and declared test evidence still needs review. Shallow checkouts fail rather than publish incomplete history.

Commit titles: `PRSG-N Description`; shared harness changes use `PRSG-0`. Nonempty daily-brief-only changes require `[REPORT] YYYYMMDD` with a valid date and optional description. Mixed changes, empty commits and cross-boundary moves require a ticket title. Reports remain tracked. Enable hooks with `sh scripts/install_git_hooks.sh`; review titles before pushing.

The [verification runner](../docs/TICKET_VERIFICATION.md) checks actual Git scope and runs explicitly approved commands, producing revision-linked JSON evidence. Manual review is never auto-accepted. Update the dated Markdown and matching JSON manifest after delivery; the dashboard audit is generated from committed history.

Create plans under `plans/YYYY-MM-DD/` using the planning date in Asia/Kuala_Lumpur. Allocate the next unused repository-wide `PRSG-N` key; never restart numbering for a new day or reuse a completed key. Filename: `PRSG-N-short-title.md`, with matching `PRSG-N.harness.json`. Preserve creation date when resuming work. Each plan has a "When it's considered done" checklist whose stable IDs match JSON acceptance items. Mark a box only when evidence is recorded; pending reviews and measurements stay unchecked.

The planning skill defines the [manifest contract and researched patterns](../skills/praesagus-feature-planner/references/ticket-harness.md). Validate a manifest with:

```bash
python3 scripts/planning/validate_ticket.py plans/2026-10-01/PRSG-1.harness.json
# Check every path in the ticket's reviewed change set, including both rename endpoints:
python3 scripts/planning/validate_ticket.py plans/2026-10-01/PRSG-1.harness.json --changed-file backend/catalyst_services.py
```

The validator checks supplied paths and declared evidence, but does not collect a Git diff, run test commands, prevent edits, verify log truth, or implement the future answer runtime. Lead must compare the complete ticket diff against the frozen base, account for pre-existing dirty changes separately, and review evidence. Protected paths win. Future manifests have provisional scope until Lead accepts exact paths and freezes a base SHA before implementation.

## Delivery record

- Engineer session: `01a0f1ee-92bc-7ba0-add1-02a5023a6dad`.
- Researcher session: `01a0f1ec-b056-7a53-904e-46b944471262`.
- Consultant session: `01a0f21f-8fee-7ed2-aa49-04a7c7a8645b`.
- Lead writes these plans; Engineer edits only the accepted implementation scope. Confirm thread identity before messaging if sessions are replaced.
- Each completion updates its spec with changed files, exact validation results, known limitations, and release commit. Do not mark completion from a passing build alone.
- Lead reviews and integrates changes before publication. Preserve concurrent report, ledger, and skill edits.

For each future item, confirm scope against current code before starting, record estimate changes and reasons, and retain a measurable outcome check. No production analytics collector exists yet; initial user metrics can be measured in a recorded manual usability session.
