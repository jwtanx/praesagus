# PRSG-4 — Shared watchlist management

Type: feature · Modules: backend, frontend, connectors · Owner: Engineer · Priority: P2 · Effort: M (3–5 person-days) · Impact: medium

Harness manifest: [PRSG-4.harness.json](PRSG-4.harness.json). Created 2026-10-01, Asia/Kuala_Lumpur. Owner: Engineer; acceptance: Lead.

State: planned, not assigned. Target: a single team maintaining tracked companies. Effort: 3–5 person-days. Expected impact: medium convenience and fewer configuration errors. The existing API-key mechanism does not identify individual users; this MVP manages one explicitly shared list.

## Interface and persistence

Add list/create/update/remove operations for the existing financial watchlist, with ticker and optional company_name, CIK, sector and priority. Preserve unrelated settings. Validate canonical ticker strings, leading-zero CIK strings, duplicates, allowed priority, bounded list size, and text lengths. Do not treat an accepted ticker as verified provider support; optional resolution uses a separately tested provider check.

Writes require server-configured authenticated access; do not allow mutation when API-key auth is disabled. Use revision/version preconditions (If-Match or explicit revision) and 409 for conflicts. Validate full replacement before writing; use atomic replace, process-safe locking, and recoverable prior revision. Paths are server-configured, not user-supplied. YAML settings/comments may be lost by serializers: choose a separate versioned JSON state or document a reviewed migration before writing existing YAML; do not overwrite it casually.

Confirm how existing scripts reload watchlists: new runs must see accepted state; long-running workers require explicit reload/restart semantics visible in the UI. Single-host persistence only initially. Per-user portfolios, holdings imports, broker sync, and multi-replica ownership are separate projects.

## Delivery and value test

UI shows shared-list scope, revision, pending/save/error states, and confirmation for removals. Tests cover duplicates, missing authentication, malformed bodies, concurrency, failed writes preserving prior state, settings preservation, and script consumption after edits. API/UI tests confirm revision conflicts are recoverable.

Metric: four of five users can add/remove a company unaided in under two minutes, and invalid-write fixtures never corrupt prior configuration. Breakdown: persistence/revision design 1 day; API/UI 1–2; script consumption 0.5–1; tests/docs 0.5–1. Main dependency is agreed configuration ownership/storage; resolve before coding. Rollback reads preserved previous revision and restores prior consumers without discarding changes.

## When it's considered done

- [ ] PRSG-4-D1: Shared-list API/UI validate values and require configured authentication for mutation.
- [ ] PRSG-4-D2: Revision conflicts and failed writes preserve prior state/settings and allow recovery.
- [ ] PRSG-4-D3: Consumers demonstrably use accepted state under documented reload/restart semantics.
- [ ] PRSG-4-D4: Focused/full checks pass; Lead accepts persistence decision, scoped diff and release evidence.

Check items and manifest acceptance evidence together; shared ownership must stay visible and user-specific identity must not be implied.
