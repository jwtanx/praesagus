# PRSG-86 Make Trader reuse the committed REST collector

Type: skill · Modules: skills, docs · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.3 person-days) · Impact: medium-high — prevents duplicate provider scripts and makes existing access discoverable.

Created 2026-10-11 MYT. The human requested that Trader use its report skill and an existing collection script at 08:00, rather than generate a provider script each run. Trader confirmed `scripts/market_collect.py` is the reusable intake path; the skill incorrectly stated REST collection was not implemented. Engineer privately verified and shared runtime, store and credential locator metadata with the registered Trader. No credential values were shared or written here.

## Accepted boundary

Lead owns the report skill, checked-in Trader schedule definition, this spec and manifest. Correct the implementation statement and add explicit collector reuse, input preflight, budget/cutoff handling, private summaries and the normal dated report's allowlisted projection. No new fetch script, credentials, account APIs, financial method/risk/model changes, private-draft rerouting, data/publication permissions, dependencies or report artifacts. The actual 08:00 automation prompt receives the same script requirement while retaining timing, active status, registered target, fallback and validator safeguards. Exact backup/readback stays private. This operational workflow change was requested by the human.

## When it's considered done

- [x] PRSG-86-D1: Skill and schedule definition require the existing collector CLI and match implemented input, budget and output boundaries.
- [x] PRSG-86-D2: Metadata/references validate; Trader replays frozen missing/failed intake and public report validation without provider requests.
- [x] PRSG-86-D3: Trader acknowledges the reuse flow and private preflight gaps; Lead reviews the complete scope and actual 08:00 schedule readback.

## Lead acceptance

Skill version 2.1 passes the existing quick metadata validator. Lead reviewed all four owned paths, the collector's actual optional daily history plan support and same-run price-only projection. Trader reviewed the workflow and replayed seven existing test nodes (18 cases): all passed. Missing store/credentials produce expected controlled failure; failed, missing, conflicting or late points do not become invented report prices. The frozen October 10 public report validator passed with 50 missing quotes, null current prices and no rated forecasts; this proves valid missing coverage, not quote availability. Lead inspected the external replay argv/log evidence and verified report/index preservation.

Actual automation readback remains ACTIVE at daily 08:00 MYT with the registered Trader target. Its original prompt remains intact with the explicit collector requirement appended. No financial policy or publication permission changes. Private locator metadata is available; Trader may prepare each nonsecret plan from the already approved universe and valid session inputs. Runtime/entitlement and coverage failures must still be reported honestly. No live provider requests, credential retrieval or new market report were performed for this workflow replay.
