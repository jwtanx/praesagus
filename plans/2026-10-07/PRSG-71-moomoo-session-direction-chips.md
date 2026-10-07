# PRSG-71: Use Moomoo quote direction for report signal chips

Type · Modules · Owner · Priority · Effort · Impact: bug · backend, frontend, market-research · Lead · P1 · S (0.5–2 person-days) · high — report chips will show the requested Moomoo per-quote bullish/bearish direction instead of an unavailable SMA-only signal; the point-in-time method and cutoff remain explicit.

## Objective

Expose and render a per-quote Moomoo direction signal from latest price versus Moomoo's previous-close field. `Bullish` means latest is above previous close, `Bearish` means below, and `Neutral` means equal. Missing, invalid, non-finite, non-positive, unsupported-market, or temporally ineligible values remain `Unavailable` with a reason. The signal is a snapshot comparison, not an SMA trend, prediction, or recommendation; keep the existing `moomoo_trend` SMA-5/SMA-20 field distinct.

`GET /api/v1/moomoo/quotes` will return `moomoo_session_direction` on every quote using values from the same Moomoo quote response. The schema-3 report projection will derive the matching field from the same-run, cutoff-eligible private snapshot without another provider request. The report table and ticker chips will use the session-direction field and label it as a quote comparison; the separate historical SMA status and Trader forecast remain distinct.

## Scope

- Add a deterministic pure comparison helper for Moomoo latest and previous-close fields and attach its result to each quote API record without removing provider fields or changing the response envelope.
- Add a validated `moomoo_session_direction` report field from eligible same-run quote snapshots, with provider/source timestamps and unavailable reasons. Do not copy raw quote prices, private-store identifiers, credentials, or account data into this field.
- Render the point-in-time direction in each schema-3 report row and ticker chip. Preserve the existing SMA trend as a separate measurement and keep forecast direction separate.
- Cover bullish, bearish, neutral, missing/invalid fields, stale/future timestamps, failed snapshots, field preservation, and all 50 report rows with deterministic tests. Do not make provider calls in tests.
- Regenerate and validate the Oct 7 private report preview from the already captured run only; no new collection, deployment, or public report change is part of this ticket.

## Non-goals

- No history fetch, SMA calculation changes, target, confidence upgrade, forecast, trading action, persistent ingestion, additional provider call, credential access, public deployment, or change to unsupported MY history behavior.
- No substitution of same-day quote direction for the separate forecast direction or for the historical SMA-5/SMA-20 field.

## When it's considered done

- [x] PRSG-71-D1: Every quote API record has an explicit Moomoo session-direction result derived from its latest and previous-close values; invalid values fail closed.
- [x] PRSG-71-D2: Report projection preserves the same point-in-time signal only for cutoff-eligible snapshot data, with timestamp and missing-data regressions.
- [x] PRSG-71-D3: Table and ticker chips render the Moomoo session direction while keeping the SMA trend and Trader forecast separate.
- [x] PRSG-71-D4: Focused API/projection/viewer checks pass, the regenerated private preview validates, and Lead independently reviews scope and limitations.

## Evidence and limitations

- Moomoo's quote/history responses provide latest price, previous close, and source update timestamps. The signal is a comparison of those provider fields, not a native Moomoo forecast. Source timestamps are preserved; a single snapshot does not imply a regular-session return or multi-day trend.
- The report workflow's current data source has 30 US snapshot rows with eligible source timestamps and 20 unsupported MY rows. Its historical-bar requests failed, so the separate SMA field remains unavailable. The API's current OpenD history integration also remains independently availability-limited.
- Official API reference: [Moomoo Open API](https://open.moomoo.com/llms.txt).


## Verification record (2026-10-07 MYT)

- `python3 -m pytest -q tests/test_moomoo_api.py` — 36 passed.
- `python3 -m pytest -q tests/test_daily_report_projection.py` — 56 passed.
- `node tests/daily_report_viewer_checks.cjs` — passed.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-07/PRSG-71.harness.json --changed-file ...` — manifest and supplied paths valid; `git diff --check` passed.
- The ticket verification wrapper did not run the focused API command because its exact-command policy does not approve `focused-api`; no policy changes were made. Focused tests were run directly.
- Lead review accepted the implementation and limitations.
