# PRSG-79 — Keep Trader reporting model-independent and locally validated

Type: skill · Modules: skills, docs · Owner: Trader · Priority: P1 · Effort: XS (0.3–0.5 person-days, estimate) · Impact: medium-high — avoids skipped scheduled reports when preferred model settings cannot be inspected and makes the existing report-component validator a required final step.

Created 2026-10-09 MYT. Frozen integration base: `ec35583d0019e5cc974cb50d95c24d53faf77081`.

## Objective

Allow the registered Trader to complete scheduled report work on the current supported runtime when preferred model settings are unavailable or unverified. Require the already committed report validator after each final report write, before delivery or publication.

The model preference remains gpt-6.1-sol/medium for Trader synthesis and gpt-6.1-sol/low for bounded report research when available. It is a preference, not a report-work gate. Do not claim the live model setting is verified without direct evidence.

## Accepted scope

- `AGENTS.md`
- `agent-operations/README.md`
- `agent-operations/schedules/trader-daily-report.md`
- `agent-operations/startup-prompts/trader.md`
- `skills/daily-market-brief/SKILL.md`
- `skills/spawn/SKILL.md`
- `skills/spawn/references/transfer.md`
- This specification and its matching harness manifest.

The configured preferred model in `agent-operations/roles.json` is preserved. Existing report artifacts, report validator implementation, model weights, dependencies, report data, forecast ledger, and live role/schedule state are protected by this ticket. The already updated app automation is external to Git and remains ACTIVE with the Trader target; this ticket does not mutate its state.

## When it's considered done

- [x] PRSG-79-D1: Trader and report guidance explicitly permits report work on the current supported runtime when preferred model settings are unavailable or unverified, while preserving preferences and prohibiting unsupported claims of verification.
- [x] PRSG-79-D2: The daily schedule and report skill require the committed local validator after the final write, specify `--public` for public reports, and treat failure as a stop condition.
- [x] PRSG-79-D3: A relevant frozen workflow replay confirms an unavailable/unverified preferred model does not block report generation and the final report validator is invoked.
- [x] PRSG-79-D4: Lead reviews exact scope, skill metadata/references, replay evidence, and external schedule readback.

## Evidence and limitations

- Trader ran `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-08 --public`; it passed on the committed Oct 8 report.
- Read-only automation metadata confirms `praesagus-catalyst-timeline-daily-report` is ACTIVE, daily 08:00 MYT, targeted to registered Trader `01a11c23-ec89-7f92-bf08-71be10a90702`, and includes both model fallback and the validator command.
- Lead reviewed all seven in-scope tracked edits and preserved the preferred model values in `agent-operations/roles.json`.
- No new test was run in this review. The workflow replay and final acceptance remain pending; this ticket must not be marked complete until they are evidenced.
- No report artifact, validator code, model, or dependency changed. No report publication or deployment is claimed.

## Fresh Lead acceptance — 2026-10-10 MYT

2026-10-10 fresh Trader frozen replay at e031c328e96c6781dd2bdb3baf9aa495fba5149c: unavailable/unverified preferred-setting scenarios continued on current runtime, identical external Oct 8 final writes followed exact public validator argv and returned 0. External timezone-removal case returned 1 and stopped delivery; repair rerun returned 0. Lead read evidence and logs independently. Instruction-level replay only, no actual model-selection failure or fresh market report generation.

2026-10-10 fresh Lead reviewed exact nine-path aeebb0a delivery (seven guidance paths plus spec/manifest), current guidance, frozen replay logs and public validator exit 0. Skill metadata/references preserved; no report/validator/model/dependency change. Restored lost explicit fallback/final-write clauses in existing transferred 08:00 ACTIVE schedule and independently read back fresh Trader target. No runtime enforcement or financial-analysis quality claim.

Historical review notes above remain preserved. D3 and D4 are now accepted for this bounded instruction/workflow ticket; this does not establish fresh report quality, provider access, predictive skill or guaranteed scheduled execution. Private scenario logs remain outside Git; no private schedule prompt or successor ID is exported.
