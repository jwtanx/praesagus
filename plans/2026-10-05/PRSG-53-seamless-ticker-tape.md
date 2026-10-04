# PRSG-53 Seamless ticker tape

Type feature · Modules frontend · Owner Engineer · Priority P1 · Effort S (0.5–1.5 days) · Impact medium: completes human request9 for continuous ticker browsing.
Created2026-10-05 MYT. Explicit overnight existing-backlog authority. Frozen basebb1d1346aecb1dc32784c4d3ab641e8c63866209; initial tree clean. PRSG52 accepted/pushed/deployed.

## Reproduction and accepted outcome
Current tradingview.js tick uses cosine oscillation, reversing at ends. Human requested seamless ticker scrolling. Replace automatic ping-pong with a continuous one-direction loop that visibly connects the last ticker to the first without a blank gap or abrupt screen jump. Keep slow consistent movement and all existing pause/reduced-motion/manual/lifecycle guards. No chart/data/financial semantic changes.

## Scope and safeguards
Only tradingview.js, index.html (minimal tape CSS/help and updated content SHA script version), tests/tradingview_checks.cjs (change only obsolete oscillation assertions; retain unrelated mapping/lifecycle/pause/safety tests), new tests/ticker_tape_loop_checks.cjs and ticket metadata. No template/report/schema/calendar/ledger edits. Exactly50 canonical supported choices, no duplicate accessibility/tab order or duplicate widget loads. If using visual repeated copies, hide them from accessibility/tab sequence and route clicks to the same canonical ticker; selection indication consistent, keyboard navigation canonical and no aria-hidden focus. Escape stops session motion; hover/focus/held pointer/touch/wheel/manual interaction pauses; idle resumption5s after release, not while held. No move when hidden/offscreen/reduced-motion, no overflow when insufficient items, no active loops/timers after update/hide/destroy. Resize and report switch reset/recalculate safely. Preserve original view/query/date behavior,44px hit targets and all curated symbol/URL identity/safety/unknown handling.

## Verification
New deterministic rAF fixture must cross at least3 complete cycles and verify seamless wrap invariant at variable item widths, resizing, one/no items and large frame gap; repeated visual choice interaction maps one canonical symbol;50 canonical choices/no duplicate accessible tabstops; selected styling and keyboard guards; all lifecycle/pause/reduced motion safety regressions. Existing tradingview_checks motion expectation may change only with documented semantic reason. Independently update script SHA first12hex and retain chart_asset_version_checks rejection tests. Commands: node tests/ticker_tape_loop_checks.cjs; node tests/tradingview_checks.cjs; node tests/chart_asset_version_checks.cjs; node tests/daily_report_viewer_checks.cjs; node tests/report_navigation_checks.cjs; node tests/report_date_navigation_checks.cjs. Lead real browser desktop/mobile motion+manual/keyboard review, with external chart/data availability limitation.

## When it's considered done
- [x] PRSG-53-D1: Continuous loop and focused/existing regression commands pass with evidence.
- [x] PRSG-53-D2: Lead independently reviews full scope, changed old assertions and real-browser desktop/mobile tape behavior.

Engineer leaves D2/review pending; no commit/push or private schedule/registry changes. Preserve any concurrent dirty scope. Escalate implementation requiring extra paths; no expanding silently.


## Engineer implementation notes — 2026-10-05 MYT

The tape moves at 12 pixels/second with a measured content-plus-gap period and modulo wrap. Fractional bounding rectangles retain subpixel widths; the existing 64ms frame-gap cap remains. Overflowing lists receive one visual span per canonical button, with matching font/width, hidden accessibility semantics and no tabstop. Visual clicks map to the original row; copies reflect selection without duplicate aria-pressed controls or chart loads. The 50 canonical report choices remain first in the DOM and keyboard navigation stays among them. Nonoverflowing, single/empty lists have no copies or motion.

Window and element resize rebuild measured copies; opening Technical analysis remeasures even without ResizeObserver. Report updates reset tape, hiding clears idle/widget timers, and destroy disconnects both visibility and size observers/listeners and ignores late rebuild callbacks. Existing hover, focus, held pointer/touch, manual idle, visibility, reduced-motion and persistent Escape guards remain.

Only the obsolete cosine reversal test block and its output description changed in the existing TradingView suite: a 704px mocked period (700px content + 4px gap) must advance continuously through three wraps at 12px/sec. Mapping, safety, keyboard, pause, held-contact, widget lifecycle and nested viewer checks are unchanged. The new fixture measures variable fractional item widths, crosses three cycles before and after resize, verifies the modulo displacement invariant and capped large gap, 50 canonical buttons and inaccessible nonfocusable copies, copy click/selection mapping, canonical End focus, reduced motion, no-overflow/single/empty cases and update/hide/destroy cleanup.

Index changes are limited to copy selection styling, one-direction help text and content SHA version `8905c00408c9`. No report JSON/calendar/ledger/schema/template/schedule/private registry changes. Actual browser appearance at the wrap, touch/manual scrolling and native keyboard usability remain Lead verification; deterministic geometry does not prove pixel continuity or hosted chart/data availability. No external scripts loaded by tests.


## Engineer delivery evidence

Status review; D1 demonstrated, D2 and review remain pending. All six final commands exited 0 from repository root using Node v26.7.0 and existing isolated jsdom26:

- `node tests/ticker_tape_loop_checks.cjs`
- `node tests/tradingview_checks.cjs`
- `node tests/chart_asset_version_checks.cjs`
- `node tests/daily_report_viewer_checks.cjs`
- `node tests/report_navigation_checks.cjs`
- `node tests/report_date_navigation_checks.cjs`

No failing replay observed in the initial delivery; the independent review regression below subsequently exposed an untested browser-readback case. Final review added remeasurement on opening and a destroyed guard, followed by a complete six-command replay. Six-path manifest validation and `git diff --check` passed. No commit/push performed. Lead retains independent review, real browser desktop/mobile loop and interaction checks, D2 acceptance and integration.


## Quantized scroll readback correction

Lead review found that rereading `scrollLeft` each frame loses increments below one pixel when browser readback rounds to an integer. Added a quantized setter/getter to the new fixture; its accumulated-movement assertion failed against the initial implementation. Motion now accumulates a logical fractional offset independently across frames, synchronizing from the actual scroll position on resume/rebuild. The new regression crosses three cycles at each of two fractional-width layouts, bounds actual readback within half a pixel of expected logical position and bounds forward/wrap behavior. Manual scrolling to 500px resumes from that actual value; a long resumed frame gap remains capped at64ms. No old pause/lifecycle guards or unrelated assertions changed. Asset version updated to `8905c00408c9`. D2 remains pending.

All six exact Node commands listed above were replayed after this correction and final hash update, each exit0. Six-path manifest validation and `git diff --check` passed again. No commit/push; browser review and D2 remain with Lead.

## Lead acceptance — 2026-10-05 MYT

Status complete; D2 independently accepted. Lead independent review 2026-10-05 MYT: all six exact Node commands passed exit0; full six-path diff and obsolete-reversal-only assertion review. CUA desktop1280/mobile390: 50 canonical buttons/50 hidden copies, matching original/copy widths and3368.1953125px period; forward64→416.5px, mobile End focuses canonical MY5285 (no hidden focus); focus release resumes3160px and wraps to8px showing SPY/QQQ/IWM, page width390; viewport reset. Rounded-readback defect corrected with failing-before/passing-after regression. Browser observations verify movement/wrap and geometry, not frame-by-frame pixel capture or external quote freshness.
