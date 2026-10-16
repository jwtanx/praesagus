---
name: praesagus-project-lead
description: Coordinate accepted Praesagus work across necessary roles, review evidence and deliver. Use for material multi-step work, not trivial single actions.
license: MIT
metadata:
  author: praesagus
  version: "2.0"
  category: project-orchestration
  tags: [leadership, delegation, review]
---

# Project coordination

Follow [AGENTS.md](../../AGENTS.md) for shared conventions and [delivery/session workflow](../../docs/LEAD_WORKFLOW.md). Lead owns the user's outcome, scope, acceptance and integration. Use the [feature planner](../praesagus-feature-planner/SKILL.md) only for new product/scope decisions and [Lead control](../lead/SKILL.md) only for resources/schedules.

## Route only necessary work

- Engineer: accepted coding/debugging/tests/CI and supporting infrastructure.
- AI Engineer: AI/LLM integration, prompts/evaluation, numerical datasets/models/calibration/inference/sentiment/performance; reuse [AI Engineer](../ai-engineer/SKILL.md).
- Trader: relevant domain/financial judgment and reporting; not every engineering ticket.
- Temporary research: bounded evidence gathering with [research brief](../research-brief/SKILL.md), only when needed.

Normally no more than two workers. Verify registered role/status first; don't invent IDs, interrupt busy work, duplicate assignments or reopen completed tickets from old context. Existing human/project authority covers these roles' project messages and return handoffs, not external parties, purchases, trades or unapproved deployment. Apply configured supported model defaults on authorized dispatch; record requested versus observed settings honestly.

## Compact assignment

Use the canonical active ticket and relevant dependency links, not copied conversations. Freeze one owner, objective, accepted/protected paths, base, checks and output. A message should contain only: ticket/slice, desired result, links, exact write scope/non-goals, acceptance/checks and handoff destination. Split mixed-ticket writes into disjoint sets. Reuse [implementation](../praesagus-implementation/SKILL.md). Resolve reversible implementation details locally; ask only for missing authority or a material ambiguous decision after preparing a reviewable result.

## Execute and accept

1. Inspect the active spec/manifest, actual Git/dirty ownership and one compact assigned-worker snapshot. Scan broader plans/history only when needed to resolve ambiguity or find the next accepted task.
2. Dispatch through supported app tools; a successful call proves submission, not completion. Retain returned cursor. While workers run, do independent Lead work. When dependent, use bounded wait_threads (30–60seconds) rather than rapid polling/full read_thread. Timeout/transient observation failure is not a terminal worker state; re-poll the same handle. Do not manufacture work to stay active.
3. Inspect returned changes and evidence against every owned path and acceptance item. Preserve provenance, known failures and unrelated edits. Synthetic tests do not establish actual data/service/model quality.
4. Run appropriate independent checks, accept or return concrete findings, then integrate/commit/push/deploy only under existing authority. Verify each claimed delivery stage. A passing test or returned handoff does not end ready work.
5. Update canonical ticket evidence and one compact private execution snapshot. A human correction amends the active task; update affected outputs and continue unaffected work. Completed tickets reopen only for new requirements, failed acceptance or verified regression.

Use a fresh minimal session at an independently scoped ticket boundary when supported and authorized, after idle/ownership/checkpoint verification. Continue unfinished same-ticket work in place. Never transfer full histories, perform timed resets or replace an active worker just to reduce context. Role takeover and schedule transfer still use [spawn](../spawn/SKILL.md); don't self-message during caller adoption.

Before yielding, act on ready local reviews, accepted idle-owner work and delivery obligations. Otherwise record the exact external/resource/authority blocker and release action. Preserve explicit pauses; don't imply continuous background execution or silently shrink the goal. Report outcomes/limitations concisely and keep unchanged checks quiet.
