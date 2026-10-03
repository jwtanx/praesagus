# PRSG-49 · Keep report section navigation visible

Type: bug · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day) · Impact: medium-high

## Why
Human request8: the report section slider/nav scrolls away. Current `.bar` is not sticky and its brief-tools parent is only as tall as the bar, which can constrain a sticky child. Section selection should remain available beneath the already-sticky top menu.

## Approach
Make the correct full-lifetime tools wrapper sticky below the measured topbar, not a child confined by a short parent. Observe topbar and tools sizes with ResizeObserver when available, plus resize/menu/view/render fallback updates. Set CSS offsets so section scroll targets clear both visible bars plus small spacing; recompute on mobile menu expansion and view toggles. Topbar above tools above report; opaque background. Existing slider/prev/next/section links, report sections and URL behavior preserved. Brief tools hide outside appropriate view; hidden bars should not reserve stale height. Existing smooth-scroll calls respect prefers-reduced-motion. No date/motion/chart/data/schema changes.

## Options and decision
Use dynamic measured offsets rather than hardcoded desktop/mobile heights; responsive wrapping and menu expansion vary height. Preserve index/template behavioral parity. No new dependencies. DOM tests can stub measured rectangles/ResizeObserver but do not prove actual browser stickiness; independent live desktop/mobile scrolling required after delivery.

## Frozen scope
Base1c237063ea09d4fd4e5e3e09f4a8863454df8d56; five exact paths: index.html, template.html, new tests/report_navigation_checks.cjs, this spec and manifest. Existing viewer/TradingView tests protected and must pass unchanged; flag conflicts. No report JSON, forecasts, tradingview.js, calendar, landing/ticket viewer, ingestion, skills or schedules.

## When it's considered done
- [x] PRSG-49-D1: Focused measured-offset/menu/view/reduced-motion regressions and existing viewer/TA tests pass.
- [x] PRSG-49-D2: Lead independently accepts complete five-path implementation and records browser verification limits.

## Engineer delivery evidence — 2026-10-03

Status: review; PRSG-49-D1 demonstrated, PRSG-49-D2 pending Lead acceptance.

The direct-body brief-tools wrapper is sticky beneath the measured visible topbar; its inner bar is static. Both pages share the same measured-offset helper and CSS behavior. The legacy template retains eight sections and has no topbar, so its topbar offset is zero; the index retains seven sections. This bounded parity interpretation was approved by Lead. ResizeObserver and resize/menu/view/render updates refresh offsets; hidden bars contribute zero height. Section scrolling clears visible bars plus 16px and respects reduced motion.

Commands run from the repository root using Node 26.7.0 and existing isolated jsdom26:

- `node tests/report_navigation_checks.cjs` — passed; `/tmp/PRSG-49-navigation.txt`.
- `node tests/daily_report_viewer_checks.cjs` — passed; `/tmp/PRSG-49-viewer.txt`.
- `node tests/tradingview_checks.cjs` — passed; `/tmp/PRSG-49-ta.txt`.

The focused suite covers desktop/mobile measurements, shared helper parity, absent template topbar, menu collapse before scrolling, hidden views, resize/observer/render fallback, invalid heights and reduced-motion scrolling. Existing viewer and TA tests are unchanged. DOM fixtures do not prove real-browser sticky positioning, scrolling or viewport overlap; independent desktop/mobile browser review remains pending. No new dependencies, report data, schema, chart mapping or chip motion changes. Delivery remains uncommitted for Lead review.

Lead review identified a fixed 150px mobile media override that bypassed the measured offset. The focused test now recursively checks every panel scroll-margin declaration, including nested media rules. It failed before the fix (`/tmp/PRSG-49-navigation-mobile-before.txt`); mobile overrides in both index and template now use `var(--section-scroll-offset,150px)` and focused replay passed.

## Lead acceptance
All five changed/new paths independently reviewed against1c237063. Exact three node commands independently replayed and passed; recursive media checks cover both corrected pages. Existing protected tests unchanged. Shared helper/body-level sticky tools, measured visible bar heights, collapsed menus/hidden views and reduced motion reviewed. Accepted implementation; browser scroll, overlap and actual deployment remain separate verification, not inferred from DOM tests.
