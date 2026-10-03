# PRSG-45 · Versioned provider previous-close retention

Type: feature · Modules: financial-data, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high

## Why the ticket is created?
The store drops provider previous close, preventing later separately scoped movement comparison. Adding it without normalization version dispatch would invalidate old canonical hashes and replay checks.

## Approach and safeguards
Freeze normalization v1 exactly. New snapshot ingests record normalization_version 2 in hashed attempt metadata and normalized payload, with optional provider_prev_close finite nonnegative or null when missing/null. News ingestion remains v1. Stored metadata alone chooses replay version; absent means v1; boolean and unknown versions reject. No DDL changes, existing records rewritten, backdating, live access or reingestion. Selection exposes retained provider_prev_close separately; prior_close stays unknown and no movement/forecast calculations added. Unknown currency/session/adjustment stay unchanged. Collector/projection/viewer/reports/connectors/skills/schedules protected. Any future private replay needs separate Lead authorization and actual new ingestion time.

## When it's considered done
- [x] PRSG-45-D1: Frozen v1 payload/hash/query/selection replay, versioned attempt dedup, v2 optional prior-close and strict invalid/tamper/mixed version regressions pass.
- [x] PRSG-45-D2: Lead independently accepts all five paths before commit.

## Resource guard
Supported account reading before work: five-hour 7% remaining; weekly 86% remaining. Recheck at checkpoint; <=5% stops new implementation and preserves evidence for review.

## Engineer evidence and boundary
Engineer exact declared offline replay: 347 passed in 4.77s on isolated Python3.12.14/cryptography50.0.2; /tmp/PRSG-45-tests.txt. First replay 1 failed/346 passed: existing null previous-close assertion updated for accepted v2 optional-null behavior, with explicit v1 strict rejection retained; /tmp/PRSG-45-tests-first-replay.txt. Python3.11 not replayed.
New snapshot metadata and payload include version 2 before ID/hash calculation. News stays v1. Old unversioned attempts dispatch v1 and retain exact canonical payload, hashes and rows. Mixed same-time v1/v2 semantic variants conservatively conflict. provider_prev_close is retained without establishing comparability: prior_close remains null with existing gaps. Lead independently reviewed five paths and reran347tests: passed5.60s Python3.12.14. No realstore rewrite/live/reingest/DDL/report edits; movement display separately scoped.
