# PRSG-41 · Classify rejected quote responses correctly

Type: bug · Modules: connectors, financial-data · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days estimate) · Impact: high

## Why the ticket is created?
A synthetic30-row HTTP200 response containing one null volume is surfaced as transport/http0 because execute_job assigns captured only after normalization. Actual transport receipt is lost. Valid1/30row synthetic responses succeed; real30batch cause still unknown. Misclassification blocks operational diagnosis.

## Reproduction and expected behavior
Inject fake transport HTTP200 containing one invalid row through execute_job. Before: failure transport/status0/empty body. Expected: received HTTP200 retained, controlled invalid-response, actual receipt time, empty rejected body. True exception before any response remains transport/status0. No entitlement/quota hypothesis asserted.

## Approach and safeguards
Track validated receipt status/time before screening; preserve a controlled screening rejection flag despite core RESTError conversion. Never emit or persist rejected body/headers/secrets/errors; successful raw bytes remain gated by existing normalized policy. Do not weaken atomic batch validation, drop invalid rows or salvage partials. Provider failure and malformed/known-secret200 rejected safely;429/5xx mapping preserved. No new broad diagnostics or response text logging. Five exact paths frozen; reuse implementation skill.

## When it's considered done
- [x] PRSG-41-D1: Paired valid1/30 and invalidrow/providererror/malformed/knownsecret200, true transport, status/time retention, no raw/credential leakage and existing focused tests pass.
- [x] PRSG-41-D2: Lead independently reviews five paths and replay evidence.

Lead accepted after full five-path diff review and independent exact355-test replay in2.27s on existing isolatedPython3.12.14/cryptography50.0.2. Historical pending handoff retained below; live root cause remains unverified.

## Limits
Offline fixtures only; live30batch root cause remains unverified. No live requests, credential reads, persistence schema change, public export or quote validity relaxation.


## Engineer handoff
355 offline regression tests passed in 2.27s using the exact declared command from the repository root, with isolated Python 3.12.14 and cryptography 50.0.2. Transcript: `/tmp/PRSG-41-tests.txt`. Python 3.11 was not replayed. Added paired 1/30-row success and rejected/null/malformed/provider/secret/status cases; actual receipt time and empty rejected body are asserted through parent persistence. Lead review remains pending. No live calls, credential reads, commits or pushes.
