# PRSG-7 — Daily report navigation and shared calendar

Type: feature · Modules: frontend, financial-data, skills · Owner: Lead · Priority: P1 · Effort: S (1–2 person-days) · Impact: high

Created: 2026-10-01 MYT. [Delivery contract](PRSG-7.harness.json).

## Accepted scope

Fix report-date selection on desktop/mobile (actual available-date buttons, URL/content/title update, errors visible, stale responses ignored). Preserve historical schema-2 reports. New schema-3 reports omit sections.calendar and inline calendar events, referencing a shared monthly calendar under artifacts/financial-calendar/YYYY-MM.json. Calendar initialization happens once per month; daily rechecks append verified revisions, never delete earlier rows. Stable event ID + increasing revision, timezone-aware recorded_at, status scheduled/cancelled, reason and evidence. Missing from a feed is not a cancellation. Viewer shows cancelled/superseded entries struck through with the justification next to them and preserves as-of history.

Reduce the new curated coverage to five instruments per display group (50 total, benchmark ETFs separate from sectors). This is a documented research shortlist, not a proven return ranking. Every prediction shows low/medium/high or unavailable evidence confidence with rationale; unsupported forecasts stay unknown/unrated and null. Do not invent numerical probabilities or targets. Preserve the old universe and report snapshots for audit.

## Owners and interfaces

Engineer: shared viewer and deterministic browser regressions only. Lead: monthly ledger utility/fixtures/tests, report validator, new universe, schema-3 current report migration, daily skill, instructions and plan metadata. Researcher: read-only selection/calendar evidence review. Shared calendar schema1: month, timezone, notes (rich source objects), entries list of complete event revisions. Daily calendar_ref: ../financial-calendar/YYYY-MM.json. Events retain date/date_end/kind/title/time/summary/details/exposures/sources plus event_id/revision/recorded_at/status/change_reason. File version append checks validate existing prefix exactly. Viewer must fail visibly for missing shared files, never silently reuse another month's calendar.

## Validation / risks

Focused Python calendar/report contracts plus viewer DOM/browser date switching at mobile and desktop widths; malformed dates, missing files, stale requests, cross-month navigation, cancelled/superseded rendering, attempted rewrite/deletion, invalid confidence and future revisions. Run full pytest and report validator. Preserve user .DS_Store edits. Monthly ingestion is idempotent on repeat input; no claim of unattended scheduler unless configured. User metrics: available-date selection succeeds without dead taps; calendar initialization repeated daily adds zero duplicate records. Impact/effort estimated, not financial ROI.

## When it's considered done

- [x] PRSG-7-D1: Date selection changes actual content/URL/title and passes mobile/desktop regressions.
- [x] PRSG-7-D2: Shared monthly append-only calendar validates with cancelled/superseded reasons and no daily duplication.
- [x] PRSG-7-D3: New reports contain five names per group and explicit supported/unavailable confidence; old reports remain readable.
- [x] PRSG-7-D4: Tests, skill validation and Lead diff review recorded; publication state tracked separately.

## Delivery evidence

Local functional delivery accepted by Lead on 2026-10-01 MYT. Full pytest: 122 passed (five existing Python3.9/Boto3 deprecation warnings); report validator passes both legacy/new formats; DOM replay passes. Engineer actual browser 1280x720 and390x844 confirms report switching/URL/title, no mobile overflow, struck-through revision/cancellation fixture reasons and missing-month errors. Consultant replay retained omitted events, rejected quote-only forecasts and later-than-cutoff reasons. Skill metadata validated; availability/scorer wording clarified. Original Oct1 snapshot is byte-identical to base801279a. Fifty rows:30US/20MY, confidence unavailable for unsupported forecasts rather than invented probabilities. Calendar retains14 revisions/11 inherited logical events; source gaps remain explicit.

Daily automation prompt updated to schema3/five-name universe/monthly reuse without changing08:01MYT schedule. Local delivery does not prove remote deployment; CI/Pages/live checks follow publication separately. Monthly utility assumes one authorized writer; it is not a distributed ingestion scheduler.
