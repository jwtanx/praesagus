# PRSG-144 — Malaysian Model History Capability

Type: spike · Modules: financial-data, connectors, market-research · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.2 person-days estimate) · Impact: high — resolve the concrete source capability blocking actual Malaysian trained-model inputs.

## Why the ticket is created?

Human25October orders both fixed50US/MY and standalone100US predictionproducts by28October and instructs continuinguntilworking.143addsMYR/XKLSofflineinputbutactualtrainedinputisnotadmitted. AI readonlyaudit verified53retainedrawcapturescontainfullOHLCVfields,whileallrequestsused100unadjustedbars;existingMYrequestguardallowsfixed20end-onlyautype0. Need an evidence-backed next collection/preparation decision,not fabricated3yearadjustment/PITcoverage.

## Question And Timebox

Within45minutes determine whether an existing permitted documented Moomoo route can provide bounded Malaysian fullOHLCV modelhistory with required forward-excluding-dividends basis and adequate coverage/provenance. Deliver exactsupported/unsupported/unknownfindings and smallest safe actualcapture/projection proposal; no speculative implementation/providercalls. Reference143andoriginal109/113contracts.

## Approach

Read sourceaudit2be68ca22a483be956ec61421c8c87104f1e791847a7bf8c402b21767fa7afe1 and relevantcurrentconnector/provider/schema code. Use atmost4targetedqueries/6officialprimarydocuments/0retry to resolve route parameters, MYmarketcoverage, adjustment semantics/paging/count/dateunits/volumeunits and permission/quotaboundaries. ExistingprivateAPIcredentials are not docs and mustnotbeopened. Preserve retrieval/publicationtime and unknowns. No endpointprobe is authorized by this spike.

## Choices

A: reuse existinghash-verifiedrawOHLCV with originalknowns for offlinecandidateprojection; autype0/shortcoveragecannotbe relabelledrequiredadjusted3year/PITinputs.
B: reuse a documentedpermittedadjustedMYhistorycapability under a later separatelyfrozenfinitecanary, then explicitcanonicalidentity/currency/units/calendar/action/rights/time receipts; no US-onlyroutealias without evidence.
C: ifthatcapabilityisunsupported/unknown, identify actualalternativeprimarydata/factor-evidence dependency or retainedresearch-onlyscope; no newpaidservice/externalcontact/policyrelaxation.

## Frozen Scope

Engineerownsprivate capabilityevidence only;Leadowns thisspec/manifest. BasefullcurrentHEADinharness. Allruntime/tests/financialreports/143modelsource/141pipeline/142UIprotected. No sourcecodechange,newdependency,providerrequest,capture/admission,fit,prediction,promotion orpublicdelivery. Existing35financialrenewalTradercontinuesindependently.

## Findings

Baseline143auditinspected53capturefieldnamesand349metadatarecords:rawOHLCVfieldsarepresent,but100unadjustedbarrequestsareinsufficientforunchangedmodelbasis/historycontract. USprovideralreadyhasadjustedboundedhistory;MYstockresearchpathisnotimplemented. DocumentedMYadjustedcapabilityremainstobeverified.

## Tradeoffs

Offlineprojectioncanpreserveexistingevidenceandavoidrefetchbutcannotcreateadjustmentfactorsorhistoricalavailability. A documentedboundedcanarymayresolvecapabilitywithoutnewpaidaccess,buttechnicalsuccessisnotfinancial/source/modeladmission. An unknowncapabilitymustnotbeconvertedintoguessedrequests.

## When it's considered done

- [x] PRSG-144-D1: Primarydocumentation/currentimplementationcapabilitymatrixwithoriginalsourceURLs/retrievaltimes explicitly distinguishesMY/UScoverage,OHLCV/basis/date/units/limits/rights andunknowns.
- [x] PRSG-144-D2: Reviewedoptionsdecisionandexactnextread-onlycapture/projectionscope/budget/preconditions orspecificexternaldependencyreturnedwithin45minutes; no code/providerreleaseorparentcompletioninferred.

## Validation And Delivery

Leadindependentlychecksprimarysources/codepins/options/requestsafetyandallchangedpathswithvalidator. Documentunavailable/contradictorysourcesandstopbounded. Preservehistory/rights/quality/sourceauthenticationlimits. Spikecompletionisadecision,notactualmodelreadinessor113strongacceptance.

## Independent Decision

Lead reviewed the capability decision, its official-source matrix, all recorded code pins and the exact proposed one-request canary. Report SHA fe33caaa66587e69313e10ad86bc1691960e493b020647d8b47079f1de7728e0 verified; all source code pins match. Four targeted queries and six official-document attempts, zero retries/provider calls. Dictionary describes autype1 as forward excluding dividends; actual Malaysian response semantics, units, rights and long-history admission remain unproven. Accept a separately scoped known BMS.1155 route canary changing only autype0 to1; no call or model promotion is granted by this spike. Raw offline projection remains a separate candidate-data option, not a substitute for adjusted history.
