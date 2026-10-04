# PRSG-58 Resolve local test helpers before installed packages

Type bug · Modules harness · Owner Engineer · Priority P1 · Effort XS (0.1–0.4 days) · Impact medium: deterministic collection across dependency environments.
Created 2026-10-05 MYT. Human requested CI repair. Frozen base81037cf3d3749643c4bd17486f7f2b9468611cbf.

## Reproduction and outcome

tests/test_daily_quote_report.py imports tests.test_daily_report_projection. The local tests directory is an implicit namespace; an installed ordinary tests package wins resolution. Lead created /tmp/PRSG-ci-shadow-package/tests/__init__.py (synthetic unrelated package) and ran PYTHONPATH=/tmp/PRSG-ci-shadow-package /Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest --collect-only -q tests/test_daily_quote_report.py --tb=short. Exit2, ModuleNotFoundError tests.test_daily_report_projection, 1 collection error in0.07s. Log /tmp/PRSG-ci-shadow-collection-before.log. RemoteCI37242245608 also exited2 in collection, but its authenticated traceback is unavailable; association is a hypothesis until remote evidence confirms.

Add a minimal tests/__init__.py so this checkout supplies its own ordinary package. Add a regression that exercises fresh Python/pytest collection with a competing synthetic tests package on PYTHONPATH, preserving helper import and collected cases. No dependencies, workflow edits, skips, test weakening, fixture duplication or runtime/model downloads. Four frozen paths only; preserve PRSG-55 work. Focused test_package_resolution plus daily_quote_report and complete3.11 suite. Do not commit/push; Lead integrates and verifies remote CI separately. Remote failure remains unresolved if this does not fix it.

## When it's considered done
- [x] PRSG-58-D1: Shadowing regression fails before and passes after; focused/full checks recorded.
- [ ] PRSG-58-D2: Lead independent scope/replay and remote CI result reviewed.


## Engineer delivery evidence — 2026-10-05 MYT

Added a minimal docstring-only ordinary-package marker, with no test/helper duplication. Fresh-process regression creates an unrelated `tests` package on synthetic PYTHONPATH and runs the existing daily_quote_report pytest collection. It checks nonempty collected node IDs match a separate clean-process baseline, then verifies `tests.__file__` and the imported projection helper resolve exactly to this checkout. Child environments contain only PATH/LANG and the synthetic PYTHONPATH; no inherited provider credentials. Timeouts bound subprocesses.

Before marker, `/Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_package_resolution.py` failed1 test in0.24s because nested collection exited2 with ModuleNotFoundError tests.test_daily_report_projection. Log `/tmp/PRSG-58-before.log`; matches the independently supplied synthetic collision evidence, not authenticated remote traceback.

After marker, `/Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_package_resolution.py tests/test_daily_quote_report.py` passed37 in0.78s, exit0 at repository root. Log `/tmp/PRSG-58-focused.log`. Runtime CPython3.11.17 is the persistent configured hook environment; selected test dependencies remain distinct from canonical complete Poetry/Linux CI parity.

Required full suite command: `PATH=/Users/jwtan/.codex/venvs/praesagus-tests-311/bin:$PATH AWS_EC2_METADATA_DISABLED=true AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_DEFAULT_REGION=us-east-1 PRAESAGUS_API_KEY= python3 -m pytest -q`. Log `/tmp/PRSG-58-full.log`. Synthetic AWS variables only, no provider access. No workflows/dependencies/other ticket paths changed, no skipped or weakened tests, no commit/push. Lead's PRSG-55/AGENTS changes preserved; no dedicated PRSG-55 replay rerun. RemoteCI exit2 association remains unproven until Lead inspects actual traceback/new run; D2 pending.

Final full suite1155 passed,11 warnings in37.70s, exit0. Four-path manifest validation and `git diff --check` passed. D1 done; D2/Lead review and remote CI verification remain pending.

Lead preliminary review: all four paths reviewed; focused37passed1.04s exit0 using persistent3.11 with --tb=short. Remote confirmation pending.
