# PRSG-96 — Responsive prediction cards and status colors

Type: feature · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high — readable instrument evidence without phone horizontal scrolling.

Created2026-10-12MYT. Accepted by human approval of Designer responsive layout and four-state chip/card colors; Lead owns review/integration. Frozen base32c9ee20678611400b512b36d4a461e035e07390.

## Accepted scope

Implement Designer HANDOFF.md and PREDICTION-COLORS.md under /Users/jwtan/Documents/praesagus-design/2026-10-12-mobile-instruments. Phone<600px stacked cards;600–1023px two columns;desktop>=1024px centered1120px table. Preserve complete financial scenario/sources, actual universe order/filter/pagination and historical/date behavior. One existing interactive prediction chip per instrument, target/range plus adjacent date/horizon, same guarded predictionState. Match chip and decorative4px side strip: Bullish#66d6a4 fill#10281f;Bearish#ff8e8e fill#301a20;Sideways#f4c26b fill#302714;Unrated#a5b2c2 fill#1b2430. Explicit labels, neutral cards, distinct blue focus. Never derive colors from quote movement/indicators. Demo symbols/targets never enter production.

Separate accessible observation disclosure retains ALL current provenance, exact timestamps and unknown-reference/failure fields. No provider branding in rendered labels, currency/session inference or target fabrication. Preserve predictionState/renderPrediction guards; no projection/schema/report data changes. Full stored scenario text remains.

One native labelled Report section selector replaces redundant slider/Prev/Next/section-tabs stack; preserve actual section IDs/order and existing history/deep-link semantics. Dynamic sticky-height scroll offset+16px. Target120px/basefont<=130px mobile/tablet, allow growth at200%zoom. Existing hero/date/disclaimer/summary and main menu remain, no global redesign.

Engineer uses existing isolated managed checkout; edits only manifest allowlist. Lead owns planning input file and commits/push. Return uncommitted patch/evidence; ask Lead before scope widening. Designer reviews implementation visuals, Trader owns any changed financial wording. No provider/credentials/Keychain access, new dependencies or report/ledger/calendar edit.

## When it's considered done

- [ ] PRSG-96-D1: Responsive cards/table, status palette and navigation implement accepted design with unchanged financial/provenance guards.
- [ ] PRSG-96-D2: Focused regressions and390/768/1440px keyboard/tap/200%zoom/reducedmotion/contrast/history/error checks pass.
- [ ] PRSG-96-D3: Designer visual review and Lead independent full-scope/preservation review, commit/push and Pages/live delivery verified.

## Checks

Run node tests/compact_report_viewer_checks.cjs and node tests/daily_report_viewer_checks.cjs with existing jsdom environment. Run approvedPython3.11 -m pytest -q tests/test_daily_report.py, bytecode/cacheoff. Add meaningful DOM regressions in allowed existing files; preserve nonpresentation safety coverage. Browser checks: no document horizontal overflow; complete names/scenarios; both disclosures independently keyboard/tap accessible with visiblefocus; no duplicate IDs/chips; missing/history/supported/null/error fixtures; exact timestamps remaincopyable; filters/date/section/navigation preserved. Contrast body>=4.5:1 andUI/focus>=3:1. Ticketvalidatorallchangedpaths and mandatoryhooks enabled. No user-study claim.
