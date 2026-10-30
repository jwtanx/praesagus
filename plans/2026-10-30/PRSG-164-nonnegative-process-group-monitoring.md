# PRSG-164 — Nonnegative Process Group Monitoring

Type: bug · Modules: harness, infra · Owner: Lead · Priority: P1 · Effort: XS (<0.5 person-day) · Impact: high — a valid unrelated system-process row must not disable every supervised run.

## Objective

Fix process snapshot portability while retaining strict positive owned-group identity and safe cleanup.

## Approach

Lead inventories canonical manifests and reproduces the parser defect before editing. Accept a nonnegative PGID in the global process table, then reject an owned group that is not positive. Reuse the existing batch supervisor and preserve all release, source, model, runtime and numerical gates. AI Engineer independently reviews this small integration fix while Engineer owns disjoint163files.

## Choices

Do not omit all zero-group rows before descendant selection, since silently dropping an owned invalid group could approve uncertain work. Keep them observable, reject owned group zero and never pass zero to group signalling. Keep PID strictly positive and reject negative PGID/RSS or malformed rows.

## Findings

A stdlib-mocked ps output with unrelated PID2/PPID0/PGID0/RSS0 plus a valid child777 raises monitor_shape_invalid under the existing pgid>0 global parser. Public CI first failed at155implementation b62509d after prior d9a3c64 success; subsequent six runs fail Run tests. The job traceback requires sign-in and was unavailable. This chronology is supporting evidence, not proof of the CI root cause. Linux proc documentation defines pgrp as a process-group field; no source evidence or forecast is altered here.

## Tradeoffs

The parser accepts a wider valid system table, but the owned-run and signal boundaries remain strict. Representative fixtures establish the observed parser defect; only a new remote run can establish remote CI recovery. No Linux-native local host, financial execution or provider call is available/needed for this bounded fix.

## Frozen Scope

Base cca89e514ed6217d3afb980063b604a53ff069c3. Lead owns only run_reviewed_batch.py and test_reviewed_batch.py changes plus this canonical pair. Engineer163and all accepted157/159/161/162workingbytes stay disjoint. Reviewer: AI Engineer for runtime boundaries; Lead integration acceptance. Runtime changes must be repinned in later163plans before execution. Original155completed approvals/source/model generations remain immutable. Allowed paths are exactly this pair, scripts/stock-research/run_reviewed_batch.py and tests/test_reviewed_batch.py; protected ingest/,connectors/,artifacts/,harness/,skills/,agent-operations/. No budgets, release authority, original forecast data or policy change.

## When It Is Considered Done

- [x] PRSG-164-D1: Reproduce an unrelated nonnegative process-group-zero row rejecting the whole process snapshot, and preserve the distinction between this portable defect and an unconfirmed remote CI traceback.
- [x] PRSG-164-D2: Accept nonnegative unrelated process-group IDs while requiring positive IDs for owned process groups and every group signal; preserve process identity, descendant tracking, sampled RSS, deadline and cleanup rejection gates.
- [x] PRSG-164-D3: Focused parser/scope/signal regressions and the existing real child exit, timeout, memory and cleanup cases pass; independent runtime review confirms no financial or execution-policy change.
- [ ] PRSG-164-D4: Integrate through mandatory hooks, inspect the resulting remote CI and report its exact result. A green run is required before claiming CI repaired; historical forecast approvals are never renewed.

## Checks

Run the manifest focused command, independent runtime-boundary review and mandatory commit/push hooks. Cover zero/negative/malformed PGID, unrelated-row preservation, owned zero rejection, positive-only group signalling, existing PID reuse/detached descendant and real child cleanup/timeout/memory behavior. Record CI separately after push; do not infer it from local tests.

## Independent Implementation Acceptance

Lead whole focused110passed7.00s; AI independent16targetedcasespassed0.48s,94deselected. Exactsource5b5625e29859b60d1ae9bfeb4df467fa98f1cbd8ebfb6564e5562cf4c7d72982; tests8571b2ec6126ca068b654c20108a2da187955a7a0e86b901c9d5f897912b7804. AIreceiptcf035d95d2b1141e66aaad7c316bf37a4493a918443023144c63f675820b2a0c. OriginalglobalPGID0rejection independentlyreproduced; realchild+authoredunrelatedrow succeeds; selectedzero/negative/malformed/signal errorsstillreject; original58+2/512MiB/1thread/0retryLIMITS ASTunchanged. OriginalCItracebackunavailable; remoteCIrepair notclaimed.

Initial authored real-child fixture appended an extra empty ps line and failed; fixed the fixture newline only, then all13new cases and final110wholecases passed. No production gate was weakened. D4 stays pending until mandatory hooks and exact remote result.

## CI Diagnosis Scope Addendum

The exact556749bremoteCIrun41003275906 still failed Run tests after the reproduced portability repair; Pages deployment succeeded. Therefore no CI recovery is claimed and D4 remains open. Lead accepts two supporting paths, .github/workflows/ci.yml and docs/TEST_HOOKS.md, to emit a bounded failure-only JUnit annotation summary through the ordinary job. Preserve the exact Poetry pytest command, all dependency constraints, full suite, nonzero failure propagation and safety replay. No continue-on-error, skipped cases or relaxed assertions. Engineer independently reviews this diagnostic change before push. The trace remains unknown until the new run supplies evidence; any resulting implementation fix requires a frozen concrete reproduction/scope.

### Diagnostic Acceptance

ExistingCIdependency4passed0.50s. Leadexecuted exactembeddeddiagnostic code: missing/malformed/oversizedreportsboundedwarnings,12failures=>8annotations,percent/CR/LFescaping,collectionerrorhandling. Privatecheck65d8a01d9a1d94e3b4813bce7408274802a91bef7c25ad33e6101d5e48bced22; independentEngineerfinalreviewa2a852b6373602694f18af5b8501c4d230b30153b8c474675d09e5e26c220e5c. Workflow4f69061d9b88398249937f96be474ca5642c19f42accd5c1940e69cc0ebf7ab8. OriginalfullPoetrypytestcommand/dependencies/nonzeroexit/safetyreplay preserved; no skip,retry,continue-on-error orcapturedoutputpublication. 1800sourcecharactersmayencodeupto5400logcharacters,stillbounded.

The prior failed-run record remains unchanged. D4 is not complete until the remaining actual CI failure is identified, fixed under accepted scope, and a new full remote run succeeds.
