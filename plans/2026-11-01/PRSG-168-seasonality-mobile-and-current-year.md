# PRSG-168 — Seasonality Mobile Scrolling and Current-Year Chart

Type: bug · Modules: frontend, financial-data · Owner: Engineer · Priority: P2 · Effort: XS (0.5–1.5 person-day estimate) · Impact: medium-high for phone users inspecting monthly returns; usage impact is unmeasured.

## Objective

Correct the mobile month-grid scroll/alignment and expose the latest partial calendar year on the all-years chart. Preserve access to every sector, benchmark and thematic proxy.

## Reproduction and expected behavior

On the published 1 November 2026 seasonality page, the phone heatmap's month labels and values could appear disconnected while the user scrolled sideways. The chart legend wrapped roughly 30 years into rows, making year selection difficult, and the all-years chart omitted 2026 even though industry/market data includes January–September 2026.

Expected: the mobile heatmap scrolls inside its own panel with its series-name column held in place; month headings and values stay horizontally aligned. The chart's year selector is a single horizontally scrollable strip with selectable years, includes 2026, and labels its line as a partial year through September. Selecting 2026 emphasizes its nine observations; selecting it again restores the full chart. The all-years heatmap remains the 1996–2025 complete-year average.

Severity: P2 usability and current-data discoverability; no data corruption.

## Baseline and scope

This is a follow-up to [PRSG-167](../2026-10-31/PRSG-167-us-industry-seasonality.md). The static Pages build embeds 369 official monthly periods through 2026-09 and the five SEC-filed ETF proxy histories. `Seasonality.tsx` previously selected only complete historical rows for the all-years chart, even though the 2026 rows were in its static dataset. On mobile the heatmap changed row layout and applied horizontal padding to body month cells but not header cells; the year legend wrapped.

Base: `110705678d33fd2b9d56e4b3f807aad4156eb0e7`.

Allowed paths:

- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `plans/README.md`
- `plans/2026-11-01/PRSG-168-seasonality-mobile-and-current-year.md`
- `plans/2026-11-01/PRSG-168.harness.json`

Protected: all other paths. Keep the existing datasets, source methods, all-years heatmap average, and 2026 available-month boundary unchanged.

## When it's considered done

- [x] PRSG-168-D1: At a 390px viewport, the page has no document-level horizontal overflow; the heatmap is internally horizontally scrollable and month headings align exactly with their values while the row label stays visible.
- [x] PRSG-168-D2: The chart year strip is horizontally scrollable and selectable. All-years chart includes each available year, including nine 2026 points through September. Focusing 2026 highlights it and shows the partial-year boundary; selecting it again restores all lines.
- [x] PRSG-168-D3: Desktop/mobile builds and ticket scope validation pass; existing all-years heatmap continues to aggregate complete years only.

## Approach and tradeoffs

Use a fixed-width month grid inside the existing heatmap scroller on phones, with a sticky series-name column and matched padding. Keep the chart's year buttons in a non-wrapping horizontal scroller. Feed the chart all official periods and available SEC periods; keep average calculations and heatmap aggregation limited to complete years so the partial 2026 line does not change historical seasonal averages. A fixed-width mobile grid requires a sideways swipe to see all 12 months, but maintains readable cells and clear month alignment.

## Checks

- Standard build: `npm run build` from `frontend/`.
- GitHub Pages build: `npm run build -- --mode pages` from `frontend/`.
- Manual headless-Chrome review at a 390×844 CSS viewport: document width 390; heatmap client width 338 and scroll width 800; header and month-cell x positions both 208; year selector client width 338 and scroll width 1758; the 2026 year button is present.
- Interaction review: all-years selected chart renders 369 monthly points (30×12 complete historical observations + 9 partial 2026 observations). Clicking 2026 sets its button to `aria-pressed=true` and the caption states data through September; clicking it again clears focus.
- The chart summary averages and heatmap continue to use 1996–2025 for the 30-year complete-period comparison.
- `git diff --check` and `scripts/planning/validate_ticket.py` with every ticket-scoped changed path.

## Findings

- The all-years chart omitted 2026 because it selected complete calendar years, despite the embedded official dataset containing nine available 2026 months through September. Including those months in the chart does not alter the complete-year heatmap average.
- On mobile, the heatmap's header and value grid had different horizontal offsets, and the year legend wrapped across multiple rows. A contained month scroller with a sticky series label and a single horizontally scrollable year strip fixes both navigation problems.
- The full repository hook also exposed an unrelated timing-sensitive child-process test failure: the output-limit case was reported as `execution-timeout`. The suite reported 4,159 passed and 2 failed; the other failure was the now-corrected ticket-brief quality requirement.

## Status

**Implementation and local verification complete; publication pending.** Responsive review used headless Chrome at an explicitly emulated 390×844 CSS viewport. The source datasets and financial interpretation are unchanged.
