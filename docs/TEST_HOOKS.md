# Local commit and push test gates

Prepare a Python >=3.11 environment with pytest and the repository test dependencies. Hooks do not install dependencies or download models. Configure this checkout and install the versioned hooks:

```sh
git config --local praesagus.testPython /absolute/path/to/environment/bin/python
sh scripts/install_git_hooks.sh
```

The configured value is one executable path, not a shell command or arguments. Paths containing spaces are supported. If unset, the hooks use `python3` from the active PATH. A missing interpreter, unsupported Python, missing pytest or failing tests blocks the operation with a nonzero status. Fix the environment or tests before retrying. The temporary isolated test environment used during development is not a durable shared runtime or proof of full Poetry/CI parity.

Both `pre-commit` and `pre-push` call `.githooks/run-tests`, running `python -m pytest -q` from the checkout root. `commit-msg` remains enabled for title and staged harness validation. The installer preserves a different configured hooksPath or existing executable hooks under Git's default hooks directory and refuses to replace them; integrate custom hooks manually. Git clones require installation per checkout.

The gate tests the current working tree, including unstaged edits. It does not prove that staged content, every pushed commit, the remote tip or a deployment has the same tested bytes. Test results are local evidence only. Full pytest is a Python check; separate frontend/browser checks still apply to their tickets. Local Git hooks can be bypassed (`--no-verify`, changed hooksPath, or removed hooks), so CI and independent review remain required. Test runtime/environment changes require their own verification; a passing local suite does not guarantee remote CI success.
