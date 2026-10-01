# PRSG-24 — Specify prior-session mover attribution and prediction replay

Type: spike · Modules: market-research, financial-data, harness · Owner: Consultant · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Base: bb0d302bd4384482e628e5e1e58630e0d68396f4. Impact hypothesis: better evidence quality and reproducible research, not guaranteed returns.

## Decision question and timebox
Within one person-day, define a reviewable research-only protocol to turn T-1 movers into evidence-backed regression candidates without look-ahead, survivorship or winner-selection bias. Read PRSG-22 overall plan and reuse technical-trend-analysis, daily-market-brief, trading-orchestrator and shared safeguards.

## Protocol requirements
Distinguish overnight gap, close return, intraday move, range and abnormal volume. Propose market/liquidity-aware thresholds, history windows and minimum sample requirements with rationale; remain proposals until frozen by Lead. Include corporate actions, FX, holidays/DST, halts, illiquidity and market/sector confounders. Daily OHLCV cannot identify intraday reaction timing.
Define news linkage windows and label taxonomy: plausible catalyst, context/correlation, contradictory, unknown; preserve both-direction movers, ordinary controls, news-without-moves and no-news cases. Retrospective explanation is not causal proof or pre-decision predictability.
Separate publication/provider availability/first observation. Backfilled articles cannot prove historical ingestion availability. Classifier sentiment/score is not future-return probability. Specify pre-decision forecasts and matured outcomes at separate frozen horizons; use chronological/event-grouped splits and purge overlapping labels.

## Deliverable and skill gate
Write docs/research/PRSG-24-mover-catalyst-protocol.md only; may update this ticket's progress/check evidence without changing scope, gates or base. Include a proposed frozen case schema and at least five worked synthetic acceptance/rejection cases covering future news, duplicate syndication, split-induced gap, unexplained mover and missed/false-positive catalysts. Mark synthetic examples, no invented market facts.
Propose how Consultant reviews candidate skill corrections and how Lead/human accepts changes only after replay. No automatic skill rewriting, trading, training, installs or benchmark claims. Return evidence-linked protocol, uncertainty and minimum next implementation to Lead; user authorizes return message. No commit/push or production edits.

## When it's considered done

- [ ] PRSG-24-D1: Sourced findings and proposed protocol independently reviewed by Lead.

## Progress

2026-10-01 MYT: Consultant prepared docs/research/PRSG-24-mover-catalyst-protocol.md with primary-source links, proposed parameters/schema, eight explicitly synthetic cases, leakage-controlled replay and a human-reviewed skill-candidate loop. Moomoo reference retrieval timed out; Bursa calendar verification and data rights remain prerequisites. Independent Lead review remains pending; no implemented feature or measured improvement.
