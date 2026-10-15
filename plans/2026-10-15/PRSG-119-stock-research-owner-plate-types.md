# PRSG-119 — preserve unsupported owner-plate types

Type: bug · Modules: financial-data, market-research · Owner: Engineer · Priority: P1 · Effort: XS (<0.5 person-day) · Impact: high — stops an irrelevant membership type from blocking industry-source intake.

Created2026-10-15 MYT. This is a corrective dependency within the already approved PRSG-109 program, not a new direction. Prior reporting tickets remain set aside.

## Reproduction and expected result

The read-only owner-plate diagnostic at21:26MYT returned40 membership rows for a company discovered by the market screener. All40 have valid code/name fields. Two have the raw string type SPECIAL;38 use accepted INDUSTRY/CONCEPT/OTHER. The present parser rejects the entire batch with invalid-industry-record. The single request completed in1.390s with verified cleanup. The private diagnostic/hash is retained outside Git; do not add real provider payloads or company rows to fixtures. Earlier diagnostic did not retain enough row fields to identify the cause; preserve that failed history.

Expected: validate structural code/name/type fields, preserve a bounded unsupported type literally with an explicit unsupported status, and retain valid rows. Never translate SPECIAL or an arbitrary future enum to INDUSTRY/OTHER, infer a sector, or silently coerce numeric/OpenD types. Downstream sector resolution continues to consider ONLY the exact INDUSTRY string with reviewed source/crosswalk evidence. Supported INDUSTRY/CONCEPT/OTHER behavior stays compatible. Empty arrays remain valid. Malformed rows still reject visibly; source/error/privacy/request boundaries stay unchanged.

Official primary reference: https://open.moomoo.com/api/quote/basic-data/owner-plate and https://open.moomoo.com/api/quote/naming-dictionary. The observed SPECIAL literal is source evidence; no unsupported semantic meaning is assigned from these references. Naming-dictionary refresh was intermittently unavailable during review, so no claim that SPECIAL is documented is made.

## Frozen scope

Base: `63d17c706c27731309c2ca982404e9d37ebeb3ff`. Allowed paths:

- `scripts/stock-research/provider.py`
- `tests/test_stock_research_provider.py`
- `plans/2026-10-15/PRSG-119-stock-research-owner-plate-types.md`
- `plans/2026-10-15/PRSG-119.harness.json`

Engineer owns only the two code/test paths; Lead owns the ticket records. Protect all other paths, especially active PRSG-114 inference/model/evaluation work, storage/collection/universe code, dependencies and unrelated primary edits. No auth, live provider/website requests, data migration, model change, deployment or commit by Engineer. No automatic replay of consumed pilots.

## Accepted normalization contract

Require clean nonempty bounded512-character code/name and a clean nonempty string type of at most128characters. Preserve the exact string in plate_type. Add explicit supported/unsupported type status on normalized owner rows. Known accepted types remain INDUSTRY/CONCEPT/OTHER; all other valid strings (including observed SPECIAL) are retained unsupported, not admitted as industry. Return a partial batch with a fixed reason when unsupported rows occur, plus bounded unsupported-type/count diagnostics in metadata and existing source hash/code/timestamps/current-only fields. This is semantic incomplete coverage, not a transport failure or permission to retry. A company name cannot replace a missing plate_name. Numeric/bool/null/missing/empty/control/oversized type, malformed code/name, oversized list and bad envelope remain rejected.

## When it's considered done

- [x] PRSG-119-D1: Mixed supported/unsupported, unknown-only, empty and malformed memberships have deterministic tested status/provenance without type inference; supported rows are preserved and non-INDUSTRY rows cannot enter reviewed sector resolution.
- [x] PRSG-119-D2: Lead independently reviews all four owned paths, runs focused regressions and required hooks, and verifies authorized commit/push separately. No full universe, live fix, currency readiness or model-quality claim follows from fixture tests.

## Evidence

Pending implementation and Lead review. Private actual diagnostic has40rows/two SPECIAL literals and hash11f3d86c102c7474ed978cea998bd7e72b867802f472c88d6d788d33831e33b1; only this summary is public. Exact original response/provider labels remain private. After code acceptance a new separately reviewed bounded capability request may be considered; none is authorized by this code assignment.

Lead independently reviewed both code/test paths and froze the literal-preserving implementation; focused173tests passed (exact time in private execution receipt). Structural rejection and exact INDUSTRY-only reviewed sector resolution are unchanged. D2 delivery/hook evidence remains pending.

Lead acceptance: implementation c79013f053c515e4d20e87f0265c3a51eeba2322 independently reviewed and pushed to exact remote main. Lead focused173passed2.63s; mandatory commit full2625passed41warnings46.31s and push2629passed41warnings45.34s. Full checks included concurrent PRSG-114 drafts; those counts do not establish PRSG-114 acceptance. No live replay or source/model readiness is claimed. This closure record has its own required hooks/delivery gates.
