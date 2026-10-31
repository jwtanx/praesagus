# PRSG-171 — Seasonality Site Navigation

Type: feature · Modules: frontend · Owner: Engineer · Priority: P2 · Effort: XS (0.25–0.45 person-day estimate) · Impact: medium for visitors navigating the standalone Pages site.

## Objective

Add a report-style header to the standalone GitHub Pages seasonality explorer so visitors can return to the Praesagus homepage or open reports, technical analysis, and ticker forecasts.

## Expected behavior

On the standalone `/praesagus/seasonality/` page, show a Praesagus brand link to the site homepage, plus links to reports, technical analysis, and ticker forecasts. Match the report page's compact responsive navigation: desktop links stay visible, and mobile links are available from an accessible menu button. Keep the in-app seasonality route unchanged because it already uses the shared app navigation.

## Baseline and scope

The GitHub Pages build renders `Seasonality` without the shared `Layout`, so its standalone route lacks navigation. The report page exposes the technical and ticker views at `../daily-market-brief/?view=technical` and `../daily-market-brief/?view=tickers`.

Base: `85d3c523cde4bf848c8595851af517c6155ab715`.

Allowed paths:

- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `plans/README.md`
- `plans/2026-11-01/PRSG-171-seasonality-site-navigation.md`
- `plans/2026-11-01/PRSG-171.harness.json`

Protected: all other paths. Preserve existing seasonality data, controls, and the app's shared sidebar.

## When it's considered done

- [x] PRSG-171-D1: Standalone seasonality page has homepage, reports, technical analysis, and ticker forecast destinations.
- [x] PRSG-171-D2: Desktop navigation is visible; mobile navigation opens and closes with an accessible menu control.
- [x] PRSG-171-D3: Pages build succeeds and ticket manifest validates against the complete changed path list.

## Findings

- The shared in-app `Layout` already provides navigation for local application routes. The missing navigation is specific to the GitHub Pages build, which mounts the seasonality page by itself.
- The report site's existing view query parameter selects its technical analysis and ticker forecast sections, allowing direct links without changing the reports application.

## Approach

Render a small navigation bar only when Vite builds the standalone Pages mode. Reuse ordinary relative links to the existing homepage and report views. Keep the shared application layout responsible for local app navigation.

## Choices

- Include both a brand link and a clearly named Home link, alongside Reports, Technical analysis, and Ticker forecasts.
- Keep all destination links visible at desktop widths; collapse them behind a button below 700px, matching the report page's mobile navigation behavior.
- Use semantic navigation and button state via `aria-expanded` and `aria-controls` so assistive technology can identify the menu state.

## Tradeoffs

The standalone page has its own compact navigation markup and styles instead of reusing the React application sidebar, since that sidebar is not part of the Pages build. Report destinations use the report page's existing `view` query parameter, so those links depend on the report site continuing to support it.

## Checks

- `npm run build -- --mode pages` from `frontend/`: passed; built the standalone seasonality page and updated CSS/JS assets.
- `python3 scripts/planning/validate_ticket.py plans/2026-11-01/PRSG-171.harness.json --changed-file frontend/src/pages/Seasonality.tsx --changed-file frontend/src/pages/Seasonality.css --changed-file plans/README.md --changed-file plans/2026-11-01/PRSG-171-seasonality-site-navigation.md --changed-file plans/2026-11-01/PRSG-171.harness.json`: passed.
- The first commit hook reported the required decision-context sections missing from this ticket; those sections were added before the passing hook retry.

## Status

**Implementation and local verification complete; publication pending.** The standalone Pages build includes the new header; no deployed-site check has been performed for this change.
