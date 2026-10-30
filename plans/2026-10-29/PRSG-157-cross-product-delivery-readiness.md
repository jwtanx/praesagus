# PRSG-157 — Cross-Product Delivery Readiness and Restart Reconciliation

Type: feature · Modules: harness, financial-data, docs · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days, estimate) · Impact: high — addresses directly reported delivery or comprehension friction; benefit remains unmeasured.

## Objective

Derive one read-only per-product readiness and safe restart view from existing immutable receipts, exact reviews and canonical tickets without creating another run framework or admission registry.

## Why the Ticket Is Created

The four 29 October role retrospectives converge on visible readiness, precise blockers and repeatable delivery. PRSG-140/141 already implement fixed50 preparation/orchestration; PRSG-155 already emits hash-bound delivery receipts and verifies both approvals. The missing delta is a cross-product derived view and restart reconciliation, not replacement execution.

## Approach

Inventory the existing fixed50, US30 and standalone100 receipt/coverage interfaces first. Reuse them through a small explicit-input inspection command; derive ticker/method/reference/issue/target status, blocker code, evidence reference, responsible role and next permitted action. Separate product denominators and horizon counts. A valid completed generation is referenced; an interrupted or consumed one-use release returns the exact safe next action and never automatically runs capture or inference. Validate all consumed timestamps, identity sets, hashes and currentness; preserve private provenance and bounded reads.

## Choices

Extend existing receipt consumers only where needed; prefer a thin adapter over a new schema. Existing source/review/model contracts remain authoritative. If the initial inventory proves an equivalent consumer already exists, document and reuse it, then close this delta by evidence rather than duplicate code. Proposed Engineer integration, Trader financial review and AI Engineer compatibility review are separate scopes; Human freezes and accepts delivery.

## Findings

Source inspection at planning base confirms run_reviewed_batch.py finalize writes delivery-receipt.json and requires child/parent approvals; PRSG-155 is complete for a dated 30-name/120-horizon research delivery. PRSG-124, 109 and 113 remain open. No cross-product readiness command was identified in the inspected interfaces; implementation must verify this against its bounded inventory before adding files.

## Tradeoffs

A derived view reduces repeated packet assembly but cannot renew financial admissions, restore expired outputs, infer rights or prove forecast quality. Immutable runs stay canonical; view generation time is separate from evidence knowledge time. Restart inspection is deliberately read-only, so consumed releases still need a newly authorized finite run.

## Ownership and Frozen Boundary

Proposed accountable owner: Engineer. No dispatch or implementation occurs in this compilation. Scope is provisional; planning baseline 50ce86d8c4c8f7a89acbe7df2536db2bb231b2b7. Human must select the final operating mode and freeze the exact accepted paths, baseline, checks and specialist write boundaries before implementation. Existing tickets retain their current ownership/status and history; this proposal does not silently transfer Lead-owned work. Independent review remains required, with Human final acceptance while Lead is on break. All existing unrelated dirty files, including .DS_Store, remain excluded.

Allowed paths: `plans/2026-10-29/PRSG-157-cross-product-delivery-readiness.md`, `plans/2026-10-29/PRSG-157.harness.json`, `scripts/stock-research/inspect_delivery.py`, `tests/test_delivery_readiness.py`, `docs/DELIVERY_READINESS.md`, `plans/2026-10-29/final-work-plan.md`. Protected paths: `connectors/`, `ingest/`, `artifacts/`, `backend/`, `frontend/`, `skills/`, `.DS_Store`. Scope expansion requires an explicit contract revision before edits. Private source data, chat transcripts, account information and operational configuration stay outside Git.

Dependencies / reuse: PRSG-140, PRSG-141, PRSG-155, PRSG-124, PRSG-109. Dependencies identify interface/evidence reuse, not a claim that every parent must be complete before this slice can start.

## When It Is Considered Done

- [x] PRSG-157-D1: Inventory existing receipts and prove the minimal missing delta; document fixed50, US30 and standalone100 contracts without reopening completed implementations.
- [x] PRSG-157-D2: Derive an attributable per-ticker/product readiness view with explicit missing, stale, incompatible, withheld and ready states, exact blocker/owner/next action and honest denominators; original knowledge times and approvals are preserved.
- [x] PRSG-157-D3: Reconcile completed, interrupted, tampered, expired and consumed-release states without network, credentials, capture, inference or implicit approval; expose the exact safe continuation.
- [x] PRSG-157-D4: Independently reproduce the view from a frozen private bundle and verify actual output references, focused negative cases and human-readable command/documentation; Lead accepts operational delivery with Trader and AI Engineer domain review; Human retains promotion/publication authority.

## Checks and Delivery

All implementation checks and acceptance items are pending. At implementation, record exact focused command/manual results and failures, inspect all changed paths (including new/deleted files and both rename endpoints), validate this manifest with every supplied changed path, and run required hooks on any authorized commit/push. Skill changes require metadata/reference checks and a frozen behavioral replay, plus human review before promotion. No code, model, prompt, rights policy, publication, schedule or role change is implemented by creating this ticket. A schema pass is planning validation only.

## Accepted Delivery Amendment — 30 October 2026

Human appoints this chat Lead and explicitly directs resumed team execution through final impactful delivery. Lead accepts PRSG-157 at base cca89e514ed6217d3afb980063b604a53ff069c3. Engineer owns only inspect_delivery.py, test_delivery_readiness.py and DELIVERY_READINESS.md; Lead owns canonical plan/manifest edits. Existing acceptance evidence requirements remain; operational delivery acceptance moves from the resting Human/Lead-free proposal to the newly appointed Lead, with relevant Trader/AI review. No model/prompt/risk promotion or source request is authorized. Implement the real receipt adapters and demonstrate actual retained private bundles; do not build a manual parallel status registry.

## Independent Acceptance — 30 October 2026

Lead independently62passed4.12s; Engineer62passed4.04s. Exact frozen code3140f7f7c80c0c6102e481ebbe4a3579f113214ce0039f3aaa65e8bb5026c754.

Clean-/tmp actual explicit-bundle inspection exit2 for missing standalone100;16input files1879231B rehashed unchanged. Historical fixed50=50slots35numeric/15withheld; US30=30names120rows0qualified; standalone100=0known100unknownslots. Lead receipt62d40dcd120db2467824db349d827fdeb6abccdbc8e635b5ea7899cda8b3a986; Trader33928fe305ce30bffc1f0fc02165a881cc18249c4a665b6e6408f7e58df7c38e; AI032df1ccc0f39b5b0543d566340ea68da3c282a1699066b6e829e30761d78b46. All120US30outcomes stillpending;90issuance-stale/30private-inspectable nextweek. No newrun,source,quality,publication or trading authority.
