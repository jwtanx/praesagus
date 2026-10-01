# PRSG-26 — Lead resource guard and schedule recovery

Type: skill · Modules: harness, skills · Owner: Lead · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Frozen base bb0d302bd4384482e628e5e1e58630e0d68396f4. Allowed scope: skills/lead/, tests/test_lead_status.py, AGENTS.md and this ticket metadata. Preserve unrelated PRSG-21–25 work and .DS_Store.

## Scope and decision

Implement read-only pmset battery probe and validated sanitized app-usage input, plus Lead-only skill instructions for delegation and save/remove/restore. The user explicitly withholds approval of recurring activation pending validation: create no 15-minute automation yet. No unsupported shell usage endpoint or auth scraping. The skill is an agent procedure, not an automatic monitor or role ACL.

Approved cadence: daily MYT quarter-hours09:00–23:45 and00:00–05:45 plus06:00 (85 checks,21-hour span), using two complementary Lead heartbeats. User approved 2026-10-01. At usage5%checkpoint, <=2% pause/checkpoint with one reported-reset wake; battery<=8% takes precedence and backs up confirmed Lead-owned schedules before removal. Bare human /lead restores a saved backup only after safe live readings; otherwise it checks resources. Private backup requires complete inventory, readback and ownership verification; partial restore retains backup, original paused statuses preserved, expired one-time schedules skipped. Unknown readings stop new work. Save work does not mean commit unreviewed files.

## When it's considered done

- [ ] PRSG-26-D1: Resource checks and Lead-only recovery workflow validated; human activation decision recorded.

## Evidence and limits

22 pytest cases passed. Skill quick validator and diff whitespace check passed. Live battery29% then28%; app usage89% remaining, reset2026-10-02 03:50:20 MYT. Independent real delete/restore and scheduler roundtrip not exercised; no live schedule mutation performed. Shell alone reports usageunknown correctly; supported app tool supplies five-hour data. Native skill discovery may require chat refresh; /lead is a text trigger, $lead explicit skill invocation.

No commit/push in this pass. Keep pending human review/activation distinct from future runtime enforcement.
