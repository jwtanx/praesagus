# PRSG-141 — One-Command Current Forecast Run

Type: feature · Modules: financial-data, market-research, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–1.5 person-days estimate) · Impact: high — removes separate collection invocation from the human forecast command while preserving source review boundaries.

## Why the ticket is created?

Human25October explicitly instructs Lead to keep working until forecasts work.135requires reproducible current>=35numeric fixed50delivery by28October.140implements store-to-batch preparation but its --offline command cannot fetch current history; calling it a fully fresh pipeline would be wrong. This ticket owns the remaining bounded collection orchestration and actual end-to-end command acceptance, not a new model.

## Objective

By28October2026 23:59MYT deliver one documented command that explicitly collects through existing approved interfaces, prepares current fixed50 candidates and consumes exact actual reviews to export predictions. Actual>=35non-demo current numerical rows and attributable CSV are required for final acceptance; review_required/insufficient output is implemented behavior, not completion of this objective. No guarantee of future eligibility or forecast accuracy.

## Approach

Reuse existing collector/store/supervisor/credentialloader and140adapter/exporter. New online runner takes explicit private bounded released history plans, exact50ordered templates/calendar/finality/rights references, private locator and current exactreview directory. Offline mode must never touch credentials or providers. Select explicit runIDs for new captures; do not mutate original config/reviews/generations. Preserve original observed/ingested/known_ms and normalization provenance. Derive no acceptedfinancialdecisions. Exact review mismatch produces review_required and cannot be silently carried forward. Return real counts and paths/status; partial/missing/upstream failures remain bounded and visible.

No provider call is released by code implementation. Before an actual run Lead/Trader freeze exact jobcodes/enddates, source-use authority, runtime pins, actualvenuecutoffs, requestbudget/pacing/deadline and output/runIDs. Existing history plans <=30jobs each,100unadjustedbars/job; at most50totaldistincthistoryjobs across finite plans,0retry,<=20seconds/job,<=2secondcleanup,<=300seconds/collectorplan and<=600secondswholeorchestration. Use explicit accepted minimumstartinterval and stop on first upstream/cleanup/integrity/rate-limit failure; no unapproved quota inference. If existing multi-job collect cannot expose pacing/stopfailure without protected edits, safe one-job derived plans may be used with original jobdigest/planbindings and globalbudget preserved. Do not widen original collector limits.

A clean current store may support skipping unnecessary collection only under explicit mode/contract and verifiable latestreference/target/finality/source review; no oldnumeric fallback. Do not pretend online call success establishes financialapproval. After capture a changed evidencehash needs matching actual current review. This implementation does not authorize recurring financial/riskpolicy automation.

## Frozen scope

Basecd55291 (resolve fullSHAinmanifest). Engineer owns ingest/private_forecast_pipeline.py, scripts/daily-market-brief/run_current_forecast.py, tests/test_private_forecast_pipeline.py and docs/CURRENT_FORECAST_COMMAND.md. Lead owns this spec/manifest. All140files/core/exporter/collector/store/provider/model/training source protected; any required change needs exact Lead extension. No new dependencies,endpoints,paidaccess,schedules,models,publicpublication,trades or credentials in source/output. Private evidence/configs stay outsideGit; tests syntheticonly. AI139closeddiagnostic/113pending and Trader138/124sourcefiles disjoint.

## Choices

Small orchestration over proven interfaces instead of replacement pipeline. Keep current reviewed numerical baseline and standalone100trainedprogram separate. Use actual financial review contracts; a concrete reusable reviewpolicy would require separate humanreview before adoption.

## Findings

140actualofflinecommand produced50rows34predictions16withheld/0demo,exit2insufficient. Missingcollectionandcurrentadmissionrenewal remain. CATtarget26Octcash is unsupported until a valid later historicalcashwindow/source/capture/admission is available; Trader separately examines earliest35-name30US+5MYpath without137methodpromotion. No35completionclaimed.

## Tradeoffs

One invocation can coordinate collection/preparation but cannot manufacture absent reviewedsourcefacts. Stop on real external/time/authoritydependencies after independent engineering work advances; do not stop merely at fixture/milestone success. Full113strongmodel cannot be established by this baselinecommand.

## When it's considered done

- [x] PRSG-141-D1: Explicit secure online/offline config and finite history orchestration implemented with existing collector/store, pacing/deadline/budgets/stopfailure, sanitized results and original provenance.
- [x] PRSG-141-D2: Existing140candidate/exactreview/export integration implemented; newcaptures mappedtoexactitems without oldconfig/review mutation, currentness checked and no automaticacceptedgates/fallback.
- [x] PRSG-141-D3: Focused mocked integration/failure tests pass for actual crossstage behavior, quotas/timeout/cleanup/partial/future/malformed/stale inputs, offline no-credentials/network and immutableoutputs; nofixture-asactual35.
- [ ] PRSG-141-D4: Lead independently reviews source/tests and actual released one-command run producing>=35currentnon-demo forecasts inexact50CSV, delivers config/command/output/status and records135acceptance by28Oct.

## Validation and delivery

Use approvedPython pytest -q tests/test_private_forecast_pipeline.py and focused140integration when warranted. Validate manifest/everychangedpath and independently inspect Git scope including new files. Private originalsource/capture/review/runreceipts remain bound. Codechecks/actualsourcequality/modelstrength/publicrights are separate. No fullsuite rerun without newimplementation/hookneed; mandatoryhooks oncommit/push. No deployment inferred.

## Independent Engineering Acceptance — Actual Outcome Pending

25OctLeadreadfull285linemodule/CLI/docs and4frozenhashes;all4Engineersuppliedpathsvalidate. Owner39focused1.36s/392integration12.59s. Required143commithookfullworkingtree3694passed41warnings77.63s includes14139cases. Leadactual141offlineCLIfrom/private/tmp producednewimmutable50rowCSV34generated16withheld0demo/reviewrequired0,exit2insufficient,no providerrefresh;outputmanifesthashbytes/50uniqueidentitiesverified. Onlineactualexecutionand>=35D4notmet;currentreviews/exactreleaseand27Octmarketwindowremainrequired. DeadlineboundsdispatchnotparentdiskI/O;noautomaticapproval.

D4remainsopen. Codeintegrationandactualoffline34CSVarenottheone-command>=35outcome. Preserveexactfinancialreleaseandfreshmatchingreviews;nooldapprovalcarryforward.
