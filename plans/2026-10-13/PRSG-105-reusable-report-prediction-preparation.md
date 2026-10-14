# PRSG-105 Reusable daily prediction preparation

Type: feature | Modules: financial-data,market-research,skills | Owner: Engineer | Priority: P1 | Effort: S 1–2person-days | Impact: high

## Required outcome

Human goal is an actual report with target price/range/direction and the following report’s refreshed next-session movement. Calculator existence alone is insufficient: current Trader workflow has no invocation. Implement a reusable normal-report preparation step and update daily-report skill invocation, preserving existing collector and final validator.

## Frozen scope and interface

Ten paths in manifest. No fetch/signing/Keychain/client code, private-draft runner, public artifact write, source admission inference or new ledger/scorer. Pure helper +CLI: normal current template/universe/calendar with reviewed evidence/admission, issuance/cutoff -> private prepared report and private audit, no publication. Exactlyone matchingSPYUSUSDrow; preserve other49rows/quotes/source/narrative/universe/gaps. Reuse build_forecast_scenario and apply_scenario_to_row, refuse authored_fixture generated output. Source links approved by reviewed input must remainpublicallowlisted; no hashes/private paths/evidenceIDs. Recompute verified reference coverage using current compact_reference semantics. Run existing full/public/compact report validation before output; no secondvalidator.

CLI bounded JSON, duplicate/nonfinite/symlink/privateownership checks, fixed safe errors, new private destination atomicwrite/no overwrite; private audit separate. Never print input values/paths/secrets/raw evidence. Require honest current cutoff and latest completed reference/next target; template metadata cutoff mustmatchacceptedactualissue/report cutoff ratherthan silentlybackdate. If inputs withheld, controlled SPYnulls/reasons; do not claimfulfillednumericreport. No artifactschangedinthisscope. Preserve originalmorning edition before a separatelyreviewednew current edition; tomorrow uses new completedreference/history/eventreview, never reuses today’s target.

Skill/reference update exactcommittedCLI afterinterfaceaccepted, metadata version andreferencevalidation. Invoke betweenexistingcollector/readinputadmission andfinaldatedreportwrite/validator, include nextvenue targetmovementandfreeze/followthroughexistingledger responsibilities. Reuse originalaccountaccess/collector, no ad hocscript generation. Skill behavioralreplays real-shapedadmittedfixture, missinghistory, futureknown, cash/targetevent, failedvalidation/failedwrite andnextday reference must refresh. No claimunattendedactualdeliveryuntilTraderconfirmed invocations/schedule and live output.

## When it is considered done

- [x] PRSG-105-D1: Exact helper/CLI/skill interface accepted.
- [x] PRSG-105-D2: Full successfulfixture + rejection/immutability/privacy/skill replays passed, existingchipguard exercised.
- [x] PRSG-105-D3: Lead independently accepts integration; actual numeric publication remains separately verified goal requirement.

## Checks

ApprovedPython -m pytest -q tests/test_report_forecast.py tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py. Skillmetadata/referencevalidation using existing skill-creator procedure, no new model/performance promotion. Focused plus full hooks. Actual sourcecapture and current/tomorrow report publication are external acceptance obligations, not replaceable by synthetic tests.

## Lead template preparation requirement

CurrentSPY row has quote timeout AND stale forecast-unavailable gap strings. Do not silentlydelete provenance/gaps inside mapper. Trader prepares a new edition template with newly reviewed current forecast-input notes before CLI; preserve originalmorning edition. CLI preserves caller’s current gaps, appendscontrolledwithholding, replacesonlyforecastoverlay andcoveragecount; it mustnot silentlyleave stale 'No supported numeric target/range method' in a newlyreviewedgeneratededition. This is a template/admission responsibility; exacthelpercontract mustexplicitly validate/reviewthatlimitation.

## Real receipt precision

Actual primary/workflow receipts have6fractional digits. Preserve those exact instants; do notfloor/ceilor backdate intake. Extend trusted scenario timestamp syntax from1–3to1–6fractional digits to represent normalPythonmicrosecondreceipts, with7+digits stillrejected and all monotonic/venue boundaries unchanged. Generator/docs/contracts reflectthisexplicittechnicalcompatibility. Add timestampregressions; no model/price change. Two existingscenario paths added toscope.

## Lead accepted preparation scope

Tenpathscope/base frozen after104. Engineer proposes exact bounded helper/CLI contract for confirmation beforecoding; code/skill integration accepted within existinghuman goal. Preserve actual6digitreceipt times and no backdating. No providercall/publicartifactwrite in implementation.

## Exact interface accepted by Lead (2026-10-14)

Pure `prepare_report_forecast(template, *, evidence, admission, issued_at, report_cutoff, template_reviewed)` returns exactly status/reasons/report/audit. Schema3 compact-v1, one matching US/SPY/USD, reviewed current-edition template, exact metadata.as_of=cutoff and MYT date required. Original inputs, other rows and all non-overlay row fields remain unchanged. Only SPY overlay and verified_forecast_reference_count change, using existing calculator/mapper/compact_reference. Missing either evidence/admission withholds in helper; generated fixture and known stale forecast missing-input strings reject, never automatically removed. Review flag is workflow attestation only; other stale summary/footer/prose must be reviewed externally.

CLI `prepare_forecast_report.py --template ABS.json --universe ABS.json --calendar ABS.json [--evidence ABS.json --admission ABS.json] --issued-at ISO --cutoff ISO --template-reviewed --output-directory ABS_NEW_PRIVATE_DIR`. Both evidence/admission flags or neither; mismatch fails before reads (Lead interim correction). Owned private canonical regular0400/0600 inputs with0700 parent, max2MiB each, duplicate/nonfinite/bounded structure and no symlink traversal; reject any Git-checkout ancestor without reading Git metadata. Full existing current-universe/public/compact validation occurs in a private temporary shared-calendar context. Output is a new0700 directory containing atomic no-overwrite0600 prepared-report.json and audit.json; ordinary errors roll back own created outputs. Pair is not crash-atomic; review remnants separately. Fixed prepared/withheld/count0|1 stdout or fixed failed category; no paths, hashes, user/provider values, exception text. No provider/credential/private-store/public artifact calls.

Scenario times1–6 fractional digits preserve exact input issuance/cutoff and comparison instants;7+ reject. Fresh next-day latest completed21-close reference, target and independent as-of event/rights/calendar review required. Tests are authored plumbing only, never source authentication or financial-performance proof. Daily skill version2.5 calls committed CLI before normal publication/final validator and retains existing ledger responsibilities; actual scheduling/publication/invocation acceptance remains external.

## Engineer evidence (2026-10-14)

Approved Python3.11 focused command `-m pytest -q tests/test_report_forecast.py tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py`: **388 passed in1.90s**, no skips. Full isolated `-m pytest -q`: **2213 passed,41 dependency deprecation warnings in43.55s**, no failures/skips. Skill-creator quick_validate passed for daily-market-brief; all4 local Markdown references from changed skill/reference resolve. `git diff --check` and complete ten-path ticket validation passed. No primary protected projection change; its SHA256 remains b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f.

Behavioral replays execute the documented private CLI and authoritative validator using authored50-row inputs: both fixed methods generated; other49rows/input bytes/provenance/quotes preserved; reference count includes other existing reference; both omitted inputs produce withheld; mismatched CLI pair rejects before any read; future-known/unknown cash amount/target event/incomplete review withhold; known stale gaps/generated fixture refuse; invalid report/universe/calendar/private boundary writes nothing; duplicate/nonfinite/oversized/deep/symlink/permissions/ownership fail privately; existing output never overwritten; failed second write and reserved-directory open roll back; next-day stale packet withholds while fresh completed reference/target passes. Actual prepared row reaches committed JS prediction guard. Receipt1–6digits preserved;7+ and microsecond future ordering reject. Initial focused runs380/385/386 passed as coverage was added; no failing105 run. Lead interim corrections incorporated before final388 check.

Independent Lead review/full Git hooks/commit remain pending. No actual source admission/numeric current report/publication established by tests; actual source intake and live report delivery remain separate active goal requirements. No credentials/provider calls, public artifact writes or schedule provisioning performed.

## Lead independent acceptance

Lead independently read all10paths;388focusedpassed2.18s; exacttyped/pairedinput, privacy/atomicrollback, cutoff/microsecond and nextday behavior reviewed. Fullhooks required on delivery. Actual admitted history/numeric publication remains separate goal. Primary unrelated projection yields existing cutoff regression failure1/192; preserved, not partof105. Clean isolated baseline passes388focused. CLI is real reusable preparation; current actual numeric report is NOTdelivered by fixture checks.
