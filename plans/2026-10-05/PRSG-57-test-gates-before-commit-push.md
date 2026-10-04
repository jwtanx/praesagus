# PRSG-57 Test gates before commit and push

Type chore · Modules harness · Owner Engineer · Priority P1 · Effort S (0.5–1days) · Impact medium: catch localtestfailures beforedelivery.
Created2026-10-05MYT. Human explicitlyrequests precommittesthook beforepush. Frozen base 35e3e315fb89be28b73e77b268086f19a52a9b38.

## Frozen scope and behavior
Nine allowed paths, including minimal AGENTS.md hook workflow update only. Add executable pre-commit/pre-push sharing .githooks/run-tests; run full python -m pytest -q from repositoryroot, propagate failure/missing runtime/pytest, no skip/ignored exit. Configurable checkout-local git config praesagus.testPython points to interpreter; otherwise use active python3. Require supportedPython>=3.11 andpytest; errors explain setup/configuration, do not install/download in hook. No env/secrets printed. Test working tree honestly, not claimed index/remote-tip proof; document Git can bypass hooks and CIremains independent. Preservecommit-msg unchanged, existinghookinstaller refusal/preservation behavior. Installer makes allversionedhooks executable and enables .githooks; no blind replacement/customhooks.

Focused isolatedGitfixtures prove failingpytestblocks commit/push, successallows, missing interpreter/pytest fails,rootcwd/argv,existingcustomhooks preserved andcommitmsg remainsenabled. Use fake interpreter fixtures forbounded failurepropagation, no liveproviders/modeldownloads. Run test_test_hooks/test_commit_hook plusfull3.11suite. PreservePRSG55/56otherownedchanges. LeaveLeadreviewpending; no commit/push byEngineer. Leadconfigure actualcheckout interpreterisolated3.11and installhook before anynewpush.

## When it's considered done
- [x] PRSG-57-D1: Hooks/installer/failure regressions pass.
- [x] PRSG-57-D2: Lead independently tests realhook and installs/configures checkout; fullsuite reviewed.


## Engineer delivery evidence — 2026-10-05 MYT

Executable pre-commit/pre-push wrappers share run-tests. The gate reads checkout-local `praesagus.testPython` or active python3, validates Python>=3.11 and pytest, changes to repository root and execs full `-m pytest -q`, propagating exact failure status. No environment values printed or automatic dependency installation. Installer retains its existing custom-hook refusal and enables executable modes for all four versioned hooks. commit-msg bytes are unchanged. Docs state current-working-tree scope, bypass limits, separate frontend/CI verification and per-checkout setup; AGENTS changes only the existing installation sentence.

Exact focused command `/tmp/praesagus-ci-repro-20261005/bin/python -m pytest -q tests/test_test_hooks.py tests/test_commit_hook.py` at repository root:53 passed in11.62s. Initial fixture run3failed50passed because isolated Git checkout omitted commit-msg's staged harness checker and the default fake interpreter log included that checker. Fixture now copies that unchanged dependency and delegates its execution to the real interpreter; default assertion checks the full-suite invocation rather than assuming it is the final Python call. No production hook or existing tests weakened. Fixture subprocess environments contain only PATH/LANG and synthetic gate variables to avoid logging unrelated environment data.

Actual isolated Git operations prove failing tests block commit/push and successful gates permit them; remote fixtures are local bare repositories. Tests assert unchanged title validation still rejects bad commit titles, missing interpreter/pytest and unsupported version block, exact root cwd/argv, failure exit37 propagation, configured executable paths with spaces, active python3 fallback, executable installation and existing configured/default custom hooks preserved. No live providers or model downloads.

Interpreter CPython3.11.17 at `/tmp/praesagus-ci-repro-20261005/bin/python`; exact selected dependency snapshot `/tmp/PRSG-CI-311-dependencies-20261005.txt` recorded in PRSG-56 spec. This is not canonical complete Poetry/Linux parity. Full command: `PATH=/tmp/praesagus-ci-repro-20261005/bin:$PATH AWS_EC2_METADATA_DISABLED=true AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_DEFAULT_REGION=us-east-1 PRAESAGUS_API_KEY= /tmp/praesagus-ci-repro-20261005/bin/python -m pytest -q`. Synthetic AWS values, metadata lookup disabled. Logs `/tmp/PRSG-57-focused.log` and `/tmp/PRSG-57-full.log`.

No checkout configuration or hook installation by Engineer, no commit/push. Lead retains actual-checkout activation and D2; PRSG-55/56 owned changes preserved separately. Pre-push checks current working tree, not all pushed commits, and local checks do not establish remote CI success.

Final full suite:1106 passed,11 warnings in35.39s, exit0. Nine-path manifest validation and `git diff --check` passed. D1 demonstrated; actual activation and D2/Lead review remain pending.

## Lead acceptance — 2026-10-05 MYT

Lead independently reviewed all nine paths and unchanged commit-msg; focused hook/title replay: 53 passed in 10.31s, exit0. Configured checkout-local praesagus.testPython=/tmp/praesagus-ci-repro-20261005/bin/python and installer core.hooksPath=.githooks verified by readback. Actual .githooks/pre-push with documented synthetic AWS environment: 1106 passed, 11 warnings in35.88s, exit0; /tmp/PRSG-57-lead-real-hook.log. Current working-tree coverage, separate CI and temporary runtime limitations retained.
