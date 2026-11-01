# PRSG-174 — November and December Calendar Publication

Type: chore · Modules: financial-data, docs · Owner: Trader · Priority: P2 · Effort: XS (0.5–1 person-day) · Impact: medium for scheduled-event visibility; no forecast claim.

## Objective

Review the source-backed November and December 2026 monthly calendars and publish them so visitors can view both months in Praesagus Financial Calendar.

## Approach

Reuse the committed monthly ledgers and existing shared calendar viewer. Trader verifies official schedules and timezone mappings; Lead appends any supported corrections with actual discovery time, then validates local rendering and publishes through GitHub Pages. Keep the two monthly ledgers independent and preserve their revision history.

## Choices

Use the current month as the latest stored schedule, with the existing previous/next controls for month navigation. Keep new public calendar events in the shared monthly JSON ledgers; do not insert calendar-only pseudo-reports into `reports.json` or rewrite old report snapshots. Represent MYT overnight boundaries with date spans and retain U.S. venue dates in the event detail.

## Findings

The report viewer already loads `../financial-calendar/YYYY-MM.json` independently of a report's own saved date and supports month navigation. The original ledgers had a Thanksgiving MYT range omission, a Christmas U.S.-date offset, no separate December FOMC meeting span, and lacked DOSM's December petroleum and natural gas release. Trader reviewed primary schedules and found no listed cancellation/rescheduling notice. The corrections and new event were appended at `2026-11-01T08:41:04+08:00`; DOSM publication time remains unspecified. The local DOM replay renders November, December, date-spanning holidays, the FOMC span, DOSM event details, and HTTPS source links.

## Tradeoffs

The monthly ledgers may include superseded revisions, so consumers must use the latest revision per event ID; the viewer already does this. MYT date spans can make an overnight U.S. market closure appear on two local dates, while titles/details preserve the one official U.S. session date. Publication remains incomplete until the main Pages workflow succeeds and the hosted page is checked.

## Scope

Allowed paths:

- `artifacts/financial-calendar/2026-11.json`
- `artifacts/financial-calendar/2026-12.json`
- `plans/README.md`
- `plans/2026-11-01/PRSG-174-november-december-calendar-publication.md`
- `plans/2026-11-01/PRSG-174.harness.json`

The site already loads the latest stored calendar independently from a selected report and has previous/next month controls. The latest stored view opens the current MYT month; December is available using next month. Keep report history and the eligible report index unchanged. Preserve source links, source timezones, recorded availability and explicit unknown publication times. Correct events only with source-backed appended revisions using actual discovery time.

## When it's considered done

- [x] PRSG-174-D1: November and December ledgers independently pass the monthly calendar schema validator.
- [x] PRSG-174-D2: Trader reviews official schedules, event dates and MYT conversions; publication-time gaps stay explicit.
- [x] PRSG-174-D3: Lead accepts the final ticket scope and records the publication disposition.
- [x] PRSG-174-D4: Published Pages calendar opens to November and month navigation loads December with event details and source links.

## Current evidence and status

After Trader review and append-only corrections, the ledgers contain 35 November revision rows (33 active event IDs) and 33 December revision rows (32 active event IDs). The monthly validator passes. The review confirmed the checked BLS/BEA dates and times, BNM Nov 5 decision time, NVIDIA Nov 18 MYT conversion, and found no official cancellations/rescheduling. DOSM release times remain unknown where not published. Corrections recorded at 2026-11-01 08:41:04 MYT: Thanksgiving closure spans Nov 26–27 MYT; Christmas closure uses the Dec 25 U.S. venue date and spans Dec 25–26 MYT; a Dec 8–9 U.S.-date FOMC meeting span is listed separately from the Dec 10 MYT decision; DOSM petroleum and natural gas Q3 statistics are added for Dec 3 with time unconfirmed. The earlier rows remain in the append-only ledgers.

Trader review source links: [BLS](https://www.bls.gov/schedule/2026/), [BEA](https://www.bea.gov/news/schedule), [BNM](https://www.bnm.gov.my/monetary-stability/mpc-meetings), [NVIDIA](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Third-Quarter-Financial-Results/default.aspx), [NYSE](https://www.nyse.com/trade/hours-calendars), [Federal Reserve December calendar](https://www.federalreserve.gov/newsevents/2026-december.htm), [DOSM November](https://www.dosm.gov.my/portal-main/arc?search_month=11&search_year=2026), [DOSM December](https://www.dosm.gov.my/portal-main/arc?search_month=12&search_year=2026). Trader separately notes that entry `recorded_at` is ingestion availability, not source retrieval time.

The static report viewer already implements the shared calendar loader and previous/next controls. A local DOM replay confirmed the November latest schedule, December navigation, event details and official source links. Lead reviewed the exact calendar and ticket scope after Trader corrections. The final local viewer replay passed: the latest schedule opened November, navigation loaded December, and tested closure spans, the December FOMC period and DOSM release displayed their details and source links.

GitHub Pages deployment for commit `50d3f6c470034b34e16a929db96e1ed93a8515ef` succeeded in workflow run [41258319651](https://github.com/jwtanx/praesagus/actions/runs/41258319651). The hosted [November calendar JSON](https://jwtanx.github.io/praesagus/financial-calendar/2026-11.json), [December calendar JSON](https://jwtanx.github.io/praesagus/financial-calendar/2026-12.json), and [financial calendar page](https://jwtanx.github.io/praesagus/daily-market-brief/) returned HTTP 200. Public payload checks confirmed 33 active November IDs and 32 active December IDs, including the revised holiday ranges, December FOMC span, and DOSM release. The local calendar viewer replay confirmed dates, event details and source links.

Status: **complete; source review, deployment and hosted-file verification accepted.**
