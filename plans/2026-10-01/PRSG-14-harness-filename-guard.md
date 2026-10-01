# PRSG-14 — Precommit harness filename validation

Type: chore · Modules: harness · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: medium

Created 2026-10-01 MYT. User accepted scope; Lead reviews findings/release.

## Accepted scope

Staged harness files must be named PRSG-N.harness.json, without the descriptive slug retained by Markdown specs. Check the staged Git index before accepting any commit title: reject malformed names, invalid JSON or ticket_key/name mismatches; permit deleting an obsolete file and renaming it to the canonical form. Preserve the pending report-title rule and add regressions for staged-versus-working-tree differences, cross-boundary renames and valid dated report titles. Do not stage unrelated changes.

## When it's considered done

- [x] PRSG-14-D1: Staged-index naming guard and focused regressions pass, with Lead review

## Validation

Actual commit-msg hook replay: 43 tests passed, including staged content differing from working-tree content, malformed names/JSON, ticket-key mismatch, canonical rename and obsolete deletion. Full pytest: 173 passed. Existing report-title rule retained; old report-exemption fixture updated to the accepted [REPORT] date prefix. Checkout already enables .githooks. No staging/committing/pushing performed; Lead review pending.

## Lead acceptance

2026-10-01 MYT Lead integration: focused hook suite43 passed; ticket dashboard DOM replay passed; daily skill metadata valid. Lead independently reviewed shared PRSG-9/PRSG-14 hook and staged guard, revised UI source and Engineer desktop/mobile handoff. No live provider or ROI claims.
Historical pending/failure notes above are retained; this acceptance supersedes them. Shared hook test paths belong to PRSG-14, skill/title instructions to PRSG-9; Lead reviewed their combined integration.
