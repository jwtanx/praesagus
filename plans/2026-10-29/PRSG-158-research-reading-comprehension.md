# PRSG-158 — Research Reading Path and Reader Comprehension

Type: feature · Modules: frontend, market-research, docs · Owner: Engineer · Priority: P2 · Effort: S (1–2 person-days, estimate) · Impact: medium-high — addresses directly reported delivery or comprehension friction; benefit remains unmeasured.

## Objective

Verify and, only where a fresh baseline finds a gap, improve one representative daily-report reading path so readers identify the finding, evidence limits and next check.

## Why the Ticket Is Created

Designer asks for finding, interpretation, next check and evidence hierarchy; Trader asks for understandable prices/predictions/timing. PRSG-87/89/96 already delivered compact report views, prediction chips and responsive cards. Their completed status does not prove reader comprehension; this new requirement is a measured reading task and a bounded design delta.

## Approach

Designer rechecks the actual current implementation and supported, Unrated, missing-observation and historical fixtures at 390px and desktop. Trader determines material adjacent limitations and approves example copy. Human selects the annotated design before any UI edit. Engineer implements only confirmed gaps using existing components. AI Engineer reviews frozen summary examples for unsupported certainty and attribution where summaries exist; absence of generated summaries is recorded and does not authorize adding an LLM path.

## Choices

One representative view, existing components and native disclosures. Keep forecasts, report data, financial calculations and timestamps immutable. A no-code outcome is valid when the baseline already satisfies the design and reader tasks; record findings rather than repeat PRSG-96 styling. Designer supplies private annotations, Trader and AI Engineer supply disjoint review artifacts; Engineer alone owns listed shared files.

## Findings

The latest Designer retrospective describes prior observations that require rechecking. PRSG-96 already records responsive, keyboard, provenance and contrast review at 390/768/1440px, while native 200% zoom remains explicitly deferred and reader-study evidence is absent. No new UI defect or usability lift is established by this planning ticket.

## Tradeoffs

Shorter first-layer copy must not remove uncertainty material to a claim. Reader observations require available human participants; if none are available, the reader gate remains pending with a concrete blocker. Automated checks and synthetic reviews cannot substitute for human comprehension evidence.

## Ownership and Frozen Boundary

Proposed accountable owner: Engineer. No dispatch or implementation occurs in this compilation. Scope is provisional; planning baseline 50ce86d8c4c8f7a89acbe7df2536db2bb231b2b7. Human must select the final operating mode and freeze the exact accepted paths, baseline, checks and specialist write boundaries before implementation. Existing tickets retain their current ownership/status and history; this proposal does not silently transfer Lead-owned work. Independent review remains required, with Human final acceptance while Lead is on break. All existing unrelated dirty files, including .DS_Store, remain excluded.

Allowed paths: `plans/2026-10-29/PRSG-158-research-reading-comprehension.md`, `plans/2026-10-29/PRSG-158.harness.json`, `artifacts/daily-market-brief/index.html`, `tests/compact_report_viewer_checks.cjs`, `tests/daily_report_viewer_checks.cjs`, `docs/RESEARCH_READING_REVIEW.md`. Protected paths: `artifacts/daily-market-brief/reports/`, `artifacts/financial-calendar/`, `connectors/`, `ingest/`, `backend/`, `frontend/`, `skills/`, `.DS_Store`. Scope expansion requires an explicit contract revision before edits. Private source data, chat transcripts, account information and operational configuration stay outside Git.

Dependencies / reuse: PRSG-87, PRSG-89, PRSG-96, PRSG-157. Dependencies identify interface/evidence reuse, not a claim that every parent must be complete before this slice can start.

## When It Is Considered Done

- [ ] PRSG-158-D1: Recheck the current four representative states, retain a baseline and have Human select a Designer/Trader-reviewed bounded layout or accept an evidence-backed no-code outcome.
- [ ] PRSG-158-D2: Essential instrument information fits 390px without horizontal document scrolling; observations, interpretations, forecasts and Unrated states remain distinct, with material limits adjacent and full provenance accessible.
- [ ] PRSG-158-D3: Verify keyboard/focus/disclosure/filter/report-date/history behavior and unchanged financial values using relevant existing checks; replay frozen summary-fidelity examples where applicable.
- [ ] PRSG-158-D4: Record reader tasks, participant count, completion and misinterpretations for finding, Unrated meaning, source time and next check, and deliver actual preview/evidence/limitations for Human acceptance; claim no measured lift without a comparable baseline.

## Checks and Delivery

All implementation checks and acceptance items are pending. At implementation, record exact focused command/manual results and failures, inspect all changed paths (including new/deleted files and both rename endpoints), validate this manifest with every supplied changed path, and run required hooks on any authorized commit/push. Skill changes require metadata/reference checks and a frozen behavioral replay, plus human review before promotion. No code, model, prompt, rights policy, publication, schedule or role change is implemented by creating this ticket. A schema pass is planning validation only.
