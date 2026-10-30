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

- [x] PRSG-158-D1: Recheck the current four representative states, retain a baseline and have Human select a Designer/Trader-reviewed bounded layout or accept an evidence-backed no-code outcome.
- [x] PRSG-158-D2: Essential instrument information fits 390px without horizontal document scrolling; observations, interpretations, forecasts and Unrated states remain distinct, with material limits adjacent and full provenance accessible.
- [x] PRSG-158-D3: Verify keyboard/focus/disclosure/filter/report-date/history behavior and unchanged financial values using relevant existing checks; replay frozen summary-fidelity examples where applicable.
- [ ] PRSG-158-D4: Record reader tasks, participant count, completion and misinterpretations for finding, Unrated meaning, source time and next check, and deliver actual preview/evidence/limitations for Human acceptance; claim no measured lift without a comparable baseline.

## Checks and Delivery

All implementation checks and acceptance items are pending. At implementation, record exact focused command/manual results and failures, inspect all changed paths (including new/deleted files and both rename endpoints), validate this manifest with every supplied changed path, and run required hooks on any authorized commit/push. Skill changes require metadata/reference checks and a frozen behavioral replay, plus human review before promotion. No code, model, prompt, rights policy, publication, schedule or role change is implemented by creating this ticket. A schema pass is planning validation only.


## Thirty-minute baseline release — 30 October 2026

Human asks Lead to continue the wishlist within30minutes. Lead selects the uncompleted158 reading/comprehension item; no completed presentation ticket is reopened. Accepted current slice is fresh baseline, two independent read-only reviews, relevant existing checks, an answer key and a real-human reader protocol. Currentbase51e0706e065f7bc767f21be8416138f48ff4bac7 supersedes the original planningbase only for this slice.

Lead owns this canonical pair and `docs/RESEARCH_READING_REVIEW.md`. Designer and Trader own separate private review folders; no shared writes and no source/provider/model/schedule work. The current manifest allows only these three documentation paths. Original proposed UI/test paths remain excluded until the required Human design selection. This boundary preserves the original acceptance items: a technical replay or AI review cannot satisfy human participant evidence or Human final acceptance. No-code is a candidate outcome requiring the same actual selection/reader evidence.

Representative baseline:8October SPY recorded numeric prediction (historical research, not current validation),21October SPY Unrated and missing-current-observation, and30September legacy AAPL. Freeze source/renderer hashes and describe real saved rows separately from authored test fixtures. The reader task uses the publicly saved21October SPY row; record missing source time as missing, never substitute report cutoff for it.


## Human-selected implementation freeze — 30 October 2026

Actual reader P1 interpreted Unrated as API-total failure and skipped work; finding/source time/next check were not answered. This is one qualitative observation, not a representative rate or measured improvement. Designer's actual390/1440 public baseline and Trader's saved-record replay identify a first-layer explanation gap; the prior no-code preference is superseded by this observed misunderstanding. Human explicitly selects **Add the explanation beside each chip** after reviewing the concrete proposal.

Engineer alone owns `artifacts/daily-market-brief/index.html`, `tests/compact_report_viewer_checks.cjs`, `tests/daily_report_viewer_checks.cjs`. Lead owns this pair and review documentation. Add a concise visible definition beneath each existing Unrated chip, a reason derived only from that instrument's recorded evidence/display guard and the next required check. Missing quote storage remains distinct from missing forecast inputs/publication review; a quote alone neither creates nor is universally required for a historical-anchor forecast. Unknown reason/check/time stays explicitly unrecorded. Keep every existing direction/numeric/unit guard,one chip perinstrument,financialvalue/null,date,horizon,scenario,source/disclosure/filter/history behavior. Link to SPY8October only with explicit historical-example label and original report date; never copy its greenchip into a later report. Retained timestamp on an unavailable row must be labelled retained,not a current issuance.

Focused checks: `node tests/compact_report_viewer_checks.cjs`, `node tests/daily_report_viewer_checks.cjs`, plus unchanged date-navigation/comparison replays already passed once for this baseline. Add meaningful reason-mapping/fallback/escape/no-data-mutation regressions to existing checks. Recheck390 layout and keyboard/disclosures after deployment or an equivalent safe review. All42 trackedfinancialJSON remain pinned and unchanged. No new provider/API call,forecast generation/model,source-rights approval or schedule is authorized by this display change. Human final acceptance and honest post-change reader observations remain required; a UI implementation alone is not proof of comprehension lift.


## Implemented candidate and independent review — 30 October 2026

The Human-selected adjacent explanation is implemented in the existing renderer. Both changed Node checks passed for Engineer and independently for Lead. Existing date-navigation/comparison baseline checks passed. Lead reviewed actual localhost public-report renders at390 and1440:document width matched viewport,one chip perinstrument remained,Enter/Space toggled prediction evidence,focus stayed visible,and8October SPY retained its dated green Bullish target/range. Full42financialJSON pins match the baseline; existing predictionState/targetTiming guards are unchanged.

Lead returned and Engineer fixed two concrete findings: a saved observed point with Unrated must not imply missing observations; unfamiliar nonempty recorded coverage notes must not be labelled absent. Their regressions passed. UI SHA256dc40b223389335a6871589a3967a1b0ddafb85861533315902b4ba99b18c7d9d. Raw known gaps remain accessible; unsupported-MY intake takes precedence over general storage failure. Historical link and retained timestamp wording preserve dates and uncertainty.

D1-D3 are verified. D4 and final Human review remain pending actual post-change reader response/acceptance; the preview and neutral reader tasks were delivered. Baseline participantN1 is actual anonymized qualitative feedback; post-changeN0 until an actual response arrives. No measured comprehension lift,200%zoom/screenreader certification,fresh forecast,provider success orsource rights are claimed. Required commit/push hooks and actual delivery are recorded separately.


## Published implementation — 30 October 2026

Implementation36265f94ef3c580ff6e8c4251d6ab6f88ab75600 is pushed toorigin/main. Required commit hook4149passed,41existingwarnings in95.03s;requiredpushhook4149passed,41warnings in92.67s. Pages run41085476040 succeeded. Public renderer bytes match reviewedSHAdc40b223389335a6871589a3967a1b0ddafb85861533315902b4ba99b18c7d9d exactly;Lead verified actual public21OctoberSPY explanation/onechip/historical link. GitHub CI41085476120 remained running at this observation and is not claimed passed. No trackedfinancialJSON changed.

The actual updated preview and neutral recheck questions were supplied to the Human. No post-change answer/final acceptance has arrived at this record,so D4,Humancheck and finalreview remain pending; ticket statusreview is intentional. Baseline N1 and post-changeN0 remain distinct,with no measured lift. This metadata delivery undergoes the required hooks too.
