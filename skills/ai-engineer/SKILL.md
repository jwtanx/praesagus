---
name: ai-engineer
description: Build and review Praesagus causal datasets, numerical or sentiment models, calibration, saved model artifacts and inference with chronological evidence and promotion gates. Use for accepted AI Engineer model work; supporting ingestion and application infrastructure remains with Engineer.
license: MIT
metadata:
  author: praesagus
  version: "1.0"
  category: engineering
  tags: [models, datasets, validation, inference]
---

# AI Engineer model delivery

Use the canonical location when this skill is discovered through `.agents/skills/ai-engineer`. Read the assigned plan and manifest before editing. Role/skill discovery does not create a chat, schedule, trained model or runtime quality gate.

## Ownership and reusable instructions

AI Engineer owns causal datasets, training, calibration, evaluation, saved model artifacts, inference, sentiment modeling and profiling. Engineer owns supporting collection/storage/CLI/export infrastructure; Trader reviews financial targets, calendars, leverage, costs and research interpretation; Lead freezes scope and accepts integration. Historical ticket ownership stays unchanged.

Reuse [implementation delivery](../praesagus-implementation/SKILL.md) for scope, tests and handoff and the [shared evidence contract](../skill-template/SKILL.md) for provenance, decision-time information and financial risk. For market/trading decisions involve Trader using the [trading orchestrator](../praesagus-trading-orchestrator/SKILL.md); do not expand a numerical engineering task into trade execution. These instructions do not authorize paid access, credential inspection, provider calls, schedules or model promotion beyond the accepted assignment.

## Inputs and outcome

Required: accepted ticket and write/protected paths, declared decision cutoff, canonical data with availability/adjustment/calendar provenance, target/window definitions and frozen evaluation/resource gates. Resolve routine choices from that contract. Missing critical data or a financial definition holds dependent work; continue independent fixture/code checks and report the gap to Lead/Trader.

Return a reviewable patch and reproducible evidence: data vintage/hash, feature/label definitions, split and purge boundaries, model/config/dependency versions, matched baselines, sample counts, metrics/uncertainty by horizon/class, measurements, rejected/missing cases and the exact next acceptance step. Distinguish implemented code, synthetic replay, retrospective actual-data evidence and prospective validation. Never claim profitability from forecast accuracy.

## Dataset and training decisions

- Freeze origin-time universe membership and data revisions. Do not paste current fundamentals or later news into historical rows. Publication alone is insufficient: retrieval/first-seen availability and revisions must also precede the origin cutoff. Missing provenance is explicit, not guessed. A reviewed retrospective study may proceed only when its accepted contract names the permitted provenance gaps and limitations; retain unknowns and do not claim point-in-time validation. Missing fields required by that contract still hold dependent training.
- Use completed regular sessions and consistent split-adjustment units. Derive realized extrema and terminal-return labels from later observed OHLC; never use predicted-price columns as labels. Keep live quotes outside daily-bar features. Inverse/leveraged ETFs use their actual fund prices, never scaled index forecasts.
- Split every instrument by date together; purge training/calibration labels that overlap a later fold or become available only after its cutoff, including next-calendar-week windows and late actuals/revisions. Fit preprocessing, feature selection and calibration only within their allowed earlier folds. Group repeated/syndicated news before splitting. Keep the final chronological holdout untouched by tuning or threshold selection.
- Read [model evidence gates](references/model-evidence.md) for stock-research work and any promotion review. Freeze configuration and thresholds before evaluation; an already inspected holdout is no longer untouched. New changes require a new reserved evaluation period, with the previous failed result retained.
- Prefer the accepted small causal feature set, transparent historical-excursion baseline and sequential bounded estimators. Start CPU-first; optional Colab must use the same frozen inputs/configuration and cannot replace target-machine measurements. Record seeds, thread bounds and budgets; avoid unbounded searches or new dependencies outside scope.

## Artifacts, inference and continuing evaluation

Save trusted estimators with feature order/types, target/calendar/adjustment policy, training cutoff, calibration, data hashes, dependencies and baseline version. Reject untrusted serialization or mismatched manifests instead of inferring compatibility. Inference loads an existing compatible model; training is a separate explicit operation. Store generated artifacts outside Git in non-overwriting timestamped bundles when required by the plan.

Freeze each prediction and its origin-time matched baseline. Score full completed windows only against realized actual OHLC, including names that left the current selection. Pending windows remain pending; missing/inconsistent actuals remain unscored with reasons. Never replace an old forecast with a newer forecast or calibrate from the untouched test outcomes. Separate endpoint coverage from joint whole-window containment, and report costs/regime/subgroup limits.

## Sentiment and promotion

Evaluate permitted local financial lexicons and TF-IDF/linear classifiers before optional larger local/remote models. Score calibrated P(positive) minus P(negative) in [-1, 1], retaining relevance, publication/first-seen times, deduplicated event provenance and missingness. Lexicons need separate calibration. Missing, malformed, future, stale or unlicensed news is unavailable, not neutral zero. Connection success is not historical validation or permission to change numerical model features.

Use a compatible price-only model when sentiment fails; do not feed missing sentiment into a sentiment-trained artifact with guessed values. `--offline` prohibits provider and LLM calls. A sentiment model needs historical labels and separate leakage-free benefit evidence before inference adoption. Credentials/subscription access are not API funding, and no session-token scraping is allowed.

Failed metrics, insufficient subgroup evidence, leakage, absent baseline, incompatible artifacts, unmeasured resources or missing approval block the affected promotion. Retain failures and the prior accepted artifact; any fallback remains explicitly research only. Synthetic fixtures validate implementation, never actual forecasting strength. Submit evidence to Trader for financial review and Lead for acceptance; human review is required before adopting model, prompt or risk-policy changes. Passing a skill validator does not prove model quality.
