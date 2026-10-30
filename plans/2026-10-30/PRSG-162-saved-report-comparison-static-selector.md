# PRSG-162 — Saved Report Comparison and Static Instrument Selector

Type: feature · Modules: frontend, market-research · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high — directly addresses repeated-context reading and unstable chart selection; measured usability lift remains unestablished.

## Objective

Make recorded report changes easy to inspect and instrument selection stable: explicit two-report comparison plus static searchable chart selector, preserving financial meaning and provenance.

## Approach

Human30October authorizes final team delivery. Designer's bounded specification in private PRSG162/designer/HANDOFF.md was prepared after inspecting current code and actual20/21October saved reports. Lead accepts that concrete design, with no report-data or forecast changes. Add a collapsed native comparison disclosure after summary. Two initially unselected indexed dates plus Compare explicitly fetch ONLY those reports with a separate controller/generation. Render paired Earlier/Later context, original links and complete supported-field differences. Do not compare the mutable shared monthly calendar as if it were a frozen event snapshot.

Replace the currently implemented requestAnimationFrame ticker tape with a static local search, native instrument candidate select and explicit Show chart. Keep all existing validated/deduplicated choices and universe order, names and curated symbol/external fallback. Search/candidate exploration never changes active chart. No-motion means remove clone/tick/idle-resume machinery, not merely hide it.

## Choices

Keep the existing single-page viewer and public module create/update/show/destroy interfaces. Prefer inline comparison logic in index.html to a new framework or provider. Preserve the current displayed date/view, existing predictionState/targetTiming guards, source safety helpers and chart generation/timeout/MutationObserver lifecycle. Exact new or changed files are frozen below. Existing motion tests must now enforce static selection behavior; this is a new requirement, not weakened financial coverage. Lead accepts Designer layout under delegated user scope; no financial/model/risk promotion.

## Findings

Designer inspected current code: tape advances12px/sec with cloned decorative choices and5-second resume. Existing87/89/96 presentation work is complete and remains historical. There is no equivalent two-explicit-saved-report comparison in the inspected viewer. Report calendar_ref points to a shared mutable monthly ledger, so authored calendar revision/cancellation comparison is outside this slice. Existing research items often lack stable IDs; label section text/source changes instead of inventing catalyst events.

## Tradeoffs

Comparison reflects recorded content, not market returns, accuracy, corrections or independent evidence. Match market:ticker, with duplicate/malformed groups marked not comparable. Ignore reorder/whitespace/timestamp-only noise while retaining original times in context. Missing entries remain not-present with unknown reason. No percentage price changes, new predictive badge, inferred cancellations, implicit latest/previous choice, source fetch, LLM or raw-data dump.

Native selectors can visually truncate long labels; keep full active identity in a wrapping text block. At390px stack controls and Earlier/Later cards with44px controls, at768px wrap, at1440px pair columns. Keep chart selection/date/current-versus-historical distinctions and all errors/fallbacks visible.

## Frozen Ownership

Engineer implements only the listed code/tests/doc files after finishing157; no overlapping writes. Lead owns this pair. Designer private annotations/review only; source reports, calendar, ledger, projection and methods remain immutable. Baseline cca89e514ed6217d3afb980063b604a53ff069c3. No provider, paid access, model/prompt/risk change, new data rights, source publication or schedules. Regenerate only the content digest in index.html for the changed tradingview.js. DOM and existing chart cache-key checks must pass. Any additional path requires reviewed extension before edits.

Allowed paths: plans/2026-10-30/PRSG-162-saved-report-comparison-static-selector.md, plans/2026-10-30/PRSG-162.harness.json, artifacts/daily-market-brief/index.html, artifacts/daily-market-brief/tradingview.js, tests/report_comparison_checks.cjs, tests/ticker_tape_loop_checks.cjs, tests/tradingview_checks.cjs, tests/compact_report_viewer_checks.cjs, tests/daily_report_viewer_checks.cjs, docs/REPORT_COMPARISON.md. Protected: artifacts/daily-market-brief/reports.json, artifacts/financial-calendar/, connectors/, ingest/, backend/, frontend/, skills/, agent-operations/, .DS_Store; all saved dated JSON reports/ledgers are additionally out of scope even where not listed as a prefix.

## When It Is Considered Done

- [x] PRSG-162-D1: Implement an opt-in comparison of two explicitly selected indexed saved reports with independent request cancellation/generation, complete paired report-date/revision/cutoff links and no change to the displayed report.
- [x] PRSG-162-D2: Compare meaningful whitelisted membership/coverage, guarded forecast fields and normalized research text/source sets with stable identities; preserve null/unknowns, reject duplicate ambiguity and ignore reorder/whitespace/timestamp noise. Absence is not cancellation; different saved forecasts are not revisions or performance.
- [x] PRSG-162-D3: Replace automatic ticker motion with a static local ticker/company/market search, native candidate selector and explicit Show chart action; keep active chart identity/context visible even when filtered out, and preserve curated mapping, fallback, timeout, date and lifecycle behavior.
- [x] PRSG-162-D4: Focused DOM/contract regressions pass for invalid/missing/equal/reversed selection, bounded two-report reads, stale responses, unsafe content, missing groups, no-match search, keyboard exploration, date changes and immutable stored reports; old motion-specific assertions are replaced by the new static behavior contract.
- [x] PRSG-162-D5: Lead and Designer independently inspect actual saved-report20/21October comparison plus 390/768/1440 layouts, keyboard/focus/chart error/selection states and no document overflow. Record native zoom/reader limitations honestly; no usability-study, calibration or model-quality claim.
- [x] PRSG-162-D6: Deliver reviewed code/docs and actual preview with unchanged original report/ledger/calendar/source/model files; commit/push and verify the exact resulting deployment when authorized.

## Checks and Delivery

Read the complete private Designer handoff; it freezes the exact labels and cases. Use existing jsdom dependency path, mock only provider/chart network in DOM cases and preserve actual browser distinctions. Run comparison/selector/legacy viewer/chart/cache-key focused checks, full mandatory hooks on authorized delivery, ticket validator with every changed path and independent Lead review. Preserve failed attempts. A build/test/screenshot does not prove real user comprehension or forecast usefulness. Native200% zoom and human reader study remain honest explicit limitations unless genuinely exercised.

## Implementation Release — 30 October 2026

Lead independently accepted157 technical implementation after62focused tests and actual clean-directory replay of16pinned original artifacts; relevant domain review continues on disjoint private artifacts. Designer162 bounded layout is accepted. Engineer now owns the listed162code/test/doc paths sequentially, with157source files frozen. Lead owns both canonical pairs. No stored JSON/ledger/calendar edits.

## Independent Implementation Acceptance — 30 October 2026

Lead independent focused comparison/staticselector/chart/compact/cache/date and nested fullviewer replays exit0; actual20/21savedpair50instrument+5textrecords, nativeexplicitkeyboardchartcommit and390/768/1440screenshots inspected. 42tracked publicJSON files byte-identical to frozenbase. IndependentLeadreceipt74191c3ebdf3fd79043d7db6ae3d295b699083055d5d403b13152006f48fbccd; Designerreview3c97322c064fb6d8e508859d9f7694ec7118143606d7dc6b5013cdb769ab88da. Native200%zoom/screenreader/usabilitystudy notperformed. Unchanged oldreport_navigation_checks null#nextfailure reproduced atbaselinecca89, not162regression; preservedoutside scope.

At implementation acceptance, D6 was pending. The verified delivery below closes it.

## Verified Implementation Delivery

Implementation committed/pushed as556749b502694b91e32468a6b93017ad99ae2341; remote main SHA independently matched. Mandatory precommit4051passed41warnings95.84s and prepush4051passed41warnings92.52s; no bypass. Independent actual implementation evidence remains asabove. Pagesrun41003275963/deployment7430763172success; canonical servedindexHTML2ff05849...,chartJS4c80ec19...,20/21OctJSON exactbytesmatch localcommit. Private deploymentbyte-reviewae0a1f9469147f3879541a9f7ed7fbebf7d94808840253dd9972c82c0f723989. https://jwtanx.github.io/praesagus/daily-market-brief/?date=2026-10-21. Nativezoom/readerstudy notclaimed.
