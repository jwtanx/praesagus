---
name: spawn
description: Adopt the current Praesagus chat as Lead, Trader or Engineer with startup prompt, verified context handoff and schedule takeover. Use for /spawn ROLE, $spawn ROLE or /spawn all; not temporary research subagents.
license: MIT
metadata:
  author: praesagus
  version: "1.1"
---

# Adopt a replacement role

Resolve this SKILL.md to its canonical filesystem location before interpreting relative references when discovered through a symlink.

Read [agent operations](../../agent-operations/README.md), [role configuration](../../agent-operations/roles.json) and [transfer procedure](references/transfer.md). Use [handoff templates](../../agent-operations/handoffs/README.md) for private records. Accept lead, trader, engineer or all. `all` means every role in roles.json, not every chat in the app. `$spawn` is native skill invocation; `/spawn` is a natural-language alias, not a custom command registration.

A single-role invocation adopts the current calling chat as the successor; it does not authorize creating another chat. It authorizes reading/applying the selected startup prompt and compact checkpoint, renaming the current chat to the role, project-scoped checkpoint/bootstrap/release messages, moving their verified role schedules, renaming predecessors to `Role [YYYY-MM-DD]` (MYT replacement date) and archiving them after verified takeover. It does not authorize a live replacement merely because this skill is being authored/reviewed. Preserve unrelated chats, worktrees, schedules and human pauses. If multiple predecessors match or ownership is ambiguous, ask for identity rather than guess.

Use the current chat with a summarized checkpoint plus the actual startup prompt; do not call create_thread or fork_thread for a normal single-role invocation. Resolve the predecessor separately and never retire the current destination. If source and destination are already the same registered role, reconcile/read the context and schedules without another transfer or archive. Preserve current Lead/Engineer model settings. Trader requires gpt-6.1-sol/medium; if the current chat's setting cannot be inspected/changed with a supported tool, report that limitation and request the human setting change when necessary. Do not create another Trader to force a model override.

For `all`, use existing human-started destination chats for every configured role; obtain an explicit destination map where ambiguous, with at most one role assigned to the current chat. Hold the group until its destinations are known. Creating additional chats requires an explicit human request to create them; never silently fall back to creation because a destination is missing. Read the current registry first to avoid replacing a takeover completed in another chat.

The current agent records its own held readiness and release acknowledgment after actually reading the startup/checkpoint; do not message or wait on yourself. Other destination chats acknowledge via authorized messages and bounded wait_threads. Never archive a busy predecessor or activate overlapping schedules. A tool failure or pending confirmation stops dependent mutations; preserve a private transaction receipt for retry. Report partial progress accurately. Emit created-thread directives only if a separate explicit request actually created chats. This skill is an agent procedure, not atomic migration code or a guarantee of background execution.
