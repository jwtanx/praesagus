# PRSG-134 — Daily Report Publication Policy

Type: skill · Modules: skills, market-research · Owner: Trader · Priority: P1 · Effort: XS (0.1–0.3 person-days estimate) · Impact: high — directly addresses the human's observed unusable reports; does not establish data availability or prediction quality.

## Objective And Boundary

Honor the human's 21 October correction: publish daily reports only when at least 70% of the fixed 50 tickers have useful paired current prices and supported predictions. Continue collection and forecast follow-through privately below this threshold. This is a narrow instruction change to the existing daily-brief skill, compact reference and Trader schedule document; no runtime gate, provider intake, report replacement or scheduler provisioning.

## Human Evidence And Decision

The human first required all or 80% of tickers to have current prices and prediction prices with colored chips, otherwise do not post. The later direct instruction, “Okay push this and update to 70 percent”, supersedes the earlier numerical minimum. It does not authorize invented predictions, stale targets, removal of hard tickers, source-rights waivers or automatic publication. The fixed denominator is 50, so the minimum same-row intersection is 35. Human authorization to commit/push completed work was conveyed by Lead on 21 October; this task prepares independent review and does not itself commit or push.

## Accepted Scope

Lead delegated review of the three already dirty publication-policy files and creation of these two canonical records. Trader owns only the five manifest paths. Base is frozen in the manifest before this review handoff; the three baseline edits were pre-existing Trader work, now documented rather than attributed as new work at that base. Preserve unrelated .DS_Store and all concurrent source/model work. No dependencies beyond current instruction/reference interfaces and independent Lead acceptance.

## Approach

Require eligible finite positive current price plus supported finite positive prediction and ordered range, recorded direction, target date/horizon, confidence, frozen basis/method and required public-use admission on the same row. Verify rendered current prices, colored chips and accessible details. Preserve all 50 names and historical editions. Keep insufficient editions outside public artifacts and reports.json/latest, with unchanged insufficient heartbeats quiet. Preserve privately recorded exact matured-forecast blockers and recheck timing. Existing structural validator remains necessary, and is explicitly not a mechanical 70% gate.

Remove the old schedule instruction that agreeing quote-versus-close/SMA observations determine direction. The human's repeated schedule instructions explicitly prohibit proxies or native counts forcing forecast direction/confidence. Numeric support still comes from the admitted method. Clarify the final scheduled validator includes --public --compact. No validator or forecast method changes.

## Choices

Publishing all structurally valid incomplete reports was the prior flow and fails the current human requirement. Dropping difficult constituents would inflate coverage and is prohibited. 

## Tradeoffs

A mechanical gate would need separately accepted implementation and tests; this ticket records the human workflow restriction honestly without claiming enforcement. Instruction-only review cannot prove future runtime behavior, while withholding avoids knowingly posting unusable editions.

## Frozen Behavioral Replay

Manual tabletop replay against the final three documents; the following fixtures are synthetic except the explicitly marked retained operational case. No provider calls, report writes or publication side effects were performed. These are observed Trader decisions under instructions, not automated integration or browser-render tests. Lead independently replays before acceptance.

| Case | Frozen inputs | Observed decision |
|---|---|---|
| R1 | 34/50 eligible paired rows; structural validation passes | Hold privately; no index/latest, commit, push or post. |
| R2 | 35/50 eligible paired rows; full compact and actual chip/detail checks pass | Numerically eligible for existing authorized publication flow; no automatic publication from count alone. |
| R3 | 35 prices and 35 forecasts, only 30 tickers overlap | Count 30/50; hold privately. |
| R4 | 35 apparent pairs; one target expired | Count 34/50; hold; do not carry target forward. |
| R5 | 35 pairs, all source admissions private-only | Zero publicly qualifying pairs; hold without rights waiver. |
| R6 | 35 supported pairs; two chips or prices fail actual rendering | Render check fails; repair and rerun final compact/render checks before posting. |
| R7 | 35 pairs only after deleting 15 missing names | Reject denominator change; preserve all 50; assess actual original intersection. |
| R8 | 34 supported pairs plus one Unrated row with agreeing quote/SMA proxies | Count 34; do not promote direction, confidence or numeric target from proxies. |
| R9 | Unchanged insufficient scheduled edition plus matured unresolved cohort | Record exact cohort/count, blocker and recheck privately; DONT_NOTIFY unless meaningful change/action. |
| R10 | Prior public edition exists; new edition below threshold | Preserve prior edition/index/latest; do not overwrite with incomplete edition. |
| R11 | 35 qualifying pairs but final compact validator fails | Stop delivery/commit/publication until repaired and rerun, even though coverage passes. |
| R12 | Retained 21 October morning report: no current quotes or numeric targets; private forecast cohort has no public-derived-use acceptance | Hold replacement. No claim that private forecast count satisfies paired public coverage. |

All 12 manual outcomes conform to the final instructions. This does not establish future agent reliability, current 35/50 coverage, source rights, prediction calibration, live chip rendering or deployed enforcement.

## When It Is Considered Done

- [x] PRSG-134-D1: Three instruction files consistently encode the human's same-row 35/50 requirement and preserve evidence/forecast guards.
- [x] PRSG-134-D2: Skill metadata, local references, whitespace, exact scope and the 12-case behavioral replay are reviewed, with limitations recorded.
- [x] PRSG-134-D3: Lead independently accepts the diff, human provenance, replay and completion; required delivery hooks and push remain Lead-owned.

## Findings

Initial brief quality check reported missing recognized choices/findings/tradeoffs fields; headings were corrected without changing scope or behavior, then the checker was rerun.

## Evidence And Next Action

Trader review confirms existing version 2.7 frontmatter retains the skill name/description/metadata. Skill-creator quick_validate passed using configured Python 3.11. Local linked file targets and final five-path scope/brief/whitespace checks are recorded in the manifest. No production model/prompt/risk policy is promoted by this instruction correction; independent Lead review remains pending. No full test suite or live UI check is claimed: no executable source or public artifact changed. Lead reviews the five exact paths, independently replays the boundary cases, synchronizes completion evidence, and performs required hooks before the authorized commit/push.

## Lead Acceptance

Lead independently reviewed all five paths and human-authorized policy provenance. Replayed R1-R12 against final instructions: 34 fails, 35 same-row eligible passes only with public-use/compact/render gates; disjoint/expired/private-only/proxy/denominator/render/validator cases reject; unchanged blockers remain privately recorded and historical editions preserved. Instruction-level acceptance only, no runtime enforcement/public coverage claim. Required commit/push hooks run at delivery.
