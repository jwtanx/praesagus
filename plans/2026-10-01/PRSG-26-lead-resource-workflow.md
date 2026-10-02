# PRSG-26 — Lead resource guard and schedule recovery

Type: skill · Modules: harness, skills · Owner: Lead · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Frozen base bb0d302bd4384482e628e5e1e58630e0d68396f4. Allowed scope: skills/lead/, tests/test_lead_status.py, AGENTS.md and this ticket metadata. Preserve unrelated PRSG-21–25 work and .DS_Store.

## Scope and decision

Implement read-only pmset battery probe and validated sanitized app-usage input, plus Lead-only skill instructions for delegation and save/remove/restore. The user explicitly withholds approval of recurring activation pending validation: create no 15-minute automation yet. No unsupported shell usage endpoint or auth scraping. The skill is an agent procedure, not an automatic monitor or role ACL.

Approved cadence: daily MYT quarter-hours09:00–23:45 and00:00–05:45 plus06:00 (85 checks,21-hour span), using two complementary Lead heartbeats. User approved 2026-10-01. At usage5%checkpoint, <=2% pause/checkpoint with one reported-reset wake; battery<=8% takes precedence and backs up confirmed Lead-owned schedules before removal. Bare human /lead restores a saved backup only after safe live readings; otherwise it checks resources. Private backup requires complete inventory, readback and ownership verification; partial restore retains backup, original paused statuses preserved, expired one-time schedules skipped. Unknown readings stop new work. Save work does not mean commit unreviewed files.

## When it's considered done

## Accepted amendment — 2026-10-02

Lead adds docs/LEAD_WORKFLOW.md to scope for the approved four-agent/resource overview; original base retained. Weekly guards now require script alignment, not just instruction text. Engineer may edit only skills/lead/scripts/status.py and tests/test_lead_status.py; Lead owns skill/docs/metadata and schedule configuration. Existing26-test evidence is historical, not proof of new weekly behavior.

Accept sanitized schema2 input: shared fresh aware sampled_at and windows.five_hour (300 minutes), windows.weekly (10080 minutes), each usedPercent/resetsAt. Parse percentages independently of reset metadata. Legacy flat input remains readable as five-hour only with weekly unknown; never overall ready. Reject mixed/unknown schemas, wrong/bool durations, nonfinite/bool percentages, stale/future/naive samples. Known low usage must remain visible with missing/invalid reset.

Battery<=8 overrides. Any known remaining<=2 checkpoints/pauses; otherwise any<=5 checkpoints; missing/incomplete metadata blocks new work. Recovery is blocked with unknown battery/window/reset, else ceil(latest reset of windows<=2)+60. Retain existing five_hour_remaining_percent/reset_epoch keys, add weekly remaining, constraining windows, recovery epoch/status and blockers. Script diagnoses only, no schedule or network mutations. Deterministic replay covers both windows, thresholds, unknown resets, legacy input, fractional reset ceiling and battery precedence. New script checks stay pending until implemented; Lead independently reviews before completion.

- [x] PRSG-26-D1: Resource checks and Lead-only recovery workflow validated; human activation decision recorded.

## Evidence and limits

22 pytest cases passed. Skill quick validator and diff whitespace check passed. Live battery29% then28%; app usage89% remaining, reset2026-10-02 03:50:20 MYT. Independent real delete/restore and scheduler roundtrip not exercised; no live schedule mutation performed. Shell alone reports usageunknown correctly; supported app tool supplies five-hour data. Native skill discovery may require chat refresh; /lead is a text trigger, $lead explicit skill invocation.

No commit/push in this pass. Keep pending human review/activation distinct from future runtime enforcement.

## Lead acceptance — 2026-10-02

Historical statements above describe earlier passes. Lead reviewed the complete current script/tests/skill/docs changes; independent84 tests passed0.08s, Researcher84passed0.06s plus synthetic edge cases found no blocker. Skillv1.4 metadata validation passed. Both Lead schedule prompts now include weekly safeguards, updated through the app tool and read back ACTIVE with original cadence/Lead target. Full configurations saved privately. Accept diagnostic guards and approved workflow instructions only: script does not mutate schedules, full battery backup/delete/restore is not end-to-end proven. Git records separate delivery; never treat this acceptance as live market-data or forecast validation.
