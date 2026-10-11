# Compact daily report contract

Read before authoring a new schema-3 report or a compact presentation revision.
The October 8, 2026 report is the reading-format reference; its historical
prices and predictions are not reusable current inputs.

## Authoring and display

- Set `metadata.presentation_profile: "compact-v1"`.
- Use 1–4 summary items, each summary body at most 50 words. Keep total main
  section prose (descriptions, item paragraphs and notes) at most 1,000 words.
- Keep each ticker's `confidence_reason` at most 40 words and `scenario` at
  most 55 words. State the useful interpretation or concrete missing input;
  avoid repeating full timestamps already retained in structured fields.
- Tables with more than eight rows require `collapsed: true` and a nonempty
  `details_label` of at most 12 words. Keep all audit rows; show the cohort
  counts, scored denominators, blockers and next recheck in the short scorecard.
- The compact viewer shows the observed price, source time/age and observation
  qualification. Full source/observation/ingestion/known/cutoff times, unknown
  reference fields, rights status and `data_gaps` remain in closed native
  details controls. Missing price coverage remains visible. Provider observations
  are not verified sortable reference closes.
- Show separate native Moomoo bullish/bearish observation chips and an
  independent Forecast chip. Current native coverage is unavailable; display
  `Moomoo bullish: Unavailable` and `Moomoo bearish: Unavailable` with expandable
  KDJ/MACD/Bollinger coverage details. Quote-versus-previous-close and calculated
  SMA trends remain raw audit inputs, not native signals or substitute chips.
  Preserve unknown native rule/parameters/timeframe/source observation time;
  missing coverage is unavailable, never zero or neutral. Keep forecast labels
  up/down/flat/Unrated independent. Color does not replace the text label.

Word limits use whitespace-delimited words. They constrain the main reading
view, not preservation of detailed evidence. Do not cut provenance or unsupported
coverage from the JSON to pass a display budget.

## Data path and forecast support

Reuse the committed `scripts/market_collect.py`, the existing authorized loader
and the approved nonsecret plan. Use normal same-run selection and
`map_public_snapshot` through `project_public_market_snapshot`; copy only the
allowlisted points into the dated report. Do not replace this flow with a private
draft runner, ad hoc quote fetch or a newly generated signing script.

At the October 11 checkpoint, the working report intake is REST with a
snapshot-only 30-US-name plan. Optional REST history transport is implemented
and a bounded probe succeeded, but approved report history jobs and completed
session/end-date/basis eligibility are unresolved. Installed SDK availability
does not establish logged-in OpenD connectivity or live indicator mapping.
PRSG-82 native KDJ, MACD and Bollinger intake remains blocked pending accepted
scope and verified provider rules, identity, timestamps and coverage. This
display correction does not add a native-result payload contract. Native
observations cannot provide numeric targets or automatically change forecast
direction/confidence.
Recheck the accepted implementation and plan before claiming those gaps resolved.

Snapshot-only intake supplies prices, not native patterns or the October 8
historical 20-return drift/Gaussian-band inputs. Existing raw price-comparison
and SMA fields do not establish native coverage. Without supported
reference/horizon/target evidence, keep forecasts Unrated with null targets/ranges
and a reason. Even agreeing eligible calculated proxies must not force forecast
direction. An independently supported forecast can remain rated when native
signals are missing, provided its own evidence passes the existing gate.

If native intake is later accepted, retain each indicator/pattern's exact
provider rule, parameters, timeframe, signal, source and observation/availability
times, with explicit unknowns and per-ticker missing/coverage status. A successful
empty screener result can include unsupported coverage; prove eligibility and
completed evaluation before calling it no-match. Screener totals count matched
securities, not per-ticker events; deduplicate group/child matches. Counts are
observations, not probabilities, target prices or forecast-confidence upgrades.
Provider defaults, legacy rules and daily period codes must not be assumed
equivalent across API versions. Receipt time cannot replace unknown event time.
Sources: [REST screening](https://open.moomoo.com/zh-cn/api/quote/screening/stock-screen),
[native pattern schema](https://open.moomoo.com/mcp-docs/available-tools) and
[SDK screening](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-stock-screen.html).

Reconcile raw collection counts to the actual rows: observed/missing US and MY,
stored quote-direction counts, available SMA count and verified reference count.
Retain those raw counts for audit, not native-signal coverage or the compact
bullish/bearish narrative. Counts are not probabilities or predictive performance.
For every rated row retain its frozen reference close/date/source, horizon,
bull/bear/invalidation, named method, positive observation/horizon-session counts,
issuance time, coherent target date and finite ordered target/range. The validator
checks declared support; it cannot verify authenticity, calibration or an edge.

## Final delivery gate and presentation revisions

After the final report/index write, use the approved Python >=3.11 environment:

```sh
python3 scripts/daily-market-brief/validate_report_json.py --date YYYY-MM-DD --public --compact
```

Failure stops delivery, commit and publication. Correct the issue and rerun the
same committed validator; do not invent forecasts to make coverage look complete.
Zero/partial input coverage with explicit gaps and Unrated/null targets is valid.
Normal validation also enforces a present compact profile; `--compact` ensures
the selected new report cannot accidentally omit it. Historical archive checks
continue through normal public validation without rewriting earlier reports.

For a presentation-only revision, increment `metadata.revision`, record actual
timezone-aware `revised_at` and explain the display change. Preserve the original
`as_of`, financial/input payloads, sources, gaps, membership and full audit rows.
Do not rewrite frozen forecast cohorts, fetch post-cutoff prices into that report
or imply the revision was available at its original issuance time.

Replay before accepting a workflow change: verbose/open long audit rejects;
compact missing-history coverage accepts with Unrated forecasts; future evidence
and unsupported rated rows reject. Also replay absent native data and successful
empty unsupported-market results as unavailable (not zero/neutral), agreeing
price/SMA proxies without forced forecast direction, and an independently
supported forecast retaining its rating despite missing native observations.
Verify the visible chips and closed details on keyboard and mobile, then verify
deployment before reporting publication.
