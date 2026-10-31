# PRSG-172 — Cross-Page Navigation, Palette, and Monthly Sector Rankings

Type: feature · Modules: frontend, market-research · Owner: Engineer · Priority: P2 · Effort: M (1–2 person-day estimate) · Impact: high for navigation consistency and monthly sector comparison.

## Objective

Use the seasonality header style across the homepage and daily brief, add Seasonality navigation on each page, align the seasonality color palette to the daily brief, and let visitors select a month to view and sort the best and worst performing official sectors without losing the existing sector search filter.

## Expected behavior

- The homepage, daily brief, and seasonality page share the same compact responsive header language and destinations: Home, Reports, Technical analysis, Ticker forecasts, and Seasonality. Preserve the daily brief's internal view navigation.
- The homepage and seasonality surfaces use the daily brief's palette (`#0c1118` background, `#141c26` and `#192432` panels, `#e8eef5` text, `#a5b2c2` muted text, `#2b3949` borders, `#89bfff` blue, `#66d6a4` green, and `#ff8e8e` red).
- Clicking a heatmap month selects it and shows separate best and worst sector lists with modern gradient bars and exact returns. These use the existing year selection and search query, and include only the 49 official industries; the benchmark and ETF proxies remain in the heatmap but are not ranked as sectors.
- A sector sort control supports original order, name A–Z/Z–A, and selected-month return high-to-low/low-to-high. The existing text filter remains active for both heatmap rows and rankings.

## Baseline and scope

The seasonality explorer is the only public page with the newer outlined header. The homepage is `artifacts/index.html`; the daily brief is the standalone `artifacts/daily-market-brief/index.html`. The daily brief already has a responsive menu and internal buttons for its report views. Sector values are already calculated for the selected period in the seasonality heatmap.

Base: `4d4ea60d171d6291364cabb611a6d9b24e3ddceb`.

Allowed paths:

- `artifacts/index.html`
- `artifacts/daily-market-brief/index.html`
- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `plans/README.md`
- `plans/2026-11-01/PRSG-172-cross-page-seasonality-experience.md`
- `plans/2026-11-01/PRSG-172.harness.json`

The requested static page files under `artifacts/` are explicitly in scope. All other paths are protected. Do not change financial source data or return calculations.

## When it's considered done

- [x] PRSG-172-D1: Homepage, reports, and seasonality share a responsive header and include links for the Home, Reports, Technical analysis, Ticker forecasts, and Seasonality destinations.
- [x] PRSG-172-D2: Homepage and seasonality use the daily brief color palette for page backgrounds, panels, text, borders, and accents.
- [x] PRSG-172-D3: Selecting a month shows the five best and five worst available official industries for the current period and filter; benchmark/proxy rows are excluded from rankings.
- [x] PRSG-172-D4: Sector rows can be ordered by source, name in both directions, and selected-month return in both directions; the existing search filter still applies.
- [x] PRSG-172-D5: Standalone Pages build and ticket scope validation pass.

## Findings

- Search filtering already runs while the table's month values are calculated. Ranking from the filtered official-industry rows lets the same filter constrain both the heatmap and top/bottom groups.
- For the all-years selection, rank the existing 1996–2025 complete-year monthly averages. For an individual year, rank that year's available monthly return; unavailable months remain excluded.
- When a search leaves fewer than ten eligible industries, split the visible matches between the best and worst lists so a sector does not appear in both.

## Approach

Keep the homepage's product cards, the report page's internal view controls, and the seasonality dataset intact. Add matching destinations to each header. Give seasonality theme variables that match the daily brief; keep positive and negative return meaning but use the brief's green/red tokens. Make month labels accessible buttons, calculate rank lists from the existing filtered series, and apply the selected sort to the visible heatmap rows.

## Choices

- The five destinations are Home, Reports, Technical analysis, Ticker forecasts, and Seasonality; report-specific Calendar navigation remains available in the daily brief.
- Ranking is limited to the 49 official industry series. The market benchmark and shorter-history ETF proxies are not sectors.
- Return sorting is enabled after a month is selected; alphabetical sorting remains available at all times.

## Tradeoffs

The static homepage and daily brief each keep a small local navigation implementation because they are standalone HTML pages, while the interactive seasonality page uses its existing React header. Rankings respond to the search filter, so a narrow query can produce fewer than five entries in one or both lists. The page displays reported historical returns, not a forecast.

## Checks

- `npm run build -- --mode pages` from `frontend/`.
- `python3 scripts/planning/validate_ticket.py plans/2026-11-01/PRSG-172.harness.json` with every changed path.
- `git diff --check`.
- Navigation and ranking code review: all three public page headers link to the requested destinations; the mobile menu remains toggleable; month ranking is restricted to filtered official industries and excludes missing observations; search filters both displayed rows and rankings; sorting supports source, alphabetical, and selected-month return order.

## Status

**Implementation and local verification complete; publication pending.** The standalone Pages build succeeds. The home and daily brief are static HTML pages included in the Pages artifact directly.
