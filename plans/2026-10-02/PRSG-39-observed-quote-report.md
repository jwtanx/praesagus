# PRSG-39 · Observed quote report integration

Type: feature · Modules: financial-data, frontend · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high

## Why the ticket is created?
Private snapshot selection now exists but the report cannot display those observations honestly: current-price sorting assumes listing currency, and quote provenance/gaps are invisible. User wants daily ticker prices and less repetitive remarks. This bridges selected evidence to a usable report draft, not another storage foundation.

## Approach, choices and tradeoffs
Lead accepts Consultant's explicit unverified-point display over withholding every numeric value. Add optional structured observed_quote to schema3 forecasts, independent of legacy current_price_value. Currency/session/adjustment/prior-close remain null and visible as unknown. Do not assign listing USD/MYR to snapshot units. Leave legacy current_price_value null/missing for projected rows: observed points are unsortable in nominal currency sorting. Preserve existing legacy reports.

Pure projection takes explicit schema3 accepted template, exact expected US universe, run ID and frozen cutoff; calls select_snapshots, uses a narrow allowlist, deep-copies inputs, keeps every US/MY row. Reject template as_of inconsistent with cutoff instead of relabeling later narrative evidence. This does not certify arbitrary narrative cutoff safety. Require unavailable forecasts/unknown direction/null targets for projected rows; reject unsupported forecast input rather than promoting it. MY remains unsupported/missing; no other-run/prior-report fallback.

Selected observed_quote: positive finite price, finite nonnegative provider volume (zero preserved), provider source timestamp, observed/ingested/known timestamps, report cutoff, origin, explicit null reference metadata, bounded gaps and narrowly allowlisted private provenance. Unknown, failed, conflicted or ineligible points stay null with explicit reasons. Validate structured temporal consistency including source<=observation, known/ingestion<=cutoff; synthetic remains visibly synthetic draft data. No raw bodies, private paths, arbitrary dictionaries or account fields.

Render heading "Observed last — report cutoff" for structured points, source time and age relative to frozen cutoff (never viewer time), "Quote currency/session unverified", "Provider volume · unit/session unverified"; display data gaps. No stale/last-close/live claim without policy. Ticker-specific observed-fact sentence may accompany existing scenario, not overwrite verified narrative. No change %, inferred direction, targets, confidence, turnover or RVOL. Chip direction unchanged.

Manual CLI writes only explicit private outside-repo draft destination: atomic no-clobber, reject public roots/symlinks, no overwrite; no artifacts reports/index updates or publication. No live API calls, credentials, scheduler, personal watchlists or portfolio access. UI code may be committed; real quote data stays private in this ticket. Public snapshot policy/export remains separate.

## Validation and acceptance
Frozen base e743fe6ed608990a72e1f28f3512303dd86fb12e. Exact ten allowed files in manifest, protect unrelated DS and existing store/collector. Reuse existing libraries and tests, no dependency installation. Offline synthetic fixtures only.
Cover deterministic inputs, input unchanged, exact universe/taxonomy/all50rows, partial/missing/conflicted/unsupported MY, timestamp precision/leakage, synthetic labeling, unknown reference metadata unsortable, no forecast invention, allowlist/path/secret exclusion, atomic private no-clobber, legacy validator/render compatibility and safe escaped DOM display. Missing test runtime is a visible blocker, not installation authority.

## When it's considered done
- [x] PRSG-39-D1: Projection/validator/selection focused regressions pass.
- [x] PRSG-39-D2: DOM regressions verify observed quote timestamps, units, gaps, unsortability and legacy compatibility.
- [x] PRSG-39-D3: Lead full scoped review and independent replay accepted.

## Progress and limitations
Lead acceptance complete after ten-path review and independent103-test replay in2.75s plus passing DOM checks. Earlier pending checkpoint statements below are retained history. No live collection, published numeric snapshot, deployment, schedule or forecast improvement claimed. Value measure: synthetic selected quote visible with explicit reference gaps, rather than hidden in private provenance; real daily delivery still needs operational integration. Browser visual QA was not run; offline DOM coverage is not deployment evidence.



## Engineer resource checkpoint — 2026-10-02

Lead reported weekly4%, five-hour46%, battery51%; checkpoint requested. Feature expansion stopped, current permitted work saved without staging/commit/push. D1/D2 demonstrated; D3 independent Lead acceptance pending.

Exact manifest pytest argv/cwd on existing isolated Python3.12.14 / cryptography50.0.2: **103 passed in2.69s**, transcript `/tmp/PRSG-39-python-tests.txt`. Exact `node tests/daily_report_viewer_checks.cjs`: passed with existing isolated jsdom runtime, transcript `/tmp/PRSG-39-ui-tests.txt`. No dependency installation, credentials, live collection or real quote export occurred. Python3.11 unavailable/not tested.

Initial replay **22 failed / 67 passed** is retained in `/tmp/PRSG-39-first-failed-tests.txt`: strict group equality incorrectly rejected valid existing role/classification metadata. Required taxonomy/key/label/emoji fields are now compared, while valid additional group metadata remains unchanged. The fixture was also made wholly synthetic instead of copying dated report content. Observed subsequent replays passed99 and103 as focused cases were added. No tests removed or weakened to conceal failures.

Implemented optional strictly validated observed_quote; deep-copy private projection, frozen cutoff/source/receipt/ingestion/known times, four unknown references, bounded allowlisted provenance/diagnostics, unsupported MY/missing/conflicted coverage, no legacy nominal price/forecast promotion. Manual private CLI validates inputs, writes atomic0400 no-clobber output in existing0700 owned private directory, and suppresses private-path errors. Renderer shows frozen source age, synthetic origin, units/session/gaps and zero provider volume; legacy prices/chip direction remain separate. Synthetic CLI/file/race and DOM safety cases pass. Accepted templates remain caller-reviewed narrative: quote projection does not certify arbitrary narrative cutoff safety or public rights. No freshness/close/change/RVOL is inferred.

Checkpoint artifacts outside repository: `/tmp/PRSG-39-engineer-handoff.patch`, `/tmp/PRSG-39-checkpoint.md`. Next step is Lead independent review of all ten files and exact regression replay; no extra feature work is required before that review. Private output fsync/link failure can leave a complete draft despite reported failure; private inspections/permissions remain operator responsibility, not an OS sandbox. Scope/whitespace gate evidence is supplied in the handoff; D3 remains unchecked.
