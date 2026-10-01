# PRSG-21 — Jev alternatives and input-specific market classification

Type: spike · Modules: market-research, financial-data, harness · Owner: Researcher · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: medium-high

Created 2026-10-01 MYT. User requested joint Researcher/Consultant research and a ticket for Lead. Lead acknowledged reservation of PRSG-21 and documentation-only scope. Impact is a hypothesis: fewer repeated generative calls could improve report cost/latency; no production savings baseline exists.

## Decision question and timebox

Within a three-hour evidence ceiling, identify the three strongest high-star open-source Jev alternatives, compare capabilities, code/checkpoint licenses, maturity, compute and evidence limits; jointly plan models for text, OHLCV, fundamentals/macros, calendar and sentiment. Define a bounded pilot, data prerequisites and decisions for Lead. Researcher owns repository documentation; Consultant and research agents contribute read-only evidence.

## Frozen scope

Base: `bb0d302bd4384482e628e5e1e58630e0d68396f4`; initially clean checkout. Allowed writes: this spec, `PRSG-21.harness.json` and `docs/research/PRSG-21-jev-classification.md`. No implementation, source-data download, training, paid API enrollment, skill changes or deployment. Lead controls any later scope extension.

## When it's considered done

- [ ] PRSG-21-D1: Primary-source top-three comparison, integrated Consultant model plan and evaluation/data decision brief reviewed by Lead.

## Delivery and evidence

Researcher completed [the compiled brief](../../docs/research/PRSG-21-jev-classification.md) for review at 20:11 MYT. Direct shortlist: Laya, Kev and SemIf, with live GitHub star snapshots and separate code/weight license boundaries. All are young repositories; popularity is not market-model validation. Mature scikit-learn/SetFit/GLiClass controls are included. Consultant's completed input-model proposal was read and incorporated, with FinBERT weight rights left unresolved. Official TypeSafe docs resolve conflicting supplied-site pricing; no vendor benchmark was reproduced.

Conditional proposal: a frozen news relevance/catalyst pilot using a simple baseline, SetFit and Laya, with catalyst-miss review, abstention, temporal integrity and total-cost/p95 measurements. Price prediction requires a separate historical dataset, horizon definition and untouched outcome evaluation. No experiment or implementation was performed.

Lead must decide pilot scope/gates, source-of-truth rights, hardware/language budget, optional paid Jev comparator, and any later price-label horizons. Findings are ready; review and final acceptance remain pending. Ticket evidence is local until Lead commits it; it is not yet in the published audit.
