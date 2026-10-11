# PRSG-88 Correct native Moomoo signal display
Type: bug · Modules: frontend, harness, skills, market-research · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-days) · Impact: medium-high

## Problem and accepted scope
Human correction on 2026-10-11: current quote versus previous close is unwanted; display actual Moomoo bullish/bearish technical signals instead. Reproduction: compact October11 report currently displays Quote: Bullish/Bearish and SMA chips; the report skill forces their agreement into forecast direction. Those are calculated proxies, not native Moomoo events.

Lead accepts a bounded correction at 622ba71251fcc95ee0355542c56f861b6e11c48b, separately from blocked PRSG-82 native intake. Native observations have not been collected. Show `Moomoo bullish: Unavailable` and `Moomoo bearish: Unavailable`, with keyboard/click/tap accessible details explaining KDJ/MACD/Bollinger coverage, unknown rule/parameters/timeframe/source observation time, and counts are observations rather than probabilities. Use a shared details control if two chips duplicate evidence. No future native-result payload contract is introduced by this bug. Display absence as unavailable, never zero/neutral. Preserve independent forecast chip, existing quote prices and full provenance, compact limits, all120audit rows, archive behavior and provider-unit sort guard. Change compact column/coverage and short narrative to remove rejected proxies; do not claim native integration complete.

Engineer writes only index.html and compact viewer replay. Trader writes only daily skill/reference and October11 report prose/presentation revision. Lead owns the two ticket files and review/integration. Exact seven-file allowlist and protected paths are in the manifest. Preserve collection/input payloads, quote/SMA raw fields, sources, financial forecasts and targets, original08:06:54cutoff, ledger/calendar/index/other dates. Short confidence_reason wording may remove comparison/SMA references without changing confidence/direction/targets. Keep historical raw proxy evidence for audit. Update skill metadata/references and replay relevant missing-coverage/forced-direction cases. Engineer/Trader: no provider/Keychain calls, API transport edits, schedules, live trading or new forecast-model promotion. Lead accepted a saved Trader prompt alignment after review found the same obsolete proxy rule there; preserve exact08:00 rule,ACTIVE state,target and all other instructions. No schedule activation or timing changes; Lead quarter-hour remains paused.

## Evidence and native intake dependency
Engineer and Trader independently reviewed official documentation and installed SDK. REST screening pattern100/101 names bullish/bearish groups; totals count matching securities. Multiple filters AND; pattern groups do not supply per-ticker event counts. Empty success may mean unsupported market. No per-event observation timestamp or exact V2 rule equivalence was established. REST basic-info identity restriction/screening routes are absent from our constrained collector; OpenD remains login-held. SDK offline packing also fails with protobuf FieldDescriptor.label compatibility. PRSG-82 stays blocked pending accepted intake scope and verified provider contract.

Sources: [REST stock-screen](https://open.moomoo.com/zh-cn/api/quote/screening/stock-screen), [official MCP patterns](https://open.moomoo.com/mcp-docs/available-tools), [SDK screening](https://openapi.moomoo.com/moomoo-api-doc/en/quote/get-stock-screen.html). No native provider or credential access occurred in this review.

## When it's considered done
- [x] PRSG-88-D1: Compact signal column removes Quote/SMA directional chips; clearly labels native bullish/bearish counts unavailable with expandable KDJ/MACD/Bollinger missing coverage; independent forecast retained.
- [x] PRSG-88-D2: Trader skill/report narrative remove price comparison as native substitute or forced direction; no forecast/financial/input changes.
- [ ] PRSG-88-D3: Lead reviews exact scope and delivers tested correction; PRSG-82 native intake remains explicitly blocked.

## Progress
Lead froze scope before implementation. Native coverage remains pending under PRSG-82; this ticket corrects the misleading substitute, not data connectivity.

Lead independently verified compact+legacy DOM,102reporttests,publiccompact50rows/65events/12dates,skillmetadata,and preservation of frozenfinancial/inputrows,collection,cutoff,all120audit. Real1280desktop Enter/390x844mobiletap details passed; no pageoverflow. No native data/signing/Keychain calls. Saved Trader08:00prompt aligned with human correction, exactrule/ACTIVE/target readback preserved; quarterhourLeadpaused. Delivery pending.
