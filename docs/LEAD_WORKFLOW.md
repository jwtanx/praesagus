# Three-agent delivery and schedule overview

## Roles

| Chat | Responsibility | Reused skills |
|---|---|---|
| Lead | Prioritize, freeze scope, review evidence, integrate and deliver | lead, praesagus-project-lead, praesagus-feature-planner |
| Engineer | Accepted bounded implementation and regression tests | praesagus-implementation |
| Trader | Financial judgment, daily reports, market interpretation and engineering context | daily-market-brief, technical-trend-analysis, trading orchestrator |

The canonical registry and safeguards are in [AGENTS.md](../AGENTS.md). Skills are instructions, not an autonomous execution engine.

## Ticket workflow

Dated PRSG spec + harness manifest -> accepted owner/base/path/check contract -> disjoint delegation -> tests and evidence -> independent Lead review -> separate ticket commit -> verified push/deployment. Busy chats are not interrupted or given duplicate work. Git history generates the ticket audit; never manually edit its generated JSON. See [verification](TICKET_VERIFICATION.md) and [planning contract](../skills/praesagus-feature-planner/references/ticket-harness.md).

## Approved schedules (Asia/Kuala_Lumpur)

- Lead coordination every15 minutes,09:00–05:45 next day (84 triggers).
- Separate06:00 wrap-up: results, blockers and next-day direction choices (85 total triggers/day). No new implementation during wrap-up.
- 06:15–08:45 inactive; app sleep/offline may delay or miss runs. A trigger is not a guarantee of execution or background continuity.
- Trader's08:00 daily-report schedule (legacy Researcher ownership until transfer) is separate and must not be altered by Lead resource recovery.

Lead-owned configurations and recovery prompts are stored privately in lead-state/schedules.md, not copied into public artifacts. Actual app-tool schedule settings are authoritative.

## Resource and recovery decisions

Use fresh supported account-usage readings and pmset battery readings. At <=5% remaining in five-hour or weekly window, checkpoint proactively. At <=2%, save context/dirty ownership; commit and push reviewed tickets only; pause confirmed Lead schedules and arrange one verified wake after the latest reset of the constraining windows. Unknown reset means no guessed wake. Fresh readings at recovery are mandatory.

At battery <=8%, save/read-back complete confirmed Lead schedule configurations before removal. Keep the private lead-schedules-backup.md until safe human /lead restoration verifies every restored configuration. Never remove Trader or other specialist schedules during Lead recovery. Battery safeguard takes precedence over usage recovery.

The [Lead skill](../skills/lead/SKILL.md) contains operating instructions and the sanitized schema2 usage input. Its status script diagnoses battery and both five-hour/weekly windows; legacy five-hour input leaves weekly unknown. Missing reset does not erase a known low remaining percentage, and blocks recovery instead of guessing. Neither this document nor the script automatically changes app schedules. Live removal/restoration requires app-tool verification.

## Credential onboarding

[PRSG-35](../plans/2026-10-02/PRSG-35-moomoo-credential-runbook.md) tracks the deferred AppKey/public-key/encrypted-private-key/login-Keychain runbook. It is not yet implemented. Credential contents, account data and recovery context never enter Git or public Pages.

Restart and migration: [startup prompts](../agent-operations/README.md), [four schedule definitions](../agent-operations/schedules/README.md), [spawn skill](../skills/spawn/SKILL.md). Verified private registry replaces fixed chat IDs. Researcher is retired as a permanent role; each role can use bounded research subagents. Preserve historical ownership and paused schedules.
