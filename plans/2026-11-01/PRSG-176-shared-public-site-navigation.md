# PRSG-176 — Share Public Navigation and Normalize Header Sizing

Type: feature · Modules: frontend · Owner: Engineer · Priority: P2 · Effort: S (0.5–2 person-days) · Impact: medium-high for consistent navigation and future page maintenance.

## Objective

Give the homepage, Daily Market Brief, seasonality and ticket pages the same reusable public navigation component, logo size and placement, link typography, container width, and responsive behavior. Keep page-specific active navigation and the Daily Market Brief's in-page report views working.

## Approach

Create one light-DOM custom element and a single shared stylesheet in `artifacts/shared/`. Static Pages documents load those files directly; the Vite seasonality app imports the same sources. Use explicit root and current-page attributes so each public page resolves its links and active state correctly.

## Choices

Keep the existing dark palette, labels, page destinations, active-page indication, keyboard access, and menu toggle. Set one shared maximum header width, 64px minimum bar height, 16px logo and link font size, and a 980px responsive menu breakpoint. Make report-view destinations use URL query parameters outside the report page and keep in-page switching on the report page.

## Findings

The homepage, report, seasonality and ticket pages implement separate header markup and CSS. They currently use different widths (1680px, 1168px, padded seasonality content and 1160px), logo sizes (15px to about 17px), outer positioning, and mobile breakpoints. The report page has internal view buttons and the ticket page measures its sticky header to position anchors.

## Tradeoffs

The shared custom element adds a small JavaScript dependency to these pages. Static pages need consistent relative root attributes, and the report page retains a small integration for its internal view state. The reusable element and stylesheet provide the convention for future public pages; new pages must include the custom element, shared asset imports, and appropriate `root`/`current` attributes.

## Scope

Base SHA: `a58512d89e50dbec6fd5d9ce7af7725430702224`. Allowed paths:

- `artifacts/shared/site-navigation.css`
- `artifacts/shared/site-navigation.js`
- `artifacts/index.html`
- `artifacts/daily-market-brief/index.html`
- `artifacts/tickets/index.html`
- `frontend/src/main.tsx`
- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `docs/PUBLIC_SITE_NAVIGATION.md`
- `plans/README.md`
- `plans/2026-11-01/PRSG-176-shared-public-site-navigation.md`
- `plans/2026-11-01/PRSG-176.harness.json`

Protected: all other paths. Do not change market data, report content or ticket audit records. Scope is frozen to this user-requested implementation; Lead review remains pending.

## When it's considered done

- [x] PRSG-176-D1: All four public pages use the same reusable header with matching logo size, position, link typography, bar height and container width.
- [x] PRSG-176-D2: Mobile navigation remains accessible and responsive, page-specific active state works, and Daily Market Brief view navigation still works both from direct URLs and within the page.
- [x] PRSG-176-D3: Pages build, shared markup/styles are present at the deployed paths, and the exact ticket scope validates.

## Checks

- `npm run build -- --mode pages` from `frontend/`: passed (Vite 5.4.21, 52 modules transformed).
- Responsive browser preview at 390×844: passed for homepage, Daily Market Brief, seasonality and Tickets; the shared menu opens and exposes all seven destinations. Daily Market Brief direct calendar view, the report-page calendar button, and in-page Technical analysis switching all worked.
- `node --check artifacts/shared/site-navigation.js`: passed.
- Exact-path `validate_ticket.py` and `git diff --check`: passed.

## Status

**Implementation and local verification complete; Lead review pending.**
