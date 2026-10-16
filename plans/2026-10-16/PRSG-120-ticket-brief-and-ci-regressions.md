# PRSG-120 — Restore Ticket Brief Metadata and CI Regression Gates

Type: bug · Modules: harness, infra, docs · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high — readable accurate ticket briefs and working delivery checks.

## Objective

Human reports lowercase dashboard titles, missing ticket details and failing GitHub CI. Recent stock-research Markdown headings are lowercase and sparse named context sections leave decision panels empty. CI run38790800494 at0eed1fb fails pytest collection/test step after dependency installation, while Pages succeeds. Exact test logs require sign-in; provider metadata alone does not prove an exact traceback.

## Approach

Correct source brief headings and provide attributable purpose, approach, choices, findings and tradeoffs. Add a deterministic pre-commit regression gate with negative missing/lowercase cases and historical-title preservation. Investigate CI environment dependencies: standalone research requirements include exchange_calendars/openpyxl and NumPy2 while Poetry job does not install that requirements file. Reproduce the missing-dependency path, fix the narrow workflow setup and guard dependency installation before tests. Verify real GitHub checks after push.

## Choices

Preserve source-authored acronym spelling and original Git history. Prefer source corrections and a deterministic gate over CSS capitalization or invented fallback details. Keep standalone research dependencies declared separately and installed into the same CI interpreter; avoid broad Poetry/package migrations.

## Findings

Lead verified recent headings and five-field context extraction and observed failing CI/successful Pages via GitHub API. Implementation and exact dependency failure reproduction remain pending; no successfulCI is claimed from localtests.

## Tradeoffs

Do not retroactively reject historical snapshots or fabricate past research. Missing or unassessed findings must remain explicit. Preserve unrelated daily-report edits, private outputs, historical ticket ownership and stock-research model gates;116 remains queued while this human-priority correction is handled.

## Frozen Scope

Base 0eed1fb41410a229ebaf97e5bdcf6a77b62fd005. Engineer owns listed implementation paths; Lead owns this ticket and recent109–119source briefs. No provider/model changes, credentials, hosted deployments or unrelated cleanup.

## When it's considered done

- [ ] PRSG-120-D1: Current brief headings and all five detail categories are accurate/readable; pre-commit rejects regression fixtures and historical display remains unchanged.
- [ ] PRSG-120-D2: CI setup failure reproduced and fixed; focused/full local checks and new GitHub CI/Pages run outcomes verified.

## Accepted Dependency Alignment

Lead extends only pyproject.toml and scripts/stock-research/requirements.txt for the minimal CI dependency compatibility fix. Preserve existing runtime/model code, estimator configuration and quality gates. Verify a common supported NumPy range with the Poetry application dependencies and standalone calendar/workbook stack; never blindly install NumPy2 over a NumPy1-only environment. Report declared resolver/import-smoke evidence separately from actual GitHub success. No broad dependency modernization or lock-file migration is authorized.

## Implementation Review

Lead independently passed103 focused audit/brief-quality/hook/CI tests in32.44s. The real pre-commit entrypoint was exercised in an isolated Git repository: a valid brief passes13 checks, while lowercase and missing-detail fixtures each exit1. The permanent hook regression additionally stages bad source and proves commits are blocked, then accepts corrected source. Current109–119briefs now have authored Title Case and all five populated effective dashboard fields; original history remains unchanged. CI installs standalone requirements into the Poetry interpreter, explicitly constrains its NumPy to1.26.4–<2, runs pipcheck and imports the Arrow/calendar/workbook/numerical stack before pytest. Standalone requirements retain NumPy2support with>=1.26.4,<3. Owner isolated compatibility and122numerical regression checks passed. Local source/test review is complete; actual new GitHubCI/Pages results and served dashboard remain pending, so the ticket is not complete.
