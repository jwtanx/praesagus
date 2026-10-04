---
name: praesagus-implementation
description: Implement accepted Lead decisions with Trader or temporary research evidence with a small, explicit plan and focused tests. Use for Praesagus engineering tasks; this guides delivery and does not implement the proposed answer runtime by itself.
license: MIT
metadata:
  author: praesagus
  version: "1.1"
  category: engineering
  tags: [implementation, testing, harness, praesagus]
---

# Praesagus Implementation

## Use when

- Trader, a temporary research subagent or Lead has supplied a report, decision, or scoped implementation task for this repository.
- A feature or fix needs a focused test harness as part of implementation.

## Workflow

1. Read the repository `AGENTS.md` and inspect the relevant code, tests, configuration, and report. Treat the Lead's decision as the scope and Trader and temporary research reports as supporting evidence; do not silently broaden either.
2. Summarize the decision as a short implementation plan: behavior to add or change, key constraints, and observable acceptance checks. Resolve routine details from the codebase. If a missing research or product decision materially affects correctness, identify the precise question and request financial clarification from Trader or scope clarification from Lead through the available workflow while continuing independent work.
3. Make the smallest coherent change using existing interfaces and dependencies. Preserve unrelated working-tree changes and existing behavior outside the accepted scope.
4. Add or update focused automated tests for each changed behavior. Prefer deterministic fixtures and mocked external services; tests must not need credentials, live data, or place orders. Cover the important rejection and failure paths for the feature, not just its happy path.
5. Run the narrow relevant checks. Run broader checks when the change spans components or the repository requires them. Report exact commands and outcomes; distinguish checks not run from checks that failed.
6. Review the final diff against the decision and acceptance checks. Update documentation only where implementation or operational guidance changed.

## Ticket harness reuse

When assigned a `PRSG-*` ticket, read its dated Markdown spec and sibling `.harness.json` before editing. Use the accepted allowed/protected paths and exact check commands; protected paths win. Do not widen scope or weaken checks silently. Record results/evidence as checks run, and tick the plan's matching completion IDs only when demonstrated. Leave Lead review unchecked until accepted. Run `scripts/planning/validate_ticket.py` on the manifest and every path in the complete ticket diff (both sides of renames, deletions and new files), accounting for unrelated existing changes separately. This is a review gate, not prevention of filesystem writes. Lead freezes scope and accepts completion; reuse this skill on subsequent engineering assignments and turn demonstrated failures into focused regressions.

## Harness boundaries

- In this skill, “harness” means the focused tests and repeatable validation around the changed feature unless the task explicitly asks to implement a runtime research harness.
- `harness/research_harness.yaml` is a design contract only. Do not describe its routing, traces, graders, or improvement loop as implemented unless code and tests establish that behavior.
- Build production harness/runtime components only when the Lead's decision includes them. Keep evaluation cases frozen and replayable where applicable; require human review for proposed prompt, skill, or model changes.

## Praesagus constraints

- Follow repository `AGENTS.md` for current architecture, data provenance, trading safeguards, and validation requirements.
- Do not claim integrations, freshness, persistence, model-backed answers, or operational cloud services without implementation evidence.
- Never add credentials or private user/account data to source, fixtures, logs, or test output.
- For investment, trading, portfolio, or event-analysis behavior, preserve decision-time information, uncertainty, disconfirming evidence, and the required action classification.
