# PRSG-33 · Compact accessible TA ticker tape with controlled slow scrolling; no invented forecast colors

Type: feature · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 estimated person-days) · Impact: high

## Why the ticket is created?

Human reports missing quote/direction evidence and oversized TA controls on October 2. Improve readability and validated data access without manufacturing forecasts.

## Approach

Replace verbose visible chip labels with emoji + ticker; retain direction meaning in accessible label/title and caption. Visually compact pills (roughly 12px text, 4px/8px inner padding) inside >=44px touch targets. Slow requestAnimationFrame scrolling only while visible and active, with hover/focus/manual guards, five-second idle resume after manual interaction, Escape stopping motion for the session, reduced-motion default off, no duplicate timers/listeners on date/view changes or destroy. No abrupt wrap: reverse smoothly at boundaries or demonstrate seamless accessible loop without duplicated focusable controls. Keep unknown gray; existing recorded scenario colors remain labeled as scenarios, not price movements. New observed quote colors depend on a separate verified quote contract, not fabricated targets. Preserve widget attribution, mapping fallback, date selection and keyboard navigation.

## Options and tradeoffs

Reuse current hosted chart and REST core rather than replace them. Compact visual controls retain accessible interaction size. Verified observations do not imply validated predictions. Private live access does not grant public redistribution rights.

## Findings

Current report has six quoted rows of fifty; targets remain unsupported. PRSG-31 core is offline-only. Authentication calendar probe succeeded, but quotes and MY access still require validation.

## When it's considered done

- [x] PRSG-33-D1: Compact spacing without stale padding override or visible motion row; five-second guarded idle resume, persistent Escape stop and existing viewer regressions pass; Lead reviews mobile/desktop rendering.

## Progress

Scope accepted by Lead from existing human authorization at base 52c60bb78e5d890b052151990a393aa581c3b4b1; implementation checks pending. Unrelated .DS_Store belongs to existing work and is excluded.


2026-10-02 MYT — Engineer implemented compact emoji+ticker labels with 12px,
4px/8px inner pills inside >=44px controls. Direction/scenario meaning stays in
accessible labels, tooltip and visible caption; unknown remains gray. Added
explicit pause/resume and one requestAnimationFrame loop with cosine reversal
(maximum approximately 12px/sec, capped frame gaps). Hover/focus, pointer/touch/
wheel/keyboard interaction, reduced-motion preference, viewport intersection,
hidden tab and inactive view guard motion. Manual pause requires explicit resume;
reduced-motion blocks motion while enabled. Dates reset position while retaining
hover/manual pause; resize restarts from current position. Destroy cancels frames,
chart timers/observer, visibility observer and removes installed listeners/button
handlers. No duplicated focusable controls or inferred price predictions.

`node tests/tradingview_checks.cjs` passed, including existing daily viewer replay,
exact compact label/accessibility/CSS sizing checks, deterministic complete motion
cycle/boundary reversal/speed, all pause guards, date/view changes, no-overflow and
cleanup. `git diff --check` passed for the three implementation/test paths.
No external scripts/network were loaded by tests; hosted chart data/coverage was
not tested. Mobile/desktop browser rendering remains Lead review-required;
jsdom asserts DOM/styles and mocked dimensions, not physical touch geometry or
real-browser scroll rounding. No commit/push/staging. Unrelated `.DS_Store` and
PRSG-34 work preserved. At Engineer handoff PRSG-33-D1/manual review remained pending. Lead subsequently accepted after independent regression replay and real localhost browser visual checks at1280desktop/390mobile; compact spacing, no motionbutton and contained tape confirmed. Hosted chart rendered; hardware heldtouch not exercised, state guarded in deterministic tests.

### 2026-10-02 MYT — Human-requested amendment accepted by Lead

Supersedes the initial visible Pause/Resume and permanent manual-pause design.
Same five paths and frozen base remain accepted. Remove the later 8px/12px outer
padding override, keep 2px outer padding/4px gap and >=44px touch region with
compact inner pills. Reduce caption/tape margins. Remove visible motion button
and redundant explanation row; retain scenario caption. Make the tape keyboard
focusable with an accessible instruction: Escape stops motion for the session,
with no automatic restart after date/view changes. Manual pointer/touch/wheel/key
interaction resumes after five seconds idle only if hover/focus/reduced-motion/
hidden/offscreen/inactive guards permit it. Reset idle timer on new interaction;
clear on update/destroy. Focused tests must assert computed outer padding, removal
of button, idle guards/timer cleanup and persistent Escape stop. Manual browser
review remains pending.

Amendment implemented: stale outer padding override and visible motion row
removed, caption/status margins reduced to 4px. Focusable tape documents Escape
via aria-describedby/aria-keyshortcuts. Five-second idle timer resets during
pointer/touch/wheel/keyboard interaction; motion resumes only through existing
safety guards. Escape clears idle work and stops motion for the session, including
later date/view changes. `node tests/tradingview_checks.cjs` passed with amended
regressions and existing viewer replay. `git diff --check` passed. Real-browser
mobile/desktop rendering remains Lead review-required; no commits/push/staging.

### 2026-10-02 MYT — Lead-accepted held-contact correction

Independent review found idle expiration could resume motion during stationary
pointer/touch contact. Scope remains the same five paths. Track active pointer
and touch identifiers explicitly; idle expiration cannot override held contacts.
Window capture handles releases/cancels outside tape. Multiple contacts and dual
pointer/touch event families remain blocked until all tracked contacts end. Release
starts a fresh five-second idle period. Window blur treats lost delivery as contact
cancellation and separately blocks motion until window focus returns.
Date updates clear pending idle work while retaining physically held identifiers
until release/cancel; this prevents date rerenders from resuming beneath a held
finger. Destroy clears contacts, timers and global listeners. Escape/reduced-motion/
hover/focus/visibility guards retain precedence. Accessible tape instruction now
mentions held-contact pause and delayed release resume.

`node tests/tradingview_checks.cjs` passed held>5s/release/cancel/multicontact/
window-blur/date/destroy regressions and existing viewer replay. Scope/whitespace
validation passed. Physical-device/mobile/desktop rendering remains Lead review;
no commits/push/staging or edits outside PRSG-33 paths.
