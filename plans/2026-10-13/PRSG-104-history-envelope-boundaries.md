# PRSG-104 History envelope rejection boundaries

Type: bug | Modules: financial-data,observability | Owner: Engineer | Priority: P1 | Effort: S 0.5–1person-days | Impact: high

## Reproduction and expected behavior

Existing real history job rejects HTTP200 at envelope, preserves0rows/nullrawhash; root/container/scalar shape is unknowable from that coarse record. Do not infer transport success or loosen validation. Expected: first exact failing trusted guard emits one fixed enum, no provider key/value/body, allowing a later bounded intake to identify concrete repair evidence.

## Frozen exact scope

Six owned paths in manifest, no collector/client/transport/credentials/artifacts/projection changes. Shared HISTORY_STAGES adds envelope-root-type, envelope-root-fields, envelope-ret-code-type, envelope-ret-msg-type, envelope-data-type, envelope-data-fields, envelope-next-time, envelope-volume-precision. Keep old envelope enum accepted for legacy persisted/transport frames. Preserve decoder+secret-screen, existing guard order/conditions and provider-rejection classification. Split only current composite guards into same sequential subguards, no new accepted payloads/defaults. Scalars unchanged; snapshot/news behavior unchanged.

## When it is considered done

- [x] PRSG-104-D1: Exact enum/guard order accepted without schema relaxation.
- [x] PRSG-104-D2: Each first-failure boundary and valid response replayed; secret/nonfinite/duplicate/oversized cases still screened; discarded body not retained.
- [x] PRSG-104-D3: Lead reviews all paths; fresh request remains separately authorized and finite.

## Checks

ApprovedPython -m pytest -q tests/test_private_market_store.py tests/test_market_collector.py. CLI regressions live in test_market_collector.py; preserve all legacy workerframe/status conditions, cleanup/storage failures, secret-canary no-disclosure and unknown enum rejection. No live call in implementation tests. Follow with exactlyone newSPYexistingcollector history request only when resource/access/source-intended-use authorization supports it; zero retries, honest fresh cutoff/end. Capture only fixed diagnostics/outcome, no raw exposure. Diagnostic improvement alone is not source readiness or report generation.

## Lead acceptance

Exact eight fixed envelope boundaries accepted; sixpath scope/base now frozen in manifest after PRSG-103. No accepted response/schema change; old envelope enum remains supported. No provider call in implementation.

## Engineer evidence

Exact eight enum boundaries implemented with original sequential guards, including provider rejection before data validation. Non-history combined envelope guard unchanged. Legacy envelope remains allowlisted, wire versions/status conditions unchanged. No collector/client/transport implementation changes required.

Approved Python3.11 `-m pytest -q tests/test_private_market_store.py tests/test_market_collector.py`: **419 passed in3.22s**, no skips (initial389 regression run passed before additional boundary tests). Coverage includes each new stage through worker/private summary/body disposal, simultaneous-fault precedence/single decode, exact scalar boundaries and valid acceptance, decode/nonfinite/duplicate/oversized/secret screening precedence, nonhistory null diagnostics and all legacy-frame/unknown-enum/status/cleanup/storage regressions. `git diff --check` and six-path ticket validation passed. No live provider/credential calls, raw response retention or actual source readiness established. Full hooks and independent Lead acceptance remain pending.

## Lead acceptance

Lead independently reviewed all six paths;419focused passed3.12s, exact first-failure types/order and privacy/legacy controls preserved. No acceptance/schema relaxation, provider call or numeric report claim.
