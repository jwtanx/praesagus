# PRSG-16 — US and Malaysia full-month financial calendar

Type: feature · Modules: financial-data, frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium — readable regional monthly schedule.

Created 2026-10-01 MYT. User accepted scope; Lead reviews delivery.

## Accepted scope

Show only US and Malaysia events with country filters. Retain other-country historical source records without displaying them. Populate verified October 1–31 schedules from primary sources, including late-month US and Malaysian releases. This is a curated calendar, not an exhaustive real-time feed or scheduler. Unknown dates remain unknown. Append corrections/classification with actual availability; never backdate evidence. Default latest stored schedule is independent of report time; preserve selectable report-as-of history.

## When it's considered done

- [x] PRSG-16-D1: Country filters, latest versus historical schedule and full-month source-backed entries pass focused regressions.
- [x] PRSG-16-D2: Lead independently reviews scope and evidence.

## Lead acceptance

2026-10-01 MYT Lead independently reviewed all7 paths: original14 ledger entries identical to HEAD prefix; country validation/filter and latest/report-as-of cutoff preserve source history, explicit timezone/coverage limitations. Focused29 tests and DOM checks passed; full197 passed with5 existing Python3.9/Boto3 warnings; diff whitespace passed. Official BLS, BEA, Fed and DOSM sources checked (DOSM CSV retrieved directly); no exhaustive coverage claim. Actual browser visual QA not run; functional source/DOM review accepted.
Earlier pending statements retained as progress history; this acceptance supersedes them.

## Evidence and limitations

Primary schedules: https://www.bls.gov/schedule/2026/10_sched.htm ; https://www.bea.gov/news/schedule ; https://www.federalreserve.gov/feeds/G17.html ; https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm ; https://storage.dosm.gov.my/meta/arc.csv ; https://open.dosm.gov.my/data-catalogue/arc_dosm . Researcher verified October dates; Engineer retrieved DOSM CSV on October 1 MYT. Original 14 committed revisions remain an exact prefix. Added classification and scheduled events at actual recording time. 21 US and 26 MY current events through October 30; full October 1–31 grid. No unsupported October 31 event invented. DOSM timestamps lack offsets; Malaysia-local assumption explicitly displayed. FOMC release time remains unconfirmed.

Focused Python: 29 passed. Offline DOM replay passed including US/MY filtering, excluded China/unclassified records, latest versus historical view and future-information rejection. Initial broader run: 196 passed, one new-ticket status typo failed; corrected to the canonical review status and reran. No deployment, commit or push performed. Lead acceptance pending.

Broader rerun: 197 passed, 5 existing Python 3.9 boto3 warnings. Scoped manifest validation and git diff --check passed. Browser visual QA not run; DOM behavior replay passed.
