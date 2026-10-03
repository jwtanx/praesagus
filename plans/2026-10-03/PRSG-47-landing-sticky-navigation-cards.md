# PRSG-47 · Sticky homepage navigation and tappable cards

Type: bug · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day) · Impact: medium-high

## Why
Human requests6 and7: homepage menu scrolls away and dashboard cards require tapping small links rather than the card. Reproduce on current landing at45ba7d3: header has no sticky positioning and products are articles with nested links.

## Approach
Keep the homepage header sticky at top with opaque background and suitable stacking. Convert each product into one semantic whole-card anchor with the same report/technical URL and accessible heading; no nested interactive controls. Preserve explanatory text, disclaimer, utility link and native keyboard/touch navigation. Subtle hover lift and dim pointer-follow glow use local CSS/JS without dependencies or network calls. Pointer updates use requestAnimationFrame or equivalent bounded coalescing; cancel/reset on leave. Touch needs no hover. Reduced-motion disables animated lift and cursor tracking; keyboard focus remains visible. Preserve valid responsive layout at390 and1280px and prevent whole-page horizontal overflow.

## Options and decision
Whole-card native anchors chosen over click handlers on articles: native keyboard/open-in-new-tab semantics and no-JS navigation. CSS-only centered glow is a fallback when pointer tracking is unavailable. No report/data/TA changes in this ticket; report section sticky progress belongs to a subsequent bounded ticket.

## Frozen scope
Base45ba7d33f1c7e66d6883a32d8331cb207e833c2a. Exact five paths: landing HTML, new dedicated landing DOM tests, existing ticket dashboard tests, this spec and manifest. Lead-approved amendment: existing landingChecks forbids every script, conflicting with requested local pointer glow. Change only that landing assertion to reject external scripts/dependencies and preserve other checks; dedicated tests must cover local behavior, cleanup and no-JS native links. No reports, ticket viewer, ingestion, skills, schedules, new dependencies or deployment commands.

## When it's considered done
- [x] PRSG-47-D1: Dedicated landing checks and existing dashboard regressions pass, including native card links, sticky style, focus, pointer cleanup/reduced-motion and mobile layout rules.
- [x] PRSG-47-D2: Lead independently reviews all five paths and accepts implementation, distinguishing DOM/style checks from real browser verification.

## Engineer evidence and limitations
node tests/landing_dashboard_checks.cjs passed with existing jsdom26 runtime; /tmp/PRSG-47-landing.txt. Native links with/without JS, sticky/focus/mobile CSS rules, frame coalescing and clamped coordinates, leave/cancel/blur/touch cleanup, runtime preference changes, reduced motion/coarse pointer and missing media/RAF fallback. DOM/style checks do not measure browser hit testing, scrolling or horizontal overflow.
node tests/ticket_dashboard_checks.cjs passed; /tmp/PRSG-47-dashboard.txt. Only approved obsolete no-script assertion changed to reject external scripts; all other dashboard coverage unchanged.
First landing replay failed because CSSOM exposes min-width via getPropertyValue, not camelCase; assertion corrected while preserving mobile constraint coverage. Transcript retained /tmp/PRSG-47-landing-first-replay.txt. No external scripts/dependencies, network calls, report/TA/ticket-viewer/ingestion/skills/schedule edits, commits or pushes. Lead independent acceptance and real-browser review remain pending.

## Lead acceptance
Independently reviewed all five changed/new paths against45ba7d3. Both exact node commands above replayed with existing jsdom26 and passed. Native whole-card anchors keep original routes and keyboard/no-JS behavior; local glow is bounded, clamped and cancels on leave/cancel/blur/touch/preferences. Opaque sticky header and mobile/reduced-motion styles present. Test amendment is confined to approved obsolete landing script guard. Accepted implementation; live browser scrolling, hit testing, overflow and deployment still require separate verification, not claimed from DOM tests.
