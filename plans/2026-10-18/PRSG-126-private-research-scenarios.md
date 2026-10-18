# PRSG-126 — Private Research Scenario Boundary

Type: feature · Modules: financial-data, market-research · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–1.5 person-days) · Impact: high — avoid coupling requested private research calculations to public redistribution permissions.

## Why the ticket is created?

The human requested a local numeric CSV. The existing calculator requires public-derived rights even for a private-only calculation. Trader explicitly distinguishes these purposes; actual private-use evidence remains unresolved, so this ticket implements the boundary with fixtures and does not approve the captured source.

## Approach

Add a separate pure build_private_forecast_scenario entry point sharing the existing numerical implementation. Preserve the existing public function signature, admission schema and all behavior. Private mode requires a separate closed admission contract: existing admission keys plus purpose exactly private_research_only. The evidence keysets, schema1/2/3, numerical methods, timestamps and seven hash-bound reviews remain. Rights review in private mode requires permitted history_collection and private_retention_research; public_derived_forecast stays unchanged/unknown and is not required for this purpose. Never rewrite rights to fabricate permission or reuse a public-purpose admission.

## Choices

Private results use a distinct closed output contract with purpose=private_research_only and no report_fields key, so existing public row mappers, overlay and report CLI cannot accept them. Include private numerical estimates, original evidence/admission hashes and provenance for later private CSV export. Authored fixtures remain visibly fictional. No filesystem export is implemented in this pure-core slice.

## Findings

Current build_forecast_scenario has one rights predicate requiring all three uses. Scope-specific review is needed, not deletion of data-use checks. Existing public calculator and mapper must continue rejecting unknown public use, private admissions and private outputs. Actual private-use permission is a separate unresolved dependency, not inferred from passing tests.

## Tradeoffs

A small separate API retains the public boundary and avoids legal-policy guesses in the calculator. It is the same uncalibrated research baseline, not a trained or promoted model and not the standalone whole-window forecast requirement. No input data, private admission, provider call or public publication is authorized here.

## Frozen scope

Base 6f289ce7a730f43de05852b80cfb92dfd4b8306c. AI Engineer owns only ingest/forecast_scenario.py and tests/test_forecast_scenario.py. Lead owns these two canonical records. Protect PRSG-125 ingestion files, report overlay/CLI, public artifacts, model/dependency/provider/credential paths and unrelated.DS_Store. Private-only CLI/CSV is a subsequent supporting Engineer slice after this API review.

## When it's considered done

- [x] PRSG-126-D1: Private-purpose closed admission/output contracts share unchanged financial calculations, accept only reviewed permitted private uses and reject missing/private-use failures; raw/cash/USD/MYR fixtures and legacy regressions pass.
- [x] PRSG-126-D2: Public function, mapper, overlay and CLI reject private admissions/results; Lead independently reviews and delivers exact scoped implementation. Actual source permission/CSV remains separately pending.

## Lead acceptance — 18 October

Independent exact source review and core/overlay run: 338 passed in 2.38s. Private-purpose admission binds the original evidence and purpose-specific admission without altering rights. Separate result has no report_fields; public API retains original signature/schema and rejects private admission/results. Frozen core SHA ed536d6adac8ac2b90d72af8395982c33156d8d22f6be893960e157c13488f1f; tests ae50eef6ff1a0688b99e5f0759a1f204ef9ac1a3658c42a267800edf7b2d82e2. Actual source-use permission and private CSV remain separate pending obligations; no live forecast or model promotion claimed. Commit/push hooks remain required for delivery.
