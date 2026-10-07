# PRSG-77 — Add concise colored statistical forecasts to the Oct 7 brief

Type: feature · Modules: frontend, market-research · Owner: Trader · Priority: P1 · Effort: M (>2–7 person-days) · Impact: medium-high — each listed name has a visible low-confidence range and direction while the viewer stays concise.

Created 2026-10-08 MYT.

## Objective

Meet the requirement that every Oct 7 watchlist row includes a price range and directional forecast. Remove provider names, source/retrieval dates and long caveats from the viewer's forecast rows and snapshot cards. Show green bullish, red bearish, and yellow sideways styling.

## Accepted scope

- `artifacts/daily-market-brief/2026-10-07.json`
- `artifacts/daily-market-brief/index.html`
- `scripts/daily-market-brief/statistical_baseline.py`
- `scripts/daily-market-brief/refresh_statistical_baseline.py`
- `tests/test_statistical_baseline.py`
- `tests/daily_report_viewer_checks.cjs`
- This spec and its matching harness manifest.

Historical/source provenance stays in report data. Do not present the baseline as validated or execution-ready.

## Observable behavior

- Every Oct 7 name has a range, mid estimate, target date, low confidence, direction and retained reference source.
- Forecast rows and compact price cards use green/up, red/down and amber/sideways indicators.
- Visible table has only market, ticker/name, group, last price and forecast/range; provider, source and source timestamps remain hidden.
- Unverified point snapshots are not used as forecast anchors or sorted as listing-currency prices.

## When it's considered done

- [x] PRSG-77-D1: Deterministic baseline accepts completed price bars only, checks currency and requires 20 returns.
- [x] PRSG-77-D2: All 50 Oct 7 names carry low-confidence ranges and retained source provenance.
- [x] PRSG-77-D3: Viewer omits provider/date chatter and colors forecast direction.
- [ ] PRSG-77-D4: Focused tests, both report validations, ticket-scope validation and independent review pass.

## Delivery evidence

- `node tests/daily_report_viewer_checks.cjs` — passed after UI adaptation.
- `python3 -m pytest -q tests/test_statistical_baseline.py` — passed (3 tests).
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-07 --public` — passed.
- `python3 scripts/daily-market-brief/validate_report_json.py --date 2026-09-30` — passed; archive left unchanged.
- `python3 scripts/planning/validate_ticket.py plans/2026-10-08/PRSG-77.harness.json` with all eight scoped paths — passed. Independent Lead review remains pending.
