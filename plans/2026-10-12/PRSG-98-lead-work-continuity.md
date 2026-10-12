# PRSG-98 Lead work continuity

Type: skill · Modules: skills · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-days) · Impact: medium-high

Human requested correction after status answers repeatedly ended ongoing work. Lead skill 1.7 removes the unchanged-state exit ambiguity, requires a private execution record and a turn-ending ready-action audit, and treats human questions as steering. Planning-first work must finish concrete reviewable outputs without silently approving implementation. Resource/time/human pauses and the two-idle-run guard remain.

Accepted scope: skills/lead/SKILL.md and these two ticket files. General automation prompt was updated through the app and read back ACTIVE with the same target and cadence, without ticket-specific instructions. Other schedules and unrelated dirty files were untouched. Private records are not public deliverables. Skill instructions do not guarantee background execution.

## When it's considered done

- [x] PRSG-98-D1: Metadata and whitespace validation
- [x] PRSG-98-D2: Independent behavioral replay
- [x] PRSG-98-D3: Lead scope and schedule review

Evidence: skill-creator quick_validate returned Skill is valid; git diff --check passed. Independent scorer_plan agent replay identified synthetic-validation authority and pause-scope ambiguities; wording corrected. Lead read back ACTIVE automation with unchanged Lead target/time window. Actual continuation: Engineer exact contract returned, Trader financial decision review dispatched, offline source clarification packet prepared. This demonstrates concrete continuation, not guaranteed unattended delivery.
