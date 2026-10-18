# PRSG-128 — History Date-Relation Diagnostics

Type: bug · Modules: financial-data, observability · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day) · Impact: high — distinguish the actual Malaysia date failure without guessing a unit conversion.

## Why the ticket is created?

One authorized BMS.1155 history observation at c43b777 failed invalid-response/date-relation and accepted0bars. Its rejected body was discarded; existing schema1 diagnostics retain only field types. Expected: a bounded safe diagnostic distinguishes documented-minute versus alternative-hour date relations without retaining timestamps, dates, offsets, prices, arbitrary strings or raw payload. Actual: the structural receipt cannot distinguish these hypotheses.

## Approach

Keep all source normalization, date guards and accepted-data behavior unchanged. Extend diagnostics with a closed schema2 structure only for date-relation rejection after the existing decode/secret screen. Preserve schema1 receipts/protocol replay. Add one bounded static-label count summary for up to370 history rows: rows_examined, minutes_match, hours_only_match, neither_match, uncheckable. Counts are exact nonnegative integers bounded370 and sum to rows_examined; minutes_match includes rows where both interpretations match. Evaluate metadata only with original integer/range checks; malformed or overflowing arithmetic is uncheckable. This is a diagnostic hypothesis comparison, never normalization or evidence of actual timezone units.

## Choices

No literal source values or exception messages enter the diagnostic. All existing structure sections remain closed; schema2 adds exactly date_relation_summary with those five count keys. Schema2 must bind to date-relation stage throughout worker frame validation, controlled error and receipt writer; other stages retain schema1/unavailable behavior. No receipt may accept arbitrary names/values or counts forged out of range/inconsistent. Preserve frame/normalization versions and legacy replay; if a version change is necessary, return exact finding before expanding scope.

## Findings

Official history docs define millisecond time_key, local-date YYYYMMDD and timezone offset in minutes. Actual failed metadata values are unavailable; do not infer+8/480 or silently multiply by60. Comparing a second hypothesis in a private count-only diagnostic provides evidence for later review while retaining rejection.

## Tradeoffs

Counts cannot reconstruct an exact offending row and do not prove a provider contract. They are enough to identify a systematic unit hypothesis safely; a later source/venue review and separately scoped normalization decision are still required. The already consumed one-job observation is not retried by this ticket.

## Frozen scope

Base c43b777c7cc98d597ccb241a8fbbfa05a7e4104a. Engineer writes only ingest/private_market_store.py, ingest/market_collector.py and their two focused test files. Lead owns records. Protect127CLI/test/guide,126numericalcore, connectors/signing/credentials, public artifacts, dependencies and unrelated.DSStore. No provider requests, raw rejection retention, changed price acceptance or altered source-use permission.

## When it's considered done

- [x] PRSG-128-D1: Closed bounded count diagnostics distinguish minute-match/hour-only/neither/uncheckable fixtures, preserve legacy protocol/receipt behavior, reject malformed/secret-bearing/forged summaries and never relax data rejection.
- [x] PRSG-128-D2: Lead independently reviews and delivers scoped patch through required hooks. Any new actual observation requires a separate Lead release after implementation acceptance.

## Lead acceptance — 18 October

Independent exact four-file review and configured focused tests passed539 tests; elapsed recorded in delivery receipt. Engineer539 passed3.41s; initial538pass/1fail was misplaced original test assertions, restored unchanged before final run. Schema2 is stage-bound at each error/frame/parent/receipt layer, with closed bounded counts only. Schema1/frame/normalization/receipt versions remain compatible. Actual normalization and rejection unchanged; no literal dates, epochs, offsets, prices or raw body retained. Frozen patch SHA256 daef7b6a95fe3cc9e3c22882bd80f59c2b14f4246351544d556ba2a6a467b244. Required delivery hooks and separate actual observation release remain.
