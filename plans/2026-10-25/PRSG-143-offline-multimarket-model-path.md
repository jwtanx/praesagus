# PRSG-143 — Offline Multi-Market Model Path

Type: feature · Modules: financial-data, market-research · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–1.5 estimated person-days) · Impact: high — removes code rejection of the 20 Malaysian report identities; actual numerical coverage still requires admitted data.

## Why the ticket is created?

On 25 October the human requested direct AI model work for both the fixed 50 US/Malaysia report names and the standalone 100 US instruments, targeting 28 October. The trained-model input path currently supports US symbols and USD contracts only. This accepted child supplies the missing offline Malaysian path. Lead reserved PRSG-143 and acknowledged its disjoint scope. PRSG-109, PRSG-113 and PRSG-124 retain their source and quality gates. This ticket does not promise perfect accuracy or establish actual trained coverage.

## Approach

Accept explicit Malaysian numeric instrument codes, bind window validation to USD/XNYS or MYR/XKLS, and save native-currency model contracts. Preserve existing US policy semantics and trusted artifact compatibility. Malaysian next-week windows use the following Kuala Lumpur calendar week and actual venue sessions. Train accepts an explicit calendar; prediction accepts explicit canonical CSV, receipt and instrument inputs in offline mode. Preserve observed labels, actual availability, chronological purging, missingness and immutable artifacts.

## Choices

Use separate venue-bound models and explicit offline inputs. Keep the US collector and its defaults unchanged. Retain the existing nine estimators, quantiles, feature order and validation thresholds. Reject currency or venue mismatches rather than applying a US model to Malaysian data. Require all three explicit input arguments for the new prediction path, and prohibit collection or fitting during offline inference. BMS provider identities require explicit reviewed mapping to MY canonical identities.

## Findings

The original reader required US symbols; window checks and trusted artifact compatibility assumed USD; training provenance recorded USD; and the weekly policy named New York. The implementation now supports the Malaysian path. The focused four-suite command passed 131 tests in 8.16 seconds, including nine new fictional cases covering identities, currency, weekly sessions, availability, training, trusted reload and actual offline CLI inference. The original 19 October US model reloaded successfully in 1.060878 seconds with all five artifact hashes unchanged and no fit or prediction.

The actual private store retains normalized closes only, with adjustment mode 0 and roughly 102–108 distinct dates per code. Those observations cannot substitute for canonical full OHLCV histories on the required comparable adjustment basis. Actual Malaysian training data and strong-model validation remain outstanding.

## Tradeoffs

This extension removes a code barrier to Malaysian model work while preserving separate venue semantics and US compatibility. It does not supply source rights, adjustment evidence, historical availability or missing training data. Fictional fits establish software behavior; they do not establish predictive quality or full ticker coverage. Per-venue artifacts require separate data preparation and measured evaluation. Existing research-only forecasts and the strong-model requirement remain distinct.

## Frozen scope

Base: cd5529107b43634ea011facbc2edbd172c4327b0. AI Engineer exclusively owns these seven paths:

- plans/2026-10-25/PRSG-143-offline-multimarket-model-path.md
- plans/2026-10-25/PRSG-143.harness.json
- scripts/stock-research/data.py
- scripts/stock-research/train.py
- scripts/stock-research/model.py
- scripts/stock-research/predict.py
- tests/test_stock_research_multimarket.py

Preserve PRSG-141 pipeline work, PRSG-142 UI work, reports, storage, configuration, collection, inference and unrelated baseline changes. No new dependencies, provider calls, actual-data fitting, source admissions, promotion or holdout relaxation are authorized by this child. Source and model originals remain read-only. New actual model artifacts require reviewed venue-bound full OHLCV receipts and a separately bounded run. Private generated evidence stays outside Git.

## When it's considered done

- [x] PRSG-143-D1: Explicit offline MYR/XKLS reader, features, labels, training, model and prediction path works; US legacy behavior is preserved; cross-market inputs reject.
- [x] PRSG-143-D2: Focused venue, weekly, currency, chronology and legacy checks, path validation and independent review are delivered.

## Validation and evidence

Run the exact focused command from the manifest and validate all seven owned changed paths. The scope validator passed, and the runtime diff passed whitespace checks. Lead independent review remains pending. No actual Malaysian fit, new forecast issuance, model promotion or accuracy claim follows from these results.

The shared PRSG-142 mandatory full hook failed one PRSG-143 brief-quality check: the authored title and required decision-context sections were missing. The other 3,686 tests passed with 41 warnings in 79.38 seconds. This document corrects that failure without changing the numerical implementation or weakening a test. Preserve the failed attempt; focused brief-quality and manifest checks are rerun before Lead retries the hook.

Supporting Engineer input-contract work was requested for after the PRSG-141 safe checkpoint. Full quality, resource, coverage and human promotion gates remain unpassed until independently demonstrated.

## Offline usage

Training accepts `--calendar XKLS`, `--csv-glob`, `--receipt` and `--model-dir`, together with the existing explicit policy, gap, cutoff and fold arguments. Actual fitting still needs admitted data. Prediction accepts `--offline --calendar XKLS --csv-glob /absolute/private/history.csv --receipt /absolute/private/receipt.json --instruments /absolute/private/instruments.json --model-dir /absolute/private/my-models --model-folder /absolute/private/my-models/GENERATION --output-dir /absolute/private/my-predictions`.

With no new arguments the existing US defaults remain. The Malaysian path requires all three explicit offline input files and a compatible MYR/XKLS artifact. The 100 US instruments and 20 Malaysian report names use separately compatible artifacts.

## Independent Lead Acceptance

25Oct Lead independently read fourruntime diffs,9newtests,calendar/inferencecallers;all7changedpathsvalidate. Fullworkingtree3687passed41warnings80.72s includes143runtime/9newcasesafter143briefrepair(firsthook1briefqualityfailed3686passed79.38s preserved). Lead actualoriginalUSD/XNYSartifacttrustedreload1.365726s/5filepinsunchanged,nofit/predict. Owner exactfocused131passed8.16s. MYR/XKLSofflineimplementationaccepted,USlegacycontractretained;actualMYtrainedcoverage/strongquality/publicrightsnotestablished. Readonly53capturefieldauditshowsrawOHLCVexistsbutall100unadjustedbars,not3year/forwardadjusted/PITinputs. SourceauditSHA2be68ca22a483be956ec61421c8c87104f1e791847a7bf8c402b21767fa7afe1. Supportingcanonicaldataset/sourcecapabilityworkremainsseparate.

This accepts venue-bound implementation only. Actual financialdataadmission,fullcoverage,training/validationqualityandhumanpromotionremainopen. Requiredcommit/pushhooksanddeliveryreceiptsareseparate.
