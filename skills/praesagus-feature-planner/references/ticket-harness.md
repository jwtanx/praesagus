# Ticket harness contract

Read this when creating or resuming a Praesagus delivery ticket. Planning date uses Asia/Kuala_Lumpur. Markdown is the human specification; JSON is the machine-readable review contract. This is a Praesagus schema, not a vendor configuration format.

## Research informing the design (1 October 2026)

- [Anthropic: effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) uses a JSON feature ledger containing descriptions, verification steps and pass state, plus progress notes and incremental sessions. Adopt stable acceptance IDs and evidence updates. The article does not demonstrate a file-access ACL enforced by the JSON.
- [OpenAI: execution plans](https://developers.openai.com/cookbook/articles/codex_exec_plans) connects AGENTS.md to living plans with progress, decisions and concrete validation. Adopt a compact agent registry and dated, resumable ticket specifications. It does not prescribe a universal JSON ticket schema.
- [SWE-agent configuration](https://swe-agent.com/latest/config/) uses YAML configuration for agent/tools/environment. [OpenAI Symphony](https://github.com/openai/symphony/blob/main/SPEC.md) uses a WORKFLOW.md contract with YAML configuration and issue workspaces. These are possible later runtime patterns, not installed Praesagus services. Avoid adding their orchestration just to manage a five-ticket backlog.

## Quick-glance tags and routing

Put a `Type · Modules · Owner · Priority · Effort · Impact` line directly below every ticket heading. Keep matching machine-readable `tags` in JSON; the backlog index exposes the same values for sorting. Vocabulary:

| Tag | Values / meaning |
|---|---|
| type | `feature`, `bug`, `spike`, `refactor`, `chore`, `docs`, `test`, `skill` |
| modules | One or more: `backend`, `frontend`, `connectors`, `financial-data`, `market-research`, `alerting`, `observability`, `harness`, `skills`, `infra`, `docs` |
| owner_role | `Lead`, `Engineer`, `Researcher`, `Consultant`; one accountable owner |
| priority | `P0` current critical outage/security/data-loss issue; `P1` next committed work; `P2` planned; `P3` optional/later. Do not label speculative risk P0. |
| effort_size | `XS` under 0.5 day, `S` 0.5–2, `M` over 2–7, `L` over 7–15, `XL` over 15; pair with positive low/high person-day estimate. Split XL delivery before assignment. |
| impact | `low`, `medium`, `medium-high`, `high`; describe affected user/outcome and evidence confidence in the spec. Not a revenue/ROI calculation. |

A `bug` includes reproducible actual versus expected behavior, affected versions/environment, severity and a regression test. A `spike` includes one decision question, timebox, three strongest options where viable, source evidence, tradeoffs and a decision brief; completion means a reviewed answer, not a production feature. Use modules to select relevant expertise and a bounded write set; tags alone do not authorize edits or external activity.

Route research/provider/product/technical feasibility spikes to Researcher (`research-brief`); market interpretation/chart/news tasks and related skill extraction to Consultant (`daily-market-brief`, `technical-trend-analysis` and applicable orchestrator); backend/frontend/connector bugs or accepted implementations to Engineer (`praesagus-implementation`); prioritization, planning/docs and integration decisions to Lead (planner/project-lead). For mixed tickets choose one owner and define separate dependent assignments with disjoint write scopes. Do not assign the same path to two concurrent owners.

Use `schema_version: 1`, `ticket_key`, `tags`, `created_on`, `timezone`, `spec_path`, `objective`, `status`, `owner`, `reviewer`, `scope_status`, `base_sha`, `allowed_paths`, `protected_paths`, `checks`, `acceptance`, and `review`. States: planned/in_progress/review/complete/blocked. Scope: provisional/accepted. Active implementation needs accepted scope and a resolved 40-character Git base SHA; planned tickets may have null base.

Paths are repository-relative exact files or trailing `/` directory prefixes. No globs, absolute paths, backslashes, dot segments or parent traversal. Directory prefixes match segment boundaries; `backend/` does not match `backend-other/`. Scope describes the Engineer write set, including exact ticket metadata files; Lead-only global docs/skills stay protected. Resolve symlinks before evaluating writes. Explicitly include new tests and both source/destination paths for a rename. Protected matches override allowed matches.

`checks` entries contain stable `id`, `kind` (command/manual), argv array plus cwd for commands, status (pending/passed/failed), and evidence strings. Commands are descriptions to run under normal task authorization, never automatically executed by the validator. Evidence records exact command/result/time/code revision and a repository artifact or trusted run URL; manual checks describe observed behavior and reviewer. Do not put secrets in commands or evidence. Future test paths are proposals until the ticket is accepted.

`acceptance` entries contain checklist `id`, description, check_ids, status (pending/done), and evidence strings. Every referenced check must exist. Done entries need passed checks and evidence. A complete ticket requires all acceptance items done and `review.status: accepted` with reviewer evidence. Acceptance evidence is recorded metadata, not proof by itself; Lead independently inspects logs/diff and records limitations. UI builds do not prove usability; skill schema validation does not prove research correctness.

## Working loop

Commit progress checkpoints in the dated spec and manifest; all relevant status/checklist/check/review evidence changes must be committed to enter the audit. At completion synchronize done checkboxes, passed checks/evidence and accepted Lead review before the delivery commit. Run `python3 scripts/planning/build_ticket_audit.py` after committing to inspect the resulting commit links and completion snapshot. Pages generates `artifacts/tickets/audit.json` from full first-parent Git history on every main push; do not commit generated audit JSON or manually insert a commit's own unknown hash. `/tickets/` provides search/filter/sort/history and CSV export; JSON/Git preserve nested audit evidence, while CSV is only a flat export. Uncommitted progress is not recorded. A PRSG delivery commit does not by itself close a ticket; retained historical snapshots are review evidence, not proof that tests or deployment succeeded. Preserve source history and never remove failed checkpoints to improve apparent results.

1. Inspect existing changes and allocate the next unused PRSG key globally. Keep creation folder stable across sessions. Freeze an accepted base and small scope; record dirty-work ownership separately in the handoff.
2. Delegate spec + manifest + relevant role skill. Agents update only permitted progress/evidence; changes to acceptance definitions, file scope, checks or base require Lead review. Do not relax gates just to pass.
3. Run meaningful tests/manual fixtures. Record pass/failure with provenance; leave unrun checks pending. Synchronize Markdown checkboxes and acceptance IDs in the same update.
4. Run `python3 scripts/planning/validate_ticket.py MANIFEST`. Also pass every reviewed changed path via repeated `--changed-file PATH`. The checker detects scope violations for those supplied paths and symlink escapes; it does not enumerate Git changes or verify that the list is complete. Lead checks tracked/untracked/deleted/renamed files against the base and separates unrelated pre-existing edits. Use an isolated checkout if overlap cannot be resolved.
5. For skill changes, run skill-creator quick_validate plus one relevant frozen behavioral case: invalid data, temporal leakage, correlated evidence, unsupported claims or workflow failures. Preserve expected outcomes and evidence; do not autonomously promote prompt/model changes.
6. Lead reviews diff and results, accepts completion, and records release evidence. Pending provider connectivity or user-impact measurement stays explicit, even if functional delivery passes.

The manifest/checker are an offline review gate. They neither intercept writes nor load/enforce `harness/research_harness.yaml`. Prevention would require separate filesystem permissions/tool mediation covering shell writes; that is outside this planning change.
