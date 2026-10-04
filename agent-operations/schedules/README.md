# Schedule definitions

All times use Asia/Kuala_Lumpur. These are four workflow definitions, not four guaranteed active automation records. Actual app-tool configurations are authoritative; app sleep/offline can delay or miss runs.

| Definition | Owner | Trigger |
|---|---|---|
| [Daily report](trader-daily-report.md) | Trader | Daily 08:00 |
| [Daily planning](lead-daily-planning.md) | Lead | Daily 06:00, report only |
| [Coordination](lead-coordination.md) | Lead | Every 15 minutes, 09:00–05:45 next day |
| [Resource recovery](resource-recovery.md) | Lead | Conditions checked during Lead work; one-time usage recovery when needed |

The 06:00 report closes the 09:00–06:00 period: 84 coordination triggers plus one report, 85 total daily. No coordination at 06:15–08:45. Resource recovery is conditional, not another recurring timer.

## Reconcile on restart

Use automation_update view and inspect local automation metadata. Match exact verified target chat and role, preserve notification policy/status and private full configuration. Keep registry `/Users/jwtan/.codex/lead-state/schedules.md` current. Do not copy private full prompts or account context into Git. Update matching owned schedules rather than duplicate them. Outside an explicit spawn transaction, create missing schedules only after confirmed takeover/release and safe checks. During a held spawn bootstrap, the coordinator may prepare inactive replacements before release; activation still requires verified cutover and resource guards. pause or backup removal takes precedence. Use heartbeat tools; do not install cron workarounds or handwrite UI directives.

For transfer, follow skills/spawn/SKILL.md. Only transfer schedules with verified ownership. Remove old schedules after replacements have been verified inactive; activate replacements only after old removal and successor release acknowledgment are verified, preserving original paused state. Confirm returned target, cadence, timezone, status and next run when available. A pending product confirmation is not active scheduling.

## Observed baseline, 2026-10-04

Local configuration showed daily report at 08:01 under Researcher (active), Lead 06:00 (active), Lead quarter-hour (paused), and an active recurring 18:05 recovery entry in another chat. This is an inspection snapshot, not live verification or an endorsed recovery timer. On first migration inspect the latter separately; do not delete unverified other-chat schedules. Move the report to Trader and change it to 08:00 only as part of an explicit verified transfer. Preserve old contexts/history; retire Researcher as a permanent role after relevant handoffs succeed.

All schedule prompts check verified active-role/transaction state first and exit while held or retired. A released waiting role continues only its permitted reporting/recovery behavior or previously accepted work; it cannot start a new human direction.
