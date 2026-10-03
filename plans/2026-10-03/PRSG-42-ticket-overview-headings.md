# PRSG-42 · Ticket overview heading extraction

Type: bug · Modules: harness, frontend · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-days estimate) · Impact: medium-high

## Why the ticket is created?
User sees Why but empty Approach/Options/Findings/Tradeoffs. Specs use combined headings not recognized by exact audit aliases.

## Approach, choices and tradeoffs
Reuse recorded source sections verbatim through explicit aliases, not invented summaries or manually edited audit JSON. Combined approach/options/tradeoffs may appear in several overview fields: repetition is preferable to hiding recorded rationale. Add accepted handoff/limits/validation aliases. Explicit manifest fields still override sources; genuinely absent decisions remain absent rather than fabricated. No fuzzy substring matching.

## Findings
Lead replayed audit regressions:47 passed in7.26s, including combined headings and historical/explicit context/reference safety. Fix affects generated audit on next main push; no browser or deployed-page claim yet. Local small fix implemented and reviewed without delegated overlap; scope contract records exact four paths before delivery.

## When it's considered done
- [x] PRSG-42-D1: Audit extraction regressions pass.
- [x] PRSG-42-D2: Lead source-backed alias and scope review accepted.

