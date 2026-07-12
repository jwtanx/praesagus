---
name: skill-template
description: Template for a Praesagus skill. Use when adding new investment, research, or signal skills to ensure consistent metadata, activation guidance, inputs, outputs, and workflow structure.
license: MIT
compatibility: Works with Agent Skills-compatible environments; no special runtime required unless referenced scripts exist.
metadata:
  author: praesagus
  version: "1.0"
  category: skill-template
  tags: [template, skill, research, finance]
---

# Praesagus Skill Template

## Overview
Summarize the skill purpose, the domain it covers, and the type of problem it solves.

## Use when
- The user asks for ...
- The task requires ...
- The output must do ...

## Clarify first
Before executing, ask for any missing or ambiguous information:
- What is the exact decision or use case?
- What asset class, sector, region, or time horizon is in scope?
- Which inputs are required versus optional?
- What level of confidence is needed?

## Inputs
- Required inputs:
  - ...
- Optional inputs:
  - ...
- Data sources and expectations:
  - ...
- Assumptions and scope boundaries:
  - ...

## Outputs
Describe the expected deliverable and structure.
- Executive summary
- Key conclusions
- Supporting evidence and analysis
- Risks / downside factors
- Recommendation and suggested action
- Assumptions and caveats

## Workflow
1. Define the objective and decision context.
2. Collect and validate data.
3. Analyze the opportunity or risk.
4. Build the narrative and evidence.
5. Summarize recommendation, conviction, and horizon.
6. List assumptions and follow-up questions.

## Research rules
- Use reliable public sources and validate calculations.
- Do not fabricate numbers or precise metrics without supporting evidence.
- Clearly label assumptions and confidence levels.
- Treat model outputs as drafts unless verified.

## Output template
- Rating: Strong Buy / Buy / Accumulate / Hold / Reduce / Avoid
- Conviction: 1–10
- Time horizon: short-term / medium-term / long-term
- Primary drivers: ...
- Key risks: ...
- Recommended action: ...

## References
- Use `references/` for deeper guidance, examples, formulas, or data definitions.
- Use `scripts/` for reusable calculation tools or validation helpers.
- Keep `SKILL.md` focused; move lengthy reference material into supporting files.
