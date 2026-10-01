# Ticket verification runner

The runner collects actual Git paths from the frozen base through HEAD, index,
working tree and non-ignored untracked files. Rename detection is disabled to
check both endpoints. It validates the manifest/spec and scope before execution.
Only exact argv/cwd pairs reviewed in `harness/verification_policy.json` execute;
no shell command construction. Each command has a 120-second timeout. Policy
changes need Lead review: allowed tests can execute arbitrary repository code.
This is verification, not a filesystem or network sandbox.

## Local workflow

Create/accept ticket metadata and freeze the Git base before implementation.
If unrelated edits exist, capture a reviewed baseline BEFORE ticket code edits:

```sh
python3 scripts/planning/verify_ticket.py PRSG-15 --capture-baseline --output /tmp/PRSG-15-baseline.json
# Implement, then run (omit --baseline on a clean starting checkout):
python3 scripts/planning/verify_ticket.py PRSG-15 --baseline /tmp/PRSG-15-baseline.json --output /tmp/PRSG-15-verification.json
```

Output paths must be new files outside the repository. Baseline paths cannot
exclude ticket-owned changes; matching worktree AND index fingerprints must
remain unchanged. Baselines are trusted, manually reviewed declarations, not
tamper-proof proof of ownership. Ignored files and concurrent edits occurring
between snapshots are limitations. Prefer an isolated checkout for overlap.

Evidence includes UTC run time, HEAD/base, manifest hash, changed-path hashes,
exit codes and output digest/size. stdout/stderr are discarded, not stored;
inspect a failing check separately without exposing secrets. A changed HEAD or
tracked/non-ignored worktree during tests causes needs_attention. Rejection
before execution exits nonzero without a result artifact. Failed commands,
timeouts and manual checks also exit nonzero; manual evidence never auto-passes.
The runner never edits acceptance, marks tickets complete or commits anything.

Current CI replays the safety regression suite; it does NOT yet automatically
resolve every changed ticket and verify its full delivery diff. That integration
needs ticket selection and explicit handling of multi-ticket commits. The
versioned command policy initially approves only the runner's own test suite.

## Closing a ticket

Update `plans/YYYY-MM-DD/PRSG-N-title.md` checklist/progress and
`plans/YYYY-MM-DD/PRSG-N.harness.json` check evidence/status and Lead acceptance.
Reference the verification artifact and its digest, tested revision and exact
commands. Later acceptance edits change the manifest hash: do not claim the old
artifact hashes the newer manifest. Tests alone do not complete delivery.
Commit both canonical files and implementation, then rebuild the audit:

```sh
python3 scripts/planning/build_ticket_audit.py
```

`artifacts/tickets/audit.json` is generated/ignored, never manually edited or
committed. Pages regenerates it on main pushes. Do not insert a commit's own
unknown SHA into that commit; Git audit derives links after the commit exists.
Preserve previous failures and incomplete research checkpoints.
