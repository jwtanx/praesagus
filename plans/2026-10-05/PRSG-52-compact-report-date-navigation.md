# PRSG-52 Compact report date and day/week navigation

Type feature · Modules frontend · Owner Engineer · Priority P1 · Effort S (0.5–1 day) · Impact medium: quicker browsing of saved reports, completing human request10.
Created 2026-10-05 MYT. Lead accepts this scope under explicit overnight existing-backlog authority. Frozen base43c9eeed5e3996335f3a1808d0bcd70235553613. Initial tree clean. No concurrent owner of viewer.

## Problem and outcome
Current date picker occupies a standalone block without day/week quick arrows. Add a compact, accessible date control row with previous/next saved report and previous/next week buttons, retaining date-picker availability rules and report/calendar/technical lifecycle.

## Accepted behavior
Day arrows choose nearest available date strictly before/after selected date. Week arrows target selected date minus/plus7 UTC calendar days, selecting nearest saved report at or beyond that target in the requested direction; disable if none. This rule skips missing days without silently moving backward on Next. Accessible labels distinguish day/report vs week; use native buttons with visible disabled state. Compact date label may show date/weekday; retain complete date in accessible label. Existing picker remains usable and dates absent from index remain disabled. Sort/deduplicate date candidates; do not mutate index. Preserve query params/current view, request cancellation and error display. No fabricated report fetches, no live data/providers, no schema/calendar/ledger edits. On malformed/failed index navigation disabled. Retain keyboard and mobile touch access, no horizontal overflow at390px. Close picker with Escape/outside interaction if already supported; avoid unrelated redesign.

## Scope and checks
Only artifacts/daily-market-brief/index.html, new tests/report_date_navigation_checks.cjs, and this spec/manifest. Preserve all other existing tests without edits. Reuse jsdom fixture pattern and existing /tmp dependency. Checks: node tests/report_date_navigation_checks.cjs; node tests/daily_report_viewer_checks.cjs; node tests/report_navigation_checks.cjs; node tests/tradingview_checks.cjs; node tests/chart_asset_version_checks.cjs. New fixture covers unordered/duplicate/missing dates, day/week boundaries/month/year/leap date, absent target/failed index, URL/current view, stale request race and keyboard/native buttons. Real browser desktop/mobile layout check required by Lead, with explicit limitations.

## When it's considered done
- [x] PRSG-52-D1: Focused navigation behavior and all existing viewer/chart checks pass with recorded commands/results.
- [x] PRSG-52-D2: Lead independently reviews complete scope and verifies desktop/mobile date control usability before acceptance.

Engineer hands back changed paths, exact tests/results, failure lessons and limitations. Do not commit/push or alter schedule/registry; Lead integrates after independent review.


## Engineer delivery — 2026-10-05 MYT

Status: review; D1 demonstrated, D2 pending independent Lead acceptance. Changes stay within the exact four allowed paths. The compact row provides native previous/next saved-report and week buttons with accessible labels, visible disabled states and 44px targets. It preserves existing report labels. Mobile styling reduces date-button padding/font size, permits wrapping, and anchors the popup to the complete row. Real 390px layout, pointer usability and native keyboard activation remain for Lead browser verification.

Sorted unique date candidates are computed without changing the index. Day arrows choose strict adjacent saved dates; week arrows use seven UTC days and choose the nearest saved date at/beyond the target in the requested direction. Buttons reuse `chooseReportDate` and existing report loading, cancellation, stale response protection, errors and current view/query handling. Invalid/failed index data is never retained as usable navigation data. No report JSON, calendar, chart module, existing tests, ledger, schedules or private registry changes.

Exact commands run from repository root, Node v26.7.0, existing isolated jsdom26; all final runs exited 0:

- `node tests/report_date_navigation_checks.cjs`
- `node tests/daily_report_viewer_checks.cjs`
- `node tests/report_navigation_checks.cjs`
- `node tests/tradingview_checks.cjs`
- `node tests/chart_asset_version_checks.cjs`

Failure lesson: initial abbreviated month text failed the protected viewer expectation (`30 Sept 2026` versus existing `30 September 2026`), including TradingView's nested viewer replay. Preserved existing index labels rather than changing protected tests; final replays passed. Focused cases include unordered/duplicate/missing dates, exact/gapped week targets, leap/month/year transitions, absent targets, malformed/failed index, single saved date, picker availability/closing on selection, native focus, report errors, URL/custom query and technical/calendar view preservation, aborted fetch signal and late response rejection. These offline DOM fixtures do not prove browser layout, native Enter/Space activation or deployment freshness. Escape/outside picker closing was not present in the original implementation; unchanged.

No commit or push performed. Lead owns independent four-path review, desktop/mobile usability verification, D2 acceptance and integration.

## Lead acceptance
Lead independently reviewed all four paths and replayed all five exact Node commands successfully on2026-10-05 MYT. CUA local browser390x844 and1280x800: Enter previous report Oct4->Oct3; full date accessible;44px touch buttons; mobile document390/no overflow, popup16..316within390, desktop1280/no overflow; dateOct4 picker selection updates URL and closes. Week controls disabled where history has no target; gaps/leap/year/races covered fixture. Real physical touch and external widget data unverified. Existing Python-wide CI failing independently; not claimed fixed by UI ticket.
