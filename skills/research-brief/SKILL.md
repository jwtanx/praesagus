---
name: research-brief
description: Research a question for a coordinating Lead; compare the three strongest options with evidence-linked tradeoffs and hand back findings without making the final decision. Use for requests to investigate choices, approaches, tools, providers, or implementation paths.
license: MIT
metadata:
  author: praesagus
  version: "1.0"
  category: research
  tags: [research, comparison, evidence, handoff]
---

# Research Brief

## Purpose

Produce a source-backed brief that helps a Lead make a decision or route follow-up work to another session, such as an Engineer. The Lead owns the final decision. Keep the research scoped to the question and requested depth.

## Workflow

1. Restate the research question, decision context, constraints, and what the Lead needs to decide. Resolve only ambiguities that would materially change the comparison; otherwise state reasonable assumptions.
2. Gather current, relevant evidence. Browse when facts may have changed, the question is niche or uncertain, or links and precise sourcing are useful. Prefer primary sources; for technical questions, rely on official documentation or primary research. Use secondary sources to add context and label them accordingly.
3. Identify and compare the three strongest viable options against the same decision criteria. If fewer than three are genuinely viable, say so instead of padding the list. Distinguish evidence from inference, and call out material gaps, conflicts, and assumptions.
4. Explain the tradeoffs and why each option makes the shortlist. Where evidence supports it, compare cost, capability, effort, risk, dependencies, reversibility, and fit to the stated constraints. Avoid false precision.
5. Return the findings to the Lead in the current conversation. Do not make the final choice on the Lead's behalf or message another session unless explicitly authorized.

## Deliverable

Use a concise structure suited to the question, normally including:

- **Question and scope** — decision context, constraints, and assumptions.
- **Finding** — the central research result in a few sentences.
- **Top options** — up to three, with evidence-backed strengths, weaknesses, fit, and source links.
- **Tradeoff and rationale** — compare options using shared criteria; make any conditional preference explicit and explain what it depends on.
- **Unknowns and next checks** — evidence that could change the comparison or needs validation.
- **Lead handoff** — the decision needed and, when useful, a concrete next task for an Engineer or other session, including relevant interface, dependency, or validation questions.

Link sources next to the claims they support, using direct URLs to the underlying source rather than search result pages. Include publication or update dates when relevant. Keep the source list short and useful; do not cite unsupported claims as established facts.

## Boundaries

- A ranked shortlist is research input, not approval to implement, purchase, publish, trade, or deploy.
- Do not invent options, costs, benchmarks, capabilities, or source support. Label estimates and inference.
- Report uncertainty and disconfirming evidence, not only evidence for the leading option.
- For investment, trading, portfolio, or event analysis, also follow `praesagus-trading-orchestrator` and `skill-template`; this skill does not replace their evidence and risk requirements.
