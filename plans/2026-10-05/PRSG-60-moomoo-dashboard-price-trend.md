# PRSG-60 — Moomoo OpenD historical price trend on Dashboard

Type: feature · Modules: connectors, backend, frontend, financial-data · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high; gives the user a directly inspectable historical price series without converting point quotes or signal scores into a trend. Created 2026-10-05 MYT.

## User problem and measurable outcome

The Dashboard currently shows signal-derived “Top trends”; those scores are not price histories. Moomoo OpenD currently provides only an on-demand latest quote snapshot on the Financial page. The user cannot inspect an actual historical price direction on Dashboard.

Deliver an on-demand chart of historical daily closes for one explicitly entered US symbol, default `US.AAPL`, with a bounded `1M` or `3M` window. Keep it clearly separate from signal “Top trends.” Success measure: for a valid mocked history response, Dashboard renders an ordered daily-close series with its symbol, selected range, adjustment basis, source time and retrieval time; missing, invalid, offline and entitlement-failure responses never render fabricated points. Baseline is zero Moomoo history charts on Dashboard. Measure as passing the deterministic regressions plus the live OpenD check when an entitled operator environment is available; no adoption or investment-performance claim.

## Existing implementation and source contract

`connectors/moomoo_opend.py` opens a request-scoped `OpenQuoteContext`, maps quote/news calls to controlled errors, and closes the context. `GET /api/v1/moomoo/quotes` returns latest snapshots; it does not persist, stream, or fetch historical bars. `frontend/src/pages/Dashboard.tsx` obtains signal summaries through `/api/v1/dashboard`.

Official Moomoo documentation describes `request_history_kline(code, start, end, ktype, autype, fields, max_count, page_req_key, extended_time)`, where dates use `yyyy-MM-dd`, `KLType.K_DAY` requests daily bars and the method returns a status, data and pagination key. For this MVP issue one bounded request and do not follow a pagination key. Use an explicit adjustment type and only the close field if supported by the installed SDK; display the adjustment basis. Source dates are exchange-session dates, not publication or retrieval timestamps. Record retrieval time separately at the API boundary. SDK/OpenD version compatibility and actual US-market entitlement remain operator dependencies.

Primary source: [Moomoo OpenD — Get Historical Candlesticks](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html) (accessed 2026-10-05). The documentation establishes the callable interface and parameter meanings; it does not establish this account’s symbol coverage, entitlement, historical quota, rights to redistribute data, or successful live operation.

## MVP behavior and boundaries

- Add a Dashboard card titled **Moomoo historical price trend**, independent from existing signal cards, charts, forecast labels and TradingView widgets.
- Accept a market-qualified US equity symbol, with `US.AAPL` prefilled. Validate the `US.` prefix and nonempty ticker on both API and UI boundaries; reject other markets and malformed/oversized values without contacting OpenD.
- Offer only `1M` and `3M` ranges. Compute inclusive `start`/`end` dates from the request date in UTC; use a calendar-month interval ending on the current UTC date. Request at most 100 daily bars, `KLType.K_DAY`, no extended-hours bars, and one explicitly chosen adjustment basis (default `AuType.QFQ`) with no silent retry or paging. Clamp dates/results defensively. The data source may return fewer bars because of holidays, coverage, or entitlement.
- Return only validated daily session date and finite positive close values from the documented K-line response, plus requested symbol/range, adjustment label and API `retrieved_at` UTC timestamp. Preserve ordered dates; reject duplicate or out-of-range dates and malformed/nonfinite prices as a controlled upstream-data error. Empty history is an explicit empty state, distinct from request failure. Do not synthesize, forward-fill, interpolate, or substitute latest snapshot prices.
- Display “Historical daily close · adjusted (QFQ)” (or the agreed explicit adjustment label), symbol, selected window, first/last session dates, and “Retrieved” UTC time. Make clear values are provider-sourced observations, not a forecast, live quote or recommendation. Do not add inferred currency, percentage performance, indicators, forecasts, confidence, trade actions, volume analysis, or unsupported freshness claims.
- Keep loading, valid empty, validation, OpenD unavailable, entitlement/upstream error and malformed-response states visible and distinct enough for the user to retry manually. A manual refresh/button is the only request trigger; no polling or automatic request loop.
- Do not add persistence, background collection, schedules, private portfolio/watchlist/account access, REST signer use, new dependencies, public report/export, or provider calls in tests. Existing quote/news APIs and signal/trading widgets retain their behavior.

## Frozen implementation scope and ownership

Current base SHA: `0a43f04f03b406cb73480a50cec9dc1b7f15f36e` (2026-10-05). Lead independently reviewed and accepted the exact scope on 2026-10-05 MYT and authorized implementation (`implementation_authorized=true`). Because the original checkout has dirty PRSG-2 work, implementation must use a separate worktree at this base; do not implement in the dirty PRSG-2 checkout. Write only these ten paths:

- `connectors/moomoo_opend.py`
- `backend/main.py`
- `frontend/src/services/api.ts`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/components/MoomooPriceTrend.tsx`
- `tests/test_moomoo_opend.py`
- `tests/test_moomoo_api.py`
- `tests/dashboard_moomoo_checks.cjs`
- `plans/2026-10-05/PRSG-60-moomoo-dashboard-price-trend.md`
- `plans/2026-10-05/PRSG-60.harness.json`

Every other path is protected except the two explicitly shared files `backend/main.py` and `frontend/src/services/api.ts`, which contain pre-existing dirty PRSG-2 changes. In the separate worktree, PRSG-60 may add only its isolated OpenD history route and client function in those files; preserve all PRSG-2 hunks and behavior. All other PRSG-2 paths are protected, including the freshness backend service, status ledger, SEC script/configuration, Financial/Platforms/Pipeline UI, tests, and PRSG-2 ticket evidence. All PRSG-31/34/37/38/39 implementation paths and ticket documents, REST transport/store/projection, existing Dashboard signals/widgets, dependencies, auth/configuration, and reports also remain protected. Keep ticket changes separate: PRSG-60 and PRSG-2 require separate commits. Lead resolves and validates integration of the two shared files without mixing ticket ownership or commits. The proposed HTTP route is read-only and request-scoped. If implementation evidence requires any additional path or contract, stop and ask Lead to freeze a scope amendment first.

Owner: Engineer. Reviewer and integration authority: Lead. Scope status is accepted and ticket status is in progress following the 2026-10-05 Lead freeze acceptance. PRSG-60 may proceed only in the separate worktree. No live-provider calls, dependency installations, trades, or credential access are authorized. Preserve all original-checkout PRSG-2 edits. If implementation requires another path or contract, stop for a Lead scope amendment.

## Validation plan

All automated provider behavior is synthetic and offline. Use the existing test runtime, with no installation. From repository root:

```sh
python3 -m pytest -q tests/test_moomoo_opend.py tests/test_moomoo_api.py
node tests/dashboard_moomoo_checks.cjs
python3 scripts/planning/validate_ticket.py plans/2026-10-05/PRSG-60.harness.json \
  --changed-file connectors/moomoo_opend.py \
  --changed-file backend/main.py \
  --changed-file frontend/src/services/api.ts \
  --changed-file frontend/src/pages/Dashboard.tsx \
  --changed-file frontend/src/components/MoomooPriceTrend.tsx \
  --changed-file tests/test_moomoo_opend.py \
  --changed-file tests/test_moomoo_api.py \
  --changed-file tests/dashboard_moomoo_checks.cjs \
  --changed-file plans/2026-10-05/PRSG-60-moomoo-dashboard-price-trend.md \
  --changed-file plans/2026-10-05/PRSG-60.harness.json
```

From `frontend/`, run `npm run build`.

Connector/API regressions must cover exact OpenD method/kwargs, context closure on success and failures, US code/range validation, endpoint response/provenance, unavailable OpenD, API/upstream failure, empty history, date order/range, duplicate dates, malformed/nonfinite closes, request caps, API-key behavior, and no provider call on invalid input. Dashboard DOM regression must cover default input, manual range/symbol request, separate placement from signal trends, chart point order and provenance/adjustment labels, valid empty/loading/error states, repeated manual request and no implicit polling/request on mount. All fixtures use fake contexts/connectors. Frontend build validates the component integration; no browser/provider acceptance is implied by a build.

Manual check: if operator-provisioned OpenD is running and logged in with US historical-data entitlement, issue one bounded US test-symbol request and verify returned session dates, closes, adjustment and retrieval provenance without printing or publishing private data. Otherwise record the exact unavailable/entitlement blocker; do not provision credentials, log in, install software or broaden access as part of implementation.

## When it is considered done

- [ ] PRSG-60-D1: The bounded OpenD historical daily-close contract and separate Dashboard chart pass the exact offline connector/API/UI regressions and frontend build.
- [ ] PRSG-60-D2: Live OpenD/US entitlement result is recorded when an operator environment is available, or its unavailable/entitlement limitation is reported without claiming live validation.
- [ ] PRSG-60-D3: Lead independently accepts the frozen path scope, adjustment/time labeling, failure semantics and test evidence.

D1 evidence is not proof of live market access or redistribution rights. D2 does not make the series a forecast, execution signal or permission to publish data. Ticket completion requires Lead review of all three items; current request authorizes only this spec and harness draft.
