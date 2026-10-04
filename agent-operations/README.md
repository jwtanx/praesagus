# Agent operations

The permanent team is Lead, Trader and Engineer. Adopt the current human-started chat as a replacement with `$spawn lead`, `$spawn trader`, `$spawn engineer` or `$spawn all`; `/spawn ROLE` is the equivalent natural-language request, not a registered slash command. Single-role invocation reuses this calling chat; it never opens an extra chat. For all, supply existing destination chats for each role; missing/ambiguous destinations require clarification, not automatic creation. Read [the migration skill](../skills/spawn/SKILL.md). This folder contains instructions, not a running agent service.

| Role | Startup prompt | Model |
|---|---|---|
| Lead | [lead.md](startup-prompts/lead.md) | Keep current setting unless human specifies |
| Trader | [trader.md](startup-prompts/trader.md) | gpt-6.1-sol, medium |
| Engineer | [engineer.md](startup-prompts/engineer.md) | Keep current setting unless human specifies |

Use [roles.json](roles.json) as the configured role list for `all`. Temporary researchers are subagents, not permanent chats: long-context extraction/comparison uses gpt-6-luna with low reasoning; research needing stronger reasoning uses gpt-6.1-sol with low reasoning. Trader report subagents use gpt-6.1-sol with low reasoning. Keep financial judgment and final report acceptance with Trader; Lead owns project scope and delivery acceptance. Do not silently raise effort or substitute unavailable models.

## Handoff templates

Use [compact handoff and private record templates](handoffs/README.md) for each replacement. Keep permanent project evidence in plans/manifests and private role/schedule continuity outside Git.

## Restart

Read AGENTS.md, the selected startup prompt, the private transfer checkpoint, actual ticket specs/manifests and working-tree status. A successor remains held until the migration coordinator explicitly releases it. It must not create schedules or edit predecessor-owned work during that hold.

Store verified active role IDs and per-role host/project/settings in `/Users/jwtan/.codex/lead-state/roles.json`; store private checkpoints/migration receipts under `/Users/jwtan/.codex/lead-state/transfers/`. Registry entries are pointers to verify against app tools, not proof of ownership. Preserve existing lead-state backups/context. Do not commit private summaries, schedule prompts, account data or chat IDs.

Read [schedule definitions](schedules/README.md). Reconcile existing schedules and partial transfers before creating any. Preserve human-paused status; startup does not authorize resuming paused work. Human-started chats use the selected startup prompt and take over summarized context in place. Fresh manually created chats need an explicitly selected role and verified registration; never infer role from this repository alone.

This delivery adds reusable instructions. Separate explicit role takeovers may already exist; inspect the private active registry and actual app state before any replacement. Legacy Researcher report ownership and Consultant-to-Trader responsibilities are transferred only when verified; historical tickets retain their original owners. These files do not initiate a takeover merely by being read.
