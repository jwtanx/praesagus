---
name: lead
description: Lead-only resource checks, approved schedule reconciliation and recovery. Use for Lead scheduling, /lead and resource restoration; not specialist work.
license: MIT
metadata:
  author: praesagus
  version: "2.0"
---

# Lead resource and schedule control

## Scope and loading

Verify the released Lead in `/Users/jwtan/.codex/lead-state/roles.json` before mutations. The registry is a pointer, not access control; reconcile actual app ownership. Use [project coordination](../praesagus-project-lead/SKILL.md) for assignments/review; load [feature planning](../praesagus-feature-planner/SKILL.md) only for new scope. Routine checks load the current compact execution pointer and active ticket, not all private notes/history.

`check` is read-only. `start` needs schedule authority. `checkpoint`/`restore` use the standing human authorization for Lead-owned resource recovery (reaffirmed16Oct2026), with no repeat permission. Bare `/lead` or `$lead` with `lead-schedules-backup.md` authorizes eligible restoration; without a backup it checks. New unrelated schedules, trades, purchases and credit redemption remain outside that authority.

## Resource gate

1. Fetch supported usage once. Use both windows from ONE rateLimitsByLimitId bucket, falling back to rateLimits; do not combine buckets. Save schema2 `{schema_version:2,sampled_at:<awareUTC>,windows:{five_hour:{usedPercent,windowDurationMins:300,resetsAt},weekly:{usedPercent,windowDurationMins:10080,resetsAt}}}` with unknown fields null. Never read authentication/session logs for usage.
2. Run `sh skills/lead/scripts/status.sh --usage-json PATH`; it samples pmset. Usage must be under5minutes old. Unknown/stale/future readings stop new work. Recheck before expensive steps and every5minutes during sustained work.
3. Follow the deterministic result. Battery<=8% takes precedence even charging. Either usage window<=5% remaining: checkpoint before new work. At<=2%: hard stop and recovery below. Other exhausted buckets still bind. Restore only with battery>8%, BOTH windows>5%, known metadata and no other blocker. Don't redeem a reset credit without explicit human approval for that use.

The script diagnoses; it does not fetch usage, dispatch, schedule, remove tasks or guarantee resource enforcement. Do not bypass tool/OS restrictions.

## Approved schedules and efficient checks

Existing Lead schedules: quarter-hours09:00–05:45 next day, plus a06:00 report, Asia/Kuala_Lumpur. No06:15–08:45 coordination. Preserve their exact targets/cadences/status/notification policy and all human pauses; don't alter Trader's08:00 schedule or other roles. Actual tool/local configuration outranks prose. No scheduler is provisioned by this skill.

Use a compact current-state check: active ticket/dependencies and owned dirty paths, one bounded app status snapshot for assigned workers, then decide. No all-team/history scan unless relevant evidence is inconsistent. Never restart a busy worker or redispatch completed work. Continue accepted ready review/integration/delivery in the same run; a question or passing test is not a stopping condition. If nothing independent remains, save the exact dependency and yield without repeated unchanged polling. Keep unchanged/non-actionable notifications quiet.

Heartbeat runs use AI; the exposed automation tool has no verified no-AI status-timer mode. Don't claim one or install cron/private-endpoint workarounds. Fresh context is a safe-boundary procedure, not an ability to erase this conversation. See [operating workflow](../../docs/LEAD_WORKFLOW.md).

06:00 is report-only: previous09:00–06:00 results with actual cutoff, accepted tickets/commits/checks, owners, pending reviews, blockers/resources and next priorities. Separate reported/verified and committed/pushed/deployed. Save one compact wrap-up/restart pointer; report late/missed runs truthfully. Ask for selection only for genuinely new directions, not already approved work.

## Checkpoint and usage recovery

Save one current private execution snapshot: active objective/authority, canonical ticket pointers, owned dirty paths, live worker IDs/cursors, verified evidence links, exact next action and stopping condition. Replace stale current content after backing it up; don't append the same status to several files. Preserve existing recovery transactions. Commit/push only already independently reviewed ticket changes; never stash/reset unrelated work.

At usage<=2%:

1. Inventory actual automations and verify exact Lead target. Back up FULL restorable configs/statuses privately, with checksum/progress; read back before mutations. Unknown ownership or failed backup means no mutation.
2. Pause only verified Lead recurring IDs; preserve originally paused state, Trader and human pauses. Verify returned/local settings. Record partial failures immediately.
3. Derive ONE candidate wake from ceil(latest reset among currently constrained windows)+120seconds. Unknown reset means no guessed wake. Reuse a matching existing wake; skip an expired anchor on human resume.
4. Try automation_update mode=create with the exact anchored COUNT=1 rule first. No additional human confirmation is needed. If the tool explicitly rejects anchored creation and requires suggested_create, submit that fallback once, mark PENDING and never call it active. Do not approximate with a recurring timer or duplicate cards. Permission denial stops the action; no shell/symlink/alternate-agent bypass.
5. At recovery, repeat fresh resource/ownership/config checks and restore only originally ACTIVE eligible Lead schedules. Verify every result. Existing authority covers continuation of approved work, not new scope. App sleep/offline may delay or miss a wake; no guarantee of execution.

## Battery removal and restoration

At battery<=8%, checkpoint and inventory verified Lead schedules including recovery wakes. Before deletion, save/read-back `lead-schedules-backup.md` with exact ID/name/kind/target/prompt/rule/timezone/status/policy/model/project/execution fields, checksum and per-entry progress. Merge an unfinished backup; never overwrite it. Delete only verified Lead entries with the automation tool, recording each result. If ownership/backup is uncertain, remove nothing. No automatic restoration while battery-low.

When resources are safe under standing recovery authority, reconcile surviving/new IDs before recreating anything. Restore only removed entries with original configuration/status; paused stays paused. Expired one-time wakes are skipped, not replayed. Record each new ID, verify all readbacks, then remove only the temporary backup while retaining the restoration receipt. Partial failure retains the backup. Never touch Trader or silently resume a human pause.

## Validation boundaries

[Resource recovery summary](../../agent-operations/schedules/resource-recovery.md) and tested status.py thresholds remain binding. Replay: weekly2% blocks despite five-hour80%; later weekly reset wins when both constrained; unknown reset forbids a wake; battery8% overrides usage; busy owner is never restarted; returned passing work still needs Lead acceptance/push; denied dispatch is not delivered. Tests prove diagnostic/mechanical behavior, not live permissions, actual model quality or schedule guarantees.
