---
name: praesagus-feature-planner
description: Turn Praesagus feature ideas or competitor scans into an evidence-backed ranked ticket shortlist and measurable MVP plan. Use when asked what to build next, for new feature opportunities, or to benchmark successful comparable products; not for implementing an already-approved scope.
license: MIT
metadata:
  author: praesagus
  version: "1.2"
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
4. **Research material unknowns.** Use primary and current sources where facts may have changed. Delegate a bounded evidence-gathering brief to the temporary research subagent when external product, API, market, licensing, or cost research is needed. Label facts, inference, assumptions, and unresolved questions separately.
5. **Build a short, comparable shortlist.** Include only credible options. Compare expected impact, ease/time-to-proof, engineering and operating cost, dependencies, reversibility, evidence confidence, and safety/compliance risk using consistent criteria. A score may organize discussion, but is not an ROI calculation unless supported by real inputs.
6. **Recommend one wedge.** Prefer the smallest reversible feature that tests the highest-value assumption quickly. Explain why it wins, what should not be built yet, and the evidence that would change the decision. If evidence is insufficient to rank options, recommend the cheapest discriminating experiment rather than false precision.
7. **Define the delivery boundary.** Specify target user and workflow, in-scope behavior, explicit non-goals, data/source requirements, provenance and freshness, UI/API/storage touchpoints, acceptance criteria, test coverage, rollout/measurement plan, dependencies, risks, and a stop/continue threshold.
8. **Hand off for decision.** Present the recommendation and evidence to the Lead. An opportunity brief is not authorization to implement, spend, publish, deploy, or make a financial recommendation. Implementation starts only after the user or Lead accepts the scope.

## Dated tickets and delivery harness

For a delivery plan, read [references/ticket-harness.md](references/ticket-harness.md). Create `plans/YYYY-MM-DD/PRSG-N-title.md` and the matching `PRSG-N.harness.json`, using the MYT planning date and next unused global ticket number. Preserve original ticket keys/dates on resumption. Include detailed scope/interfaces, effort/impact assumptions, and a "When it's considered done" checklist with stable IDs mapped to JSON acceptance items.

Freeze accepted write scope, protected paths, base SHA, checks and owners before delegation. Reuse the assigned role's existing skill from the AGENTS.md registry. Update progress/evidence incrementally; the Lead reviews scope changes and completion. Validate the manifest and complete ticket change set with the referenced checker. JSON is a review contract, not a filesystem sandbox; do not claim runtime-enforced file restrictions or automatic test execution. Existing user authorization to let Lead choose/build remains effective.

Give every ticket quick-glance type/module/owner/priority/effort/impact tags using the reference vocabulary and matching JSON fields. Route feasibility spikes to Lead/Engineer with temporary research help or Trader for market interpretation; code bugs and accepted implementation to Engineer; planning/integration to Lead. Bugs need reproduction and regression criteria; spikes need a timeboxed decision question and reviewed findings. Choose one owner for mixed work and delegate disjoint scopes.

## Competitor scan and top-five ticket mode

Use this mode when the user asks what new feature to work on, requests competitive research, or asks for a feature shortlist. Keep it inside this skill; do not create a separate overlapping planner skill.

1. Ask temporary research subagent for a read-only, evidence-linked scan of 5–8 comparable products and their important user workflows. Cover direct and adjacent products only where their workflow is relevant to Praesagus. Prefer primary product documentation and credible public adoption evidence. Separate company-reported claims from independently corroborated evidence; if traction is not public, say so. Popularity, funding, longevity, and product quality are not interchangeable with profitability or customer value.
2. Compare observed workflows with the actual checked-in Praesagus baseline. Identify what exists, what is incomplete, and what is only proposed. Use competitor behavior as a source of hypotheses, not proof that Praesagus users want a feature; avoid cloning without a user/problem fit argument.
3. Return exactly five ranked candidate tickets when evidence supports five; if fewer are defensible, explain why rather than padding. Rank on expected user value, feasibility, time-to-proof, evidence confidence, dependencies, ongoing cost, and risk. Do not label a subjective score as ROI or invent revenue/adoption estimates.
4. For every candidate, provide: ticket title; target user problem and outcome; supporting product/evidence links; impact and feasibility rationale; estimated effort (S/M/L, explicitly an estimate); dependencies; testable acceptance criteria; one measurable success metric (include baseline/measurement window if known); and key risk or open question.
5. Recommend the smallest high-value experiment where justified, but leave selection to the user. Do not create issue-tracker tickets, modify implementation, or start spending/deployment until the user selects and authorizes the scope.

This workflow is available on demand through prompts such as “what should we build next?”, “find new feature opportunities”, or “run a competitor scan and rank five tickets.” For recurring scans, create or update an app automation only when the user explicitly requests a cadence; preserve their notification intent and keep unchanged runs quiet. A request to make this skill reusable is not itself authorization to schedule it.

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

For competitor-scan mode, include a compact product/workflow comparison and the five ticket cards described above, then end with the explicit user choice needed. Keep citations adjacent to claims and link directly to the underlying source.
