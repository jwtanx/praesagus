# PRSG-70: Return per-quote Moomoo trend signal

Type · Modules · Owner · Priority · Effort · Impact: feature · backend, market-research · Lead · P1 · XS (0.2–0.5 person-days) · medium-high — attaching the existing trend signal to quotes closes the API gap for the report workflow; behavior is verified with mocked data, while live OpenD remains unverified.

## Objective

Add the existing Moomoo trend signal to every quote record returned by `GET /api/v1/moomoo/quotes`. Use the same SMA-5 versus SMA-20 signal as `GET /api/v1/moomoo/trends`, calculated from Moomoo OpenD daily adjusted closes: `bullish`, `bearish`, or `neutral`. Return `unavailable` with a reason when history is insufficient, invalid, unavailable, or the market/code is unsupported. Preserve every provider field and the existing response envelope.

The quote's latest-price comparison with previous close is not the requested trend and is not used. Moomoo OpenD supplies historical closes; this API reuses its established SMA-5/SMA-20 calculation. The signal is descriptive trend context, not a forecast or recommendation. Because OpenD history currently supports US symbols only, other market quotes carry an explicit unavailable reason.

## Scope

- Reuse the existing SMA-5/SMA-20 calculation and history endpoint logic for each US quote; do not substitute same-day price movement.
- Enrich each quote record in the existing FastAPI endpoint with `moomoo_trend`, preserving the established trend fields and explicit unavailable reasons. History is fetched once per US quote, bounded to the existing three-month/100-row request.
- Preserve raw quote keys, endpoint code validation, request-scoped subscription, API-key behavior and the response-level `retrieved_at` timestamp.
- Add deterministic endpoint tests for bullish, bearish, neutral, insufficient history, and unsupported-market signals. Tests use fakes only.

## Non-goals

- No forecast, target, probability, recommendation, polling, persistent ingestion, cache, trading action, report publication, deployment or frontend behavior.
- No changes to public report rights validation or the private report draft from PRSG-69.
- No claim of live OpenD connectivity or market-data entitlement. Functional acceptance uses deterministic mocked data.

## When it's considered done

- [x] PRSG-70-D1: Every returned quote record includes the SMA-5/SMA-20 Moomoo trend signal; same-day price movement is not used as the trend.
- [x] PRSG-70-D2: API regressions cover bullish, bearish, neutral, unavailable history, unsupported markets, record-field preservation and one signal per quote without live credentials.
- [x] PRSG-70-D3: Ticket scope, diff, focused tests, and OpenD/API limitations receive independent Lead review; no live provider request is made by tests.

## Evidence and limitations

- Moomoo OpenD historical closes are request/response and require a subscription. The quote response keeps its source quote fields and adds the existing calculated SMA signal. Each US quote adds one bounded history request; non-US markets are reported unavailable under the current history connector contract.
- Official docs: [Get Real-time Quote](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-stock-quote.html); [Moomoo REST/OpenAPI index](https://open.moomoo.com/llms.txt).
- No live OpenD connection test is part of this ticket; the repository's existing local OpenD service was not verified as available.
