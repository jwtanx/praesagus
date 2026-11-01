# PRSG-175 — Fix Seasonality Heatmap Overlap and Add Ticket Navigation

Type: bug · Modules: frontend, docs · Owner: Engineer · Priority: P2 · Effort: S (0.5–2 person-days) · Impact: medium for mobile browsing and site navigation.

## Objective

Prevent text in the seasonality heatmap's sticky industry column from blending with colored monthly cells during horizontal overflow, and give the ticket dashboard the same responsive site navigation as the other public pages.

## Approach

Keep the heatmap's existing sticky label column, but preserve its opaque panel background beneath rank/selection gradients so cells moving underneath during horizontal scrolling cannot show through the labels. Extend the ticket page navigation to shared Praesagus destinations with an accessible mobile menu and a current-page state for Tickets.

## Choices

Preserve the existing heatmap sizing, horizontal scrolling, rank colors, data and ranking behavior. Reuse the ticket page's current sticky navigation container and offset handling, adding the shared links and menu toggle without changing the ticket dashboard's search, table or detail interactions.

## Findings

The name column is sticky while the heatmap overflows horizontally. Its rank and selection rules replace the opaque base with semi-transparent gradients, exposing the month cells underneath. The ticket page currently has only brand, Daily brief and Tickets links and lacks the collapsible menu used by the report, homepage and seasonality pages.

## Tradeoffs

The ranking tint remains visible over an opaque panel color, so the gradient is slightly less luminous while labels remain readable. The ticket navigation adds more destinations but collapses behind a menu below the mobile breakpoint.

## Scope

Allowed paths:

- `frontend/src/pages/Seasonality.css`
- `artifacts/tickets/index.html`
- `plans/README.md`
- `plans/2026-11-01/PRSG-175-seasonality-overflow-and-ticket-navigation.md`
- `plans/2026-11-01/PRSG-175.harness.json`

Protected: all other paths. Do not change seasonality data, ranking calculations, report behavior or ticket audit data.

## When it's considered done

- [x] PRSG-175-D1: Sticky heatmap labels remain opaque while horizontal scrolling through ranked and selected rows; text does not overlap colored month cells.
- [x] PRSG-175-D2: Ticket dashboard has shared home, reports, technical analysis, ticker forecasts and seasonality links, with Tickets marked current and an accessible mobile menu.
- [x] PRSG-175-D3: GitHub Pages frontend build and complete ticket-scope validation pass.

## Checks

- `npm run build -- --mode pages` from `frontend/`: passed.
- Focused ticket-page DOM inspection: passed; mobile Menu toggle updates `aria-expanded` and menu visibility, Tickets is current, and all six shared destinations are present.
- Seasonality CSS inspection: passed; the sticky label cell retains an opaque panel background while all ten rank gradients and selection treatment are set as background images.
- `python3 scripts/planning/validate_ticket.py plans/2026-11-01/PRSG-175.harness.json --changed-file frontend/src/pages/Seasonality.css --changed-file artifacts/tickets/index.html --changed-file plans/README.md --changed-file plans/2026-11-01/PRSG-175-seasonality-overflow-and-ticket-navigation.md --changed-file plans/2026-11-01/PRSG-175.harness.json`: passed.
- `git diff --check`: passed.

## Status

**Implementation and local verification complete; Lead review accepted.**
