# PRSG-173 — Seasonality Ranking and Selection UI

Type: feature · Modules: frontend · Owner: Engineer · Priority: P2 · Effort: XS (0.25–0.45 person-day estimate) · Impact: medium-high for visitors comparing monthly leaders and selecting chart series.

## Objective

Keep the heatmap search and sort controls side-by-side, automatically sort sector rows when a month is selected, distinguish rank-one through rank-five leaders and laggards with progressively toned gradients, and replace the selected row's left stripe with a cleaner selection treatment.

## Expected behavior

- Search and sort controls stay on one horizontal line at desktop and tablet widths, and share a row on mobile when the viewport allows.
- Selecting a month automatically orders rows by that month's return, highest to lowest. The visitor can still choose alphabetical or opposite return order.
- The best and worst official sectors receive rank-specific gradient treatments from rank one through five; ranking order remains clear.
- The selected sector has a subtle outline, a softly tinted name cell, and a compact check marker. Its existing `aria-pressed` state remains.

## Baseline and scope

The existing section heading allows search and sort controls to wrap, month selection does not change the default source order, and the selected row uses a bright inset left stripe. Ranking bars use the same gradient at every rank.

Base: `374f77b7e79942b77fcf879067c93e8d2145b882`.

Allowed paths:

- `frontend/src/pages/Seasonality.tsx`
- `frontend/src/pages/Seasonality.css`
- `plans/README.md`
- `plans/2026-11-01/PRSG-173-seasonality-ranking-and-selection-ui.md`
- `plans/2026-11-01/PRSG-173.harness.json`

Protected: all other paths. Keep source datasets, ranking calculations, and return methodology unchanged.

## When it's considered done

- [x] PRSG-173-D1: Search and sort controls remain horizontal on desktop/tablet and use a two-column row when mobile width permits.
- [x] PRSG-173-D2: Selecting a month automatically sorts the heatmap rows by return descending; manual sort choices still work and deselecting the month restores source order.
- [x] PRSG-173-D3: Top and bottom sectors have rank-specific gradient shades in both ranking bars and heatmap name cells.
- [x] PRSG-173-D4: Selected sector uses a whole-row outline, name-cell tint, and check marker without the detached left stripe; the pressed state remains accessible.
- [x] PRSG-173-D5: Standalone Pages build and ticket scope validation pass.

## Findings

- The existing month ranking already provides stable rank order and filters to official industries. Reusing those ranked arrays provides rank positions for color emphasis in the heatmap without changing return values.
- Designer review recommended an outline around the whole row, a tinted name cell, and a small check marker. This keeps the current selected-row state clear without relying on color alone; `aria-pressed` continues to expose selection state.

## Approach

Force the control group to stay on a single flex row above mobile layout rules. When selecting a month, set the table sort to return descending; when deselecting it, reset a return sort to source order. Map the top and bottom five sector codes to their rank and apply rank-specific green/red gradients to their name cells and ranking bars. Replace the selected row's left box-shadow stripe with a soft full-row outline, name-cell tint, and check marker.

## Choices

- Ranking gradients use five progressively softer shades so rank one stands out and rank five remains legible.
- The check marker is decorative because the row button already exposes its state through `aria-pressed`.
- User-selected alphabetical or ascending order remains respected after month selection; the default month selection uses descending return order.

## Tradeoffs

The rank gradient is strongest in the sector name cell, leaving each monthly return cell's heatmap color readable. If the search filter matches fewer than ten sectors, existing split ranking behavior shows only the available distinct top and bottom rows.

## Checks

- `npm run build -- --mode pages` from `frontend/`.
- `python3 scripts/planning/validate_ticket.py plans/2026-11-01/PRSG-173.harness.json` with every changed path.
- `git diff --check`.
- Design review recommended a whole-row outline, tinted name cell, and check marker; this replaces the left stripe and retains `aria-pressed`.
- Code review: month selection defaults to return-descending order; deselection resets an active return sort to source order, and manual name/return choices remain available.

## Status

**Implementation and local verification complete; publication pending.** The standalone Pages build passed; source series and ranking calculations remain unchanged.
