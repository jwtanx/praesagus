# PRSG-18 — Default ticket-key descending sort including reset.

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 days) · Impact: medium

## Accepted scope

Default ticket-key descending sort including reset. Preserve data, source history, current design and existing interactions. Scope/base in sibling manifest. Separate commit per ticket; Lead implements locally. No backend changes. UX value unmeasured.

Default and reset use numeric key descending; ascending remains selectable. Cover keys1/3/10 to prevent lexicographic sort.

## When it's considered done

- [x] PRSG-18-D1: Requested behavior and focused DOM regressions pass; Lead reviews scoped diff.

## Validation

2026-10-01 MYT: node tests/ticket_dashboard_checks.cjs passed desktop/mobile DOM regressions. Lead reviewed exact four-file diff; no data/backend modifications. git diff --check passed. Actual rendered-browser visual QA not run.
