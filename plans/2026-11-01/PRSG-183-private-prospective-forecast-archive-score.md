# PRSG-183 — Private Prospective One-Day Forecast Archive Score

Type: spike · Modules: market-research, financial-data, harness · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium — preserve additional genuinely prospective forecast outcomes without retraining or expanding public claims.

Created 2026-11-01 MYT. Lead accepted this bounded scope before scoring.

## Objective

Score preserved, immutable Praesagus one-day forecast vintages whose issue time precedes the target session, whose origin row is bound to the saved input, and whose completed target close is available by 2026-10-30. Keep each saved model version separate. Compare only the prediction and its own saved matched baseline plus a zero-return point. Results remain private and descriptive.

## Approach

Enumerate only previously saved one-day JSON forecasts with issue-time, input, receipt and target evidence. Check each full source input against the issue timestamp, bind the origin close and typed security identity, verify same currency/basis and a later completed target close, then score immutable model and saved-baseline quantiles without refitting.

## Choices

Keep model generations in separate groups. Exclude incomplete horizons and future targets; do not infer a single cross-version model score from these few dates. Use zero return as a reference and each forecast's own matched volatility baseline. Keep all detailed per-name scores and source evidence private.

## Findings

Thirty-three one-day forecasts across three issue dates passed the frozen lineage and target checks. All 1,758 source rows were known by their bundle issue time. Scores are recorded separately by model hash; the earliest groups contain only one and two names, so they cannot establish model quality.

## Tradeoffs

Using issued forecasts with later actual outcomes preserves the original issue-time information boundary. The archive is small, targets are correlated, Moomoo finality is unverified and the QFQ adjustment formula is uncertified; this provides useful observations but not a representative or statistically powered backtest.

## Frozen inclusion rules

- Include exactly the `1d` rows in these verified prediction bundles: PRSG-147 (SPY, origin 2026-10-23, target 2026-10-26); PRSG-150 (AAPL and SPY, origin 2026-10-26, target 2026-10-27); PRSG-155 (30-name cohort, origin 2026-10-28, target 2026-10-29). All were issued before their target session opened.
- Bind each bundle to its exact saved input CSV and receipt/admission evidence. Require every input row's `known_at_ms` to be no later than issue time; exact origin close, code and typed security ID, USD currency and `forward-excluding-dividends` label must match the prediction and later actual row.
- Use the frozen later actual packet ending 2026-10-30. Only completed 1d terminal close-to-close outcomes are scored. Provider finality remains unverified; preserve that limitation.
- Exclude the PRSG-113 23-Oct SPY `next_week` forecast because this ticket is 1d only; exclude 3d/5d/next_week rows because they are outside the frozen horizon, duplicated endpoints, or incomplete. Exclude 1-Nov forecasts whose target market session has not occurred. Do not substitute CSV-only exports for source-bound JSON forecast bundles.
- Keep `model_sha256` generations in separate groups. Do not pool a current-model vintage with challenger replays; PRSG-182's 29-Oct challenger results remain its separate one-origin analysis.

## Frozen sources

- PRSG-147 prediction JSON SHA-256 `ff1d8efc1ca87f7fb1fbb74e3d437e3e2d55669741612c22371438dda806365e`; origin input CSV `02db0873edf8fffd51ed14e0a0a777f59e1da9d2d3e3e5f6e218aafe27176707`; source receipt `38678e96909893a0325ec8984a0606ecd16b326bcae3eb9bf3cbf2f53c830597`; model `a787346c693debd64d4bd0f39c5a682c665aaa2e8e03bf55a301cd5e7f857388`.
- PRSG-150 prediction JSON SHA-256 `75b43e8ab10651466a5da6a1dcd08f7b8901b3b182192e35d721607cfa4733f6`; origin input CSV `0d1acaa282ed54f3d8def5008399e8f8e6e8fadd6492f6063eac4c40de8c31ae`; admission receipt `03292864eb0be5caf313a19c23c13d157e857eb0ef16d32f7527164445e11ac8`; model `c759e8c17532a1f82d8c1906d1340c2d910db2443ad5667744d6f0d55959e350`.
- PRSG-155 prediction JSON SHA-256 `8d8776c4a95f1404b6c7c6e9efd0b5bc7a62ce8cbdb599a94eebb5d5a25ef5c7`; origin input CSV `47d740a77473c6ecbcdf935fb8b10631c1a57776d5a4fdee6b0eb1cbf5a23c18`; model `fc633c3cbfd46f5cafde3792db07b6fa6c8eaea8ec3d0d0c71d14fd5a3ba2b59`.
- Outcome history CSV SHA-256 `27c2e2f845c9310119aecf6a0360c26e5f4f49a52b67821e7e81f63afa3067be`; typed instrument map SHA-256 `b151e7e30592ffcd0d322edab84b93e8eb6d6b7a1197daf6d3223dc845bb9a66`.

## Measures and limits

For each included immutable row, record realized close-to-close log return, model and baseline median direction hit, absolute log-return error, q05/q50/q95 pinball losses and central 90% coverage where available; record zero-return absolute error and direction result. Report per-name rows, counts and summary by model hash and horizon. No confidence intervals, significance, pooled model winner, profitability inference, publication or model promotion. The vintages have few dates and overlapping market-wide outcomes; these descriptive points are not independent validation.

Private output path: `~/.codex/lead-state/PRSG-183/`. Keep only derived scores and provenance receipts there; no raw bar copy or account identifiers.

## Acceptance

- [x] PRSG-183-D1: Lead freezes exact source bundle hashes, inclusion/exclusion rules, outcome vintage and metrics before scoring.
- [x] PRSG-183-D2: Reproduce issue-time/source lineage, origin identity/close, currency/basis and matured-target compatibility for every included row; retain excluded rows with reasons.
- [x] PRSG-183-D3: Score deterministic one-day outcomes against each forecast's own model, saved baseline and zero-return; retain private per-name evidence and model-version-separated summary.
- [x] PRSG-183-D4: Lead corrected a simple-return/log-return quantile mismatch, rescored all 33 rows, and independently reproduced the corrected private result hash; source bindings and limitations remain accepted. No public metrics or model promotion.

## Scoring correction

Lead review found the original scorer paired realized log returns with the saved simple-return quantiles. The private scorer was corrected to use `relative_quantiles[2]` for both model and baseline, and all 33 forecasts were rescored. Direction counts are unchanged; error, pinball and coverage metrics now use consistent log-return units. The corrected private results supersede the original score hash.

## Execution record

- [x] PRSG-183-D1: Scope and source hashes frozen before scoring.
- [x] PRSG-183-D2: 1,758 saved input rows were all known by issue time; 0 were future-known. All 33 eligible 1d rows passed exact origin close, typed ID, USD, adjustment-label, and completed target checks. Source/admission receipts were hash-verified where present; PRSG-155 uses the exact input already frozen under PRSG-182.
- [x] PRSG-183-D3: Deterministic private scoring completed; 33 per-name rows across three model generations remain separated, each against its own saved baseline and zero-return. Exact metric values remain in the private score bundle.
- [x] PRSG-183-D4: Lead corrected the quantile units, independently reproduced private result SHA-256 `4a5673fd7623b8afadfd7178aaffdbd5ee71fbf8e41f08e524011bc060997cc4`, confirmed 33 eligible rows, 1,758 inputs known by issue time and zero future-known, and accepted the three separately identified model vintages as descriptive only. No pooled cross-version score or validation claim.

Private score: `~/.codex/lead-state/PRSG-183/multi-vintage-score.json` (SHA-256 `4a5673fd7623b8afadfd7178aaffdbd5ee71fbf8e41f08e524011bc060997cc4`). Reproduce with `python3 ~/.codex/lead-state/PRSG-183/score_archive.py` (script SHA-256 `ec1bafe610880e81e4f192f92cd8a76990896a80f36b460c532763cc1a506690).

## Duplication review

PRSG-182 remains the separate one-origin 29-Oct external zero-shot bakeoff. This ticket archives only the saved Praesagus 1d predictions for matured target dates, without challenger reruns or cross-version comparison. PRSG-113 owns chronological fitting/validation; this ticket makes no claim that its zero-row folds are repaired.
