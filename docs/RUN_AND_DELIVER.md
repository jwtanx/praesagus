# Run and Deliver

`scripts/stock-research/run_and_deliver.py` is a small operator over two existing
commands. It defaults to read-only inspection. It never collects provider data,
creates financial admissions, fits a model, selects a latest model, schedules
work, or promotes forecasts. Only explicit `execute` dispatches a child.

Use the configured Python environment that runs the approved child, Python3.11+:

```sh
python -I -B /absolute/repo/scripts/stock-research/run_and_deliver.py \
  --plan /absolute/private/workflow.json --plan-sha256 PLAN_SHA
```

Add `--mode recover` to finish an outer delivery seal from a previously verified
child. Add `--mode execute --approval /absolute/private/approval.json
--approval-sha256 APPROVAL_SHA` only with an exact finite reviewed approval.
Execute refuses an existing attempt/child target; it never silently retries.

Exit0 returns inspection or a verified delivery/result. Exit2 returns a held
blocker, stage, affected workflow/target, field/reference where known, responsible
role and next action. Child stderr/source bodies are not dumped into the
operator response. A zero wrapper exit is not a forecast-quality or trading gate.

## Typed plan

Top-level fields are exactly `schema_version:1`, `workflow_id`, `runner`, `python`,
`runtime_files`, `inputs`, `attempt_parent`, `target_claim_parent`, `resources`,
`expected_outputs`. No shell, arbitrary argv, environment, module, code, retry,
implicit date or model override is accepted. References are exactly
`{"path":"/absolute/file","sha256":"64 lowercase hex","bytes":123}`.

`python` must identify the active configured `sys.executable`; its resolved
executable bytes are pinned. Private inputs/control files are owner0600 and their
directories owner0700, outside the repository. Code references are a fixed
repository-relative allowlist, not arbitrary supplied programs. Unknown fields,
unsafe paths, symlinks, bool-as-integer, duplicate/nonfinite JSON, changed hashes,
overlapping output/input paths and incorrect resource constants are rejected.

The claim root is **derived**, not chosen freely:
`child_output_parent/.run-and-deliver-claims`. Create that owner0700 directory
during private setup. Every workflow ID targeting the same canonical output must
use this same claim location. `attempt_parent` holds distinct workflow folders.
The wrapper never automatically deletes, expires, resets or unlocks claims.

| Alias | Typed inputs | Exact child semantics |
| --- | --- | --- |
| `quality-scorecard161` | `bundle` reference, `output_parent` | Existing `quality_scorecard.py --bundle PATH --bundle-sha256 SHA --output-parent PARENT`, using `-I -B`; original frozen outcome cutoff retained |
| `us30-reviewed155` | `bundle`, `child_release`, `inspection_bundle` references | Existing public `run_reviewed_batch.py --bundle PATH --bundle-sha256 SHA --release PATH`, using `-I -B`; all original child gates retained |

For161, `expected_outputs` contains exactly `artifacts`, `summary`, `review_at`.
The artifact map has the reviewed SHA/bytes of all four deterministic files:
scorecard.json, scorecard.csv, scorecard.html, provenance.json. Preaccepted output
pins and original counts/cutoff are not recomputed in parent inspection.
The child target is `output_parent/scorecard-<bundle SHA first20>`.

For155, `expected_outputs` is null. Its target is the original bundle output
parent plus child release runID. The157 inspection bundle must bind that exact
US30 bundle/release/target. It also retains honest fixed50/standalone states.
Neither fixed50 nor standalone CLI execution is enabled by this wrapper. Missing
100-name coverage remains missing; private evaluation completion does not fill it.

## Runtime, resources and authorization

Common runtime refs are this wrapper, inspect_delivery.py and
run_reviewed_batch.py. The161 closure additionally contains quality_scorecard.py,
evaluation.py, data.py, storage.py, market_calendar.py, inference.py, model.py,
features.py, ranking.py and harness/forecast_review.py. Parent inspection loads
only the standard-library helpers from verified bytes; no evaluator/model import
or child preflight/scoring runs by default.

For161 execution, verified source bytes are staged into an exclusive private
relative-layout tree and the unchanged child entrypoint runs there. Canonical
public argv and actual snapshot argv are both recorded. No old pyc is staged and
`-B` prevents new bytecode. Output is forbidden in the original repository as well
as the snapshot. All four output bytes must match the reviewed originals, whose
provenance uses relative code hashes. This copies code, never model artifacts.

161 uses60s work+2s cleanup,512MiB sampled process-tree/group RSS,1 numerical
thread through the existing environment controls,0 retries.155 retains its
58s+2s child limit and gates; the outer command allows120s+2s for bounded
preflight/finalization but must fit within the original release/first-open
deadline. The wrapper sets cwd `/tmp`, stdin DEVNULL, shellFalse and removes
PYTHONPATH/PYTHONHOME. Stdout/stderr capture is bounded64KiB each.

Supervision reuses155 observed PID-birth/tree/group rules. It rejects unobserved
work, monitor gaps>1s, excess sampled RSS/time and uncertain cleanup. If this host
denies group signaling, the receipt records that denial and cleanup falls through
to birth-checked individual PID signaling; only independently verified group
absence can establish cleanup. This is not a hard RSS/thread cap, absolute peak,
filesystem lock, or proof that a descendant escaping before observation was seen.

Execution approval is separate from the plan, avoiding cyclic selfhashes. Exact
fields: schema_version1, kind`run-and-deliver-execution`, approvedTrue,
plan_sha256, workflow_id, runner, not_before_ms, expires_at_ms, resources,
resources_confirmedTrue, exclusive_local_run_confirmedTrue, review_reference.
The review reference must approve the same planSHA/workflow. The interval is at
most10minutes and must leave the full fixed work/cleanup reserve before dispatch.
Outer approval is never original155 source, financial, model or inference
authority.155 still requires its separately valid exact child release and all
existing currentness/resource/runtime gates. Expired/consumed releases are never
renewed by recovery.

## Durable stages and recovery

The wrapper fsyncs exclusive workflow/target claims and dispatch intent **before**
one fixed-argv launch. Stages are immutable files: claim.json,
dispatch-intent.json, supervisor.json, child-verified.json, delivery.json.
Inspection reports the actual durable stage without creating missing files:
planned, interrupted-before-claim, claimed, dispatch-uncertain,
child-finished-supervisor-recorded, child-verified or outer-delivered.

An existing directory without a claim is uncertain. An intent without successful
original supervision remains held even if output files look complete. Recover
never launches a child. It verifies the exact original resource limits, sampled
RSS/identity/gap/time/cleanup, actual argv and snapshot, original approval stage
window, target claim, expected output hashes/counts/cutoff, then finishes only the
outer seal. The seal binds claim/intent/supervisor/child/target-claim hashes.
Tampered redundant metadata is also rejected. Repeated recovery revalidates
evidence and creates no second child. Historical approval is checked at original
stage times, not required to be currently unexpired.

A historical completed155 delivery may be adopted into an outer recovery record
only after157 verifies its original final receipt, both approvals, artifacts and
original supervisor cleanup. This is historical evidence, not a new run. Its
immutable completion counts remain separate from current readiness; inspection
derives current states again without retimestamping forecasts.161 cannot adopt
bare foreign output files without its own original outer supervision proof.

## Checks and actual release gate

```sh
python -m pytest -q tests/test_run_and_deliver.py
```

Fixtures exercise wrapper contracts only. Synthetic subprocesses test observation,
timeouts, output bounds and cleanup, without providers/models/evaluators. Actual
completion additionally requires Lead's finite approval of frozen code/plan,
real161 evaluation into a new private target matching all four accepted artifacts,
and recovery without a second child. Retained155 is reconciled separately; that
does not prove a new155 inference run. Exact plans, receipts, failures and hashes
stay private outside Git. Commit/push, independent review and remote deployment
are separate delivery stages; this document creates no schedule or authority.

## Verified actual demonstration — 30 October 2026

Lead executed the pinned161 evaluation plan once from `/tmp` under its separate
finite approval: exit0,0.642s,95,698,944 bytes sampled peak group RSS,14 samples,
verified cleanup. All four artifacts matched the accepted161v3 hashes and38
original references were unchanged. This measured one local evaluation, not
prediction performance or a general resource guarantee.

Lead preserved the original outer seal and temporarily withheld it to exercise
recovery. Read-only inspection reported child-verified; recovery and repeated
recovery returned evaluation-complete with no child invocation. Original
claim/intent/supervisor/child hashes stayed unchanged. A consumed execute request
was held. This was a controlled seal-withholding drill, not an observed real
crash. Retained155 inspection/adoption also returned forecast-complete without
inference; its original release remains consumed/expired. Exact private review:
`PRSG163/lead/actual-execution-and-recovery-review-r1.json`, SHA-256
`bfe3e60424cdd159116aa763026152869ecfe386dfb2bcb6b48f5b0b84efec65`.
