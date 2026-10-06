# PRSG-67 — Remove destination gate from daily report skill

Type: skill · Modules: skills, market-research, docs · Owner: Lead · Priority: P1 · Effort: XS (<0.5 person-days) · Impact: medium-high; lets the existing Trader workflow complete requested reports without pausing at a separate Moomoo destination approval prompt. Created 2026-10-06 MYT.

## Objective

Update the daily market brief skill so report generation and ordinary delivery proceed through the operator's configured report workflow without an extra Moomoo publication gate. Preserve truthful cutoffs, source attribution, observed-versus-derived labels, data gaps and uncertainty. This change alters workflow instructions only; it does not rewrite or delete the existing report publisher, private-store security, or connector code.

## Accepted scope

Lead accepted the human's explicit request on 2026-10-06 MYT. Base SHA: `e45050f6957e045800c3a45121b68176ded64463`.

Allowed paths:

- `skills/daily-market-brief/SKILL.md`
- `plans/2026-10-06/PRSG-67-daily-report-delivery-skill.md`
- `plans/2026-10-06/PRSG-67.harness.json`

Protected: all other paths.

## Required behavior

- Do not ask for, wait on, or require separate private/public destination confirmation as a prerequisite to producing the requested dated report.
- Keep the normal report workflow's output and delivery destination instructions; do not invent a separate Moomoo-specific delivery blocker.
- Keep observed timestamps, data gaps, source attribution, uncertainty and forecast-versus-indicator distinction accurate.
- Do not claim that a snapshot is live or continuous; do not convert descriptive signals into a guaranteed prediction or execution instruction.
- Retain credential and account-data security requirements.

## Validation

- Validate frontmatter name/version and all relative file/command references.
- Replay a synthetic missing-credential/partial-market-data request: the skill should continue report generation, label unavailable fields, preserve cutoff/provenance, and proceed to normal delivery without a private/public approval question.
- Re-read the full changed skill and verify no Moomoo-specific destination permission gate remains.
- Run the ticket validator with the three listed paths and `git diff --check`.

## When it's considered done

- [x] PRSG-67-D1: The daily brief skill no longer directs the report workflow to stop or request destination-specific publication approval.
- [x] PRSG-67-D2: Provenance, cutoffs, uncertainty, read-only and credential-security requirements remain clear.
- [x] PRSG-67-D3: Metadata/reference validation and the synthetic behavioral replay pass; Lead reviews the exact skill diff.

## Delivery evidence

2026-10-06 MYT: bumped skill metadata to 1.6; removed Moomoo destination/rights approval branches while retaining the read-only API boundary, explicit missing-input behavior, source times and credential locator safeguards. Frontmatter/reference check and synthetic unavailable-input/report-delivery replay passed. Ticket validation and `git diff --check` passed. Lead accepted the reviewed skill-only behavior change; PRSG-67 complete. Commit `25941ad596a1193a6f4e32d43bbdb75f8f48b2ff` was pushed to `main`; Pages run [37463970301](https://github.com/jwtanx/praesagus/actions/runs/37463970301) and CI run [37463970352](https://github.com/jwtanx/praesagus/actions/runs/37463970352) both succeeded.
