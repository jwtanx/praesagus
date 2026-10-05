# PRSG-60 — Moomoo OpenD historical price trend on Dashboard

Type: feature · Modules: connectors, backend, frontend, financial-data · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high; gives the user a directly inspectable historical price series without converting point quotes or signal scores into a trend. Created 2026-10-05 MYT.

## User problem and measurable outcome

The Dashboard currently shows signal-derived “Top trends”; those scores are not price histories. Moomoo OpenD currently provides only an on-demand latest quote snapshot on the Financial page. The user cannot inspect an actual historical price direction on Dashboard.

Deliver an on-demand chart of historical daily closes for one explicitly entered US symbol, default `US.AAPL`, with a bounded `1M` or `3M` window. Keep it clearly separate from signal “Top trends.” Success measure: for a valid mocked history response, Dashboard renders an ordered daily-close series with its symbol, selected range, adjustment basis, source time and retrieval time; missing, invalid, offline and entitlement-failure responses never render fabricated points. Baseline is zero Moomoo history charts on Dashboard. Measure as passing the deterministic regressions plus the live OpenD check when an entitled operator environment is available; no adoption or investment-performance claim.

## Existing implementation and source contract

`connectors/moomoo_opend.py` opens a request-scoped `OpenQuoteContext`, maps quote/news calls to controlled errors, and closes the context. `GET /api/v1/moomoo/quotes` returns latest snapshots; it does not persist, stream, or fetch historical bars. `frontend/src/pages/Dashboard.tsx` obtains signal summaries through `/api/v1/dashboard`.

Official Moomoo documentation describes `request_history_kline(code, start, end, ktype, autype, fields, max_count, page_req_key, extended_time)`, where request dates use `yyyy-MM-dd`, `KLType.K_DAY` requests daily bars and the method returns a status, data and pagination key. Returned `time_key` values use `yyyy-MM-dd HH:mm:ss` in US session time. Parse that exact format and preserve its exchange-local date portion without timezone conversion. For this MVP issue one bounded request and do not follow a pagination key. Use an explicit adjustment type and only the close field if supported by the installed SDK; display the adjustment basis. Source session dates are not publication or retrieval timestamps. Record retrieval time separately at the API boundary. SDK/OpenD version compatibility and actual US-market entitlement remain operator dependencies.

Primary source: [Moomoo OpenD — Get Historical Candlesticks](https://openapi.moomoo.com/moomoo-api-doc/en/quote/request-history-kline.html) (accessed 2026-10-05). The documentation establishes the callable interface and parameter meanings; it does not establish this account’s symbol coverage, entitlement, historical quota, rights to redistribute data, or successful live operation.

## MVP behavior and boundaries

- Add a Dashboard card titled **Moomoo historical price trend**, independent from existing signal cards, charts, forecast labels and TradingView widgets.
- Accept a market-qualified US equity symbol, with `US.AAPL` prefilled. Validate the `US.` prefix and nonempty ticker on both API and UI boundaries; reject other markets and malformed/oversized values without contacting OpenD.
- Offer only `1M` and `3M` ranges. Compute inclusive `start`/`end` dates from the request date in UTC; use a calendar-month interval ending on the current UTC date. Request at most 100 daily bars, `KLType.K_DAY`, no extended-hours bars, and one explicitly chosen adjustment basis (default `AuType.QFQ`) with no silent retry or paging. Clamp dates/results defensively. The data source may return fewer bars because of holidays, coverage, or entitlement.
- Return only validated daily session date and finite positive close values from the documented K-line response, plus requested symbol/range, adjustment label and API `retrieved_at` UTC timestamp. Preserve ordered dates; reject duplicate or out-of-range dates and malformed/nonfinite prices as a controlled upstream-data error. Empty history is an explicit empty state, distinct from request failure. Do not synthesize, forward-fill, interpolate, or substitute latest snapshot prices.
- Display “Historical daily close · adjusted (QFQ)” (or the agreed explicit adjustment label), symbol, selected window, first/last session dates, and “Retrieved” UTC time. Make clear values are provider-sourced observations, not a forecast or recommendation; the latest bar may still reflect an active session because completion is not established by this request contract. Do not add inferred currency, percentage performance, indicators, forecasts, confidence, trade actions, volume analysis, or unsupported freshness claims.
- Keep loading, valid empty, validation, OpenD unavailable, entitlement/upstream error and malformed-response states visible and distinct enough for the user to retry manually. A manual refresh/button is the only request trigger; no polling or automatic request loop.
- Do not add persistence, background collection, schedules, private portfolio/watchlist/account access, REST signer use, new dependencies, public report/export, or provider calls in tests. Existing quote/news APIs and signal/trading widgets retain their behavior.

## Frozen implementation scope and ownership

Current base SHA: `9bf9cf334cc1c96e2ab6ec0c7c132c0c222558b2` (2026-10-05). Lead independently reviewed and accepted the exact scope on 2026-10-05 MYT and authorized implementation (`implementation_authorized=true`). Because the original checkout has dirty PRSG-2 work, implementation must use a separate worktree at this base; do not implement in the dirty PRSG-2 checkout. Write only these ten paths:

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

Owner: Engineer. Reviewer and integration authority: Lead. Scope status is accepted and ticket status is complete after the 2026-10-05 Lead freeze and final review. Implementation remained in the separate worktree. No live-provider calls, dependency installations, trades, or credential access occurred. Preserve all original-checkout PRSG-2 edits. If implementation requires another path or contract, stop for a Lead scope amendment.

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

Connector/API regressions cover exact OpenD method/kwargs, context closure on success and failures, US code/range validation, endpoint response/provenance, unavailable OpenD, API/upstream failure, empty history, date order/range, duplicate dates, malformed/nonfinite closes, request caps, API-key behavior, and no provider call on invalid input. `tests/dashboard_moomoo_checks.cjs` is a source-contract regression: it checks Dashboard placement separate from signal trends, default symbol/ranges, manual-only trigger, API client contract, labels/error/empty states, and ordered/validated SVG source structure. It does not execute React, mount the component, or exercise browser DOM state transitions. A browser DOM/visual replay was not run and is not claimed. All connector/API fixtures use fake contexts/connectors. Frontend build validates component compilation/integration only; it does not prove runtime rendering or provider access.

Manual check: if operator-provisioned OpenD is running and logged in with US historical-data entitlement, issue one bounded US test-symbol request and verify returned session dates, closes, adjustment and retrieval provenance without printing or publishing private data. Otherwise record the exact unavailable/entitlement blocker; do not provision credentials, log in, install software or broaden access as part of implementation.

## When it is considered done

- [x] PRSG-60-D1: The bounded OpenD historical daily-close contract and separate Dashboard chart pass the exact offline connector/API regressions, frontend source-contract checks, and frontend build. No browser DOM behavior is claimed.
- [x] PRSG-60-D2: Live OpenD/US entitlement result is recorded when an operator environment is available, or its unavailable/entitlement limitation is reported without claiming live validation. Evidence: a local-only TCP readiness check to the configured loopback port 11111 was refused; no OpenD API request was made, no history rows were returned, and no quote success is asserted. The offline unavailable behavior remains covered by deterministic tests.
- [x] PRSG-60-D3: Lead independently accepts the frozen path scope, adjustment/time labeling, failure semantics and test evidence. Evidence: Lead rechecked all ten changed paths, the focused 35-test Python run, Node Dashboard regression, frontend build, exact ticket validator, diff checks, and executable pre-commit/pre-push hooks; scope accepted.

D1 evidence is not proof of browser DOM behavior, live market access or redistribution rights. D2 does not make the series a forecast, execution signal or permission to publish data. D2 records OpenD as locally unavailable, not as a quote success. Lead final review is complete as D3. A Pages run was previously reported for this SHA, but it remains collaborator-reported pending independent verification and is not used as acceptance evidence.

## Engineer implementation handoff — 2026-10-05 MYT

Ported the exact accepted ten-path scope into the fresh worktree at `/Users/jwtan/.codex/worktrees/prsg-60-rebased/praesagus`, based on `9bf9cf334cc1c96e2ab6ec0c7c132c0c222558b2`; the original detached worktree remains untouched as backup. Added a single-page OpenD `request_history_kline` adapter call for validated US symbols, daily QFQ close-only data, a max100 response and no paging; a read-only history endpoint with UTC 1M/3M bounds and retrieval provenance; and a manually triggered Dashboard SVG chart separate from signal trends. Strictly parse returned `yyyy-MM-dd HH:mm:ss` session times and preserve the exchange-local date without UTC conversion. Invalid, duplicate, unordered, out-of-range, nonfinite or nonpositive points fail as upstream-data errors. Empty series stays an explicit empty result. OpenD unavailable and request/upstream failures surface for manual retry. No polling, data storage, new package, credential access or live request.

Exact owned paths changed: `connectors/moomoo_opend.py`, `backend/main.py`, `frontend/src/services/api.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/MoomooPriceTrend.tsx`, `tests/test_moomoo_opend.py`, `tests/test_moomoo_api.py`, `tests/dashboard_moomoo_checks.cjs`, this spec and its harness manifest. Original dirty PRSG-2 checkout was not edited. PRSG-2 overlap in `backend/main.py` and `frontend/src/services/api.ts` still requires separate Lead integration and ticket commits.

Checks in the fresh worktree at base `9bf9cf334cc1c96e2ab6ec0c7c132c0c222558b2`: `PATH=/Users/jwtan/.codex/venvs/praesagus-tests-311/bin:$PATH python3 -m pytest -q tests/test_moomoo_opend.py tests/test_moomoo_api.py` — 35 passed, 20 existing Starlette/httpx deprecation warnings. Tests exercise realistic `yyyy-MM-dd HH:mm:ss` OpenD rows, keep the exchange-local date (including no UTC date shift), reject malformed timestamp formats, and prove empty history returns HTTP200 with `series=[]` and `count=0`. `node tests/dashboard_moomoo_checks.cjs` — passed offline source-contract assertions; this is not a browser DOM replay. Scope validator with all ten manifest paths and `git diff --check` passed. `npm run build` — passed with Vite 5.4.21, 46 modules, 331ms; a temporary symlink to existing frontend dependencies was removed immediately afterward, with no install. The shared `.githooks` path has executable pre-commit and pre-push hooks. Local OpenD readiness check found the configured loopback port 11111 refused; no OpenD API request was made and no quote success is asserted. No browser visual test was performed. D1 automated evidence, D2 unavailable limitation, and D3 Lead acceptance are complete.
