# Local commit and push test gates

Prepare a Python >=3.11 environment with pytest and the repository test dependencies. Hooks do not install dependencies or download models. Configure this checkout and install the versioned hooks:

```sh
git config --local praesagus.testPython /absolute/path/to/environment/bin/python
sh scripts/install_git_hooks.sh
```

The configured value is one executable path, not a shell command or arguments. Paths containing spaces are supported. If unset, the hooks use `python3` from the active PATH. A missing interpreter, unsupported Python, missing pytest or failing tests blocks the operation with a nonzero status. Fix the environment or tests before retrying. The temporary isolated test environment used during development is not a durable shared runtime or proof of full Poetry/CI parity.

Both `pre-commit` and `pre-push` call `.githooks/run-tests`, running `python -m pytest -q` from the checkout root. The runner uses Git's hook context to locate the checkout and interpreter configuration, then removes only `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, and `GIT_PREFIX` from the pytest process environment. This lets tests create independent temporary Git repositories while preserving the hook's normal test command and exit status. `commit-msg` remains enabled for title and staged harness validation. The installer preserves a different configured hooksPath or existing executable hooks under Git's default hooks directory and refuses to replace them; integrate custom hooks manually. Git clones require installation per checkout.

The gate tests the current working tree, including unstaged edits. It does not prove that staged content, every pushed commit, the remote tip or a deployment has the same tested bytes. Test results are local evidence only. Full pytest is a Python check; separate frontend/browser checks still apply to their tickets. Local Git hooks can be bypassed (`--no-verify`, changed hooksPath, or removed hooks), so CI and independent review remain required. Test runtime/environment changes require their own verification; a passing local suite does not guarantee remote CI success.

## Current ticket brief quality and CI dependency parity

The existing full-pytest pre-commit/pre-push gate includes `tests/test_ticket_brief_quality.py`. It checks current working-tree briefs selected by canonical manifests for PRSG-109 onward: source-authored Title Case (minor words and literal inline code allowed), preserved acronyms, and nonblank effective purpose/approach/choices/findings/tradeoffs using the dashboard's actual named-section/explicit-context extraction. It never title-cases text, fills missing details or alters historical audit validation. Legacy tickets below PRSG-109 and older Git snapshots retain their original wording. Content accuracy and explicit unassessed findings still need human review. Like the existing gate, this is a working-tree check, not proof that staged bytes match unstaged content.

The hook integration regression stages a lowercase brief and then a brief missing choices in an isolated repository, executes the real new pytest quality checks through the unchanged pre-commit runner, and proves both commits fail before a corrected brief succeeds. Negative helper fixtures and historical audit preservation are separate regressions. To inspect current quality without Git mutation: `python scripts/planning/check_ticket_briefs.py`.

CI first installs Poetry dependencies, then installs the standalone research requirements with `poetry run python -m pip` into the same interpreter used for pytest. The standalone NumPy range is `>=1.26.4,<3`, retaining its tested NumPy 2 support. CI adds an explicit `numpy>=1.26.4,<2` constraint in that same install command, compatible with Poetry's `^1.26` and the NumPy 1.x environment for PyArrow 12; exchange-calendars 4.13.2 requires at least 1.26.4. No package migration to NumPy 2 is implied. CI runs `pip check`, asserts NumPy major version 1, and imports NumPy, Arrow/parquet, pandas, scikit-learn, exchange-calendars and openpyxl before collection. Offline subprocess import-blocking fixtures reproduce collection exit 2 when either missing research dependency is unavailable. Local isolated-stack checks do not establish the inaccessible original CI traceback or substitute for a new successful remote run.
