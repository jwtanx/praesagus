# PRSG-140 — Fixed50 Current Batch Command

Type: feature · Modules: financial-data, market-research, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–1.5 person-days estimate) · Impact: high — closes the verified current-history-to-batch preparation gap for human invocation.

## Why the ticket is created?

Human25October requires a repeatable command generating current predictions in one batch by28October, rather than individual manual ticker handoffs. Engineer source audit confirms completed launcher only exports static reviewed inputs; no checked-in store-to-current-fixed50 evidence producer exists. PRSG135owns actual release acceptance;124owns full50sourcecoverage;139/113own trained-modelvalidation. This adapter uses the existing uncalibrated baseline and does not require trained-model promotion.

## Objective

By28October2026 23:59Asia/Kuala_Lumpur provide a deterministic fixed50 private command which assembles current candidate evidence from the existing verified market store, consumes separately matching actual reviews, invokes the existing batch exporter and reports exact generated/withheld/review-required counts and output path. It must not advertise guaranteed numbers when current financial/source reviews are absent. Actual35-name release remains an independent135acceptance.

## Approach

Reuse PrivateMarketStore integrity-checked finite queries, existing schema3/core and immutable exporter. Explicit private config supplies exact50ordered identities, existing store/run selectors, supported native units/basis/provenance, fully reviewed venue sessions/revision cutoffs, current action/rights/narrative references, exact-review directory and private output parent. Store rows supply actual observed source times; mapper must not fabricate missing provenance or accepted decisions. Produce candidate hashes for review; bind only exact current independently reviewed admissions. First implement offline/store-based preparation and export; this is NOT fresh provider collection and must say so. A separate explicit online orchestration mode is allowed only if it reuses existing bounded approved collector plan(s), explicit pacing/deadlines and existing credential loader without bypass; if that interface cannot safely be reused within frozen files, return exact scope extension instead of inventing provider access. No live call released by this ticket.

Currentness uses separately supplied accepted complete US/MY venue schedules and operational finality cutoffs; reject/withhold missing latest21completed sessions, unavailable reference, expired target, incomplete calendar or unavailable current action terms. Original retrieved/ingested/known times remain unchanged. No weekday approximation, history filling, implicit approval, adjustment invention, copied stale admission or fallback to aging numeric editions. Exact same evidence may remain current over a weekend; arbitrary refetch is neither necessary nor sufficient.

Statuses: ready only if exact50identities and>=35currentgeneratednon-demo rows pass; insufficient_coverage otherwise (including review_required reasons). Proposed CLI exit0ready,2insufficient_coverage,1fatal setup/integrity/input/write error; document and test these dispositions. Preserve50row reason ledger where safe. Valid withheld exports must not look like achieved release. Returned JSON includes private CSV path/counts/current cutoff/reference/targets and review-required count; sanitize failures and do not print credentials/rawproviderbodies/privateevidence.

## Frozen scope

Base6eb4f0cabb0aff7365803c4a7e8e28ab44c3979f. Engineer owns scripts/daily-market-brief/refresh_private_forecast.py, ingest/private_forecast_refresh.py, tests/test_private_forecast_refresh.py and docs/MANUAL_FORECAST_CSV.md. Lead owns this spec/manifest. Preserve completed launcher/exporter/core/collector/store/numerical model, all original private artifacts, public reports,139AIrunner/test,135Leadfiles,138Traderfiles and .DS_Store. No new dependencies, schedules, method changes, review-policy promotion, provider endpoint, public rights or paid services. A new runner must be usable from another cwd and private paths with spaces, with Python>=3.11. Config/input/output private-path permissions reuse existing checks.

## Choices

Small explicit adapter over existing interfaces; no general runtime. Keep reviewed fixed50 and standalone100 workflows distinct. Consume exact actual reviews or return review_required; automatic recurring financial approval is not accepted. Prefer supported homogeneous new immutable editions over mixed-edition splicing.

## Findings

Audit b5e9239f307a6c13addaad95e799e4439d3e8baaf78d751c0a9dc86d86780074 inspected existing interfaces. Collector history plans cap30jobs/100unadjustedbars,300secondrun/20secondjob and0retry; all50 requires separate finite plans/pacing, never raised limits. Newbars invalidate exact old admission hashes. Current34actualpredictions do not prove the missing adapter.

## Tradeoffs

Offline/store refresh makes reusable preparation explicit but requires prior collection. Optional approved online orchestration can remove that separate command, not source-review authority. Human invocation cannot guarantee >=35numbers without eligible current evidence/reviews. State this limitation rather than relabeling generated fixtures or withholding as successful actual coverage.

## When it's considered done

- [x] PRSG-140-D1: Exact private config/candidate/review/status interface documented; deterministic verified-store mapping of50identities/current21sessions with original provenance and explicit missing/stale/review reasons implemented.
- [x] PRSG-140-D2: Command consumes only exact current accepted reviews, invokes existing exporter, preserves editions and returns documented ready/insufficient/fatal status/count/path; offline versus optional online modes unambiguous.
- [x] PRSG-140-D3: Focused integration tests pass for clean-shell/other-cwd/paths, mixedvenues/currentness, changedhashreviewrejection, finite failures and immutable output; fixtures remain demo and do not count toward actual35.
- [x] PRSG-140-D4: Lead independent review, reproducible command/config documentation and exact actual-run release prerequisites delivered to135 by28Oct; no source/public/model promotion implied.

## Validation and delivery

Run Python>=3.11 pytest -q tests/test_private_forecast_refresh.py for changed adapter behavior; run existing relevant suites only for integration concerns/hooks. Include malformed/missing/future/stale data, duplicate/conflicting revisions, history20/19not21, expired targets, missing/current rights/actions, old admission mismatch, setup/store integrity/write failures, no-network offline and any online finite mock budgets. No automatic acceptance from provider success. Lead independently checks every new/changed path and actual output. Generated fixtures/evidence remain private. Commit/push/CI/deployment separate.

## Lead Review — Missing Per-Name Evidence Contract

Lead independently inspected fourfrozenfiles/hashes and ran35focusedtests:35passed7.24s. Actual-data usability requires unsupportednames remain explicit without invented templates. Accepted same-path extension: template:null is valid unavailableevidence; run_id:null is valid nocaptureselector. Preserve exact50identities/code/currency; nulltemplate produces template_missing withheld row, nullrun produces history_unavailable withheld row; do not query unavailable selectors or require fabricated source/calendar/action facts. Non-null malformed inputs still fail. Engineer returns mixedsupported/null regressions and updated documentation/hashes before acceptance. No actualsource/35claim yet.

## Independent Code Acceptance

25Oct Lead independently read4files and initialfrozenhashes;35focusedtests passed7.24s. Review found unsupported16required inventedtemplates; samepathnulltemplate/nullrunextensionimplemented. Lead reviewed correction and independently replayed8newcases:8passed35deselected0.46s. Engineer final43passed7.71s. All4changedpathsvalidate,diffcheckpass. Exacthashes:{"docs/MANUAL_FORECAST_CSV.md": "3168a0c6875c033465aac402ca7c7b16f503da21bccbacc56c74c307d7eeab3d", "ingest/private_forecast_refresh.py": "102ba6256901db0abf77b210d4699e8d1e35034719249bf005bb5f1f3bd8ee95", "scripts/daily-market-brief/refresh_private_forecast.py": "6090ca361909788602da983c5e1a0f8f87cd5f9dedcca81451363d63a9c4314d", "tests/test_private_forecast_refresh.py": "5c10c992a2351a2777b66b5ad88b971735b241d27ca263c5f83bec27ef758152"}. Offline-store only,no providerfreshnessgrant; actualconfig/preparationpending,numeric35gateunmet.

D4remains pending private actualconfiguration/readiness delivery. Noactualforecastissue,onlinecollection,publicpromotion,commit/push/deploymentclaimed.

## Actual Preparation Finding — Known-Time Preservation

Actualstore comparison found original known_ms is ceiling-millisecond availability, sometimes later than microsecond ingestion. Initialadapter known_at=ingested_at incorrectly moved that boundary earlier. Lead returns mapping for same-path correction: exact originalknown_msUTC, retrieved<=ingested<=known<=issue, no roundingdown; fractionalboundary regression/actualcandidateparity required. Noactualforecastexportoccurred. PriorD1mappingacceptance reopened for this verified defect, preserving earlier passedchecks as historical evidence.

## Final Independent Acceptance And Actual Command

25Oct18:22MYT Lead actual offlineCLI from/private/tmp exit2insufficient_coverage:50uniqueorderedrows,34generated/16withheld/0demo,34exactoriginalevidenceparity/714bindings,reviewrequired0. Correctedknown_msUTCboundary independently tested:1passed43deselected0.46s; Engineer44passed8.12s. Lead independently verified4finalcodehashes/config/original34templates/finality/exactadmissionobjects,outputmanifesthashbytes/allrowresulthashes/privatepermissions/pendingtargets/originalCSVunchanged. NewCSV SHA b435b5b871874f02e4b375b6f18a5d2beac1accdafd13f0fcca836c2fa879c78. Privateactualconfig/receipt/outputreview under engineeerPRSG140actual-config-prepared. No providerrefresh/newapproval/training/publicpromotion;135>=35/full50/full100/strongmodel stillunmet.

Correctedmapping preserves originalstoreknown_ms including ceil-millisecond availability. All34candidatehashes match actual prioradmissions without modification. Adapter delivery accepted; actual135release remains insufficient34/35. This is offline stored-data preparation, not automatic continuous providerrefresh or financialreview.
