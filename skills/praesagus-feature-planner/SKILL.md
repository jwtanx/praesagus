---
name: praesagus-feature-planner
description: Turn Praesagus feature ideas into an evidence-backed priority decision and measurable MVP plan. Use when comparing opportunities, estimating impact and feasibility, or deciding what to build next; not for implementing an already-approved scope.
license: MIT
metadata:
  author: praesagus
  version: "1.0"
  category: product-planning
  tags: [prioritization, feature-planning, roi, product]
---

# Praesagus Feature Planner

## Purpose

Help the project Lead choose a small number of valuable product bets from the actual needs, evidence, architecture, and constraints of this repository. Produce a decision-ready proposal, not a speculative roadmap or an implementation claim.

## Workflow

1. **Frame the decision.** Identify the target user, unmet job, decision to make, time horizon, and constraints. State assumptions when missing information does not change the comparison; ask only for information that materially changes the recommendation.
2. **Establish the baseline.** Read `AGENTS.md`, relevant README/docs, code, tests, configuration, and current working-tree state. Separate implemented capabilities from planned work. Note existing services, skills, APIs, dependencies, operational gaps, and unfinished changes that affect the proposal.
3. **Define measurable value.** Choose an outcome metric before proposing a solution: for example, time-to-answer, qualified adoption, paid conversion, evidence coverage, alert lead time, error rate, or operating cost. Establish a baseline if data exists. Do not invent revenue, user demand, cost savings, or accuracy lift.
4. **Research material unknowns.** Use primary and current sources where facts may have changed. Delegate a bounded evidence-gathering brief to the Researcher when external product, API, market, licensing, or cost research is needed. Label facts, inference, assumptions, and unresolved questions separately.
5. **Build a short, comparable shortlist.** Include only credible options. Compare expected impact, ease/time-to-proof, engineering and operating cost, dependencies, reversibility, evidence confidence, and safety/compliance risk using consistent criteria. A score may organize discussion, but is not an ROI calculation unless supported by real inputs.
6. **Recommend one wedge.** Prefer the smallest reversible feature that tests the highest-value assumption quickly. Explain why it wins, what should not be built yet, and the evidence that would change the decision. If evidence is insufficient to rank options, recommend the cheapest discriminating experiment rather than false precision.
7. **Define the delivery boundary.** Specify target user and workflow, in-scope behavior, explicit non-goals, data/source requirements, provenance and freshness, UI/API/storage touchpoints, acceptance criteria, test coverage, rollout/measurement plan, dependencies, risks, and a stop/continue threshold.
8. **Hand off for decision.** Present the recommendation and evidence to the Lead. An opportunity brief is not authorization to implement, spend, publish, deploy, or make a financial recommendation. Implementation starts only after the user or Lead accepts the scope.

## Project-specific constraints

- Treat `harness/research_harness.yaml` as design-only unless runtime code and tests demonstrate otherwise. Skills do not themselves provide an agent runtime.
- Prefer staged validation: prototype the riskiest assumption, then evaluate the smallest end-to-end user path before expanding.
- For financial research features, preserve source, publication/retrieval times, decision-time availability, uncertainty, disconfirming evidence, and market-data rights. Moomoo inputs are not independent confirmation or investment advice.
- Do not propose live trading or order execution as an MVP without explicit user direction, provider/legal review, human approval, and independent risk controls.
- Preserve existing local changes. Do not turn unrelated cleanup into a prerequisite for a focused feature proposal.

## Decision brief

Use a concise format suited to the question, normally:

- **Decision and recommendation** — one selected opportunity, or a bounded experiment if evidence is weak.
- **Target and problem** — user, job, and current friction.
- **Evidence and assumptions** — linked evidence; distinguish observed facts from estimates and inference.
- **Alternatives and tradeoffs** — shared criteria and why the selected option wins.
- **MVP boundary** — in scope, non-goals, key interfaces, and acceptance checks.
- **Value test** — baseline, metric, measurement window, and continue/stop threshold.
- **Risks, dependencies, and unknowns** — include the next cheapest check.
- **Lead decision required** — explicit approval or unresolved choice, if any.

For a downstream Engineer, provide an accepted scope and testable criteria; use `skills/praesagus-implementation/SKILL.md` when that skill is available.
