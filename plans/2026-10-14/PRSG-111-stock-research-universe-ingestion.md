# PRSG-111 — Dynamic Stock and ETF Universe Ingestion

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

Dynamic 80-stock/20ETF plus10speculative selection and immutable vintages/actuals retention.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `2961a216d777167119803999dcb5a965142ba02a`. Allowed paths:

- `scripts/stock-research/universe.py`
- `scripts/stock-research/collect.py`
- `scripts/stock-research/storage.py`
- `scripts/stock-research/config.py`
- `scripts/stock-research/config.example.toml`
- `scripts/stock-research/requirements.txt`
- `scripts/stock-research/provider.py`
- `scripts/stock-research/contracts.py`
- `scripts/stock-research/API_CONTRACTS.md`
- `scripts/stock-research/etf_metadata.csv`
- `tests/test_stock_research_provider.py`
- `tests/test_stock_research_universe.py`
- `plans/2026-10-14/PRSG-111-stock-research-universe-ingestion.md`
- `plans/2026-10-14/PRSG-111.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-111-D1: Deterministic dedup/refill/liquidity/sector/exposure filters and honest shortfalls tested.
- [x] PRSG-111-D2: Incremental histories/revisions and prior forecast instruments retained in timestamp folders.

## Evidence

Implementation and deterministic fixture behavior accepted after independent Lead review; real full-universe data readiness and forecasting quality remain separate unverified obligations.

## Storage/universe invariants

Defaultparent ~/Documents/stock-research-data; every collect/train/predict generation creates exclusiveMYT YYYY-MM-DD_HHMMSS folder, rejects collisions, neveroverwrites. Artifacts/cache/modelstate liveinsidegenerationfolders. Latestcompatible state/modeldiscovery reads manifests; no destructive fixedlatestcache/model writes. In-repoparents require completeGit exclusion and reject repositoryroot/codepaths.

Universeselection is fromwholemarketdiscovery, not privateportfolio/reportlists. ForETFverifiedregistrytagging doesnotseedmarket discovery; sector/exposurefamilies need sourcedidentity. Corestocks>=5price,median20turnover>=25M,>=252validcompletedbars, sectorcap16;ETFsameprice/turnover/history and verifiedsignedleverage/reset, cap2perfam. Compute medians fromhistoricalbars, never substitute screenermean. Up to10speculativenamesdisjoint price>=1/median20turnover>=5M; flagsprice<5 orhistory<252 orATRfraction>.08 orabsreturn>.15. Noforceddailyrotation orfill.

Retain priorforecastsymbols inactualscollection even afterleavingselection; revisionvintagesappendonly. Point-in-timemembershipstarts atobservedfirstcollection; don'tbackfillfictionalhistoricalmembership. Historical backfillmode explicitlyretrospective and cannotqualifystrongdynamicuniverseacceptance. Defaultconfigsmallboundedrequestbudget+transparentpartialcoverage; resume incrementalcollector withoutautomaticretry orsilentquotaexpansion.


## Lead-reviewed selection clarifications — 2026-10-15 MYT

Trader review is saved privately at `reviews/PRSG-111-Trader-metadata-20261015-090716.md`. Verified ETF wrappers with real-estate exposure (including XLRE if independently discovered and otherwise eligible) are permitted in the ordinary-long bucket; individual REITs, ETNs and unidentified trusts are not substitutes. This resolves the private registry wording without adding undiscovered ticker seeds or relaxing eligibility.

Use deterministic quota-aware allocation/reassignment across ETF buckets and shared exposure-family caps, rather than a sequential greedy algorithm that can produce false shortfalls. A bounded minimum-cost maximum-flow allocation is one permissible implementation: source-to-bucket quotas, eligible instrument capacity1, family capacity2, ranked costs; maximize filled slots before rank. Test the Trader structural counterexample using fictional eligible inputs; its real symbols are metadata witnesses, not recommendations or demonstrated eligible investments. Distinguish budget/coverage/identity failures, true exhausted pools and unresolved allocation failures.

Unknown stock sectors stay in Coverage diagnostics and are excluded from the verified sector-capped core; ticker/name inference is forbidden. Permit sourced classification/issuer-share-class input keyed by independently discovered instruments; preserve source, observed time and unknown effective intervals. Provider plates or concepts cannot silently become a sector taxonomy. Missing mapping can produce an honest core shortfall, never a claim of verified diversification. Keep exact benchmark identity, any attributable provider-symbol/return-basis mapping and concentration family separate; no automatic IBB/BIB benchmark equivalence.

Turnover median must use the latest20 required completed exchange sessions with comparable units/adjustment, not20 compressed older rows. Handle attributable corporate actions and price/volume basis revisions without overwriting prior vintages; announced future actions do not imply a present halt. Current registry metadata cannot be projected onto historical periods as dated mandate evidence.


Lead scope detail 2026-10-15: after PRSG-110 delivery, ingestion may extend configuration and requirements for safe local output/state paths and the numerical/calendar/workbook dependencies needed by accepted later stages. Do not edit these shared paths concurrently with PRSG-110. Do not create a local `calendar.py` that shadows the standard library; AI Engineer later supplies `market_calendar.py`.


## Sourced sector and issuer input contract

A private Trader decision packet (`reviews/PRSG-111-sector-issuer-contract-20261015-092925.md`) records the actual evidence gap. Ingestion may validate supplied reviewed identity/classification records now; it must not fabricate a default crosswalk or company alias list.

Industry evidence retains exact security/listing identity, source endpoint/URL/hash, raw industry code/name/type, vendor taxonomy snapshot identity, actual retrieval/first-seen/availability and unknown effective intervals. Profile industry labels remain separate from plate IDs. A reviewed crosswalk keys vendor market/taxonomy snapshot/industry code to a declared broad-sector taxonomy/version and source-backed mapping version with reviewer/known/effective dates. No fuzzy name mapping, concept fallback, first-item selection or silent industry-to-sector equivalence. Mapped sector may be verified, unmapped, ambiguous, conflicting or stale, with evidence IDs and reason; unresolved classifications stay outside the verified core.

Issuer aliases distinguish provider security ID, exact listing, ISIN/company display name/website from authoritative issuer namespace/ID, grouping/share-class relationship and dated evidence. Security ISIN, name/site equality and ticker punctuation alone cannot establish common issuer or share class. Require an attributable filing/exchange/issuer relation table or supplied reviewed record for deduplication; retain unknown identities diagnostically. No claim of issuer-deduplicated80 without these inputs.

Official Moomoo source contracts identified (not currently implemented or added to PRSG-110's allowlist): [owner-plate](https://open.moomoo.com/zh-cn/api/quote/basic-data/owner-plate) distinguishes INDUSTRY/CONCEPT/OTHER and uses plate_name for the industry, not name (company name); [company profile](https://open.moomoo.com/zh-cn/api/quote/company/profile) has stable stock attribute50 industry,9 company name,8 ISIN; ETF/REIT tag routes lack those stable attribute IDs; [industry catalog](https://open.moomoo.com/zh-cn/api/quote/plate/plate-list) returns a market/type-specific vendor taxonomy. Actual taxonomy/memberships and reviewed crosswalk/issuer evidence require a separately frozen adapter follow-up or supplied reviewed offline files. Empty/unavailable metadata is not a forced fill. The16 broad-sector cap remains unchanged.


## Frozen provider follow-up within ingestion

The accepted live pilot established the cumulative_property_result wrapper and INT (not bool) period_average echo shape for daily requests; the echo value itself was not persisted. Extend typed decoding conservatively for3104/3105: exact factor/day descriptor, integer0/1 only when strictly equal to the requested boolean encoding, exact numeric result tag and documented scaling; unexpected echoes/types stay invalid or unavailable. Keep3102 numeric values/base units unavailable and derive verified ranking changes from comparable completed daily bars. Tests must reject alternative integers and wrong descriptors; future mean20 semantics are not established by the one-day pilot. Preserve raw time_zone=-4 and runtime-unit/finality uncertainty; daily dates/calendar completion do not silently resolve those units.

Optional source enrichment for the existing metrics/sector/issuer objective is now accepted in these same provider paths: only US security GET owner-plate and company/profile with empty query/body, plus GET plate-list with exact market=US and plate_class=INDUSTRY. Freeze these explicit read-only paths, headers/query validation and request budgets in tests; account/order/arbitrary endpoints remain forbidden and the old collector/transport remain unchanged. Preserve raw source industry identities and current-only metadata; no automatic broad-sector crosswalk or issuer grouping from names/sites/ISIN. Field contracts may display documented quote financial metrics with nullable financial period/units/status; current fundamentals never populate historical training rows.

Normal modeling history defaults to forward split adjustment excluding distributions (autype1), retaining explicit mode and source vintage. Raw-mode data stays explicitly raw and cannot be silently treated as split-continuous. Comparable price/volume/turnover basis and corporate-action uncertainty remain visible; do not turn missing adjustment evidence into precision. Source enrichment and cached input parsing may proceed offline; no new authenticated collector execution until Lead independently reviews code and releases a concrete bounded run.


## Lead implementation acceptance — 2026-10-15 MYT

Lead independently reviewed all14 ticket-owned paths and replayed **122 focused tests, passed in2.64s** after correcting share-class allocation, exact currency/security binding and evidence timing, cached enrichment, offline metadata replay, changed-security quarantine and latest-session turnover ranking. The prior119passed2.30s was preliminary. Complete owned scope validates against the frozen base; diff whitespace check passed. All49 ETF lookup records reconcile with reviewed issuer inputs (41 existing preserved,8 added); none seed discovery.

Collection saves exclusive timestamped, hash-checked generations, canonical numeric histories and revisions, current-only identity bindings, calendar/version/schedule hashes and honest coverage. Missing older history resumes across bounded runs, exited forecast names remain actuals-only, and unknown financial/native signal data is retained as unavailable. The default history basis is forward split-adjusted excluding distributions, with explicit vintage/factor uncertainty. No new authenticated collection, full100-name selection, model training, numeric forecasts, workbook export or deployment was exercised by these checks. Provider field currency, reviewed sector/issuer input and historical point-in-time evidence remain explicit readiness limits. D1/D2 accept ingestion implementation and failure handling, not strong-model validation. Mandatory full hooks and commit/push evidence are recorded at delivery.

Final handoff added physical provider-security deduplication (including ETF alias cap1) and maximum actual evidence availability, preventing earlier asserted known times from admitting later observations. Lead separately reviewed both additions and replayed **389 tests, passed in2.83s**, including124 collection/provider cases and265 existing REST/security regressions. Implementation commit `e1e6422` mandatory full hook passed **2471tests,41existingwarnings,37.60s**. Prior122 is an earlier review snapshot; no full-universe or model-quality claim follows from these checks.

## Why the ticket is created?

Discover liquid instruments independently of portfolio and reporting ticker lists while retaining historical observations.

## Approach

Select the target 80-stock/20-ETF universe with sector/exposure caps, a separate speculative panel and immutable versioned history.

## Choices

Refill overlaps from ranked pools; report quota shortfalls instead of relaxing eligibility or forcing ticker rotation.

## Findings

Offline ingestion and selection mechanics passed review. Actual admitted-universe readiness still depends on attributable currency, listing, issuer and sector evidence.

## Tradeoffs

Conservative identity and metadata requirements can leave fewer names, while preventing false diversification and unsupported eligibility.

## 16 October actual-source regression amendment

Reopened for verified actual-source regression, preserving prior D1/D2 acceptance/history. Fresh bounded diagnostic at 21:22 MYT returned 10 rows; 8 well-typed price2201/result_type2/ival values were string `0`. The provider aborted the whole page; 0 normalized/admitted instruments. One actual request, 2.811 seconds, cleanup verified; original earlier response remains unavailable. Zero values establish unusable prices, not penny-stock/listing status.

Frozen revision base `f10bbe4760ac80343cf6c945a32c319631ae674a`; Engineer owns contracts.py/provider.py/collect.py/README.md and two provider/universe tests; Lead owns these two ticket records. Use the six-path proposal reviewed 16 October: strict specialized nonpositive-price rejection after valid wire parsing; provider validates all other row fields before exclusion, bounded rejection provenance and raw-count/cursor budgets; persist dispositions into existing collection state/coverage. Allow only documented optional exact US+inclusive price-floor1/5 queries (raw1000/5000); defaults/speculative rules unchanged. No average-turnover proxy for required median, no guessed status filters, no broad malformed-data catch, no extra retries. Prior accepted PRSG-116 edits, model/report/ingest paths and unrelated dirty files protected. Work in the existing clean review checkout at the frozen base; do not reset the news checkout.

Published price-filter contract reviewed from official REST screening and official available-tools catalog; actual filter behavior remains unverified until a separately bounded live run. Implementation/tests only are released here; no credentials/provider/history/fitting or model promotion. All changed paths require Lead review and narrow checks before required hooks/delivery.

- [x] PRSG-111-D3: Actual observed nonpositive-price rows excluded with visible provenance, strict remaining validation, exact optional filters and truthful raw pagination budgets.

Lead accepted D3 after independent final source/test/hash review and 234 focused checks. Exact optional filter JSON/scaling independently checked against official indexed screening/catalog documentation; direct page fetch timed out. Raw source traversal remains separate from candidate admission. No provider call occurred for this patch, and live filter acceptance/history currency/model quality remain unverified. Initial Engineer fixture failure and correction remain in private handoff evidence; no threshold changed. Required full commit/push hooks still apply.
