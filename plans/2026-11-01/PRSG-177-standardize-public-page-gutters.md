# PRSG-177 — Standardize Public Page Content Gutters

Type: bug · Modules: frontend · Owner: Engineer · Priority: P2 · Effort: XS (<0.5 person-day) · Impact: medium: prevents edge-clipped content and aligns all public pages.

## Objective

Fix Daily Market Brief's missing left/right content padding and standardize the content container width and outer gutter across the homepage, Daily Market Brief, Seasonality, and Tickets.

## Reproduction and expected behavior

On Daily Market Brief, the shared navigation is inset but the page heading, report controls, and cards begin nearly flush against the viewport. Its inline CSS contains a malformed selector (`header,main,footer,max-width:...`) so the intended layout declarations are ignored. All four public pages should align primary content to the shared navigation container and retain a consistent responsive outer gutter.

## Approach

Add a reusable `.praesagus-page-content` rule to the shared public-site stylesheet. Apply it to each page's main content shell and replace page-specific horizontal container sizing/padding that conflicts with the common rule. Preserve page-specific vertical spacing and internal card padding. Repair Daily Market Brief's malformed selector and keep its in-page toolbar usable.

## Choices

Align page content to the same 1680px maximum width as the shared navigation, with 24px outer gutters on desktop and 12px on compact screens. Keep vertical spacing and component-level padding specific to each page.

## Findings

The Daily Market Brief stylesheet had `header,main,footer,max-width:...` instead of a valid selector block, so the browser ignored the intended width and padding declarations. The homepage, Seasonality and Tickets each had independent container rules, while the report toolbar had a separate narrower width.

## Tradeoffs

The shared content class is coupled to the shared navigation stylesheet, which keeps the two aligned and avoids additional CSS assets. Future static and Vite-rendered public pages must load the shared stylesheet and apply the class to their main content shell.

## Scope

Base SHA: `a0c6651dad4f571178e562bf36d82e615e2aebf3`. Allowed paths:

- `artifacts/shared/site-navigation.css`
- `artifacts/index.html`
- `artifacts/daily-market-brief/index.html`
- `artifacts/tickets/index.html`
- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `docs/PUBLIC_SITE_NAVIGATION.md`
- `plans/README.md`
- `plans/2026-11-01/PRSG-177-standardize-public-page-gutters.md`
- `plans/2026-11-01/PRSG-177.harness.json`

Protected: all other paths. Preserve page content, seasonality data, report behavior, ticket data, and shared navigation behavior.

## When it's considered done

- [x] PRSG-177-D1: Daily Market Brief has a valid content container and no longer renders flush to the viewport edge.
- [x] PRSG-177-D2: Homepage, Daily Market Brief, Seasonality, and Tickets use the same reusable max-width and responsive horizontal gutter aligned with the navigation.
- [x] PRSG-177-D3: Pages build, the exact changed-path scope validates, and the diff has no whitespace errors.

## Checks

- `npm run build -- --mode pages` from `frontend/`: passed (Vite 5.4.21, 52 modules transformed).
- Local static preview of Daily Market Brief: page and report content loaded with the shared navigation.
- Exact-path `validate_ticket.py`: passed for all 10 allowed changed paths.
- `git diff --check`: passed.

## Status

Implementation and local verification complete; review pending.
