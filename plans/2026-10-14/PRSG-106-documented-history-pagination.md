# PRSG-106 Documented history pagination envelope

Type: bug | Modules: financial-data,connectors | Owner: Engineer | Priority: P1 | Effort: S 0.5–1person-day | Impact: high — unblocks documented history shape; actual source readiness remains separately verified.

## Problem and evidence

The version3 private normalizer requires exactly ret_code/ret_msg/data. Current official pagination guidance says pagination is top-level; the history exception uses extra.next_time. A consistent authored history row with this documented metadata is rejected at envelope-root-fields. Actual Oct13 one-job capture failed at that same boundary; its discarded body does not establish its precise keys. Do not claim documented repair explains the real response until a fresh accepted capture verifies it.

Primary sources independently fetched Oct14: https://open.moomoo.com/zh-cn/api/quote/pagination.md , https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline.md , https://open.moomoo.com/zh-cn/api/quote/overview . Endpoint example lacks metadata while field tables require date/time_zone: preserve explicit metadata requirement; no inferred timezone/date/currency/finality.

## Accepted frozen candidate and interface

Eight paths only. Introduce history normalization version4. Keep history1–3 replay behavior immutable and snapshot/news untouched. V4 accepts mandatory exact ret_code/ret_msg/data plus only documented optional pagination/extra. Proposed pagination exact required has_more bool with optional total nonbool integer0..2**63-1; no next_key for history date paging. Extra exact next_time nonbool integer0..2**63-1. Preserve data allowed kline_list/next_time/volume_precision; reject conflicting duplicate cursor locations. No unlisted root fields, permissive wrappers, alternative status keys, automatic pagination/request/retry. Preserve raw bytes and original declared shape; normalization does not invent a complete window from has_more. Empty rows explicit all-missing. Row shape/date-offset guards unchanged. Bound all fields even if unused.

Engineer proposes exact interface before implementation; Lead accepts final contract. Propagate version4 consistently through worker,parent/store; store metadata supports3and4 history and exact version replay. Existing secret/decode/size/duplicate/nonfinite guards precede shape admission. Add fixed diagnostics for malformed documented pagination/extra only; failed bodies remain discarded. No live request/credentials/store reads in implementation.

## When it is considered done

- [x] PRSG-106-D1: Exact documented versioned envelope contract accepted, old replay unchanged.
- [x] PRSG-106-D2: Documented good-shape/malformed/privacy/worker/store and old-version regressions pass.
- [x] PRSG-106-D3: Lead independent full scope review, integration and delivery verified.

## Checks and boundaries

Approved Python -m pytest -q tests/test_private_market_store.py tests/test_market_collector.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py ; full installed hooks. Actual fresh intake/admission/report publication is a separate bounded Trader action after delivery, not completion evidence for this code repair. No changes to financial method, projection, forecast/report artifacts or existing attempts.

## Actual-shape diagnosis required for bounded next capture

Current root-field enum is insufficient to identify unexpected actual envelope. Engineer may propose a bounded value-free PRIVATE structural inventory on history-only failures after existing decode/secret screening, while failed raw bodies remain discarded. No values, credentials/privateIDs/paths, arbitrary exception text or unscreened keys; root/key/type summary bounded <=32fields, names lowercaseASCII<=64 and secrets checked, types fixed enums. Include only root and documented data/pagination/extra/first-row schema metadata; no recursive arbitrary body projection or counts implying accepted bars. Unknown/unsafe/overflow input => fixed unavailable diagnostic. No public CLI names/body/value output; private typed receipt only under existing ownership. Frame/summary versions must retain old compatibility and not alter admission, replay or raw archive. This feature exists solely to obtain actual shape once, not accept undocumented payload. Exact diagnostic interface/types/storage paths and tests require Lead confirmation before implementation. Additional CLI path permitted only if required to retain private diagnostic without public output.

## Lead exact interface acceptance

Lead read private PRSG-106-interface.md and accepts its strictv4/immutableoldreplay + explicitworkerframe3/versionpropagation + PRIVATEfixed-field/typeinventory and preflighted nooverwrite0600diagnosticreceipt. Reject arbitraryproviderkeynames; fixed inventory unavailable after decode/secretfailure; failedrawbytesdiscarded. Add only two known root diagnostic labels code (officialpagination example) and error (endpoint error.code table), increasing fixedfields15to17; these are DIAGNOSTIC ONLY and must NOT change root admission or add status aliases/error payload projection. All values/types/eligibility/legacy/forgery/cleanup guards from exactproposalapply. Equal typed duplicatecursor locations accepted, conflicting rejected, rawbytesunchanged. No livecall authorized by this implementation. Eightpathbase frozen06da92b, clean daily-report-delivery worktree.

## Engineer evidence

Implemented strict history4/default current intake, workerframe3 explicit normalization4 and typed private inventory, oldframes1/2 history3 parsing, store metadata3/4 and exact stored-version replay. Snapshot/news and all protected paths unchanged. Fixed17-label inventory only; no actual provider key names/values copied, diagnostic code/error labels do not admit aliases. Optional receipt preflight occurs before collector/store/credentials; stdout schema2 unchanged. Atomic nooverwrite0600 receipt, type/eligibility/forged-linkage checks and own-link/temporary cleanup preserve existing files.

Approved Python3.11 focused command `-m pytest -q tests/test_private_market_store.py tests/test_market_collector.py tests/test_moomoo_rest.py tests/test_moomoo_rest_live.py`: **761 passed in3.63s**, no skips. Full isolated `-m pytest -q --tb=short --maxfail=3`: **2290 passed,41 dependency deprecation warnings in43.35s**. `git diff --check` and complete eight-path ticket validation passed. First regression run was65failed/622passed from old tests' default3 metadata and frame2 expectations; preserve legacy intent with explicit normalization3 and updated current-worker frame3/pagination-stage assertions, then687passed before new cases. No acceptance/privacy guards removed. Additional v4/documented-malformed/alias/date/pagination/legacy raw replay/forged headers/types/status/inventory/no-key-value-privateID/receipt preflight/temporary collision/failed-write/cleanup/storage/clock/budget cases added (754 then761passed).

Authored offline fixtures and temporary stores only; no provider/credential/existing private store reads or live intake. This candidate is documented-shape support, not proof of the actual discarded response's cause, complete qualifying history, rights/finality or numeric report eligibility. PRSG-107 actual-template depth repair remains separate; not changed here. Independent Lead review/full installed hooks/delivery remain pending; one actual fresh request is separately authorized after delivery.

## Lead independent acceptance

Lead independently reviewed all8paths/versionedworker-store-replay/private17fieldtypedreceipt;761focusedpassed3.58s. Existingguards/protectedprojection unchanged. Fullhooks required. Noactualproviderresponse/cause/historyadmission inferred. Documentedv4candidate success tested, realsourceintake follows separatelyaccepted108scope. Failed105actualCLI depthcase tracked separately107; no evidenceflattening or mixedscope.
