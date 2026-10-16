# Four-role delivery workflow

Shared safeguards/ticket conventions: [AGENTS.md](../AGENTS.md). Requested role models: [roles.json](../agent-operations/roles.json). Skills/configuration guide agents; they are not an autonomous runtime.

## Audit and disposition — 16 October 2026

| Finding | Decision | Change |
|---|---|---|
| Existing manifests, audit, validators, hooks, resource probe and verified app dispatch | KEEP | Reuse; no new registry/framework/database/dashboard |
| Routing/startup/recovery/continuation repeated in many long documents | SIMPLIFY | Shared rules in AGENTS; selective short role startup and Lead skills |
|6.9KBquarter-hour prompt and repeated all-team/history scans | SIMPLIFY | Short current-state/active-owner prompt; expand only for inconsistency or next accepted work |
| Four overlapping current private notes and append-only repeated status | FIX | Back up originals; one compact execution snapshot, other notes become pointers |
| Stale three-agent overview, null requested defaults and unconditional specialist loading | FIX | Four roles, verified supported IDs, requested effort defaults and relevant-only skills |
| Duplicate current-state prose and stale-history redispatch | REMOVE from hot path | Retain archived evidence/history; never infer unfinished work from old narrative |
| No exposed deterministic background dispatch/status-timer adapter | KEEP boundary | Existing heartbeat uses AI; don't claim a no-AI scheduler or replace it with private APIs/cron |

The installed app exposes programmatic send_message_to_thread and bounded wait_threads; project submissions, completions and returned evidence have been observed. Local resource/ticket/Git checks are deterministic. Neither makes those app tools callable by an unattended shell daemon. Official [scheduled task](https://learn.chatgpt.com/docs/automations) and [SDK](https://learn.chatgpt.com/docs/codex-sdk) documentation describe separate capabilities; no new SDK/runtime is installed here.

## Small working set

At entry load the verified role, ONE compact current checkpoint, active canonical ticket and necessary dependencies/files. Read broader plans/Git history only when finding the next accepted item or resolving inconsistency. Detailed feature planning, finance, model or transfer skills load only for that task. Never reread full logs/large JSON or whole trees to retrieve one field; select bounded fields and exclude runtimes/venvs.

Canonical dated harness manifests are the ticket registry. Matching specs hold durable requirements/evidence; Git records delivery and the audit is derived. Private execution state holds active-ticket pointers, ownership, decisions, handles/cursors, blockers and next action, not copied checklists or a competing registry. Completed tickets remain complete unless a new requirement, failed acceptance or verified regression justifies reopening. Preserve IDs/history.

## Sessions and dispatch

Use requested defaults on authorized supported creation/dispatch: gpt-6.1-sol low for Lead/AI Engineer, medium for Engineer/Trader; AI may use medium for a documented complex task. Bounded routine research may use gpt-6-luna/low. Configured/requested/applied/observed settings are different evidence; don't claim runtime verification without observation.

Prefer fresh minimal context per independent Lead run/worker ticket at a safe boundary; continue unfinished useful same-ticket work. Never transfer whole conversations, reset by elapsed time, restart an active worker or create chats solely to reduce a counter. Fresh context in this app requires an explicitly authorized new session and verified [spawn](../skills/spawn/SKILL.md) cutover; a heartbeat reuses its target chat and cannot erase its history. No fresh sessions are silently created by these documents.

Invoke only necessary roles, normally no more than two workers. A compact assignment links ticket/slice, exact scope/base/checks/output and handoff destination. Supporting specialists join only when their judgment affects acceptance. A successful dispatch is submission, not completion. Preserve one cursor and wait30–60seconds when dependent; don't poll unchanged snapshots rapidly or fetch full threads. Timeout/transient observation failure is not a terminal worker state. New user input amends active work; update affected artifacts and continue ready steps.

Lead reviews returned paths/evidence, performs appropriate independent checks, then integrates/commits/pushes/deploys under existing authority. Passing tests are not service/source/model/publication proof. Continue the next ready accepted dependency in the same run; otherwise save an exact blocker and release action. No invented backlog/activity.

## Schedules and resources

Keep verified original Lead quarter-hours09:00–05:45 next day and06:00 report; Trader08:00 remains separate. All timesAsia/Kuala_Lumpur. Preserve human pauses and ownership. No06:15–08:45 coordination. Check active work/resources cheaply; reason only for ready decisions, exceptions, reviews or blockers. A quiet heartbeat still uses AI; no no-AI scheduling mode is verified. App sleep/offline/permissions can prevent or delay execution.

Use [Lead control](../skills/lead/SKILL.md) and [resource recovery](../agent-operations/schedules/resource-recovery.md): fresh supported both-window usage and battery; checkpoint at<=5%, hardstop/recovery at<=2%, battery<=8% takes precedence. Exact private backups/readback precede mutations; only eligible original Lead schedules restore. Try exact direct one-time creation first; a tool-required suggestion remains pending, never active. No credit redemption without explicit authorization, duplicate wakes, silent pause reversal or restriction bypass.

## Verification and measurements

Use existing [verification](TICKET_VERIFICATION.md), scoped validator, role-selection/resource tests and focused behavior regressions; commit/push hooks remain mandatory. Replay completed-ticket preservation, busy owner, returned result, user amendment, missing worker state and denied dispatch without inventing completion. Skill validation alone is insufficient.

Compare UTF8instruction/prompt bytes before/after and count actual dispatch/status calls for this delivery. Byte reductions are not measured token/cost savings. Historical compaction frequency and reliable per-ticket model usage are unavailable in current exposed telemetry; report unavailable rather than estimate. No workflow claims model-quality or trading-performance improvement from instruction trimming.
