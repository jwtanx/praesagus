# PRSG-178 — Increase Shared Public Page Gutters

Type: bug · Modules: frontend · Owner: Engineer · Priority: P2 · Effort: XS (<0.5 person-day) · Impact: medium: keeps homepage and section layouts aligned with navigation.

## Objective

Increase and consistently apply the same left/right outer margin to the homepage, Daily Market Brief, Seasonality, Tickets, and shared navigation.

## Reproduction and expected behavior

After PRSG-177, the homepage hero and cards still render flush to the viewport edge, while the navigation remains inset. The homepage `.wrap{width:100%}` rule has the same specificity as `.praesagus-page-content` and is declared later, overriding the shared width. All page content and the navigation should use the same, visibly larger gutter on desktop and mobile.

## Approach

Increase the shared desktop gutter to 40px and compact-screen gutter to 20px for both navigation and page content. Add a more specific `.wrap.praesagus-page-content` selector so the homepage's utility width rule cannot override the shared container width. Keep the 1680px maximum width and apply the shared rule consistently to existing page shells.

## Choices

Use equal outer gutters: 40px per side on desktop, 20px per side at and below the navigation breakpoint. Keep the current 1680px content maximum, centered on wide screens.

## Findings

The homepage already has `.praesagus-page-content`, but its later `.wrap{width:100%}` declaration overrides the shared class width due equal selector specificity. The navigation and other page shells use width rules that do not conflict with this homepage selector.

## Tradeoffs

Larger margins provide more breathing room and align content edges with the navigation. At narrow widths, 20px per side leaves slightly less room for content; existing responsive layouts and horizontal table scrolling remain responsible for narrow data views.

## Scope

Base SHA: `4bd7f955350557a6e53f7f46d9db31e79553baaf`. Allowed paths:

- `artifacts/shared/site-navigation.css`
- `docs/PUBLIC_SITE_NAVIGATION.md`
- `plans/README.md`
- `plans/2026-11-01/PRSG-178-increase-shared-page-gutters.md`
- `plans/2026-11-01/PRSG-178.harness.json`

Protected: all other paths. Preserve all page content and behavior beyond outer width and gutter alignment.

## When it's considered done

- [x] PRSG-178-D1: Home page container keeps the shared width despite `.wrap` styles.
- [x] PRSG-178-D2: All public pages and navigation use matching 40px desktop / 20px compact-screen gutters.
- [x] PRSG-178-D3: Pages build, exact-path scope validates, and the diff passes whitespace checks.

## Checks

- `npm run build -- --mode pages` from `frontend/`: passed (Vite 5.4.21, 52 modules transformed).
- Exact-path `validate_ticket.py`: passed for all five allowed changed paths.
- `git diff --check`: passed.

## Status

**Complete; Lead review accepted on 2026-11-01.**
