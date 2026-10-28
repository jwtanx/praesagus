# PRSG-152 — Remaining US Model Source Cohorts

Type: feature · Modules: financial-data, connectors, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: high — supplies the remaining24actualUS30 model source series while preserving independently released ceilings.

## Objective

ExistingacceptedfullUS30coverage remains unfinished. SPY/AAPL and151V/JNJ/WMT/XOM histories already exist and mustnotbe recollected here. Collect remaining24historicalseries using sixclosed four-namecohorts, in exactfixedUS30order: (QQQ,IWM,JPM,GS); (MSFT,GOOGL,NVDA,TSM); (AVGO,LLY,ABT,PG); (KO,TSLA,HD,MCD); (COP,SLB,CAT,GE); (UPS,LIN,FCX,NEM). Exactcodes useUS.prefix. QQQ/IWM expectedETF; other22expectedSTOCK; actualdistincttypedIDs/state/unitcontext mustbe returned and verified, neverguessed/coerced.

## Approach

Reuse151reviewedsecureResearchProvider/basicinfo/history/transientinspection/preimport/runtime/sourcepins/oneuse/supervision patterns. Engineer owns only newprivate /Users/jwtan/.codex/lead-state/PRSG152/engineer/ and sixdisjointcohortsubfolders. Lead owns these2canonicalrecords. No runtime/test/dependency/oldsource/model/CSV/otherroleedits. Freeze oneexact1POSTfouridentities+7GET/name percohort, using151same2023-10-23–2026-10-23windows/counts126/124/126/123/126/122/37 with6five-dateseams/name. ktype2/autype1/num370/max_pages1, rawbodiesnotretained, all3136historyobservations/3016code-dates percohort preserved inboundedpercodefiles. No SPY/AAPL/V/JNJ/WMT/XOM/probes/discovery/fallback/news/account endpoints.

## Choices

Eachcohort has itsOWN finite release,29requests/10364wire/480secondoperation+2secondcleanup/10secondHTTP/3secondactualstartspacing/0retry. Sixcohorts imply atmost174plannedrequests,notoneexpandedceiling orpermissiontoautoexecute. Leadreleases each after freshresources/privatepurpose/exclusiveknownmanagedIP/actualcodeandinputpins. No concurrent sourcecohorts; stopfirstfailure withincohort, preservecompletedcodes/partial/unknowns, holdthenreviewbefore anyremainingcohort. Neverrepeatfailed requests implicitly. Nativecurrencyabsent remainsNone, newliteralorprecision/basis/identitychangeholdsforreview. Sourceclock strictlybefore28Oct04MYT; no automaticrollover.

## Findings

151actual4series returned754unique dates/name,24seams/1800exactfieldchecks,3136observations,29requests/0retry/verifiedcleanup; financialreview acceptedboundednativeUSDfieldinference/privatefuturefitpurpose withfirstseen/factor/PIT/historicalactionsunknowns. This supports interface reuse, not automaticnew24unit/basis/entitlement/trainingadmission. ETFtradedunit is notunderlying/mandate/effectivehistoricalmetadata. Fullfinancialsourceuse/units/privatefuturefitpurpose needretainedpernamecontext andactualsourceaftercapture; newcanonicaldataset/fitstudy/release remainsseparate.

## Tradeoffs

Sixsmallcohorts bound source and quota risk and preserveoriginalcaps. Sixadditionalfixtureclones or genericclosedcohortentrypoint are acceptable ifimmutable code/plan/type-map inventories stayclosed and independentlyverified. Eachpercodefile<=2MiB and boundedreferenceindex; no giantcombinedrowblob. Exactall15comparablefields andoptionaltypedIDecho at every5datejoin; norescale/tolerance/fill/drop/average. Currentrequestedadjustment/seamagreement doesnotcertifyfactorformula, totalreturn, historicalPIT orpublicrights. Fixedcurrentcohortresearch/unknownhistoricmetadata policy remains; no strongclaim fromcompletion.

## Acceptance

- [x] PRSG-152-D1: Sixclosed29requestpreparations/sourcepurpose/type-maps/pins andmeaningful rejectionQA independentlyaccepted.
- [x] PRSG-152-D2: Actualremaining24x754source dates/144exactfive-date joins/originalvintages andfinancialsource readiness independentlyverified afterseparatefinitecohortreleases.

## Validation

Meaningfulfixtures must exercise firstcohort mixedETF/STOCK identities, unexpected/missing/duplicated/typealiasIDs, exactqueries/noextraendpoints, all15seamfield revisions, units/currency/future/missing/duplicate/precision/contextdifferences, laterwindow/codefailures, privacy/429/upstream/transportunknown, preimporttamper/oneuse/clock/purpose/resources/cleanupfailure, boundedpercodeoutputs and offline-onlylabels. Actualevidence notfictionalQA establishes source readiness. Privatepurposecaptureapproval precedeslive;fullspanfinancial/AIcanonicaladmission/newfitcontract precedetraining. No source/modelpromotion/publiclicensing inference.

## Reviewed Delivery Evidence — 28 October 2026

Six finite cohorts:174 actual requests/0retries,18816 observations/18096 unique code-dates,144 five-date seams/10800 exact field comparisons. Lead preparation510QA passed; all six actual-source reviews and financial basis resolutions accepted. Private evidence /Users/jwtan/.codex/lead-state/PRSG152/lead/ and PRSG153/lead/full30-candidate-admission.json. Conditional nativeUSD inference retains nativeNone; cash-linked adjustments disclosed, no provider formula/PIT/public certification.
