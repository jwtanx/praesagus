# PRSG-181 — Publish Partial Research Model Signals

Type: feature · Modules: market-research, daily-report · Owner: Lead · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high — ends the all-Unrated report gap with visible low-confidence research output.

## Purpose

The user explicitly authorized publication of supported forecasts even when confidence is low, provided the fixed 50-name dashboard is not entirely Unrated. User also confirmed Moomoo public display and derived-forecast rights for US and MY. For this dated 1 November edition, OpenD returns only US data; Malaysia stays Unrated. The accepted model run is research-only, LOW / UNCALIBRATED and all NO TRADE.

## Objective and Boundary

Publish the 1 November 2026 edition with exactly the fixed 50 identities, supported one-day US model estimates, and explicit Unrated rows for unsupported MY names. For this edition only, admit a partial set when at least one row has complete, hash-bound evidence. Preserve row-level source/time, model/run hashes, uncertainty, LOW confidence, NO TRADE action, no-trading disclaimer, and measurable post-session scoring. Do not publish raw historical bars, refit/promote the model, or imply executable advice.

## Frozen Scope

Base SHA: 8f0a1e7 (PRSG-180 pushed main). Lead owns the policy, report artifact, evidence mapping, and final review. Allowed paths: `scripts/daily-market-brief/publication_gate.py`, `tests/test_daily_report_publication.py`, `docs/DAILY_REPORT_PUBLICATION.md`, `skills/daily-market-brief/SKILL.md`, `artifacts/daily-market-brief/2026-11-01.json`, `artifacts/daily-market-brief/reports.json`, `artifacts/daily-market-brief/evidence/2026-11-01-model-inference.json`, and this ticket pair. Preserve normal structural validation and strict per-row evidence checks. Older editions keep their existing gate and history.

## Findings

The one-use locked run completed with 120/120 numeric research forecasts across 30 US names and four horizons; all 120 actions are NO TRADE and none qualify for trading. The one-day model median is positive for all 30 names. Input history contains 64+ daily bars each; only the 51-session inference window is used.

## Choices

Use one-day median sign as a directional research label (positive bullish, negative bearish, exact zero sideways), keep every confidence low, show model status NO TRADE, and retain all 20 unsupported MY identities as Unrated. Do not assign probabilities or publish historical bars.

## Approach

Add a narrowly versioned research-model evidence contract for this edition, bind it to exact report bytes and the reviewed inference CSV digest, replay each report row against the public-safe one-day output projection, and allow >=1 eligible pair only for this explicit LOW/NO-TRADE report type. All other rows must remain unavailable with null numeric values and reasoned gaps. Archive the minimal derived forecast projection needed to revalidate; exclude raw bars, private paths, account identifiers, and secrets.

## Tradeoffs

30/50 rows are supported; 20 MY rows remain Unrated because the installed OpenD API rejects MY history. All 30 US model directions are bullish; this one-sided result is surfaced as a low-confidence model tendency and not counted as qualified for trading. Historical comparisons are not available for this fresh vintage until outcomes mature.

## When It Is Considered Done

- [x] PRSG-181-D1: Evidence and report preserve exactly 50 names, 30 supported US one-day estimates, 20 explicit MY Unrated rows, and user-authorized partial-coverage semantics.
- [x] PRSG-181-D2: Publication validator binds the exact dated report and output evidence, rejects altered/missing/duplicate rows and fabricated directions, and retains existing checks for prior editions.
- [ ] PRSG-181-D3: Focused checks, public/compact schema validation, rendered mobile review, ticket scope review, and live Pages report verification pass.
- [ ] PRSG-181-D4: Actual 2 Nov outcome observation is retained for later scoring; no performance claim is made before maturity.

## Review Evidence

Private model output is from the one-use saved-model run in `~/.codex/lead-state/PRSG-1NOV/`; hashes and source provenance will be recorded in the public-safe evidence projection before the report is committed. Raw source bars remain private.
