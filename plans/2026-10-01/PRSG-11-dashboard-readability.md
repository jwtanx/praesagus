# PRSG-11 — Dashboard readability and home navigation

Type: feature · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.3 person-days) · Impact: medium

## Accepted scope

User requests distinct colored emoji status badges, separate ticket ID and title columns, and a product home page offering Reports and Technical Analysis (coming soon), with Tickets in a bottom utility bar. Preserve audit semantics, safe text rendering, filters, links and existing report pages. Emoji badges retain readable status words so color is not the only cue. No backend, report-data or pending PRSG-9 changes.

Frozen paths and base are in PRSG-11.harness.json. Check offline DOM regressions and desktop/mobile browser layout. Lead owns release review; usability gains remain unmeasured.

## When it's considered done

- [x] PRSG-11-D1: Separate ticket/title columns and accessible distinct status badges pass regressions.
- [x] PRSG-11-D2: Product landing offers Reports, a clearly unavailable Technical Analysis area, and Tickets in the bottom utility bar.
- [x] PRSG-11-D3: Desktop/mobile layout and Lead review recorded.

## Validation evidence

Offline DOM checks passed including actual generated audit. Browser review at 1280×720 and 390×844 confirms status styling, ID/title separation, both landing destinations and ticket details. Updated times display readable MYT while retaining original timestamps. Full pytest: 147 passed; 2 existing pending PRSG-9 hook expectations fail against its changed report-title rule. No protected hook files changed. Lead review and publication remain pending; this ticket is not complete.

User refinement: replace the chooser heading with a market-research product home. Research is assigned separately in PRSG-12 and PRSG-13. The PRSG-11 JSON filename is now canonical; PRSG-10 already uses PRSG-10.harness.json. Earlier evidence applies to the superseded chooser; revised landing needs fresh checks.

Revised landing checks passed on 2026-10-01: product hero, Reports, Technical Analysis coming soon, and bottom Tickets utility bar. Actual browser widths 1280 and 390 have no page overflow. Full pytest now 173 passed after aligning the pending report-title test with its existing hook rule. Canonical filename checks are tracked by PRSG-14. Lead acceptance/publication pending.

## Lead acceptance

2026-10-01 MYT Lead integration: focused hook suite43 passed; ticket dashboard DOM replay passed; daily skill metadata valid. Lead independently reviewed shared PRSG-9/PRSG-14 hook and staged guard, revised UI source and Engineer desktop/mobile handoff. No live provider or ROI claims.
Historical pending/failure notes above are retained; this acceptance supersedes them. Shared hook test paths belong to PRSG-14, skill/title instructions to PRSG-9; Lead reviewed their combined integration.
