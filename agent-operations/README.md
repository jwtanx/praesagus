# Agent operations

Configured roles and requested defaults: [roles.json](roles.json). Registration is separate: verified IDs, states, model observations and transfer receipts live privately under `/Users/jwtan/.codex/lead-state/`. Never commit those IDs, prompts, credentials or private context.

| Role | Startup | Requested model |
|---|---|---|
| Lead | [lead.md](startup-prompts/lead.md) | gpt-6.1-sol / low |
| Engineer | [engineer.md](startup-prompts/engineer.md) | gpt-6.1-sol / medium |
| AI Engineer | [ai-engineer.md](startup-prompts/ai-engineer.md) | gpt-6.1-sol / low; medium for complex work |
| Trader | [trader.md](startup-prompts/trader.md) | gpt-6.1-sol / medium |

Verify support on the actual host before applying defaults on authorized creation/dispatch. A requested setting or successful submission is not independent runtime verification. An unavailable preference must not block useful work; use an available supported setting and disclose it. Bounded routine research may use gpt-6-luna/low; stronger research gpt-6.1-sol/low. Invoke only required roles, normally at most two workers. Preserve historical owners and unrelated Designer work.

## Shared startup

Read AGENTS.md, this file, the explicitly assigned role prompt and the compact active-ticket checkpoint. Verify current role/checkout, accepted ticket scope and dirty ownership. No assignment means wait; don't replay old tickets or reporting. During takeover stay held until verified release; no duplicate schedules, predecessor edits or source retirement while busy. Project-scoped registered-role messages/return handoffs are authorized; external messages, paid access and trades require their own authority.

Independent tasks use fresh minimal context at safe verified boundaries when supported/authorized. Continue useful unfinished same-ticket work. Load only active ticket, necessary dependencies/files and durable decisions; no full histories, arbitrary time resets or automatic compaction requests. One private current snapshot links to canonical evidence; archive a prior snapshot before replacing it. See [workflow](../docs/LEAD_WORKFLOW.md) and existing [handoff templates](handoffs/README.md).

## Role replacement

Use [spawn](../skills/spawn/SKILL.md) for `$spawn`/`/spawn lead|trader|engineer|ai-engineer|all`. Normal single-role adoption reuses the caller; explicit fresh-role/all modes create held destinations with readiness/ownership/schedule verification. Respect no-predecessor-context requests and existing returned IDs on retry. Configuration/skill edits do not create a chat or perform a takeover. AI Engineer has no default schedule; aliases ai_engineer/ai engineer select that role.

[Schedule definitions](schedules/README.md) describe existing workflows, not provisioned runtime. Preserve all human pauses and unrelated schedules. Human-started fresh roles must be explicitly selected and registered; never infer a role from repository access. These instructions do not implement a general agent service.
