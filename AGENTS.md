# Praesagus Agent Guidance

Repository-wide source of agent instructions; nearer AGENTS.md files may add scope. Keep this file accurate and concise. Load detailed instructions only for the active task.

## Implemented behavior

Praesagus has FastAPI services (`backend/`), Vite/React (`frontend/`), connectors/settings (`connectors/`, `ingest/config/`), financial scripts (`scripts/`), and local Compose/LocalStack/Terraform scaffolding (`infra/`). Documentation or Terraform does not prove deployment.

- `harness/forecast_review.py`: deterministic CSV validation/outcome scoring at an explicit review timestamp; not answer generation.
- `harness/catalyst_replay.py`: authored in-memory temporal/revision/fold replay; not provider ingestion, causal proof, training or prediction scoring.
- `artifacts/daily-market-brief/`: schema-2 reports and schema-3 five-name cross-market shortlists. Monthly calendar: `artifacts/financial-calendar/YYYY-MM.json`; `scripts/daily-market-brief/monthly_calendar.py` initializes/appends complete revisions and does not schedule itself.
- `scripts/stock-research/`: bounded collection, explicit chronological numerical training, saved-model inference/evaluation and immutable CSV/XLSX exports. `run.py` shares one generation across stages; `demo.py` uses fictional data without providers/training. Source coverage, model promotion and forecast quality are separate gates.
- Read-only `connectors/moomoo_opend.py` and `/api/v1/moomoo/news`/`quotes`: request/response news and quote snapshots. No persistent ingestion, continuous push or model-backed analysis. OpenD runs separately at configured host/port (native127.0.0.1:11111; Compose host gateway), with entitlements. News limit10calls/30seconds is process-local; quote subscriptions are request-scoped, not continuous streams or distributed quota coordination.

There is no hosted LLM answer path, general agent runtime, persistent answer trace or runtime-enforced answer-quality loop. `harness/research_harness.yaml` is an unloaded future contract. Label roadmap and synthetic evidence accordingly. Use implementation/tests as evidence; never infer operation from configuration.

## Work and delivery

Inspect relevant implementation/tests; preserve unrelated dirty files and source provenance. Prefer existing interfaces/dependencies and documented APIs. Respect authentication, rights and quotas. Keep failures bounded/visible; validate malformed/missing/future/stale data, duplicates, upstream/rate-limit failures and rejection paths. Never put credentials, tokens, private account/user data or generated secrets in source, fixtures, logs or commits.

Commit titles: `PRSG-<number> <description>`; retain the dash, reserve PRSG-0 for shared workflow infrastructure. Exception: nonempty staged changes entirely within `artifacts/daily-market-brief/` use `[REPORT] YYYYMMDD` with valid date and optional description. Mixed/empty commits, monthly-calendar edits and renames crossing that boundary require PRSG-N. Reports remain tracked. Install versioned hooks once per checkout with `sh scripts/install_git_hooks.sh`; use Python>=3.11/pytest via `praesagus.testPython` ([setup](docs/TEST_HOOKS.md)). Hooks can be bypassed; Lead independently reviews title, scope and evidence before push.

Run focused checks first and broader checks when scope or hooks require them. Don't rerun unchanged passed suites merely to manufacture progress; required commit/push hooks still run. Report exact results, including failures/not-run checks. Never weaken tests just to pass. Distinguish implemented, reviewed, committed, pushed and deployed.

## Roles, context and skills

Configured roles/defaults: [agent-operations/roles.json](agent-operations/roles.json). Lead owns scope/architecture/prioritization/review/integration; Engineer coding/debugging/tests/CI and supporting ingestion/storage/CLI/export; AI Engineer AI/LLM integration, prompts/evaluation/performance plus datasets/numerical models/calibration/artifacts/inference/sentiment; Trader relevant domain judgment/financial reporting. Historical Researcher/Consultant ownership remains unchanged. Unrelated Designer ownership stays intact.

Requested defaults use supported `gpt-6.1-sol`: Lead low, Engineer medium, AI Engineer low (medium for complex work), Trader medium. `gpt-6-luna`/low may handle bounded routine research. Verify current host support before applying; configuration is not runtime proof. Invoke only required roles, normally at most two workers. Don't wake all peers for a single-role ticket.

Read only the assigned role's [startup prompt](agent-operations/README.md). Start independent tickets/runs with minimal fresh context at a verified safe boundary when supported/authorized; continue useful unfinished same-ticket work. No timed resets, full-history transfer or automatic reopening of completed tickets. See [delivery/session workflow](docs/LEAD_WORKFLOW.md).

| Need | Load |
|---|---|
| New prioritization/specification | [feature planner](skills/praesagus-feature-planner/SKILL.md) |
| Material coordination/review | [project lead](skills/praesagus-project-lead/SKILL.md) |
| Lead resources/schedules | [Lead control](skills/lead/SKILL.md) |
| Accepted implementation | [implementation](skills/praesagus-implementation/SKILL.md) |
| Model/dataset/AI work | [AI Engineer](skills/ai-engineer/SKILL.md) |
| Financial reporting/interpretation | [daily brief](skills/daily-market-brief/SKILL.md), [trading orchestrator](skills/praesagus-trading-orchestrator/SKILL.md), relevant technical/Moomoo specialists |
| Bounded evidence research | [research brief](skills/research-brief/SKILL.md) |

Shared evidence rules live in [skill-template](skills/skill-template/SKILL.md). Skills are instructions, not executable agents or runtime enforcement. Skill changes require metadata/reference checks and a relevant behavioral replay; a validator alone does not prove quality. Human review remains required before model/prompt/risk-policy promotion.

`$spawn` or `/spawn lead|trader|engineer|ai-engineer|all` uses [spawn](skills/spawn/SKILL.md); aliases ai_engineer/ai engineer are canonical AI Engineer. Normal single-role requests adopt the caller; explicit fresh-role requests create one held destination, and all creates one per configured role. Explicit destination/no-context instructions prevail. Role config alone creates nothing. Verify private registration, readiness, idle ownership and unique schedules before release/retirement. Preserve human pauses and unfinished edits; don't archive busy chats. Active IDs, checkpoints and transaction receipts stay outside Git.

## Authoritative tickets and continuity

Dated `plans/YYYY-MM-DD/PRSG-N.harness.json` manifests are the ticket registry; matching `PRSG-N-title.md` contains the specification and reviewed evidence. IDs are globally unique, dates MYT. Preserve history and completed states; reopen only for new requirements, failed acceptance or a verified regression. Inspect a compact active-ticket/dependency view first; read full history only for an inconsistency. Private continuity stores pointers, durable decisions, ownership and exact next action, not a second ticket registry or copied logs.

Freeze owner, objective, dependencies, accepted/protected paths, base SHA, checks and outputs before implementation. One owner per ticket; mixed-role writes must be disjoint. Tags: type(feature/bug/spike/refactor/chore/docs/test/skill), modules, owner, P0(actual incident)/P1(next committed)/P2(planned)/P3(later), effortXS<0.5/S0.5–2/M>2–7/L>7–15/XL>15 person-days and rationale-backed impact. Stable checklist IDs/status/evidence must agree between Markdown and JSON. Research/spikes do not authorize implementation; bugs need reproduction/expected behavior/regressions, spikes need timebox/question/sources/tradeoffs/findings.

Use `scripts/planning/validate_ticket.py` for the manifest and every changed path, including new/deleted files and both rename endpoints. Protected paths win; account separately for unrelated baseline edits. This checker validates supplied paths/evidence, not complete diff discovery or filesystem enforcement. Lead independently accepts completion.

`scripts/planning/verify_ticket.py` checks actual Git scope against frozen manifests and executes only exact argv/cwd pairs allowed by `harness/verification_policy.json`; evidence stays outside Git and manual checks remain review-required ([contract](docs/TICKET_VERIFICATION.md)). CI replays runner regressions, not automatic dispatch of every ticket.

`scripts/planning/build_ticket_audit.py` derives `artifacts/tickets/audit.json` from full first-parent Git history on main pushes; generated JSON is untracked. `/tickets/` is read-only search/filter/sort/timeline/CSV. Canonical specs/manifests/Git outrank a stale generated view. Harness filenames must be exactly PRSG-N.harness.json; the commit-msg hook checks staged filename/JSON/ticket_key, including rename destinations, before title validation.

## Financial and data safeguards

Preserve source URL/provider, publication/retrieval/availability/ingestion time, timezone, period, connector and revisions. Keep facts separate from interpretation. Prefer primary disclosures/regulators/exchanges/official statistics; label secondary/vendor/proxy/social, missing or stale evidence. Deduplicate syndicated/correlated evidence. No later information may justify an earlier signal; keep forecasts immutable and score realized outcomes separately. Never infer predictive performance, source readiness or deployment from tests.

News, sentiment, anomalies, flows and derivatives are ambiguous inputs. Check liquidity/context/events/already-priced-in effects, bull/bear/disconfirming evidence and measurable invalidation. Missing required evidence lowers confidence or yields NO TRADE. Sneaky Pivot is an unvalidated hypothesis until formal rules, costs/fills, regime/event/risk filters and robust out-of-sample evidence exist. Preserve skill vocabulary: research only/watchlist/paper trade/human approval required/execution-ready/NO TRADE. Live trades need explicit human authority and independent risk checks; the repository does not execute trades by implication. No new direction, paid access or external-party contact without applicable authority.

For daily reports reuse the daily-brief skill and normal dated schema-3 dashboard flow. Map available allowlisted Moomoo price-only points via `ingest.daily_report_projection.map_public_snapshot`, retaining observation/source/ingestion/known/cutoff times and explicit unknown references. No raw capture, private IDs/account details/full responses in public output; don't substitute the private-draft runner. Use five curated names/group, confidence+rationale, null/Unrated unsupported targets. Reuse the monthly calendar; append source-backed correction/cancellation revisions, never erase prior events or infer cancellation from absence. Render superseded/cancelled entries struck through with justification. Workflow instructions do not provision schedulers.

Future answer-harness improvements require frozen replayable evaluation sets, independent graders/human review and measured quality/calibration/latency/cost. Don't enable autonomous production self-training/self-editing. Roadmap includes persistent deduplicated OpenD ingestion, an evidence-backed research harness and improved SEC/QR/alerts/health/feature-store/deployment workflows; claim each only when implemented and verified.
