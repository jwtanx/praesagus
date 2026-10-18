# PRSG-125 — Bounded Malaysia Daily History

Type: feature · Owner: Engineer · Priority: P1 · Effort: S (0.5–1.5 person-days) · Impact: high — remove the concrete US-only ingestion dependency for the approved daily forecast report.

## Why the ticket is created?

The fixed daily shortlist includes Malaysia instruments. Existing history collection rejects the documented candidate BMS.1155 at five checks across four source files. PRSG-124 calculation and batch support is delivered; actual Malaysia observations are still unavailable.

## Approach

Permit only literal BMS.1155 for raw daily history through the existing secure collector, connector, transport and private store. Freeze end-only ktype2/autype0/num100 and no start. Preserve all US options, request signing, credentials, TLS, redaction, quota/deadline/size limits, diagnostics and canonical stored identity. Reuse existing CLI; no new client or framework.

## Choices

Use one exact documentary candidate rather than generalizing every market prefix. Mocked regressions cover plan, exact request, transport and store. No provider request is released by this implementation ticket. A later bounded observation requires separate Lead release.

## Findings

Engineer inspected US-only checks in market_collector.job_request, REST history_kline, secure transport route allowlist and two private-store metadata/normalization checks. Existing explicit integer offset/date arithmetic can be tested with480 without inferring actual returned timezone units. BMS identity does not establish MYR, entitlement, settlement, actions or source-use permission.

## Tradeoffs

One candidate is intentionally narrower than final20-name Malaysia coverage and provides the cheapest supported observation path. Passing fixtures establishes mechanics only. Preserve raw offsets; never multiply by60 or assign currency/calendar from a prefix. Unknown support yields a controlled failure, with no alternate-prefix retries.

## Frozen scope

Owner Engineer; Lead owns these two records. Base 6f289ce7a730f43de05852b80cfb92dfd4b8306c. Accepted source/test paths are exactly the eight listed in the manifest. Protected: credentials/signing implementations outside those paths, models, forecasts, public artifacts, report CLI, dependencies and unrelated dirty .DS_Store. No provider calls, trades, paid access or public output. Source candidate reference: https://open.moomoo.com/api/quote/overview ; this documentary route is not an entitlement assertion.

## When it's considered done

- [x] PRSG-125-D1: Exact candidate passes mocked end-only raw daily100 plan/request/transport/store round-trip; unsupported variants and malformed/future/duplicate data reject; existing US behavior preserved.
- [x] PRSG-125-D2: Lead independently reviews complete diff, focused regressions and mandatory delivery gates, commits and pushes; actual observation/admission remains separate.

## Lead acceptance — 18 October

Independently reviewed all eight frozen source/test paths and ran the configured regressions: 825 passed in 3.43s. Exact candidate restrictions apply at all five guards; US options and security remain covered. Lead bounded official overview HTML review confirmed Malaysia/BMS/BMS.1155 example; this proves a documentary route, not account entitlement or live success. Frozen handoff patch SHA256 d26d7bd1ce8e7506b2eb2983e432dd1f9dda85ecd001819a06e7d37d63efbe8f. No actual observation, price currency, rights, finality or forecast coverage inferred. Required commit/push hooks apply.
