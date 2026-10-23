# PRSG-136 — Daily Report Publication Enforcement

Type: feature · Modules: market-research, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — prevents the human-observed incomplete public editions from recurring; no prediction-quality claim.

## Objective

Implement the existing human publication policy mechanically for new/modified daily report deliveries. PRSG-134 completed instructions only and explicitly says current structural validation permits missing data. At least35 of the fixed50 tickers must have both an eligible current price and a supported publicly admitted numeric prediction/range on the same row. This is a new runtime-enforcement scope, not a reopening of134.

## Scope And Dependencies

Depends on134 policy and existing report schema/allowlisted public projection. Write only the manifest's nine exact paths. Do not edit archived report JSON, forecast methods, source observations, public-use rights, skills, provider adapters or UI markup. Base40f0cee; unrelated .DS_Store remains protected. Lead accepts this bounded implementation under23OctMVP authority; start after the highest-priority124 operational handoff or when its external dependency blocks independent work.

## Approach

Reuse validate_report_json.py and shared validation conventions. Add a small explicit publication check with a real timezone-aware publication cutoff; do not use an old metadata timestamp to launder expired targets. Count same-row exact fixed-universe identities once, keeping50 denominator, finite positive current_price_value/estimated_mid_case_value/range bounds, existing source/time/basis/reference/method/confidence and intended public-use evidence. Missing or ambiguous admission fails closed. Reuse existing admissible public structures; do not invent a truthy rights flag. Preserve separate quote/forecast statuses and actionable bounded diagnostics.

Wire the existing CI/Pages path so newly added/modified daily editions and index/latest advances cannot bypass the check. Use changed-path Git evidence with correct event base/initial-run handling; do not retroactively reject unchanged historical snapshots merely because today's targets expired. Full archive structural validation remains unchanged. If the existing interfaces cannot unambiguously identify a public-use admission or freshness rule, return that concrete interface question to Lead with a minimal proposed contract before coding an invented interpretation.

The existing compact validator and actual rendered-chip/detail review remain separate required gates. This numerical enforcement does not prove browser rendering or permit private values to be published. No workflow should auto-publish or generate forecasts from missing data.

## Choices

Prefer a small reusable publication predicate and explicit changed-edition integration over rewriting the viewer or making all historical structural validation require current forecasts. A count-only check is rejected because disjoint prices/forecasts and private-only predictions can falsely reach35.

## Findings

Baseline validator accepts null numeric fields when explicit gaps/statuses exist; CLI currently offers --public/--compact structural checks. Both CI and Pages invoke structural validation without35/50 enforcement. Current policy/reference already requires paired coverage; no claim of35 qualifying public rows exists.

## Tradeoffs

Fail-closed publication can block deployment of an insufficient changed report. It must preserve historical archives and unrelated deployments without silently waiving new-edition checks. Rights and freshness are evidence inputs, not something this code creates. No tests establish trading performance.

## When It Is Considered Done

- [ ] PRSG-136-D1: Explicit actual-cutoff publication validation enforces35/50 eligible same-row pairs, fixed identities and source/public-use/time rules.
- [ ] PRSG-136-D2: Boundary34/35, disjoint pairs, expired/private-only/stale/future/malformed rows and unchanged archive regressions pass.
- [ ] PRSG-136-D3: CI/Pages changed-edition/index advancement path invokes the guard and preserves archive structural validation.
- [ ] PRSG-136-D4: Lead independent review, docs, mandatory checks and actual delivery evidence accepted.

## Validation

Engineer runs focused tests/test_daily_report_publication.py and tests/test_daily_report.py plus existing report structural validator/archive and workflow checks; records exact commands/results including failures. Lead independently replays relevant positives/rejections and inspects complete Git scope, including new/deleted/rename endpoints. Required commit/push hooks remain binding. No report or source/model promotion is part of this ticket.
