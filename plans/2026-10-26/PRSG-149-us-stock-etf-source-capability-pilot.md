# PRSG-149 — US Stock and ETF Source Capability Pilot

Type: feature · Modules: financial-data, connectors, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 estimated person-days) · Impact: high — obtains the missing actual identity and AAPL full-field evidence for a valid multi-name model route.

## Objective

StageA prepares exactly two read-only requests: one POST /api/v1.0/quote/stock-basicinfo with code_list US.AAPL and US.SPY, then one GET history-kline for US.AAPL only with start27April2026/end23October2026/ktype2/autype1/num370. Expect126completed AAPL sessions, actual returned current typed identities and field precision; no guessed provider IDs. Existing SPY data may be reused only after exact old/new overlap, basis, rights and new-fit-purpose review; no new SPY history call is released. Later AAPL3year history/fit and full30/full100 are separate held stages.

## Approach

Reuse existing ResearchProvider.basicinfo/history, signed secure transport, credential-reference loader, transient secret inspection and private immutable capture patterns from147. New fixed-list wrapper only because collect.py performs market discovery. Preserve source/request/response hashes, actual original clocks, requested adjustment/raw timezone qualifiers and explicit unknown currency/unit/fit admission. No public values or credentials. Reuse SPY only after148 exact retained121-overlap review; review AAPL native fullOHLCV/turnover/volume applicability after capture before any training admission. This tests actual source capability/identity, not factor correctness or model quality.

## Frozen scope

Lead owns these two repository records. Engineer writes only new private /Users/jwtan/.codex/lead-state/PRSG149/engineer/ wrapper/QA/plans/receipts. No repository runtime/test/dependency/secret or old147packet edits. AI148andTrader148 private outputs remain disjoint. Existing credential directory/AppKeyID references may be reused internally by the unchanged secure worker; do not inspect/print secret bytes. Engineer preparation makes no live call. Lead separately releases exact request/runtime/input/source-use/resource/exclusive-managed-window/one-use pins.

StageA budgets: max2requests total (1POST+1GET),2identity rows plus370history wire-row cap=372,0retry/otherendpoint/follow-up, at least3seconds between actual starts,10second HTTP timeout per request,90second operation and2second cleanup. Any denial/429/empty/missingidentity/malformed/partial126calendar/wrongcode/unknownattempt/clock/resource/cleanup failure stops remaining calls; do not retry or silently shrink expected dates. Failures must retain honest request-attempt/response/unknown-outcome receipts. No account endpoints or new paid access. Synchronous disk limitations remain explicit; do not invent absolute hard memory/kill guarantees.

## Choices

The smallest stock-plus-ETF stage checks actual source fields before another6olderAAPLhistoryGETs or fit can be considered. It is not a full-history dataset. Existing SPY-only transfer cannot be described as trained30/100coverage. New fit needs explicit dataset/nativeunit/basis/private-fit admission and separate bounded release after actual3year coverage.

## Findings

148AI identified existing basicinfo as POST and a conditional present-cutoff research fit path without changing113strong gates. Trader148 supports only a preparation-level own-account private research scope; AAPL full adjusted field and fresh typed identity evidence are missing. SPY147exact126source is independently reviewed but inference-only, not blanket training admission.

## Tradeoffs

A current successful capability sample may permit later research-source collection; it cannot prove adjustment formula, historicalmembership/PIT, untouchedOOS, adequate calibration, fullcoverage or public rights. Keep all unknowns and original clocks. Reject unsupported units or source progress rather than fill missing rows or reinterpret raw timestamps.

## When it is considered done

- [x] PRSG-149-D1: Exact fixed-list wrapper and bounded rejection QA independently accepted.
- [x] PRSG-149-D2: Actual separately released StageA packet and financial/canonical readiness independently reviewed.

## Validation and delivery

Focused fixture coverage for identity types/missingcodes/batchPOST, exact requests, row/response caps, partial/missing/future/malformed/duplicate/stale clocks, rate limits/upstream errors, stop-first-failure/zero retries and cleanup/resource/one-use rejection. Lead independently reviews all private code/pins and meaningful QA. Actual source and financial review evidence stay private. No provider call, source/fit/model promotion or paid authority arises from this specification alone.

## Pre-implementation amendment

StageA initially proposed3requests including a freshSPYhistory call. Before wrapper freeze or any release, Lead superseded that draft with1POSTbothidentities+1AAPLhistoryGET (2requests/372rows). Existing SPY754through16October plus147126through23October are candidates for explicit121-date overlap/source-vintage/rights/new-fit-purpose review; no automatic training admission. FreshSPYfallback requires separate accepted scope/budget, not a retry. Preserve earlier drafts as superseded.

## Stage B scope accepted after actual Stage A success

StageA completed one POST plus one AAPL history GET:2completedresponses/128wire rows/126 AAPL dates,5.174seconds,3.043seconds actual start spacing,0retry/unknown and verified cleanup. Lead independently verified9manifest artifacts, actualdistincttypedintIDs/current STOCK AAPL andETF SPY,126calendar dates/positive ordered OHLC/nonnegative volume/turnover and actual clocks. Native currency is absent and remains unadmitted. Exact source packet is private149/engineer/intakes/2026-10-26_115306_181094. Initial Lead QA failed from missing basetemp parent, then stale148acceptance metadata pins; setup corrected and exactly2source metadata hashes independently refreshed without guard weakening. FinalLead49QApassed4.92s.

Before any StageB implementation or live call, Lead accepts a NEW private149/engineer/stage-b/ preparation using the same secure APIs/normalizer/credential-reference/secret/oneuse/supervision patterns. Never alter completedStageAinputs or outputs. No provider call is released here. StageB is exactly six GETs for US.AAPL, ktype2/autype1/num370/max_pages1 per explicit one-page call. Ranges (inclusive):3Nov2025–1May2026;12May2025–7Nov2025;18Nov2024–16May2025;28May2024–22Nov2024;7Dec2023–3Jun2024;23Oct2023–13Dec2023. Each intentionally overlaps the newer slice by five scheduled sessions. Expected returned counts124/126/123/126/122/37;658olderreceived plus126StageA=784observations/754unique target dates, if actually complete. StageB caps6GET/2220wire rows/180secondsoperation+2secondcleanup/10secondHTTP/atleast3secondactualstartspacing/0retry/otherendpoints. Stopfirstfailure/missing/extra/duplicateoutsideallowedseam/basis/unit/precision/identitydifference/clock/unknownattempt/cleanupfailure.

Preserve both observations and original hashes/vintages/knowns at each seam. Require exact six-field OHLCV/turnover plus code/typedID/unit/precision/basis agreement across all five dates at every seam; unknown currency stays explicitly unknown until review. Reject any revision mismatch without rescaling, averaging, synthetic filling, dropping contradictions or additional calls. Canonical revision choice happens only after values agree and exact source/training-purpose admission is independently reviewed. Lead freezes StageAactualresponse/typedidentity/currentconditionalfinancialreview and exactStageBcode/plan/request/sourcepins before one finite new release. Reuse-first means no newSPYhistory; any freshSPYfallback needs separate accepted scope/budget.

- [x] PRSG-149-D3: Six older windows and754unique AAPL target dates/seams/lineage independently reviewed for source readiness.

This extension is actual source collection only, not fit approval or numerical execution. Trader+Lead must separately review full-field AAPL nativeUSD/currentadjustment/source-use assumptions, retained mixed-vintage SPY component and explicit new pooled research-fit purpose. 150fit remains held until exact1508row admission and finite fit release. Strong113D2/full50/full100/publicrights remain unchanged.

## Lead execution review — 27 October

StageB pre-import provenance gap was corrected before live release. Independent64fixture checks passed17.70seconds; all32runtime/private/externalpins matched. Exactly6newhistoryGETs completed with658olderobservations,0retries,0unknownoutcomes and verifiedcleanup in16.156seconds. IncludingStageA,784observations cover754unique AAPL dates; all30duplicate seam observations agree across15numeric/basis/sourcefields (450checks). All27manifestartifacts matched bytes/hashes. Raw response bodies are not retained, only response hashes; original normalizedobservations/knowns/vintages remain. Fullspanfinancial/newfit-purpose review and1508cohortadmission precede any training. No fit/inference/strongpromotion/fullcoverage accepted here.

Trader independently accepted exact754AAPL+754SPY financial/source-use components for the new private present-cutoff150researchstudy. Lead verified all44inputpins and scoped conditions. NativeUSD remains explicit inference known at the newreview, not a returnedcurrencyliteral. Mixedvintages, oldSPYunverifiedinternalpageseams, currentrequestedadjustment and unavailablehistoricalPIT remain limitations. D1–D3 accepted;150canonicaltrainingadmission and finitefitrelease remain separate.
