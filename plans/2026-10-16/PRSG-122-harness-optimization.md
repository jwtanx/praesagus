# PRSG-122 — Harness Optimization

Type: refactor · Owner: Lead · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high — reduce repeated context and unnecessary coordination while preserving evidence and acceptance.

Created 2026-10-16 MYT.

## Why the ticket is created?

The human requested an audit and in-place optimization of the four-role harness: minimal tokens, reliable continuation, concise context and accurate tickets. Existing instructions repeat routing, recovery and continuation across startup, skills, schedules and private notes.

## Approach

Audit before edits; keep existing ticket manifests, verification tools and app dispatch. Consolidate operating instructions, request the supported per-role model defaults, make task loading selective, preserve compact private continuity and shorten existing Lead schedule prompts without changing ownership, cadence or human pauses. Use current tool completion snapshots; do not introduce a runtime, database, dashboard or scheduler.

## Choices

Canonical dated harness manifests remain the ticket registry and matching Markdown holds specification/evidence; generated audit remains derived. New independent work uses a fresh minimal session at a verified safe boundary when explicitly authorized and supported; unfinished same-ticket work continues. At most two workers, only necessary specialists. No instruction can clear an existing chat context or turn an AI heartbeat into a no-AI timer.

## Findings

Baseline: AGENTS21093bytes, Leadskill18221bytes, projectlead6411bytes, Leadcoordinationprompt6897bytes. Four private continuity files total141927bytes and292top-level private records exist. Read-only model metadata exposes gpt-6.1-sol with low/medium and gpt-6-luna/low. App dispatch/completion tools have succeeded in actual project work; no deterministic background dispatch/completion adapter is installed. Historical compaction and per-ticket token attribution are unavailable; do not invent savings measurements.

## Tradeoffs

Keep privacy, provider provenance, financial/model gates, frozen scope, dirty ownership, exact recovery and independent delivery review. Archive superseded private notes before replacing them with a current snapshot and pointers. Preserve unfinished forecast/news work and Trader schedules. Models/configuration are requested defaults until applied and observed; user authorization does not bypass tool permissions.

## Frozen Scope

Base1c992de8676203aa4d47bea275bbd86c894fcead. Lead owns only declared instruction/configuration/reference/test and this ticket paths. No forecast, report, provider, application, hook or ticket-history changes. Existing unrelated edits remain protected. App-only changes limited to compacting the two verified Lead schedule prompts with original status/cadence/target intact; record exact private backups/readback. No new recurring schedules or agents are required for this audit.

## When it's considered done

- [x] PRSG-122-D1: Audit classifications, supported model defaults and concise role/skill/session contracts reviewed.
- [x] PRSG-122-D2: Existing Lead prompts/private continuity compacted with backups, actual tool capability boundaries and pauses preserved.
- [x] PRSG-122-D3: Focused regressions, references, behavioral continuity/dispatch evidence, size measurements and scoped delivery verified.

## Reviewed evidence

Lead focused regression command: `/Users/jwtan/.codex/venvs/praesagus-tests-311/bin/python -m pytest -q tests/test_spawn_routing.py tests/test_lead_status.py tests/test_ticket_brief_quality.py tests/test_ai_engineer_role.py`: **131 passed in 0.21s**. Existing resource cases cover stale/unknown usage, weekly constraints and battery precedence. Changed Markdown local links, skill metadata, all declared paths, JSON and unrelated-file hashes checked. Engineer independently reviewed instructions read-only with no blocking findings; app dispatch accepted requested gpt-6.1-sol/medium and bounded completion detection verified the returned review. This does not independently observe all running models.

Manual continuity replay preserved completed tickets, unfinished same-ticket work, busy-owner protection, returned-review acceptance, human amendments and denied-dispatch boundaries. Missing-state/timeout behavior is an instruction replay, not a newly installed autonomous runtime. No fresh sessions were created; clearing existing chat history or unattended deterministic dispatch is not implemented.

Same 14 measured instruction/configuration files: **86,266 → 58,377 UTF-8 bytes** (32.3% reduction). Lead coordination prompt **6,897 → 1,188**, daily prompt **1,263 → 780**; actual tool update and local readback preserve IDs/names/targets/cadences/PAUSED statuses. Trader configuration is identical. Four private hot continuity files **141,927 → 6,256 bytes**, with exact originals/hashes retained privately and one current snapshot. Byte reductions do not establish token/cost savings; historical compaction frequency and per-ticket usage are unavailable.

Private audit/backup/readback receipts remain outside Git. Existing forecast and sentiment obligations, seven unrelated dirty paths, ticket IDs/history, resource recovery and model/data acceptance gates remain preserved. No provider calls, training, app runtime, hook or scheduler replacement was performed. Lead resource restoration, if eligible, is a separate standing-authorized operation; prompt changes themselves preserve status.

Full pre-commit gate initially found one stale unset-default expectation (2,720 other checks passed); updated that existing role/schedule contract to the approved defaults and removed the redundant added test. Focused rerun: 131 passed in 0.21s. Mandatory full hooks rerun before commit/push.
