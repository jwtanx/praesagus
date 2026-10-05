# PRSG-21 — Jev alternatives and input-specific market classification

Type: spike · Modules: market-research, financial-data, harness · Owner: Researcher · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: medium-high

Created 2026-10-01 MYT. User requested joint Researcher/Consultant research and a ticket for Lead. Lead acknowledged reservation of PRSG-21 and documentation-only scope. Impact is a hypothesis: fewer repeated generative calls could improve report cost/latency; no production savings baseline exists.

## Decision question and timebox

Within a three-hour evidence ceiling, identify the three strongest high-star open-source Jev alternatives, compare capabilities, code/checkpoint licenses, maturity, compute and evidence limits; jointly plan models for text, OHLCV, fundamentals/macros, calendar and sentiment. Define a bounded pilot, data prerequisites and decisions for Lead. Researcher owns repository documentation; Consultant and research agents contribute read-only evidence.

## Frozen scope

Base: `bb0d302bd4384482e628e5e1e58630e0d68396f4`; initially clean checkout. Allowed writes: this spec, `PRSG-21.harness.json` and `docs/research/PRSG-21-jev-classification.md`. No implementation, source-data download, training, paid API enrollment, skill changes or deployment. Lead controls any later scope extension.

## When it's considered done

- [x] PRSG-21-D1: Primary-source top-three comparison, integrated Consultant model plan and evaluation/data decision brief reviewed by Lead.

## Delivery and evidence

Researcher completed [the compiled brief](../../docs/research/PRSG-21-jev-classification.md) for review at 20:11 MYT. Direct shortlist: Laya, Kev and SemIf, with live GitHub star snapshots and separate code/weight license boundaries. All are young repositories; popularity is not market-model validation. Mature scikit-learn/SetFit/GLiClass controls are included. Consultant's completed input-model proposal was read and incorporated, with FinBERT weight rights left unresolved. Official TypeSafe docs resolve conflicting supplied-site pricing; no vendor benchmark was reproduced.

Conditional proposal: a frozen news relevance/catalyst pilot using a simple baseline, SetFit and Laya, with catalyst-miss review, abstention, temporal integrity and total-cost/p95 measurements. Price prediction requires a separate historical dataset, horizon definition and untouched outcome evaluation. No experiment or implementation was performed.

Lead must decide pilot scope/gates, source-of-truth rights, hardware/language budget, optional paid Jev comparator, and any later price-label horizons. Findings are ready; review and final acceptance remain pending. Ticket evidence is local until Lead commits it; it is not yet in the published audit.

## Accepted documentation correction scope — 2026-10-05 MYT

Lead accepted a dated current-source clarification within the existing three ticket paths, frozen correction baseline `c31b6bde28e47a4839a0861888c04831c3550d13`. Engineer is delegated writer; original base/date/historical Researcher owner and research_evidence remain unchanged. Preserve October 1 snapshots and conditional ranking as historical. Clarify smaller Kev calibration and Laya base/fine-tuned/context differences, primary-source audit failures/fallbacks and outstanding license/pilot decisions. All other paths protected. No models/downloads/paid/provider calls/tests/implementation/commit/push; D1 and final Lead review remain pending.

## Engineer correction delivery — 2026-10-05 MYT

2026-10-05 MYT Engineer bounded public-source audit and documentation correction: appended dated current-source clarification only, preserving Oct1 prices/stars/activity/conditional rankings. Current Kev README distinguishes small4B/0.8B ID-development temperature fitting from larger held-out datasets; no finance/OOD calibration inference. Laya Englishcard reports weak base typed-decisions versus benchmark-finetuned checkpoint and512token total option/state budget; pinned checkpoint/task/chunking/calibration required. TypeSafe identity/texttyped/version/math/time sources, Laya/Kev code+card licensing, SemIf MIT/upstream separation, sklearn calibration/TimeSeriesSplit reopened. FinBERT weightlicense unresolved. Failed rawSemIfmain/LICENSE resolvedviaactualmaster; LayaGitHubAPI failed but repo/license/card accessible. No snapshot re-verification, benchmark, model/security/license approval or classifier selection; no tests/models/downloads/paid/provider access/commit/push. Current humanMoomoo/privateportfolio/provisionalwidget priorities retained. Lead final acceptance pending.

Three-path manifest validation and diff/readback checks passed. Original baseline/date/owner/research_evidence and dated research body retained. D1 and Lead final acceptance remain pending; this delivery adds qualifiers rather than approving a pilot.

## Lead final research acceptance — 2026-10-05 MYT

2026-10-05 MYT Lead final research acceptance: independently read original brief/spec/manifest and all three correction diffs; reopened official TypeSafe models, SemIf repository, Kev README exact calibration statement (line453 at review) and Laya English card Honest Limits/token budget. Dated source addendum correctly limits unsupported zero-shot/calibration claims and preserves history. Accept research deliverable and documentation correction only: no classifier, pilot or model approval; no financial-quality, rights, production-baseline or savings claim. Existing unresolved FinBERT weight rights, source timing/failure limits and hardware/data/checkpoint/calibration/pilot decisions retained. Findings addendum unchanged; delivery is next, not automatic feature selection. No Engineer commit/push.

State: complete for the research deliverable and dated documentation correction. Earlier pending-review notes remain historical. Lead owns delivery/integration.
