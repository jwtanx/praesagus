# PRSG-116 — Optional Stock Research Sentiment

Type: feature · Owner: AI Engineer · Priority: P1 · Effort: S (0.5–2 person-days estimate) · Impact: high — one bounded component of the accepted standalone program.

Created 2026-10-14 MYT.

## Objective

AI Engineer model logic and Engineer RSS plumbing: permitted local-first cutoff-safe sentiment, optional remote/fallback.

Use [PRSG-109](PRSG-109-stock-research-program.md) as the complete human-approved contract. Old reporting/tickets are set aside. No paid access, orders, public raw data, secrets or model promotion are authorized. Live read-only market intake requires the bounded reviewed collector; no credential access in role/routing/model tests.

## Frozen scope

Base: `c64f975ffc9654f91d63c3c54f03af718cf0342c`. Allowed paths:

- `scripts/stock-research/news.py`
- `scripts/stock-research/sentiment.py`
- `tests/test_stock_research_sentiment.py`
- `plans/2026-10-14/PRSG-116-stock-research-sentiment.md`
- `plans/2026-10-14/PRSG-116.harness.json`

Lead owns these ticket metadata files. Implementation owner changes for model work to AI Engineer only after verified role registration and validator vocabulary; retain historical ownership. Re-freeze current base before each dependency-ordered implementation.

## When it's considered done

- [x] PRSG-116-D1: RSS conditional caching/dedup/backoff/budgets and text/source/cutoff handling tested.
- [ ] PRSG-116-D2: Numeric local sentiment calibration/training and forecast benefit assessed; absent/unvalidated addon falls back to price-only.

## Evidence

Pending implementation and independent review; tests alone do not establish real data access or forecasting quality.

## Why the ticket is created?

Explore whether attributable numerical news sentiment can improve research while keeping the tool independent of LLM access.

## Approach

Plan cutoff-safe news caching, entity-specific tone, explicit missingness and local-first sentiment evaluation before numerical-model integration.

## Choices

Compare lexicon diagnostics and small TF-IDF/linear candidates first; keep price-only fallback until separate calibration and forecast-benefit evidence exists.

## Findings

News and cached-input mechanics are entering implementation. Academic dictionary parsing tests demonstrate mechanics and a known negation weakness; they do not establish a calibrated classifier or forecast benefit.

## Tradeoffs

News rights, polling permission, historical availability and multi-entity/ETF relevance can limit usable coverage; none may be replaced with neutral zeros.

## Accepted News Mechanics Slice

Refrozen at 0e0c56c068fac1d4bb84bf2a7de23aa25509e2bb. Engineer exclusively owns news.py and tests/test_stock_research_news.py in this slice; AI Engineer sentiment.py/test remains held until the shared news contract is stable. Lead owns both records. No run/export/model/provider/dependency changes or actual feed requests are released.

Implement supplied/cached NewsRecord schema1 validation, as-of revision selection, explicit exact typed security/entity/aspect relevance, cutoff-safe dedup/representative and original freshness receipts. Public boundaries: validate_source_policy(policy, at_ms), normalize_supplied_news(entries, source_receipt, policy), select_news_as_of(records, cutoff_ms, policy), collect_configured_news(policies, transport=..., clock_ms=..., cache=...), append_cache_generation(records, receipts, output_parent=..., generated_at=...). Freeze your exact field contract in module documentation before returning it for AI consumption. Publication alone never establishes availability. Direct fund, manager, underlying and macro relevance remain separate; do not invert or scale text tone.

Every current candidate source is disabled until an attributable source policy establishes rights and exact polling permission. Default300seconds and optional60seconds are permitted only by such a policy; no scheduler is created. Off/offline/unknown policies make zero transport calls. Any prospective collection uses explicit injected transport only, allowlisted HTTPS endpoints and headers, no auth/account/portfolio inputs, article/enclosure fetches or arbitrary redirects. Conditional200/304 observations never refresh original text/event age.429/503Retry-After/backoff and shared local request attempts remain visible; no same-run retry or distributed guarantee.

Freeze mechanical caps:3sources,1request/source/run,3total,0retries,10-second transport timeout contract,2MiB response/source,1000articles,32KiB permitted text/article,4MiB aggregate text,8MiB normalized cache artifact. Stricter source policy wins; reject over-budget data without truncation. Reject DTD/entities, malformed structure, unsafe paths and inconsistent IDs/hashes/timestamps; retain explicit missing/stale/rejected coverage. Append-only private0700/0600 timestamped cache generations remain outside Git; verify all declared hashes and preserve prior bytes. No live-client deadline or cross-host coordination is established by mocked transport tests.

Focused fictional checks cover zero-call disabled/offline paths, exact ID and policy/cutoff validation, revisions/dedup/freshness, conditional caching, first-failure/backoff/budgets, XML and aggregate input bounds, private immutable cache safety and input/error redaction. No source activation, dictionary redistribution, model training, calibrated numeric sentiment or price-model change is authorized here. Current human academic purpose permits separate local research evaluation of appropriately sourced inputs; it does not waive privacy, rights receipts or empirical model gates.


## News Mechanics Acceptance — 16 October

Lead accepts PRSG-116-D1 on the exact frozen two-file owner handoff: news module SHA256 `856a8550cb5d49053354eb8c18b1f39ea48592c61ac9080f21357795fb504ecc` and test SHA256 `4d95f8c2e61712b38e6cfe0df91b7305e6aac769c86bdce9fe322a71b7c0c259`. Lead reviewed the complete module and independently passed136focused tests in0.79s. AI Engineer independently passed136checks in0.81s and reviewed the annotation/cache/as-of case. Engineer reports490compatible stock-research checks in18.48s; that broader result is owner evidence. Existing-schema whole-evidence-envelope revision semantics are frozen: actual annotation changes advance revision/ingestion and version identity while preserving unchanged content and original publication/first-seen/age. Prior cached bytes remain immutable.

This accepts local mechanics only: source policies remain disabled, injected transport is not a verified live client, canonical event/entity facts and rights remain external, conservative plain RSS/Atom and bounded whole-parent cache limitations remain explicit. No calibrated score, trained sentiment artifact, actual-source coverage or forecast benefit is established. PRSG-116-D2 remains pending. Accepted news code and this metadata are not yet committed or pushed. Current app permissions prevent cross-chat release and Git delivery; no success is claimed for blocked actions. Next step is exact AI sentiment mechanics scope/release and reviewed ticket integration once supported permissions permit it.


## Prepared AI Sentiment Mechanics Slice — Delivery Pending

Lead prepares this next accepted slice against the frozen news API above. AI Engineer exclusively owns `scripts/stock-research/sentiment.py` and `tests/test_stock_research_sentiment.py`; all news, numerical model/features/training/inference/actions, provider, CLI/export, dependencies and third-party assets remain protected. This scope is ready for delivery, but the message has not been delivered under the current tool restriction; do not describe AI implementation as running.

Implement pure offline functions from the reviewed proposal: validate bounded combined NewsRecord selection against its cutoff/policies instead of trusting its status; lexicon diagnostics from a caller-supplied permitted in-memory dictionary and source/version/hash/rights/known-at receipt; cached scoring with explicit unavailable/no-artifact disposition; validated per-event probability aggregation against an explicitly supplied reviewed contract; and price-only model disposition. Reuse the frozen global selection/dedup and exact typed instrument/entity/aspect/scope keys. No filesystem assets, network, provider/LLM probes, fitting, pickle loading, model downloads or numerical-model integration are released.

Lexicon counts and raw diagnostic balance never populate calibrated probability/score fields. No-match, missing relevance, incompatible language/scope, future artifact or source/annotation receipt, stale input and unknown rights return explicit unavailable reasons. Require entity-conditioning semantics before attributing whole-article tone to an entity. Keep fund/manager/underlying/macro scopes separate with no inverse/leverage transformation. A generic numerical scalar or probability triple is not trusted evidence. No calibrated artifact currently exists: tests may exercise fictional contract/probability mechanics but cannot establish calibration, availability of a production model or forecast benefit.

For eligible externally reviewed event probabilities, require finite positive/neutral/negative components, exact class/label/target/model/calibration/cutoff provenance and sum-to-one within frozen tolerance1e-8; reject rather than clip. Define score as positive-minus-negative. Aggregate unique compatible event probabilities with explicit nonnegative finite weights and positive total, documented original-age decay, retained coverage/disagreement and `aggregate_calibration_status=unestablished`. Missing input is never neutral zero. Keep `forecast_use_allowed=false` and select the existing compatible price-only model; sentiment-trained model selection or feature zero-filling is prohibited.

Focused fictional tests must cover malformed/future/stale/revised inputs, cross-source duplicates and exact typed target identity, multi-entity/ETF scope isolation, dictionary/no-match/rights/version provenance, no-artifact fallback, finite probability/sum/score consistency, genuine zero versus missing, weight/coverage/disagreement behavior and zero network/fit calls. Command: configured Python `-m pytest -q tests/test_stock_research_sentiment.py`, then compatible news/data/model/inference regressions as warranted. Return hashes, test evidence, exact API, unsupported cases and empirical-data blockers before acceptance. D2 remains open until separate historical-label/calibration and forecast-benefit evidence is assessed; these mechanics cannot satisfy that gate.

## 18 October integration update

Human granted permissions and requested committing pending work. D1 exact previously accepted news/test hashes were copied into primary and rechecked in the current tree; combined news/projection check had191passes and one unrelated projection-cutoff failure, now isolated under PRSG-123. D1 code is delivered separately through the full clean-checkout hooks. Previous permission blockers above describe the October16checkpoint and are superseded for Git integration. D2 mechanics remain undispatched and empirical sentiment calibration/forecast benefit remain unestablished; no sources are enabled and no model/prediction integration is claimed.
