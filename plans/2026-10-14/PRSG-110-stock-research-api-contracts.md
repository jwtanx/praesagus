# PRSG-110 — stock research api contracts

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Bounded standalone REST discovery and typed field/unit/OHLC contracts reusing secure signing.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `e955e4b92e73cab4800b09a4c6559c85c517c5c4`. Allowed paths:

- `scripts/stock-research/provider.py`
- `scripts/stock-research/contracts.py`
- `scripts/stock-research/config.py`
- `scripts/stock-research/config.example.toml`
- `scripts/stock-research/requirements.txt`
- `scripts/stock-research/etf_metadata.csv`
- `scripts/stock-research/API_CONTRACTS.md`
- `tests/test_stock_research_provider.py`
- `plans/2026-10-14/PRSG-110-stock-research-api-contracts.md`
- `plans/2026-10-14/PRSG-110.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-110-D1: Mocked screen/snapshot/history paging and field units/errors/caps validated; no account/order access.
- [x] PRSG-110-D2: Capability receipt distinguishes exact native UI counts, entitlements and quota unknowns.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Reviewed wire/data requirements

Standalonewrapper must not weaken the old SecureReadTransport allowlist or collector quotas. Reuse injectable request/signing/credential interfaces with a new explicit allowlist for POSTstock-screen/stock-basicinfo/snapshot and USdailyhistory; noaccount/order/arbitrary URL. Stockscreen data.items/orderedresultwrappers and TOPLEVELpagination; result_type1double/2integer/3string with exact descriptor matching, no formatted value fallback. Price2201andturnover3105 magnification1000; volume3104raw; screeneraverage20 isNOTmedian20. ChangeRatebaseunitsremainunverified; usecompletedbarreturns forverifiedwinner/loserfinalranks. Bodyopaque next_key pagination, unchangedquery, duplicate/repeated/no-progressguards, request/page/rowbudgets, sequentialcalls/noautomaticretries. NumericRESTquotasunknown are explicit; nevercopyOpenDquota.

Basic stock_typeETF/trust flags do not prove exactfundtype/leverage/reset. Include issuer-sourced ETFclassificationregistry only for classifying market-discoveredcandidates, neverseedportfolio/reportuniverse. Sector sourcedmapping orUNKNOWN, no inventedplate equivalence. Canonical OHLC rows require finitepositiveprices and consistentlow<=open/close<=high, sessiondate, currencyUSDonlywhenproviderestablished, adjustmentunits, source timestamps/ownretrievalknown, explicithistory mode and revisionvintage. Rawtimezonefield isretained; inconsistent documentedunits cannot be silentlyreinterpreted. Bootstrap requested3years usesboundeddatebackfill; provider next_time unit mismatch cannot silentlytreat as enddate. Historybarsonly prove>=252 whencompleteactualcalendarcoverage.

References: https://open.moomoo.com/zh-cn/api/quote/screening/stock-screen ; https://open.moomoo.com/zh-cn/api/quote/basic-data/stock-basicinfo ; https://open.moomoo.com/zh-cn/api/quote/basic-data/history-kline ; https://open.moomoo.com/mcp-docs/available-tools . No authenticatedprovider calls occurred in this contractreview.


2026-10-15 09:00 MYT: resource hold released after fresh supported usage/battery checks; scope re-frozen against e955e4b92e73cab4800b09a4c6559c85c517c5c4. Engineer may implement the accepted offline REST contract scope; bounded live read-only pilot follows review of the collector.


## Implementation checkpoint — 2026-10-15 MYT

Lead independently reviewed the eight owned provider/config/contract/registry/doc/test paths. All five preliminary findings and the final daily change-rate request/sort gap were resolved. Exact configured Python3.11 command runs provider + existing REST + secure-transport regressions: **344passed in0.43s** (79newprovider cases); prior343passed0.40s was before the final interface addition. Registry41unique issuer observations reconcile with the reviewed classification input; no universe is seeded from it. Old transport/collector remain unchanged. D1 accepted; D2 remains pending a separately bounded, supervised live capability receipt. No authenticated requests, credential reads, model training or numeric forecasts occurred in these checks. API_CONTRACTS explicitly reports all unsupported/unverified capabilities and evidence limits.


## Lead acceptance — 2026-10-15 MYT

The reviewed implementation was committed and pushed as `c0c05d7`; mandatory full hooks passed2426tests/41existingwarnings (commit34.78s, push33.68s). Lead separately reviewed and replayed13private pilot controls, then accepted exactlyone supervised authenticated read-only pilot: **5requests,25returnedrows,5.394s,cleanupconfirmed**. The earlier reported23rows was corrected to25 (3screen+3basic+3snapshot+8history+8history); Lead reconciled the artifact hashes, counts and private permissions. No public raw/provider payloads or secrets are committed.

The pilot established sample access to the four allowed endpoint families. It observed `cumulative_property_result`, integer period_average echo and typed integer-string factor results; the current decoder continues to withhold those unverified fields pending a scoped normalization follow-up. History raw time_zone=-4 is retained with runtime-unit/finality uncertainty; no silent conversion occurred. Native UI counts, rate base units, numeric REST quotas, broad entitlements, data rights and full history/point-in-time universe readiness remain unknown. D1/D2 are accepted as the bounded API contract/capability-assessment epic, not acceptance of ingestion100, strong forecasts or production model promotion. NextPRSG-111 owns ingestion and any explicitly frozen provider enrichment/decoder follow-up.
