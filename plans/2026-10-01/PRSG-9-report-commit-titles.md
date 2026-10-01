# PRSG-9 — Structured report commit titles

Type: chore · Modules: skills, harness, docs · Owner: Researcher · Priority: P1 · Effort: XS (0.1–0.3 person-days) · Impact: low (consistent history labels).

Created: 2026-10-01 MYT. [Delivery contract](PRSG-9.harness.json).

## Accepted scope

Direct human request: daily-report commit titles start with `[REPORT] YYYYMMDD`; all ticket identifiers retain the dash, for example `PRSG-9`. Lead accepted base 427f1d746ca5bc92785dd1d0d3533b6bf2a4bcd7 and the five owned paths in this manifest. The existing nonempty daily-market-brief-only boundary remains unchanged. Report subjects allow a nonblank optional description and require a valid Gregorian date. Mixed changes, empty commits and cross-boundary renames require `PRSG-<number> <description>`. Monthly-calendar changes are outside the report-only boundary and require a ticket prefix or separate report-only commit. Use commit-msg, the Git hook that can reject titles before recording the commit; existing published history stays intact.

## Ownership and validation

Researcher edits hook, daily skill, AGENTS title paragraph and this spec/manifest only. Lead/Engineer separately update and run compatible hook regressions; Researcher does not add/run tests under current session instructions. Existing tests assume the old exemption and need revised expectations before delivery. Record real results, keep test/review acceptance pending until Lead validates. Installer preserves existing hooks. Skill metadata validation is structural, not behavioral proof; the bad report-title replay must be verified by Lead. No commit/push until Lead final review.

## When it's considered done

- [x] PRSG-9-D1: Hook requires dated report prefix in existing report-only boundary and dashed ticket prefix elsewhere; relevant updated behavior coverage passes.
- [x] PRSG-9-D2: Daily-report skill and AGENTS state consistent title/boundary requirements; metadata and references validated.
- [x] PRSG-9-D3: Lead reviews complete scoped diff and accepts delivery.

## Lead acceptance

2026-10-01 MYT Lead integration: focused hook suite43 passed; ticket dashboard DOM replay passed; daily skill metadata valid. Lead independently reviewed shared PRSG-9/PRSG-14 hook and staged guard, revised UI source and Engineer desktop/mobile handoff. No live provider or ROI claims.
Historical pending/failure notes above are retained; this acceptance supersedes them. Shared hook test paths belong to PRSG-14, skill/title instructions to PRSG-9; Lead reviewed their combined integration.
