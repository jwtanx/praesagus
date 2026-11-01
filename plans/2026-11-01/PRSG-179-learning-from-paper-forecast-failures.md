# PRSG-179 — Encourage Auditable Paper Forecast Experiments

Type · Modules · Owner · Priority · Effort · Impact: docs · docs, market-research, harness · Lead · P1 · XS (0.25–0.5 person-day) · medium-high for reducing repeated planning without sacrificing evidence quality.

## Objective

Make the shared role guidance encourage small, permitted research forecasts and honest learning from forecast errors while preserving abstention for missing, stale, invalid or unauthorized inputs.

## User need and evidence

The user explicitly wants a full-universe report, visible confidence, daily comparison and learning from misses rather than indefinite 0/50 rated coverage. The latest saved public report is 0/50 rated; current canonical work already covers fixed-50 per-ticker research scenarios (PRSG-124), stronger model evaluation (PRSG-113), and public eligibility/recovery (PRSG-138). This ticket changes shared decision guidance only; it does not claim those implementation gates have passed.

## Approach

Add a concise repo-wide instruction for all roles to attempt the smallest falsifiable paper forecast when valid evidence, permitted use and accepted scope exist. Require dated immutable forecast cohorts, explicit uncertainty, comparable matured outcomes, chronological evaluation and preserved misses. Keep unsupported cases visible with a reason and next check.

## Choices

Permit a low-confidence experimental direction only when a method actually computes from valid inputs. Separate it from supported public output and execution-ready decisions. A complete coverage denominator means every name has a state; it does not mean every name must receive a directional label. Existing PRSG-124/113/138 remain the implementation owners.

## Findings

The latest saved public report is dated 21 October 2026 and contains 0/50 rated rows. Fixed-50 research plumbing exists, but actual public inputs/use eligibility and model-quality gates remain distinct. The direct unmet need here is shared role guidance against indefinite discussion, not another predictor implementation ticket.

## Tradeoffs

More paper attempts can reveal model failures sooner, but weak or poorly separated experimental output can be mistaken for a tradable signal. Clear labeling, frozen vintages, immutable scoring, chronological evaluation and human promotion review reduce that risk. Stale, missing or unauthorized inputs still require abstention.

## Guardrails

Add one concise repo-wide instruction applying to all roles: attempt the smallest falsifiable forecast when data/use rights and accepted scope permit; preserve immutable forecast cohorts and comparable matured outcomes; report losses, unresolved outcomes and coverage against baselines; test revisions chronologically. A valid but weak experimental output may appear only as distinct paper research with a low or qualitative confidence rationale. Keep unsupported/stale/unlicensed cases explicitly withheld with reason and next check. No requirement may force Bullish/Bearish/Sideways labels to achieve 50/50 directional coverage, expose private data, claim profitability or trigger live execution. Daily scorekeeping cannot autonomously retrain or promote production models.

## Duplication review

Do not create another forecast runner or model ticket: PRSG-124 owns the fixed-50 per-ticker numerical path, PRSG-113 owns model validation/calibration, and PRSG-138 owns public eligibility. PRSG-179 closes only the cross-role instruction gap for experimentation and evidence handling.

## Scope

Base SHA: `15a8f0f938305a4f93b02db231c71b4beb085ef1`.

- `AGENTS.md`
- `plans/README.md`
- `plans/2026-11-01/PRSG-179-learning-from-paper-forecast-failures.md`
- `plans/2026-11-01/PRSG-179.harness.json`

Protected: model and report implementation/data, forecasts, tests, connectors, schedules, role prompts and skills. No model, code, data, report, source permission, training job, or scheduler is changed here.

## When it is considered done

- [x] PRSG-179-D1: All roles receive an explicit instruction to make bounded permitted forecast attempts and retain failures as auditable evidence.
- [x] PRSG-179-D2: Guidance separates paper experiments from supported public forecasts and prohibits forced directional labels, leakage, autonomous production retraining and unreviewed promotion.
- [x] PRSG-179-D3: Existing fixed-50, model-validation and publication work is reused rather than duplicated; guidance examples for valid-weak, missing/stale/unauthorized and matured-failure cases are consistent.

## Checks and delivery

- `python3 scripts/planning/validate_ticket.py ...`: passed for every changed path.
- `python3 scripts/planning/check_ticket_briefs.py`: passed.
- Manual policy replay: valid weak forecast → paper-only with explicit confidence; missing/stale/unauthorized input → named abstention; matured comparable miss → immutable score and candidate follow-up, no automatic promotion. Passed.
- `git diff --check`: passed.

## Status

**Complete; Lead review accepted on 2026-11-01. No predictions or model evaluations were produced by this instruction-only ticket.**
