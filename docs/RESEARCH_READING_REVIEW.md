# Research reading review — PRSG-158

Review date:30 October2026 MYT. Baseline:`51e0706e065f7bc767f21be8416138f48ff4bac7`. This review tests report comprehension and presentation. It does not establish source readiness, predictive quality or a current forecast.

## Baseline and selected change

One actual human participant interpreted Unrated as total API failure and skipped rating work. The participant did not answer the requested finding, source-time or next-check tasks. This is one qualitative observation; task duration was not measured. No population rate, comprehension percentage or improvement is claimed. Participant identity, verbatim chat and detailed evidence remain private.

Designer inspected actual saved public reports at390×844 and1440×1000. Trader independently replayed the current deterministic renderer and reviewed financial wording. The initial no-code candidate was superseded by the observed misunderstanding. Human explicitly selected visible reasons and next required checks beside existing Unrated chips.

The selected change keeps the single directional chip and all forecast guards. Unrated is explained as lack of a supported directional forecast, distinct from Sideways. Missing observations and forecast blockers remain separate; restoring a price API response alone does not supply a forecast. A supported historical-anchor forecast can coexist with a missing current quote. Reasons and required checks derive from the row's recorded gaps or display-coverage guard. Unknown reason/check/time stays unknown. A clearly dated historical SPY example does not supply a current forecast.

## Four representative states and answer key

| State | Actual saved example | What the reader must distinguish |
|---|---|---|
| Supported numeric display |8Oct SPY: Bullish,US$781.37,rangeUS$764.19–US$798.94,target9Oct,3sessions | Historical low-confidence statistical scenario with20-session/Gaussian/no-out-of-sample limitations; not a current or validated recommendation. |
| Unrated |21Oct SPY: null target/date,unknown direction | No supported public forecast; missing reference window/current target and reviewed public-use evidence. Not Sideways,zero expected return or proof the API returned nothing. |
| Missing observation |21Oct SPY and MY4707 | SPY's snapshot was not stored. MY's row-specific unsupported-market intake takes precedence over the global storage-failure string. Neither gets an invented source timestamp. |
| Legacy/historical |30Sep AAPL | Original Bullish targetUS$340.86/rangeUS$323.99–350.99 retained with original date; absent target date/horizon remains unavailable. |

Supported and historical are overlapping properties, not four independent cohorts. An additional authored TEST0 fixture exercises an observed point with no forecast; it is synthetic test evidence. The12Oct SPY public point supplies a separate real source-time example with source/observation/ingestion/known/cutoff clocks and unverified unit/session/rights limitations.

For21Oct SPY, source time is **not recorded**: no saved observation exists. Its report cutoff08:07:10.294768+08 is not a source timestamp. SPY forecast_as_of is null; NVDA retains20Oct08:01:22.284029+08,which must be labelled retained rather than current issuance. The next requirement is to verify completed reference data and current target/public-use review; storage must separately be restored for an observation. No ticker-specific next-check time is recorded. The report-level22Oct08MYT plan is historical, not an active promise.

## Domain-approved copy rules

- Definition: “Unrated means no supported directional forecast. It does not mean Sideways.”
- SPY21Oct separates “current snapshot was not stored” from unavailable completed reference data and a reviewed public forecast.
- MY rows use their structured unsupported-market reason before any general storage-failure reason. This describes the saved intake's coverage, not the availability of every Malaysian data provider.
- Missing public-use admission is missing reviewed evidence, not proof all provider permissions were denied.
- A numeric/order/currency/display guard failure uses its own display-coverage reason. Unrecognized reasons do not become invented API/history/rights claims.
- A retained timestamp remains immutable and distinct from a new issuance. Missing check times are not guessed; no scheduler or retry is created.

## Baseline checks and limitations

Lead ran these existing offline checks successfully before editing:

- `node tests/compact_report_viewer_checks.cjs`
- `node tests/daily_report_viewer_checks.cjs`
- `node tests/report_date_navigation_checks.cjs`
- `node tests/report_comparison_checks.cjs`

Designer verified390px document width390 in inspected21Oct/8Oct states, native Enter/Space disclosures, visible focus, MY filter/reset, native saved-date selection and direct browser back/forward. Per-picker history entries are not claimed: the picker uses replaceState. Native200%browser zoom,screen reader,touch hardware and a full accessibility certification remain unverified. DOM tests do not measure pixel layout or human comprehension.

Baseline rendererSHA256:`2ff058493e19733449e0768f95227ea9a177d8d5e10bd96938e9022c73dc9fc2`. All42 tracked report/calendar/universe/ledgerJSON files are pinned for byte-for-byte comparison. They must remain unchanged.

## Post-change reader protocol

Give the selected report without explaining the intended answer. Ask the same participant:

1. What is the main finding for SPY in this saved edition?
2. What does Unrated mean; is it the same as Sideways?
3. What source time can you find,or is it missing?
4. What must be checked next,and is the archived example a current forecast?

Record actual answers,help,missing answers and elapsed time only if measured. Report baselineN1 and post-changeN separately. The initial response alone is not a completed four-task assessment or a comparable timed baseline. Human layout selection is recorded; post-change participant observations and final Human acceptance remain pending until actually supplied. No AI reviewer is counted as a participant.

## Implementation and delivery

Engineer handoff and Lead independent checks passed. Both changed Node checks passed after correcting observed-point and unfamiliar-gap edge cases. Actual390/1440 browser renders have no horizontal page overflow; nativeEnter/Space disclosure behavior,visiblefocus and dated archived greenSPY chip were rechecked. All42financialJSON and numeric/unit guard functions remain unchanged. AI Engineer independently accepted five frozen uncertainty/attribution replays on the same renderer hash; deterministic authored summaries remain unchanged,with no LLM runtime. Required Git hooks and delivery are next. PRSG-158 stays open until its actual reader/final-acceptance gate is met. A display improvement does not resolve the missing current forecasts or authorize source/model/publication claims.
