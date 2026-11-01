# PRSG-180 — Request Dates with OpenD Historical Closes

Type: bug · Modules: connectors, market-research · Owner: Engineer · Priority: P1 · Effort: XS (0.25–0.5 person-day estimate) · Impact: high — restores the read-only history path needed by the fresh US prediction cohort.

## Objective and Boundary

Fix `MoomooOpenDConnector.get_history`: it validates `time_key` but currently asks OpenD for only the close field. On the installed Moomoo SDK 10.12.7208, a live 30 October 2026 SPY request with only `KL_FIELD.CLOSE` returned columns `code,name,close`; the connector then rejected the absent session date. The same request with `KL_FIELD.DATE_TIME` and `KL_FIELD.CLOSE` returned `code,name,time_key,close` and the 30 October session.

## Frozen Scope

Base SHA: `1069ee1762d5f3257f42f7f7cea7256db668055e`. Engineer owns only `connectors/moomoo_opend.py` and `tests/test_moomoo_opend.py`. Lead owns these ticket records and final review. Preserve the bounded single-page request, existing US-only history boundary, adjustment choice, validation, and context cleanup. No model, forecast, report, source admission, schedule, credential or publication changes are in this ticket. Live reproducer is already captured; automated tests must use fixtures only.

## Approach

Request the SDK date/time field alongside the close field so the response shape matches the existing parser. Add a regression asserting both requested fields and retain the current invalid-date, bounds, order, duplicate, close-value and cleanup checks.

## Choices

Do not remove session-date validation or infer dates from request bounds. Do not widen history support to Malaysia: current Moomoo OpenD entitlement probe rejected `MY.1155`, and Malaysia source support belongs in its separate accepted source work. This ticket fixes the confirmed US history defect only.

## Findings

The live connector was successfully authenticated for quotes. US latest-price snapshots for all 30 fixed US names were returned with session date 30 October; history failed for all 30 due to the missing requested date field. A one-row direct SDK probe confirmed that adding `KL_FIELD.DATE_TIME` supplies the required `time_key`.

## Tradeoffs

History requests will return one additional scalar date field per bar. The code continues to discard all unrequested provider fields and emit only validated date/close pairs. This does not prove forecast quality or authorize publication by itself.

## When It Is Considered Done

- [x] PRSG-180-D1: OpenD history explicitly requests both session date/time and close fields; returned date validation remains strict.
- [x] PRSG-180-D2: Focused regression proves the SDK request includes both fields, output dates remain exchange-local, and existing failure/cleanup cases still pass.
- [x] PRSG-180-D3: Lead independently reviews the exact four-path scope and accepts focused checks before commit/push.

## Checks

- Configured Python 3.11: `-m pytest -q -p no:cacheprovider tests/test_moomoo_opend.py`
- `python3 scripts/planning/validate_ticket.py plans/2026-11-01/PRSG-180.harness.json --changed-file connectors/moomoo_opend.py --changed-file tests/test_moomoo_opend.py --changed-file plans/2026-11-01/PRSG-180-opend-history-date-field.md --changed-file plans/2026-11-01/PRSG-180.harness.json`
- `git diff --check`

No live provider calls are required for acceptance; the already observed live response is evidence for the reproduced failure and fix shape.


## Review Evidence

Focused OpenD tests: 21 passed. Ticket manifest/path validation passed; `git diff --check` passed. Lead review confirmed the date/time request fix preserves the existing US-only boundary, adjustment, validation, bounds and context cleanup. Reviewed 2026-11-01 MYT.
