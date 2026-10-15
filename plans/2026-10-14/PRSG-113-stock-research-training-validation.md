# PRSG-113 — stock research training validation

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: M (2–4 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer to own baseline/nine quantile fits, calibrated artifacts and strong actual-data gates after registration.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `4974b79235b95c8599b643c04add5ea1798602e5`. Allowed paths:

- `scripts/stock-research/model.py`
- `scripts/stock-research/train.py`
- `tests/test_stock_research_model.py`
- `scripts/stock-research/storage.py`
- `tests/test_stock_research_universe.py`
- `plans/2026-10-14/PRSG-113-stock-research-training-validation.md`
- `plans/2026-10-14/PRSG-113.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-113-D1: Baseline/quantile train/save/reload, no random temporal validation and reproducibility tested.
- [ ] PRSG-113-D2: Actual-data walk-forward/untouched holdout passes frozen strong-model gates and measured hardware budgets.

## Evidence

D1 research implementation accepted after independent review; D2 remains blocked on actual-data quality, provenance and full-size resource evidence. This ticket is not complete.

## Frozen model acceptance contract

The baseline covers min-low, max-high AND terminal logreturn, all q05/q50/q95, conditioned on the identical horizon lead/count and instrument/leverage class. Fit/calibrate baseline and challenger using earlier data only; save both at origin. Report price-normalized endpoint MAE, terminal-return MAE, pinball per target/quantile and equal date/target weights. Near-zero baseline errors (<=1e-8 normalized units) cannot establish relative improvement and leave that gate unassessable.

Require >=5% held-out improvement separately in low and high median MAE, aggregated pinball and terminal MAE/pinball for directional promotion. Paired95% date-block CI of baseline-minus-challenger must be >0, using common date blocks across all instruments/windows; block length at least maximum origin-to-label-end session distance, minimum10sessions; deterministic seed and1000bootstrapreplicates. No holdout tuning. Endpoint90% coverage must be85–95% for EACH adequately sampled promoted class/horizon and width no worse than matched-coverage baseline. Joint envelope coverage reported separately. q05<=q50<=q95 and medianlow<=medianhigh; crossing rejects forecast/promotions rather than silent repair. >=252 unique OOS dates overall and >=100dates/10nonoverlappingblocks per provisional subgroup/horizon; smallgroups unvalidated.

Actual-data gate additionally requires evidence of contemporary universe membership/delistings and origin vintages. Current100 retrospective backfills/synthetic fixtures cannot satisfy strong dynamic-universe model acceptance. Human review required before promoting candidate artifacts. Failed/unknown gates leave researcher model/baseline only and preserve strong-model criterion incomplete. Freeze all policies before test results; no model can manufacture assured profitability.


## Lead release details — 2026-10-15 MYT

PRSG-112's accepted reader/features/calendar contract is the input boundary. Keep strict actual availability and explicit reviewed retrospective feature assumptions; empty historical folds after fresh backfill are an insufficient-evidence result. A present-cutoff researcher fit may use valid available inputs, with all provenance gaps preserved, but it cannot satisfy D2. Implement D1 and the executable evaluation/rejection machinery now; keep D2 pending or blocked until actual chronological evidence and measured budgets pass. After independent acceptance of D1, already-approved research-only inference/export integration may proceed while D2 remains open. This does not promote a model or weaken any strong-model threshold.

Freeze a small CPU configuration, random/bootstrap seeds, input hashes, date folds, baseline version, calibration policy, fixed feature variant and quantitative gates in a receipt before evaluating outcomes. No expensive hyperparameter search, automatic retraining, holdout reuse or guessed historical instrument mandates. Keep baseline predictions matched to the same origin/window/class/leverage and uncertainty levels. A no-benchmark or missing-class researcher variant must be explicit; unknown is not neutral zero or an inferred current mandate.

Training defaults to the configured local collection/history parent, with explicit CSV directory/glob or read-only SQLite overrides and attributable receipt sidecars; invalid/missing identity or canonical fields fail with setup guidance rather than fabricated provenance. Save all model and evaluation artifacts inside a new exclusive timestamp generation outside Git. Binary model writes require exclusive private files, manifest SHA256/byte entries and a trusted local load boundary; check schema/dependencies/data/calendar/adjustment/feature compatibility before deserialization. Inference must not silently fit.

Owner AI Engineer writes model.py, train.py and model tests; Lead owns the ticket metadata. Supporting Engineer has a disjoint two-file assignment to extend existing Generation.write for .joblib bytes and test exclusive/hash/name guards in storage.py and test_stock_research_universe.py. Existing CSV/JSON behavior remains unchanged; no new provider calls, credentials, deployment, training data sources or auto-promotion are authorized. Model profiling may use standard-library process resource measures with correct platform units; save hardware, input size, threads and wall/peak evidence, and do not claim the 110-name targets from tiny fixtures.


## D1 implementation checkpoint — 2026-10-15 MYT

Lead independently reviewed all seven owned paths and ran the exact three-suite check: **106passed in6.60s**. Eight additional frozen logical gate cases passed, including threshold/CI/missing-baseline/subgroup/coverage/nonfinite rejection and human-review-only qualification. Storage support separately passed44tests in2.70s. The fixed sequential model configuration is seed109/bootstrap113,40iterations,7leaves,depth3,minleaf20,learningrate0.05,L2=1,one thread. Missing columns are explicitly excluded by a training-only saved feature mask; missing values are not neutral zero.

Walk-forward and untouched holdout reports/gates remain separate; pooled metrics are diagnostic. The252-date requirement applies to distinct OOS dates overall, while subgroup100dates/10blocks remain unchanged. Subgroups share calendar block anchors and the same1000bootstrap draws; missing draws are unassessable. Exact observed coverage equality (tolerance1e-12) is the conservative initial operationalization before width comparison; unmatched coverage blocks that claim and intervals are never changed using holdout outcomes.

Artifacts retain actual fit/calibration bounds, data hashes, variants, calendar/version/schedule, adjustment/currency, targets and window policy. Loading uses the same hash-verified buffers for JSON and joblib and rejects incompatible runtime policies. Explicit public fit/calibration cutoffs and no silent refit are tested. Manual CLI help, missing-input and fictional canonical CSV-to-freeze/empty-fold behavior are verified. Tests use fictional data; intermediate failures remain in private handoff history.

**D2 remains unmet.** No actual-data-trained strong model, full-universe forecast, measured full-size hardware acceptance or promotion is delivered by this checkpoint. The current250000 prepared-record budget can reject100–110names across3–5years/four horizons (for example100×706×4≈282400). A bounded layout/resource decision and measured profile are required before that full-size fit; no silent truncation, shortened history or relaxed validation is accepted. Current-universe backfills cannot establish historical membership/delistings/origin vintages. Model artifacts remain research only; already-approved research inference/export code may proceed without treating D2 as done.

The first mandatory full commit check failed2 budget-test cases (2540passed,43.46s): the new model test loader reloaded the dataset module after existing aliases were bound. The new loader now reuses an already loaded module from the same source path; both existing budget assertions remain intact. Lead replayed the dataset-first ordering:106passed in6.70s. The failed attempt remains part of delivery evidence; full hooks are rerun before publication.
