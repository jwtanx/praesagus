# PRSG-133 — Independent ETF Directory Discovery

Type: feature · Modules: financial-data, market-research · Owner: Engineer · Priority: P1 · Effort: S (1–2 person-days estimate) · Impact: high — resolves a demonstrated discovery dependency; eligible fund coverage is uncertain.

## Decision Context

Accepted child of PRSG-109 under standing implementation authority. Existing broad Moomoo ETF labels include REITs/trusts, retained300 and bounded600 actual candidates contain no confirmed ETF. Three-document follow-up did not verify an ETF-only selector; this does not prove none exists. Lead chooses an optional separately attributed official-directory candidate cohort instead of blind paging or registry seeding. PRSG-111 stays complete.

## Objective And Boundary

A manual collection run can discover fund candidates from a complete reviewed official directory pair, then apply existing typed provider enrichment and unchanged financial eligibility/quota rules. This is discovery evidence, not a curated portfolio or admission from an ETF flag.

## Choices

Use the optional official pair as an independent discovery cohort; keep generic paging unchanged, and retain waiting for a documented ETF-only API as an alternative. No selector is guessed.

## Tradeoffs

The directory route offers complete current listing candidates with attributable origin, but adds a freshness/checkpoint contract and still needs bounded provider enrichment and financial review. It cannot reconstruct historical membership or guarantee eligible fund coverage.

## Accepted Scope

Freeze base075d22167811e073b8afaca634229cb60b80d56b and the exact manifest paths. Add an OPTIONAL reviewed local directory-pair manifest to standalone configuration and collection. Default without it retains existing three stock pools. No network directory fetching in this ticket. Manifest identifies both actual NasdaqTrader nasdaqlisted/otherlisted files with allowed official source URLs, bytes/hash, actual retrieval/known time and explicit current-only origin. Use existing secure private-file reader conventions. Require complete nonempty paired files, exact mandatory headers and creation footer, bounded size/count, content hash binding and known/retrieved <= cutoff. Freshness maximum24hours at cutoff; historical files can support authored/offline tests but cannot silently become current membership. Preserve footer verbatim; do not infer its timezone.

Enumerate ALL ETF=Y/TestIssue=N rows before existing bounded enrichment. Exact reviewed listing aliases only; conflicting/ambiguous alias or duplicate security stays rejected/UNKNOWN, never arbitrary first-match. Preserve source file/row/hash/actual-known lineage. Add a separately named ETF discovery origin and compatibility/checkpoint binding. Changed pair/options cannot resume an old compatible generation. Existing request/row/time budgets and incomplete-state handling bind; no attempt to look up thousands outside those budgets. Do not use first20, manual49-name classification registry or portfolio/daily list as a universe. Registry continues classifying only actual discovered candidates. Existing provider identity/snapshot/history/source-rights/price>=5/252sessions/median20>=25M/mandate/signed-leverage/reset/familycap2 gates and 12/2/2/2/1/1 quotas remain unchanged. ETF directory flag alone is insufficient financial eligibility. Exclude directory-only candidates from company winner/loser/volume and speculative stock pools; overlapping genuinely discovered listings retain attributable reasons without changing quotas. Persist honest incomplete/shortfall status.

## Constraints And Non-Goals

No live calls, credentials, directory download, provider selector guess, public data export, model training/promotion, new financial thresholds, order execution or automatic scheduling. Do not modify provider/universe policy, connectors, ingestion, public artifacts, completed111 records or unrelated .DS_Store. No extra dependencies. Scope/interface changes require Lead review.

## Validation

Focused offline fixtures: both directory formats; full-pair missing/malformed/truncated/header/footer/hash failures; duplicates/test issues/conflicts and exact aliases; stale/future retrieval/known times; 24h cutoff edges; changed source resume rejection; separate ETF-only pool provenance; budget-limited incomplete collection; no registry/manual seed; unchanged default stocks/speculative selection and quotas. Mock transports must show no actual network. Run new focused regressions plus existing stock-research collection/config/universe tests appropriate to changed paths. Lead independently reviews full diff/scope and actual hook checks before authorized commit/push. Offline tests do not establish live source rights, fund eligibility or strong-model performance.

## When It Is Considered Done

- [x] PRSG-133-D1: Optional complete-pair importer validates source/times/identity and preserves lineage.
- [x] PRSG-133-D2: Separate ETF cohort integrates bounded enrichment and resume compatibility while default stock behavior stays unchanged.
- [x] PRSG-133-D3: Focused offline rejection/budget/default regressions pass with exact evidence.
- [x] PRSG-133-D4: Lead independently accepts scope, implementation and delivery evidence; live data admission remains separate.

## Evidence And Next Action

Private inputs: lead-state/standalone100-etf-discovery-20261021/contract-followup/handoff.json and directory-extension-decision.md. Retained19Oct directory pair is evidence input only, not fresh21Oct membership. Original109 specifies liquid/activity-ranked20funds; this adds an independent discovery source without changing eligibility or selection targets. Engineer implements this frozen scope and returns diff/check evidence; no live source/provider release.

## Accepted Interface Detail — 21 October

Lead accepted optional collection.etf_directory_manifest with schema1/current_only, exactly two official files/hash/bytes/actual retrieved/known times and reviewed_by. Simple unambiguous listed codes map exactly to US.same-symbol; punctuation/namespace differences require an explicit source-backed reviewed alias, never heuristics. The new etf_directory_candidates_per_run defaults40/max400 independently of stock max_candidates. Enumerate the whole pair before the lexicographic work slice; pending work/cursor bind the pair/manifest/aliases and slice option. This is enrichment scheduling, not selection of first20. Changed bindings cannot resume prior compatible membership. Existing shared provider budgets and original stock/retained-forecast priority remain unchanged.

## Approach

Use a bounded owner-only no-symlink local parser with exact headers/footer/hash/size/time/freshness validation. Add the independent cohort and hash-bound checkpoint in existing state/coverage/receipt artifacts; reuse one existing enrichment path after stock work. Keep directory-only unknown/nonfund observations outside company/speculative candidate selection; pass verified ETFs through the unchanged registry/eligibility/allocator. Validate again at the final cutoff and reject a changed source without finalizing membership. Offline imports do not advance the enrichment cursor.

## Findings

The first new importer/integration run passed38 tests in1.28s. Combined new/provider/universe regression run passed307 in4.00s before adding interruption/source-mutation/speculative-leak witnesses. Final importer-only command passed49 tests in1.39s; final importer/provider/universe/exports command passed352 in12.15s after checkpoint-hardening cases. A prior combined344passed12.38s is preliminary. No implementation test failure occurred. Source authenticity and aliases remain explicit reviewed declarations, not authentication; source timestamps stay original and membership first-seen is the collection observation. Actual data/financial admission and100-name readiness are not established.

Lead reported an initial brief-quality failure caused by an unrecognized purpose heading, then repaired Objective And Boundary and confirmed the brief checker passed; manifest scope validation passed throughout. Earlier premature passed wording was corrected by Lead. This history is retained without changing acceptance or claiming an Engineer test failure.

## Engineer Evidence — Pending Independent Lead Acceptance

Implemented exactly the six source/test/doc paths plus updates to these two existing Lead-created records. Existing provider, universe allocator, ETF registry, connectors, ingestion, completed111 and public artifacts are unchanged. New parser/source assertions remain candidate evidence only. Original stock work retains priority and the same optional-feature-off compatibility/call sequence; directory-only unverified/provider-stock cases cannot leak into speculative selection. Same-binding interrupted enrichment resumes pending work; changed pair/options and source mutation cannot finalize stale membership. Stale or future pairs fail even offline.

Checks: configured Python3.11 command for tests/test_stock_research_etf_directory.py passed49 in1.39s; combined with test_stock_research_provider.py, test_stock_research_universe.py and test_stock_research_exports.py passed352 in12.15s. Full eight-path manifest validation, current brief quality and whitespace checks passed. Earlier38/1.28s and307/4.00s, then344/12.38s were intermediate passing runs. Required commit/push hooks and Lead completion review are not run by Engineer because no commit/push release was supplied. All acceptance checkboxes remain pending under the manifest's independent-review dependencies. No provider calls, credentials, actual source import/admission, training, commit, push or deployment occurred.

Unrelated baseline .DS_Store and the already dirty trader-daily-report schedule/daily-brief skill/compact-report reference are preserved outside this ticket; ownership is not inferred. Cold history may require multiple explicitly invoked bounded runs within a fresh pair's24hour window. Changing the pair/options intentionally starts another compatible state and never proves historic ETF membership. Exact code hashes/full diff/check evidence are retained in the private Engineer handoff for Lead.

## Lead Acceptance

Lead independent eight-path hash/full diff review accepted;352 focused importer/provider/universe/exports tests passed12.28s. Private fixtures only;no actualsource/provideradmission. CompleteGitpathinventory excludes4unrelateddirtyfiles. Requiredhooks run at delivery.
