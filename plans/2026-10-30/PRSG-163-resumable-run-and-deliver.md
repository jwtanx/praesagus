# PRSG-163 — Resumable Run and Deliver Command

Type: feature · Modules: harness, financial-data, docs · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high — turns readiness and existing delivery interfaces into one recoverable operator workflow; no quality/coverage uplift promised.

## Objective

Deliver the role-requested resumable Run and Deliver operator command over existing approved interfaces, with stage-aware at-most-once recovery and actionable output/blocker reporting.

## Approach

Human30October directs final impactful changes based on role feedback. Engineer explicitly proposed one command against reviewed configuration, stage visibility, reuse of completed verified artifacts, no automatic retry after uncertain provider attempt, actionable failures and clean-directory demonstration. PRSG-157 intentionally stays read-only; it cannot be renamed as this execution feature. First inventory existing runner boundaries and propose the smallest typed plan/argv contract for Lead acceptance. Then reuse existing fixed50 reviewed-baseline, US30 reviewed saved-model and standalone offline interfaces where supported. Collection/admission remains an explicit external prerequisite unless an exact existing separately released finite collector can be safely reused inside the frozen contract.

## Choices

Default inspection/recovery is offline and does not execute. An explicit execution mode needs the exact reviewed child input and finite authority required by its original runner. Reconcile a consumed completed attempt using its verified immutable receipts; never call it a new current forecast. Unknown/uncertain attempts require review and a new release when appropriate, not blind retry. A durable workflow plan/receipt links original evidence and execution stages, not a second financial admission registry.

## Findings

Completed140/141/155 already implement actual commands and receipts;157 derives readiness. No equivalent outer stage-aware resumable operator contract was identified in the bounded prior inventory, but the assigned Engineer must prove the actual missing delta before adding a new wrapper. At current planning time prior US30 release is consumed and original first windows have started; current-source/financial renewal remains an external gate. A retained completed delivery is recoverable, but that does not grant new inference or future reference dates.

## Tradeoffs

A wrapper can make prerequisites and recovery usable without automating financial judgment or inventing source authority. The positive actual-execution gate cannot be replaced by mocks if no valid current release exists. Continue code/negative tests/retained recovery while preparing exact release evidence; report any real external dependency without shrinking the objective.

## Scope and Ownership

Implementation accepted under the frozen typed contract below; actual child execution requires a separate finite approval. Engineer owns only run_and_deliver.py, test_run_and_deliver.py and RUN_AND_DELIVER.md. Lead owns this pair and final-delivery-campaign.md. Other workers'157/161/162 files are protected by ownership even if not a literal prefix. No provider, credential, source, financial-policy, model, training, prompt, public projection or schedule change. Existing runners/calculators/ledgers remain unchanged unless a separately reviewed scope amendment is necessary.

Allowed: plans/2026-10-30/PRSG-163-resumable-run-and-deliver.md, plans/2026-10-30/PRSG-163.harness.json, scripts/stock-research/run_and_deliver.py, tests/test_run_and_deliver.py, docs/RUN_AND_DELIVER.md, plans/2026-10-30/final-delivery-campaign.md. Protected: scripts/stock-research/run_reviewed_batch.py, scripts/stock-research/run.py, ingest/, connectors/, artifacts/, harness/, skills/, agent-operations/, .DS_Store. Freeze current full Git SHA before implementation; planning base cca89e514ed6217d3afb980063b604a53ff069c3. Preserve all historical source/output/model generations and unrelated dirty files.

## When It Is Considered Done

- [x] PRSG-163-D1: Inventory the existing approved runners and freeze a typed hash-bound workflow-plan contract and exact supported argv before implementation; no arbitrary shell commands, implicit provider access, dates or review authority.
- [x] PRSG-163-D2: Provide one operator command that checks original prerequisites and invokes only typed quality-scorecard161 or reviewed-us30-155 aliases when explicitly authorized; offline evaluation is distinct from fresh prediction and original child gates remain authoritative.
- [x] PRSG-163-D3: Resume from a verified completed delivery without repeating capture or inference. Persist exclusive stage/attempt evidence; an uncertain started provider or inference attempt is held for review and never automatically retried or reused with a consumed release.
- [x] PRSG-163-D4: Return the actual output path/hash/counts or exact missing evidence, affected scope, owner and next action. Historical completion and present forecast readiness remain distinct; full50/standalone100/strong-model/public rights are never inferred.
- [x] PRSG-163-D5: Demonstrate clean-directory retained155 reconciliation and a finite explicitly approved actual161 offline evaluation, matching all four accepted artifacts, then recover without a second child. Guarded155 fresh execution remains unavailable without its own current exact release; fixtures do not prove new inference. Focused interruption, failure, concurrent-target, expiry, tamper and no-network default tests pass.
- [x] PRSG-163-D6: Deliver runnable instructions, independent review and authorized commit/push evidence. Existing provider/financial/model promotion rules remain; no new framework or duplicate authoritative admission registry.

## Checks

Use the exact focused argv plus appropriate existing-runner integration checks. Exercise meaningful interruption-before/after-claim, completed-child/outer-finalization crash, symlink/tamper/hash/permission/expiry errors, malformed plans, stale authority, concurrent invocation, sanitized failure and no network/model/default execution. Actual receipts remain private and are independently reviewed; model/source/coverage/public gates are separate. No commit/push by worker; Lead owns integration and mandatory hooks.

## Frozen Typed Contract — 30 October 2026

Lead accepts typed contract proposal017f26a62c4a70e820d6fc742618c8034e61fac9f25c88ac12928d854e9a137e(10203B), AI boundaryreview5119064637d062ecea5984fdf7d9fa360d5bb8724aa6546fd67bf1ba9e99e311. Two fixed aliases;161private verified relative-layout source snapshot preserving accepted output bytes, canonical and actualargv recorded. Defaultinspection has no writes/subprocess/evaluator/model import. Exact private600/700 paths; fsyncedworkflow+crossworkflowtargetclaims; uncertainstartedattemptheld; originalsuccessfulsupervision required for outer-onlyrecovery. 16160s+2s/512MiB sampledRSS/1thread/0retry;155child58s+2s unchanged,outer120s+2s constrainedoriginalexpiry/firstopen. Fixed50/standaloneexecutionexcluded untilseparatelyreviewedauthority,157readinessvisible. SeparateplanSHA-bound<=10minouterapprovalnotchildfinancialauthority. Implementationonly now; actualfiniteapproval follows frozenreviewablecode/plan.

The original broad runner inventory is preserved. Existing fixed50/standalone CLIs have no equivalent finite execution authority, so v1 exposes their retained/missing state via157 and exact external release dependency. Do not represent the actual161 evaluation demonstration as new current inference, additional numeric coverage, source collection or a completed full50/100 product. Both enabled execution aliases remain required; a read-only157 wrapper is insufficient.

### Portability and Recovery Review Amendment

Lead accepts replacing personal-path constants with the active configured interpreter identity and one deterministic output-parent-derived shared target-claim directory. All workflow IDs for the same canonical child target must converge on that claim location; plans cannot choose a second claim store to bypass at-most-once protection. Preserve exact pinned executable bytes, public/actualargv, and original600/700private boundaries. Recovery independently validates resource/sample/PID/gap/elapsed limits and original execution approval against original stage times, binds claim/intent/supervisor/child hashes, and reports the actual durable stage plus safe structured evidence/blocker/owner/next action. This strengthens operational portability and tamper detection without renewing child financial authority.

## Independent Actual Acceptance — 30 October 2026

Lead independently66focusedtests passed3.83s; Engineer66passed3.78s. Frozen wrapper4f0eff1122be5ca6855a31aad6e350d54ecaddce1022e00455fa1365c82f3685; tests624e84eae3ee670cd40492351937bfb59a59f64ba3a51d5ecafa79d7125432f8. Finiteplan573b776626d3df1639d45f5dd5ebd861645d24b03b0759fdc7fc34434933591d and exactapproval908470b53c14e7d451cd824034686828203cc5d0c598fd39dde2c383c9a6bed0 produced real161evaluation once from/tmp, exit0,4acceptedartifacts byte-identical,38originalrefs unchanged. Observed0.6418s/95698944BsampledRSS/14samples/maxgap0.0518s,cleanupverified. Controlledoutersealwithholding preserved originalsealbytes; inspectchild-verified(no writes), recover/repeatrecover0nochild; consumedexecute2held,claim/intent/supervisor/childhashesunchanged. Retained155inspect/recover0forecastcomplete/nochild. Actualreviewbfe3e60424cdd159116aa763026152869ecfe386dfb2bcb6b48f5b0b84efec65. No new155inference/provider/source/fit/promotion; original155expiredrelease remainsconsumed. A stale descriptivecodepin inreviewtextwascorrected inpreservederrata; exactplanruntimehasheswereverifiedbeforeapproval andactual4fcodeused.

At implementation acceptance, D6 was pending. The verified delivery below closes it.

## Verified Implementation Delivery

Implementation committed/pushed as556749b502694b91e32468a6b93017ad99ae2341; remote main SHA independently matched. Mandatory precommit4051passed41warnings95.84s and prepush4051passed41warnings92.52s; no bypass. Independent actual implementation evidence remains asabove. User-runnable CLI/docs shipped; actualfinite161execution/recovery and retained155reconciliation alreadyindependentlyproven. No new155/currentforecast admission implied.
