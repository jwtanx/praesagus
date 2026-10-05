# PRSG-0 — Isolate Git hook environment from pytest subprocesses

Type: bug · Modules: harness, docs · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high; the shared local test gate blocks commits/pushes when repository tests create nested Git repositories. Created 2026-10-05 MYT.

## Reproduction and expected behavior

Both `.githooks/pre-commit` and `.githooks/pre-push` delegate to `.githooks/run-tests`. That runner resolves the checkout root and configured Python, then `exec`s `python -m pytest -q` without removing the Git context variables inherited by Git hooks. Git hook processes may carry `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, and `GIT_PREFIX`. Pytest subprocess tests that run commands such as `git -C <tmp> init/add` then inherit the parent checkout context instead of operating on their temporary repository and fail with `fatal: this operation must be run in a work tree`.

Lead-reported evidence (not independently rerun during this read-only scope preparation): a pre-commit full-suite run failed with 51 failures and 65 errors; rerunning the exact suite after unsetting only those four Git variables passed 1178 tests with 23 existing warnings in 40.90 seconds. Existing tests in `tests/test_test_hooks.py` exercise actual commit/push hook operations and blocking behavior, but currently do not invoke them with inherited hook Git variables or prove a nested Git operation succeeds in the test subprocess.

The CI workflow runs pytest directly under Poetry and does not invoke these hooks. No CI workflow change is proposed.

## Decision and bounded implementation

Preserve hook context while the runner locates the repository root and reads Git-local interpreter configuration. Remove only `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, and `GIT_PREFIX` from the environment of the final pytest child process. Preserve the configured Python path (including paths with spaces), checkout-root cwd, prerequisite checks, full-suite command, and exit status. Do not alter Git config, hook installation, title validation, staged harness validation, tests themselves, or CI behavior.

Expand the existing synthetic actual-hook regressions. Invoke pre-commit and pre-push with a simulated Git hook environment containing all four variables; prove the runner's pytest child sees them unset and can create/use an independent temporary Git repository. Keep cases proving pytest failure blocks commit/push and success permits them. Keep commit-message validation behavior unchanged.

### PRSG-0 metadata compatibility found during scope review

The commit-title regex and `scripts/planning/check_staged_harness.py` already accept `PRSG-0`, as required for shared workflow infrastructure. However, `scripts/planning/validate_ticket.py` currently accepts only `PRSG-[1-9][0-9]*`, and `scripts/planning/build_ticket_audit.py` has the same positive-number-only manifest-path regex. A canonical PRSG-0 plan/manifest therefore cannot pass the documented validator and is ignored as a manifest checkpoint by the audit, even though PRSG-0 is reserved for this class of ticket.

Include the smallest compatible PRSG-0 support in the validator and committed audit manifest discovery, with focused regressions. Retain the existing staged filename/title support; do not rewrite historical activity-only records or change other keys' behavior. This makes the shared-infrastructure ticket itself valid and auditable.

## Accepted frozen scope and exclusions

Frozen base: `0a43f04f03b406cb73480a50cec9dc1b7f15f36e`. Lead accepted this exact scope and authorized implementation on 2026-10-05 MYT. Writes were limited to these nine paths:

- `.githooks/run-tests`
- `tests/test_test_hooks.py`
- `docs/TEST_HOOKS.md`
- `scripts/planning/validate_ticket.py`
- `tests/test_ticket_harness.py`
- `scripts/planning/build_ticket_audit.py`
- `tests/test_ticket_audit.py`
- `plans/2026-10-05/PRSG-0-test-hook-env-isolation.md`
- `plans/2026-10-05/PRSG-0.harness.json`

Protect all other repository paths. In particular preserve `.githooks/pre-commit`, `.githooks/pre-push`, `.githooks/commit-msg`, `scripts/install_git_hooks.sh`, `scripts/planning/check_staged_harness.py`, `.github/workflows/ci.yml`, the existing commit-title gate, PRSG-60's staged plan/manifest and all implementation files, and every dirty PRSG-2 path in the original checkout. Keep PRSG-0 as the shared workflow ticket; do not mix other ticket work or edit the caller's staged index.

Owner: Engineer; reviewer/scope authority: Lead. Lead accepted the exact paths, base, exclusions and checks on 2026-10-05 MYT. Implementation and checks are complete; ticket status is review and scope is accepted pending Lead review. Implementation was limited to the separate worktree at the frozen base and the nine listed paths. Any further Git-environment variables or behavior changes require a scope amendment; initial evidence supports only these four variables.

## Verification plan

Use synthetic temporary Git repositories and the existing configured Python >=3.11 test environment; no network, providers, credentials, dependency installation or commit/push of user work.

From repository root:

```sh
sh -c '"$(git config --get praesagus.testPython)" -m pytest -q tests/test_test_hooks.py tests/test_commit_hook.py'
sh -c '"$(git config --get praesagus.testPython)" -m pytest -q tests/test_ticket_harness.py tests/test_ticket_audit.py'
sh -c 'env GIT_DIR="$(git rev-parse --absolute-git-dir)" GIT_WORK_TREE="$(git rev-parse --show-toplevel)" GIT_INDEX_FILE="$(git rev-parse --git-path index)" GIT_PREFIX= sh .githooks/run-tests'
sh -c '"$(git config --get praesagus.testPython)" scripts/planning/validate_ticket.py plans/2026-10-05/PRSG-0.harness.json \
  --changed-file .githooks/run-tests \
  --changed-file tests/test_test_hooks.py \
  --changed-file docs/TEST_HOOKS.md \
  --changed-file scripts/planning/validate_ticket.py \
  --changed-file tests/test_ticket_harness.py \
  --changed-file scripts/planning/build_ticket_audit.py \
  --changed-file tests/test_ticket_audit.py \
  --changed-file plans/2026-10-05/PRSG-0-test-hook-env-isolation.md \
  --changed-file plans/2026-10-05/PRSG-0.harness.json'
git diff --check
```

The synthetic hook regressions must prove: hook Git variables are present on entry; only the test child receives those four variables unset; a nested `git init/add` succeeds in that child; nonzero test status still blocks commit/push; successful tests permit them; and existing commit-message title checks remain active. Ticket metadata regressions must show the PRSG-0 manifest validates and is replayed by the audit as a manifest checkpoint, while existing PRSG-positive manifests, PRSG-0 activity-only history without a manifest, and other title/harness behavior remain unchanged.

The full-suite-under-hook-context command above verifies the reported class of failures across tests without changing CI. Full-suite and targeted results are separate evidence; neither proves a remote environment is identical. Lead reviews the complete frozen diff and checks before accepting completion.

## When it is considered done

- [x] PRSG-0-D1: Actual pre-commit/pre-push regressions with simulated Git hook variables prove the isolated pytest child can use temporary Git repositories and preserves failure/success gating.
- [x] PRSG-0-D2: PRSG-0 manifests pass the ticket validator and appear as canonical manifest checkpoints in the audit; existing PRSG-0 activity-only and positive ticket behavior remains covered.
- [x] PRSG-0-D3: Focused checks and full pytest under simulated hook context pass; docs, scope and Lead review are recorded without changing CI/title/staged-filename gates.

Reported baseline failure/pass results above are Lead-supplied evidence, not this assignment's test run. Lead accepted this ticket's exact frozen scope and verification checks on 2026-10-05 MYT. Implementation and checks are complete within that scope. PRSG-0 validation/audit compatibility is included so this canonical manifest validates and becomes auditable.

## Engineer handoff evidence

`.githooks/run-tests` keeps Git context through checkout-root and interpreter configuration checks, then removes only the four hook context variables from the pytest child. Actual pre-commit and pre-push fixture tests supply all four variables, verify the child receives none, initialize and stage in an independent temporary repository, preserve failure blocking and success behavior, and retain the existing commit-message gate. The configured test interpreter is Python 3.11.17.

The focused test commands resolve `praesagus.testPython` from Git config rather than relying on `python3` on PATH, which is Python 3.9.6 in this checkout. Using the configured Python 3.11.17, the hook regressions passed (55 tests in 13.13s; `/tmp/PRSG-0-hook-regressions.log`) and ticket metadata regressions passed (131 tests in 13.40s; `/tmp/PRSG-0-ticket-metadata.log`). The full hook-context suite passed (1161 tests, 11 existing deprecation warnings in 34.93s; `/tmp/PRSG-0-hook-context-full.log`). The hook-context command derives Git dir, worktree and index with `git rev-parse`; simple `.git` paths are invalid in linked worktrees. Hook regressions cover both simulated hook context and invocation from a nested working directory, confirming the runner changes to checkout root. Manifest JSON, all nine explicit scope paths, and `git diff --check` pass. No CI, title, staged-filename, protected paths, PRSG-60 files or dirty PRSG-2 checkout were changed.

## Lead acceptance — 2026-10-05

Lead independently reviewed the full nine-path diff and reran the focused hook suite (55 passed), ticket metadata suite (131 passed), full suite under simulated hook context (1161 passed, 11 existing warnings), explicit-path validator, JSON parse and diff check. Lead accepted PRSG-0-D1/D2/D3 and the ticket at 2026-10-05 19:58:24 MYT (11:58:24 UTC). No commit or push was part of this acceptance.
