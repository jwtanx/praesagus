# PRSG-15 — Ticket verification runner

Type: feature · Modules: harness, docs · Owner: Lead · Priority: P1 · Effort: S (0.5–1.5 person-days) · Impact: high

## Accepted scope and rationale

User approved local implementation without new delegation. Lead implements; existing workstreams remain separate. Small offline CLI reuses validate_ticket, captures actual Git diff including index/untracked/deletion/rename endpoints, runs only approved argv/cwd, bounds commands and writes outside-repo JSON evidence. Manual review always remains manual. Scope and integration base frozen in sibling manifest after prior workstream commits; preparatory runner code was developed locally before that integration checkpoint. No claim of pre-write filesystem enforcement.

Value: repeatable evidence and fewer silently omitted paths; quality improvement is not yet measured. Non-goals: autonomous acceptance/self-training, full CI ticket dispatch, sandboxing, deployment or research-answer runtime.

## Interface, limitations and tests

See docs/TICKET_VERIFICATION.md. Exact baseline fingerprints are trusted Lead inputs, not proof of authorship. Ignored files excluded. Tests cover real temporary Git repos, staged-only changes, untracked/deleted/rename scope violations, baseline mutations, escaping symlinks, approved/unapproved commands, failed/mutating checks and manual-review rejection. CI explicitly replays regressions, not arbitrary ticket commands. Timeout is120 seconds; command outputs discarded, only digest/size retained. Completion updates canonical Markdown/JSON, not generated audit.

## When it's considered done

- [x] PRSG-15-D1: Actual Git scope and safe approved-check runner demonstrated; focused/full regressions pass, docs/CI and Lead review recorded.

## Delivery evidence

2026-10-01 MYT: focused runner suite15 passed; full python3 -m pytest -q189 passed with5 existing Python3.9/Boto3 warnings. Real PRSG-15 CLI artifact /tmp/PRSG-15-verification-reviewed.json SHA256 e2818b47583203b8eda772e68cb3878b4fa02ed2c58d57d042c4030a87b62460: all9 paths in scope, runner exit0, manual review required, worktree/HEAD unchanged. Artifact covers pre-acceptance manifest cfa61ac501134a6966d753c31124b3570035f9ffd3ea1f184acea580bfd7bd45, not this later evidence edit.

Lead independently reviewed9 allowed files, exact argv/cwd allowlist, index/worktree baseline hashing, no raw output retention, bounded process-group timeout and manual-check non-acceptance. CI only replays regressions; no automatic ticket dispatch or sandbox claimed. Existing PRSG-12/13 research remains review-pending. Functional delivery accepted; impact unmeasured.
