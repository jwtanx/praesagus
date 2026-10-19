# PRSG-130 — Fixed Malaysia History Candidates

Type: feature · Modules: financial-data · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: high — removes the literal-one-symbol ingestion limit blocking the already approved fixed50 report. Estimate, not a delivery guarantee.

## Why the ticket is created?

PRSG-129 is complete. Its separately released actual BMS.1155 request returned100 integrity-replayed bars through16October with raw offset8 and explicit hypothesis offset480. This establishes narrow mechanical feasibility, not semantics or financial admission. The approved daily universe has20MYnames; the current five-layer guards admit only1155. User requests a working report command today by18:00MYT. This bounded supporting change uses that existing implementation authority, not a new product direction.

## Approach

Engineer owns the six code/test files in the manifest, base 6272eff3d1805722730b58f14325492a82bcaa12; Lead owns records. Admit only these exact case-sensitive BMS codes for raw daily100 end-only history: 0820EA, 0800EA, 1155, 1023, 0277, 0259, 0166, 0097, 5225, 5878, 4707, 3689, 5296, 4715, 6033, 5681, 5246, 3816, 1961, 5285. Do not accept arbitrary BMS/MY, alternate prefixes, padding/case/substring aliases or new endpoints. ExistingUS and BMS1155default/norm5 behavior and all previous replay versions remain unchanged.

New closed token `bms_fixed20_hours_hypothesis_v1` selects normalization6 for this fixed set, including1155 if explicitly selected. Old `bms1155_hours_hypothesis_v1` remains onlyliteral1155/norm5. For the other19symbols, reject missing/old/unknown token before credentials/provider. No implicit default/fallback. Fixed set may be exposed as an immutable connector constant and reused by store/collector without circular import; do not add a generic registry/framework.

Reuse existing request: GET `/api/v1.0/quote/BMS.<exactcode>/history-kline`, exact end/ktype2/autype0/num100, no start, no extra parameters. Norm6 uses the already-reviewed explicit integer-hours relation, retaining rawdate/time_key/time_zone and separately computed effectiveoffsetminutes, `operator_selected_hypothesis_not_vendor_confirmed` basis and inference quality. Raw HTTP/signing bytes never include local dialect. Bind token/version/code in job digest, worker frame/context, parentvalidation, immutablemetadata and integrityreplay; prevent norm5/6/legacy substitution/downgrade. Legacy frames cannot acquire new scopes. All date/end/future/secret/row-count/finitepositive/duplicate gates remain.

No source financial admission, MYR assumption, actualcalendar/settlement claim, public rights, model/training/output behavior or automatic transport release. The token is an explicitly declared research hypothesis for each candidate, not proof that all fields have uniform semantics. A provider rejection or metadata mismatch remains bounded and visible. Actual19namecollection requires a later separate finite Lead release.

## Acceptance and checks

- [x] PRSG-130-D1: All20 exactsymbols have positive offline closed-job/connector/worker/store/replay coverage under norm6. Old1155/norm5 and US/legacy behavior remain covered.
- [x] PRSG-130-D2: Reject unsupported/case/padded/alternateprefix codes; missing/old/crossmarket token; crossjob/version/digest/context substitution; malformed/future/date/end/duplicate/secret cases. No actual provider call during tests.
- [x] PRSG-130-D3: Lead independently reviews complete changed scope and runs focused regression tests; required commit/push hooks pass. Actualsource/20MYnumeric/model gates stay separate.

## Ownership and outputs

Only unrelated.DS_Store is baseline dirty. No other worker writes these paths. Engineer returns exactpatch/sourcehashes/testresults/failures and handoff; Lead integrates/delivers under standing human authority. Protect secure transport/signing/credentials, scripts, artifacts and numericalmodel/forecast code. No new dependency, provider call, raw rejected-payload retention or UI change.

## Scope amendment — sixth secure route guard

Before edits Engineer identified SecureReadTransport._validate independently permits onlyUS/literal1155 and enforces1155query. Lead authorizes exactly connectors/moomoo_rest_live.py and tests/test_moomoo_rest_live.py in addition to sixpaths: reuse the same closed20symbolconstant for route and rawdaily100query validation. Signing, TLS, credential loading, URL/origin/security/deadline/response policies are protected behavior and must remain unchanged. No genericprefix or skippedguard. Focused check includes the live-transport test file; mocking itself does not prove a provider entitlement. Trader-owned19October report/index edits are unrelatedbaseline and must be preserved.

## Lead acceptance

Lead independently reviewed8frozenpaths and exactclosed20/version6/old1155norm5/USlegacy/digest/frame/parent/rawreplay/privacy behavior. Securetransportdiff limitedimport+route/queryguards, signing/TLS/credentials/deadlines unchanged. Independent1096passed4.00s; Engineer1096passed4.11s, no initialfailures. Frozenpatch4939ddc3dd8663640c219e09b12e5854c0fccea984a599332432040acf6a972a. Actualprovider/sourcefinancialadmission remainsseparate; mandatorydeliveryhooks runatcommit/push.

## Choices

Use one immutable20symbolset shared by existing guards, rather than arbitrary BMS matching. Select a new explicit dialect/version6, retaining the old literal1155token/version5 and defaultminute behavior. Other19names cannot inherit legacy-frame permissions. Keep the existing secure client and collector; do not introduce a second ingestion path.

## Findings

Actual1155canary returned100bars with rawoffset8 and date matches under the explicit hours hypothesis. That evidence justified testing the same interpretation for a closed candidate set, but does not prove semantics of othernames. A pre-edit inspection found a sixth securetransport guard; the exact two-path amendment was reviewed before edits. Eightfile independent checks passed1096tests. First delivery hook rejected this authored brief for missing decision-context sections:3398passed/1failed/41warnings60.09s. The missing sections are now supplied; tests are unchanged and the gate will rerun.

## Tradeoffs

The closed list limits maintenance and permissions to the existing fixed50report. Another ticker requires a reviewed scope change. Explicit research hypotheses preserve ambiguity and replay integrity but add a version/token branch. This mechanical path can capture data while currency, actions, calendar and forecast admission remain independently reviewed; fixture success cannot establish actual19name coverage.
