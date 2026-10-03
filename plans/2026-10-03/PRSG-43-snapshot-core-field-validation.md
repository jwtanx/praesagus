# PRSG-43 · Validate consumed snapshot fields explicitly

Type: bug · Modules: financial-data, connectors · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: high

## Why the ticket is created?
Lead reports the approved thirty-name HTTP 200 snapshot is rejected solely by a negative finite auxiliary lowest_history_price. The store currently applies nonnegative validation to every suffix _price, exceeding the core connector contract.

## Reproduction and expected behavior
A synthetic row with valid core prices and volume plus negative finite lowest_history_price must retain its usable quote. Invalid consumed prices, volume, timestamps, duplicates, nonfinite auxiliary numbers and secrets must still reject the entire response without raw persistence.

## Approach and safeguards
Validate last/open/high/low/previous-close prices, volume, turnover and turnover rate explicitly, matching the existing connector. Keep recursive whole-body finite and secret screening and validity flags. Auxiliary historical fields are unconsumed; accepting finite auxiliary values does not endorse their economic interpretation or adjustment basis. No dropped rows or partial salvage.

## Sources and limitations
https://open.moomoo.com/mcp-docs/available-tools describes current REST snapshot fields. https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-market-snapshot.html identifies lowest_history_price as a historical float; it does not establish that a particular negative value is correctly adjusted. Synthetic regressions prove consumed-field boundary only. Live proof follows independent Lead acceptance through the secure supervisor.

## When it's considered done
- [x] PRSG-43-D1: Focused store, collector, REST, selection and projection regressions pass, including finite auxiliary acceptance and strict rejection cases.
- [x] PRSG-43-D2: Lead independently accepts the exact four-path change.

## Engineer evidence
Engineer exact declared offline replay: 479 passed in 5.24s; isolated Python3.12.14/cryptography50.0.2; /tmp/PRSG-43-tests.txt. First replay 2 failed/477 passed due new test using nonexistent StoredAttempt attribute, corrected to persisted metadata; /tmp/PRSG-43-tests-first-replay.txt. No live call or credential access; Python3.11 not replayed.
Lead reviewed all four paths and independently replayed the exact declared suite: 479 passed in 4.86s on Python3.12.14. Bounded secure-supervisor live proof returned HTTP200,30 accepted US rows,0 missing,failure null,cleanup true. No credentials, quote values or raw bodies emitted. MY coverage, public projection and forecast quality remain outside this proof; report regeneration is separate.
