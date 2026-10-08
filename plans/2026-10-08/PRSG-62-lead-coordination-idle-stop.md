# PRSG-62 — Register and clarify Lead coordination workflow

Type: skill · Modules: skills, docs · Owner: Lead · Priority: P2 · Effort: S (0.5–1 person-day) · Impact: medium; makes Lead workflow discovery reliable and stops an unproductive recurring coordination schedule after two consecutive idle team runs.

Created 2026-10-08 MYT. This is a narrow follow-up to the Lead role and schedule workflow.

## Objective and boundary

Expose the existing Lead skill through the repository's `.agents/skills` discovery path and clarify how two consecutive 15-minute coordination runs without team coordination or progress affect the schedule. The Lead skill must direct the operator to pause the quarter-hour schedule, record both runs in private context, and await explicit human direction before reactivation. Unrelated solo maintenance does not reset the consecutive-idle count.

No app code, ticket verification logic, report workflow, peer role, or unrelated schedule is in scope. The instruction is not an autonomous runtime and does not make the app execute while closed.

## Frozen scope

Base SHA: `14407bdb1df85044390083989400d56d51fb4961`. Write only `skills/lead/SKILL.md`, `.agents/skills/lead`, and this ticket's Markdown/manifest. The symlink must resolve inside the repository to `skills/lead`. All other paths are protected. Owner and reviewer: Lead.

## When it's considered done

- [x] PRSG-62-D1: Lead skill is discoverable through the repository symlink and passes skill validation.
- [x] PRSG-62-D2: The two-consecutive-idle rule is present in the reusable skill and the active schedule prompt; the schedule remains active before the condition occurs.
- [x] PRSG-62-D3: Offline behavior replay confirms two consecutive runs with no team coordination/progress lead to pausing and recording both runs; solo maintenance does not reset the count.

## Evidence and limits

The `.agents/skills/lead` symlink resolves to the repository's `skills/lead` directory. The bundled `skill-creator/scripts/quick_validate.py` reports the Lead skill valid. Local automation metadata confirms the active 15-minute schedule targets the registered Lead chat and its prompt contains the two-run pause and record rule. An offline scenario replay of `no team work`, `no team work` yields `pause and record`; a solo-only first run does not clear the counter. No real two-run pause event has occurred during this review, so the production schedule remains active. Prompt instructions are not runtime-enforced by application code.
