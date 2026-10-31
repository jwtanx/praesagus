# PRSG-167 — U.S. Industry and Market Seasonality Explorer

Type: feature · Modules: frontend, financial-data, market-research · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-day estimate) · Impact: high for comparing historical calendar-month return patterns; adoption and decision value are unmeasured.

## Objective

Add a responsive Praesagus page reachable from the dashboard navigation and the public GitHub Pages homepage. Show monthly U.S. industry and broad-market returns for the 30 complete calendar years 1996–2025, default to an all-years arithmetic-average heatmap, provide a slider for all-years or an individual year, and draw one monthly line per year for the selected series when all years are shown. Clicking any row updates the chart. Add 2026 separately using only available month observations.

## Baseline and boundary

The frontend is a React/Vite single-page application with a sidebar navigation and no charting library. Core industry data is the official Kenneth R. French Data Library 49 Industry Portfolios monthly value-weighted return table. It includes dedicated `Chips` (semiconductors) and `Softw` (software) series. The overall-market benchmark is the Fama/French market return (`Mkt-RF + RF`), which yields the value-weighted return of eligible U.S.-incorporated NYSE, AMEX, and NASDAQ stocks. The latest downloaded official release, based on the September 2026 CRSP database, contains 369 months from 1996-01 through 2026-09; 1996–2025 are complete and 2026 has nine months. October 2026 is absent from this release. Values are monthly total returns in percent, not price levels or forecasts. Industry labels follow the source portfolio definitions; named companies are illustrative examples only, not verified portfolio constituents. AI, robotics, quantum, nuclear and renewable themes use explicitly labeled fund proxies, not inferred sector indices. Monthly class total returns are taken from SEC EDGAR Form N-PORT Item B.5. Each row shows its ETF, filing source and shorter coverage period; exact filing accession, return field, filed value, URL and source-file hash are retained with every observation.

Base: `78b2b4915aca8ed8e68c71cb1f66af56d61d010d`.

Allowed paths:

- `frontend/src/App.tsx`
- `frontend/vite.config.ts`
- `frontend/package-lock.json`
- `frontend/src/components/Layout.tsx`
- `frontend/src/index.css`
- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `frontend/src/data/industry-seasonality.json`
- `artifacts/index.html`
- `.github/workflows/pages.yml`
- `scripts/sector-seasonality/build_dataset.py`
- `tests/test_sector_seasonality_dataset.py`
- `plans/README.md`
- `plans/2026-10-31/PRSG-167-us-industry-seasonality.md`
- `plans/2026-10-31/PRSG-167.harness.json`

Protected paths include all backend/API, ingestion provider, model, trading, connector, report, and live schedule/role files. This user-approved scope extension opens only `.github/workflows/pages.yml` and `artifacts/index.html` for the requested static publication; other CI workflows and report artifacts remain protected. No live data service, external scheduler, investment recommendation, forecast, or trading action is in scope.

## User-approved scope extension — 1 November 2026

The user asked to add the broad U.S. market as a selectable row in the heatmap/chart and publish this section from a third homepage tile on GitHub Pages. The French Data Library's September 2026 factor archive is pinned separately from the industry archive. `Mkt-RF + RF` is calculated from the source's percentage columns and aligned to all 369 industry months. Vite's dedicated Pages build writes the standalone explorer under `artifacts/seasonality/`, and the existing Pages workflow publishes it with the rest of `artifacts/`. A lockfile and Node 22 setup make that build reproducible.

The user then requested clickable year focus in the chart: selecting a year emphasizes it and fades the other lines; selecting it again restores the complete view. Hoverable/focusable month points expose each year's return, that month's 30-year average, and the difference in percentage points. The user authorized pushing and publishing the updated section.

On 1 November 2026, the user requested AI, semiconductors, robotics, software, quantum, nuclear and renewable-energy coverage, and 2026 data through October. The user approved combining the official 49-industry history with separately sourced shorter-history thematic proxies, provided those sources and definitions are legitimate and not guessed. The checked official CRSP-based French industry and factor releases currently end at September 2026, so October is pending publication by that source. The user authorized publication for private, noncommercial research. The selected proxy observations come from SEC public fund filings rather than a vendor feed; no Yahoo data is bundled. SEC records are linked at observation level, and the page distinguishes fund proxies from official industry portfolios.

## User-approved scope extension — incremental source sync

The user requested an on-demand command to refresh the overall market aggregation, all 49 official industries and five SEC fund proxies. By default it adds newly published missing months through the current Asia/Kuala_Lumpur calendar month, without replacing stored observations. `--month YYYY-MM` scopes insertion to one month. `--start-year YYYY` and `--back-years N` re-sync a selected window; `--missing-only` fills only empty periods within that window. The update instructions are placed in `scripts/stock-research/README.md` beside the price-prediction/CSV workflow, with a note that seasonality datasets are separate from model inputs.

The French endpoints provide ETag/Last-Modified validators, so unchanged archives return HTTP 304 with no payload. If either archive changes, the publisher provides the full ZIP; the script downloads that changed archive but merges only requested months. SEC filing-index metadata is checked each run; previously stored accessions skip XML downloads. Range re-sync downloads filings whose report period overlaps the selected range. Returns not yet published are left blank and are never estimated. This scoped README edit is the only allowed path under `scripts/stock-research/`; other stock-research implementation paths remain out of scope.

## Acceptance

- [x] PRSG-167-D1: Dataset is reproducibly extracted from the pinned official source archive; it has 369 contiguous months through September 2026 × 49 value-weighted U.S. industry portfolios plus the market benchmark, with source attribution, retrieval/as-of metadata, and no missing markers.
- [x] PRSG-167-D2: Praesagus navigation opens the new seasonality page. It defaults to all-years monthly average returns and supports sliding to each individual year 1996–2025.
- [x] PRSG-167-D3: Every industry row is keyboard- and pointer-interactive. Selection displays the chosen industry's 12 monthly observations for each of the 30 years in all-years mode, or that one selected year in single-year mode.
- [x] PRSG-167-D4: Monthly return units, aggregation, industry classification, source revision/caveat, and illustrative-company limitation are visible. The heatmap has a color legend and accessible exact values.
- [x] PRSG-167-D5: Overall-market benchmark is extracted and pinned from official Fama/French monthly factors, calculated as Mkt-RF + RF, and shown as a selectable heatmap row and chart series.
- [x] PRSG-167-D6: A reproducible static build, homepage tile, and workflow build step prepare the standalone explorer for the existing GitHub Pages deployment.
- [x] PRSG-167-D7: Layout remains usable on phone and laptop widths; focused dataset checks and both frontend production build modes pass.
- [x] PRSG-167-D9: Clicking a year emphasizes its chart line and fades other years; clicking the same year again restores the full chart. Monthly points expose return, 30-year monthly average, and percentage-point difference.
- [x] PRSG-167-D10: Add official semiconductor/software industry series and explicitly labeled, SEC-filing-based short-history fund proxies for AI, robotics, quantum, nuclear, and renewable energy.
- [x] PRSG-167-D11: Show official industry/market data through September 2026 and each SEC proxy through its latest reported month (June–August 2026); leave October onward unavailable until the sources publish observations.
- [ ] PRSG-167-D8: Verify the published GitHub Pages homepage tile and seasonality section after the user-authorized push; no claim is made that seasonality is predictive or a trading signal.

- [x] PRSG-167-D12: Provide an on-demand incremental seasonality sync for official industry/market data and the five ETF proxies, with a current-month default, a single-month selector, start-year/rolling-year re-sync, and missing-only range mode; document it beside stock-research CSV generation.

## Approach

Keep the historical returns as a reproducible static dataset extracted from pinned official source archives. Use a Pages-mode Vite build for the standalone public section and link it from the existing homepage. Keep the all-years view as the default; chart selection only changes visual emphasis and point inspection, not the underlying return series.

## Choices

Use the Fama/French market total return (`Mkt-RF + RF`) as the broad-market series. Keep year selection in the chart legend so users can compare years without changing the table's chosen period. On a phone, constrain horizontal scrolling to the 12-month heatmap while keeping the chart inside the viewport.

## Findings

The 49-industry dataset rebuilds byte-for-byte from pinned official industry and monthly factor archives. Focused tests validate 369 contiguous months through September 2026 and market-return arithmetic. SEC filing tests validate report-month alignment, series/class identifiers and continuous fund-return histories. The local Pages preview confirmed 30 chart lines, year focus/toggle, accessible point metrics, the homepage tile, and phone-width layout without page-level horizontal overflow.

## Tradeoffs

The explorer is static and historical, so it does not reflect current conditions and the source may revise CRSP history later. Monthly historical seasonality describes past returns; it is not evidence of a persistent edge or a forecast. Company names are examples, not proof of historical portfolio membership.

## Checks

- Focused data/source/sync tests: `python3 -m unittest tests.test_sector_seasonality_dataset tests.test_sec_etf_returns tests.test_sector_seasonality_sync`.
- Frontend development build: `npm run build` from `frontend/`.
- GitHub Pages build: `npm ci --no-audit --no-fund && npm run build -- --mode pages` from `frontend/`.
- Manual desktop interaction confirmed the market row, market-specific average, 30 yearly chart lines, and the Pages homepage tile. Manual phone-width visual review and public deployment remain pending.
- Manual interaction confirmed 2020 can be focused and toggled off, with the other lines fading and restoring. Point labels expose return, monthly mean and difference. At 390×844 the page had no document-level horizontal overflow; the heatmap scrolls horizontally within its panel.
- Ticket scope validation and required checks are recorded in the harness. The user authorized the sync README path as a scoped exception; no other `scripts/stock-research/` path is opened.
- Ticket scope validation with all changed paths supplied.

## Status

**Publication pending.** The feature uses official 49-industry and Fama/French market data for 1996-01 through 2026-09; it includes 30 full years plus nine 2026 observations. This data may be revised by the publisher as underlying CRSP history changes. Semiconductors and software are present in the official classification. Five short-history thematic ETF proxies are sourced from public SEC N-PORT filings and their monthly observations link to exact filings. An on-demand incremental updater preserves missing-only defaults and supports source-window re-syncs. No selected source contains October 2026 returns as of 1 November 2026; the UI marks those cells unavailable. The GitHub Pages build, homepage route, year focus interaction, month metrics, and expanded phone-width layout were reviewed locally. Public deployment will be claimed only after the remaining requested data scope is resolved, the user-approved release is pushed, the Pages workflow succeeds, and the live route is verified.
