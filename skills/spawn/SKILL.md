---
name: spawn
description: Adopt the current Praesagus chat for one role, or create fresh Lead, Trader and Engineer chats for all, with startup prompts and verified schedule takeover. Use for /spawn ROLE, $spawn ROLE or /spawn all; not temporary research subagents.
license: MIT
metadata:
  author: praesagus
  version: "1.2"
---

# Adopt a replacement role

Resolve this SKILL.md to its canonical filesystem location before interpreting relative references when discovered through a symlink.

Read [agent operations](../../agent-operations/README.md), [role configuration](../../agent-operations/roles.json) and [transfer procedure](references/transfer.md). Use [handoff templates](../../agent-operations/handoffs/README.md) for private records. Accept lead, trader, engineer or all. `all` means every role in roles.json, not every chat in the app. `$spawn` is native skill invocation; `/spawn` is a natural-language alias, not a custom command registration.

A single-role invocation adopts the current calling chat as the successor; it does not authorize creating another chat. It authorizes reading/applying the selected startup prompt and compact checkpoint, renaming the current chat to the role, project-scoped checkpoint/bootstrap/release messages, moving their verified role schedules, renaming predecessors to `Role [YYYY-MM-DD]` (MYT replacement date) and archiving them after verified takeover. It does not authorize a live replacement merely because this skill is being authored/reviewed. Preserve unrelated chats, worktrees, schedules and human pauses. If multiple predecessors match or ownership is ambiguous, ask for identity rather than guess.

Use the current chat with a summarized checkpoint plus the actual startup prompt; do not call create_thread or fork_thread for a normal single-role invocation. Resolve the predecessor separately and never retire the current destination. If source and destination are already the same registered role, reconcile/read the context and schedules without another transfer or archive. Preserve current Lead/Engineer settings. Trader prefers gpt-6.1-sol/medium, but inability to inspect or select it must never block the takeover or assigned report work; preserve the current runtime setting and never claim an unverified setting. Do not create another Trader to force a model override.

For `all`, the invocation explicitly authorizes creating one fresh local chat per configured role with create_thread and renaming each to its exact role name (Lead, Trader, Engineer). Call list_projects first and select the verified Praesagus project; use its local environment without a worktree or fork. The calling chat coordinates the transfer and does not adopt a role. Do not ask for a destination map or separate creation confirmation. Record each returned ID before creating the next chat; on retry reuse this transaction’s verified destinations instead of creating duplicates. Read the current registry first to avoid replacing a takeover completed in another chat. If the human explicitly supplies destinations instead, honor that map.

When the human says not to pull over context, do not read predecessor chat history or private narrative checkpoints and do not request narrative handoffs. Bootstrap each role from its actual startup prompt, the human-supplied progress summary and canonical ticket evidence. Still verify predecessor identity, idle status, dirty-file ownership and schedule configuration through bounded operational evidence; if that cannot be established without excluded context, keep the affected transfer held and report the gap.

The current agent records its own held readiness and release acknowledgment after actually reading the startup/checkpoint; do not message or wait on yourself. Other destination chats acknowledge via authorized messages and bounded wait_threads. Never archive a busy predecessor or activate overlapping schedules. A tool failure or pending confirmation stops dependent mutations; preserve a private transaction receipt for retry. Report partial progress accurately. Emit a created-thread directive for every chat actually created by an `all` invocation; use clientThreadId only while creation is pending. This skill is an agent procedure, not atomic migration code or a guarantee of background execution.
