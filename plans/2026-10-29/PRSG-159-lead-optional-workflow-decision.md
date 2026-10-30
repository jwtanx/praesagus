# PRSG-159 — Lead Skill and Schedule Simplification or Removal

Type: spike · Modules: skills, harness, docs · Owner: Lead · Priority: P1 · Effort: S (0.5–1 person-days, estimate) · Impact: high — addresses directly reported delivery or comprehension friction; benefit remains unmeasured.

## Objective

Deliver a bounded, reviewable decision and candidate prompts for slim Lead, on-demand Lead, or Lead-free delivery, preserving human pauses and independent financial/model review.

## Why the Ticket Is Created

All four retrospectives criticize coordination overhead or delayed integration. PRSG-122 completed an earlier instruction-trimming pass; PRSG-98 and 121 already address continuity and recovery. This is a new operating-model decision and observable-behavior check, not a duplicate promise to shorten the same prose. Lead is on break and gets no assignment.

## Approach

Timebox to one person-day. Engineer inventories only the relevant Lead skill, coordination/startup references and schedule definitions; privately inspect actual owned configuration read-only if needed. Compare three options: retain a shorter scheduled Lead; use Lead only on request/exception; or have Engineer integrate, specialists cross-review and Human freeze scope/accept delivery. Produce a concise candidate coordination prompt and a report-only prompt plus explicit ownership/acceptance/recovery substitutions and a dry-run cutover/rollback checklist. Link supporting rules once rather than copy them.

## Choices

Recommend a bounded Lead-free pilot for the next accepted delivery: Engineer integrates, AI Engineer and Engineer cross-review technical/model work, Trader reviews financial admission, Designer checks reading quality, Human owns scope and final acceptance. Retain optional Lead consultation only if the pilot reveals a specific unmet need. This is a recommendation, not a role retirement or authority change. Keep resource/rights/one-use releases and independent reviews; remove repeated packaging only.

## Findings

Checked-in schedules define 84 quarter-hour coordination opportunities plus one 06:00 report daily, with separate Trader 08:00. These are definitions, not verified current activity. PRSG-122 already recorded reduced instruction/prompt bytes; it did not measure a coordination-cost or delivery-time improvement. This ticket must inspect current behavior rather than assume prior trimming solved the bottleneck.

## Tradeoffs

Removing a permanent coordinator reduces handoffs but places integration load on Engineer and final decisions on Human. Slim scheduled Lead retains continuity at recurring overhead; on-demand Lead may delay unattended exceptions. Configuration cannot prove runtime guarantees or a no-AI timer. Never remove a role without replacement responsibilities and verified rollback.

## Ownership and Frozen Boundary

Proposed accountable owner: Engineer. No dispatch or implementation occurs in this compilation. Scope is provisional; planning baseline 50ce86d8c4c8f7a89acbe7df2536db2bb231b2b7. Human must select the final operating mode and freeze the exact accepted paths, baseline, checks and specialist write boundaries before implementation. Existing tickets retain their current ownership/status and history; this proposal does not silently transfer Lead-owned work. Independent review remains required, with Human final acceptance while Lead is on break. All existing unrelated dirty files, including .DS_Store, remain excluded.

Allowed paths: `plans/2026-10-29/PRSG-159-lead-optional-workflow-decision.md`, `plans/2026-10-29/PRSG-159.harness.json`, `docs/LEAD_OPTIONAL_DECISION.md`. Protected paths: `skills/`, `agent-operations/`, `AGENTS.md`, `docs/LEAD_WORKFLOW.md`, `connectors/`, `ingest/`, `artifacts/`, `.DS_Store`. Scope expansion requires an explicit contract revision before edits. Private source data, chat transcripts, account information and operational configuration stay outside Git.

Dependencies / reuse: PRSG-122, PRSG-98, PRSG-121. Dependencies identify interface/evidence reuse, not a claim that every parent must be complete before this slice can start.

## When It Is Considered Done

- [x] PRSG-159-D1: Compare the three viable operating modes within the one-person-day timebox, using current local evidence, ownership costs, risks and an explicit recommended pilot with stop/continue criteria.
- [x] PRSG-159-D2: Deliver concise candidate skill/coordination/report prompts and a role-responsibility map, showing actual UTF-8 byte counts and unavailable telemetry honestly; preserve pauses, resource gates, review and recovery semantics.
- [x] PRSG-159-D3: Replay completed-ticket preservation, busy owner, returned result, user amendment, missing worker state, denied dispatch, expired admission, resource block and human pause against the proposed behavior; record expected versus observed judgments.
- [x] PRSG-159-D4: Record the Human-selected continued Lead role, short-handoff pilot, concrete cutover/rollback and retained independent review. Candidate production prompt/schedule adoption remains human-review gated; no production instructions or schedules are changed by this spike.

## Checks and Delivery

All implementation checks and acceptance items are pending. At implementation, record exact focused command/manual results and failures, inspect all changed paths (including new/deleted files and both rename endpoints), validate this manifest with every supplied changed path, and run required hooks on any authorized commit/push. Skill changes require metadata/reference checks and a frozen behavioral replay, plus human review before promotion. No code, model, prompt, rights policy, publication, schedule or role change is implemented by creating this ticket. A schema pass is planning validation only.

## Accepted Scope Amendment — 30 October 2026

Human appointed the current Lead and explicitly resumes final team delivery. The chosen mode is continued lean Lead with short handoffs, not the earlier Lead-free recommendation. Lead owns this decision spike and docs/LEAD_OPTIONAL_DECISION.md; Engineer independently reviews it after157 implementation. Base cca89e514ed6217d3afb980063b604a53ff069c3. The spike delivers a decision and reviewable candidates, not installed production prompts or scheduling changes. The prior human-review-before-promotion boundary is preserved; Human-selected role authority is current evidence. All original options, quantitative honesty and frozen behavioral checks remain required.

## Independent Acceptance — 30 October 2026

30Oct independent Engineer review b6b5d9d1a4e6da0c1dd6132e2832e133514f39f3eb8fa82398ee7bc94632a527 accepted all10 frozen instruction cases and674/270UTF8candidate bytes; reviewed functional document d8ab65ff1ec67dcf740de9992ad14ccf3a4326a982b4f7cc3c459baad79ec7cd. Lead verified referenced hashes/cases and changed only final status sentence afterward; candidates/rules/measurements unchanged. Decision artifact only, no production prompt/schedule adoption. Final status-note-only document SHA 5fde5481e062fe1841b730f5b2df49b672fe19fa317ae765598046404d9df4e9. No runtime dispatch/cost improvement or production instruction promotion claimed. Commit/push hooks run at integration; this acceptance covers the completed decision spike only.
