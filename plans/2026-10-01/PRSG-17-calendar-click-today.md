# PRSG-17 — Click-only calendar selection with MYT today highlight.

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 days) · Impact: medium

## Accepted scope

Click-only calendar selection with MYT today highlight. Preserve data, source history, current design and existing interactions. Scope/base in sibling manifest. Separate commit per ticket; Lead implements locally. No backend changes. UX value unmeasured.

Today means Asia/Kuala_Lumpur date, with aria-current=date and visible distinct highlight. Latest schedule initially opens today's month; historical report mode retains report month. Other months select first day. Hover/focus must not change selection; native button activation remains accessible.

## When it's considered done

- [x] PRSG-17-D1: Requested behavior and focused DOM regressions pass; Lead reviews scoped diff.

## Validation

2026-10-01 MYT: node tests/daily_report_viewer_checks.cjs passed desktop/mobile DOM regressions. Lead reviewed exact four-file diff; no data/backend modifications. git diff --check passed. Actual rendered-browser visual QA not run.
