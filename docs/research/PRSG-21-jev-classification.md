# PRSG-21 — Generation-free classification for market research

Research date: 1 October 2026, Asia/Kuala_Lumpur. Owner: Researcher; market-model planning contributor: Consultant. Action class: **research only**. Lead owns selection, budget and promotion decisions.

## Decision and current baseline

Can local classifiers replace repeated generative judgments in Praesagus without degrading evidence quality, while reducing total cost and latency? Compare direct Jev alternatives, then choose an input-specific evaluation rather than assuming one model can predict every market outcome.

Repository baseline inspected: `bb0d302bd4384482e628e5e1e58630e0d68396f4`. `backend/main.py` research route returns a queued placeholder; it does not invoke a model. Moomoo routes provide read-only request/response news and quote snapshots. `harness/research_harness.yaml` is a design contract. Consequently there is no measured production LLM baseline or token-saving result to report. This document proposes an experiment, not an implemented classifier or forecasting service.

## Jev identity and cost

The user supplied [jevai.net](https://jevai.net/). That page advertises $0.084 per million input tokens and links its API call to `defapi.org`; its affiliation was not established. Use [TypeSafe's official site](https://typesafe.ai/) and [documentation](https://docs.typesafe.ai/introduction) as the vendor reference. Official Jev returns closed-set Choice, rubric Score and yes/no Noul outputs. This avoids generating prose but does not establish that a selected value is correct.

[Official model documentation](https://docs.typesafe.ai/models) lists `jev-1.13.0`, $0.042/M input tokens, free outputs, text-only input and changing service limits. Pin a version for any approved comparison. These are current vendor terms, not a negotiated quote. At that input rate, one million hypothetical requests of 1,000 total billed input tokens each cost $42 before other charges; actual request size and usage must be measured. Local inference has hardware, operations and labeling costs despite having no API output-token bill.

[Vendor limitations, reviewed 17 September 2026](https://docs.typesafe.ai/model-jaggedness/jev-1.13) explicitly include unreliable arithmetic/date comparison, distractors and adversarial content. Keep numeric calculations and time ordering in code. [Vendor confidence documentation](https://docs.typesafe.ai/confidence) describes confidence as a statistic of the answer distribution; it is not automatically the probability of a future stock return. We did not verify promotional speed or accuracy claims on Praesagus data.

## Top three direct open-source alternatives

GitHub public API observations on 1 October 2026, approximately 12:07–12:10 UTC / 20:07–20:10 MYT. Counts are snapshots, not evidence of quality; these projects were created only about two weeks earlier. Maintainer-reported features below were reviewed from primary repositories/model cards; no models were downloaded or benchmarks run.

| Option | GitHub stars; creation / last push | License boundary | Strength and fit | Tradeoff / reason it may lose |
|---|---|---|---|---|
| **[Laya](https://github.com/NandhaKishorM/laya)** | **29,553**; Sep 18 / Sep 29 | Apache-2.0 code; [English checkpoint](https://huggingface.co/convaiinnovations/laya) also Apache-2.0 | Small encoder-based typed decisions with a Jev-shaped server. First direct candidate for limited compute and frequent semantic decisions. | Very young project. Language/domain changes require separate validation; its own documentation shows confidently wrong multilingual behavior. No demonstrated financial forecasting accuracy. |
| **[Kev](https://github.com/jaredpalmer/kev)** | **8,129**; Sep 17 / Oct 1 | Apache-2.0 code; [Kev-4B](https://huggingface.co/jaredpalmer/kev-4b) and [0.8B](https://huggingface.co/jaredpalmer/kev-0.8b) cards Apache-2.0; retain base-model notices | Qwen-based trainable decision family, TypeSafe-compatible endpoint, documented held-out temperature calibration. Challenger when customization matters. | Larger memory/compute footprint. Maintainer evaluations have different in/out-of-domain results and proxy-label limitations; no guarantee of finance transfer. |
| **[SemIf](https://github.com/TheoLeeCJ/SemIf-OpenJev)** | **4,638**; Sep 16 / Sep 23 | MIT code; selected upstream checkpoint license is separate | Frozen-model option-logit readout, shared-state processing and local runtime choices. Useful to isolate benefits of avoiding decoding before specialized training. | Reproduces an interface pattern, not undisclosed Jev training. General-model logits need calibration; reuse/precision choices can alter decisions. |

Star/activity sources: [Laya API](https://api.github.com/repos/NandhaKishorM/laya), [Kev API](https://api.github.com/repos/jaredpalmer/kev), [SemIf API](https://api.github.com/repos/TheoLeeCJ/SemIf-OpenJev). Push dates indicate repository activity, not release stability or security review. Code licensing does not grant market-data rights.

**Conditional recommendation:** evaluate Laya first as the direct replacement, with Kev as the larger trainable challenger and SemIf as the readout-only control. Change this ordering if available hardware, finance calibration, language coverage or maintainability favors another candidate. None is approved for production by this research.

## Mature task-specific alternatives and controls

These are substitutes for particular classification calls, not universal Jev replicas. GitHub API snapshots at 12:07 UTC on 1 October:

| Method | Stars / licensing | Why include it | Limitation |
|---|---|---|---|
| **[scikit-learn](https://github.com/scikit-learn/scikit-learn): TF-IDF + logistic regression** | 67,438; BSD-3-Clause | Reproducible CPU baseline for fixed event/relevance labels; no foundation weights needed. [Official text example](https://scikit-learn.org/stable/auto_examples/text/plot_document_classification_20newsgroups.html). | Requires labels; weaker contextual understanding and vocabulary drift. |
| **[SetFit](https://github.com/huggingface/setfit)** | 2,825; Apache-2.0 framework | Few-shot semantic classifier for a stable taxonomy with reviewed examples. [Official docs](https://huggingface.co/docs/setfit/main/en/index). | Labels remain necessary; select checkpoint license/language separately. Published small-sample examples do not establish sufficient finance sample size. |
| **[GLiClass](https://github.com/Knowledgator/GLiClass)** | 544; Apache-2.0 code and [small checkpoint](https://huggingface.co/knowledgator/gliclass-small-v1.0) | Zero-shot, multilabel challenger for evolving taxonomies. | Smaller community; small checkpoint is English and synthetically trained. Raw scores require task-specific calibration. |

A potential multilingual SetFit body is [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), Apache-2.0, with Malay/Chinese coverage; it still needs task training and slice evaluation. [fastText](https://github.com/facebookresearch/fastText) has 26,523 stars and MIT code but is archived; its [pretrained vectors](https://fasttext.cc/docs/en/crawl-vectors.html) have a separate CC BY-SA 3.0 license. [FinBERT](https://github.com/ProsusAI/finBERT), 2,244 stars, is an English financial sentiment control, not a price predictor. Its code is Apache-2.0, but the [checkpoint card](https://huggingface.co/ProsusAI/finbert) did not specify weight licensing in this review; resolve that before deployment.

## Input-to-model plan

Consultant's completed brief was read at 20:11 MYT on 1 October ([session](codex://threads/01a0f21f-8fee-7ed2-aa49-04a7c7a8645b)). Consultant independently favors relevance/event routing first, deterministic calendar/numeric processing, and separate future-return evaluation. Its input mapping and catalyst-miss/calibration/fallback requirements are incorporated below. Researcher adds the direct OSS shortlist and checkpoint-license caveat: Consultant's proposed FinBERT control remains conditional on resolving weight rights. Consultant did not run experiments or change files; an extended vendor-audit subagent was stopped at its research limit.

Proposed architecture: **source capture → deterministic validation/deduplication → specialist classifiers/features → abstention/review → sourced synthesis**. Reserve generative work for explanation and ambiguous analysis. The classifier never supplies its own factual evidence.

| Input | Output to model separately | Candidate approach | Required evidence / boundary |
|---|---|---|---|
| News, filings, transcripts | Ticker relevance, event category, sector, fact/opinion, textual sentiment; multilabel where necessary | Rules + TF-IDF baseline; SetFit fixed taxonomy; Laya/Kev flexible semantic questions; GLiClass zero-shot control | Primary text, entity IDs, publication and original availability, event clusters, reviewed labels. Sentiment is not return direction. |
| OHLCV and market context | Observed trend/regime; separately future up/flat/down at a frozen horizon | Deterministic returns/volatility/trend first; logistic classifier, then LightGBM challenger | Licensed adjusted history, corporate actions, session calendars, delisted symbols, spread/liquidity, timestamped features. Latest quote snapshots alone are insufficient. |
| Fundamentals / earnings | Quality flags, surprise categories, financial-condition features | Deterministic ratios/XBRL checks + text classifier; numeric model only after point-in-time joins | Filing acceptance/availability, original/restated versions, fiscal periods and contemporaneous consensus rights. Revised values cannot justify earlier signals. |
| Macro / cross-asset | Release surprise, regime features and exposure | Deterministic surprises against contemporaneous forecasts; simple supervised numeric baseline | Original release vintages, available consensus, units, calendars, FX and rates. Small event sample and changing regimes limit inference. |
| Financial calendar | Scheduled/confirmed/revised/cancelled status and event category | Date parsing and comparison in code; classifier only for ambiguous notes | Exchange/central-bank/company primary schedule, source revision and timezone. Missing item is not cancellation. |
| Social sentiment / flows | Sentiment, entity relevance, anomaly flags | Dedup/bot filtering, language-specific text model; numeric anomaly baseline | Timestamp, provider rights, liquidity and event overlap. Correlated posts and flows do not prove informed direction. |
| Charts/images | Validated extracted fields or visual descriptions | Structured OHLCV preferred; OCR/vision only if source data unavailable | Jev text endpoint cannot read pixels directly. Record extraction error; do not infer precise chart values from screenshots. |

[LightGBM objectives](https://lightgbm.readthedocs.io/en/latest/Parameters.html) support multiclass and quantile regression, but do not establish market predictability. A price interval needs a separately evaluated return/quantile model; multiplying a sentiment score by current price is unsupported.

## Evaluation proposal and promotion gate

1. **Start with one wedge:** ticker relevance + catalyst category on archived US/MY news. Freeze a human-reviewed corpus and source snapshots; include ordinary, rare, duplicate, conflicting, missing, future-dated, multilingual and adversarial cases. Record taxonomy version and label disagreement. Proposed initial pilot: 500–1,000 event-clustered examples, then increase sample size where intervals remain too wide; this is a planning estimate, not proof of adequacy.
2. Use chronological train, calibration and untouched test windows. Group syndicated copies and related events; reserve issuer/source holdouts. Fit preprocessing only on training data. For outcomes, purge overlapping forecast intervals and use exchange-session horizons, not a random split. [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) supports chronological splits/gaps but does not automatically solve irregular event spacing or overlapping labels.
3. Report macro-F1, per-class precision/recall, material-event miss rate, reliability diagrams, Brier/log loss and coverage versus error under abstention, with uncertainty intervals and US/MY/language/source slices. [Calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) requires calibration data distinct from classifier training; a lower Brier score alone does not prove better calibration.
4. Measure identical input/hardware: p50/p95 end-to-end latency, cold starts, throughput, input/output usage, memory/energy, retries, review/fallback rate and **total cost per accepted classification**. Include training/annotation and idle hosting. Compare against majority/rules/TF-IDF and a pinned generative control; paid Jev only with approved access/budget. No measured savings exist yet.
5. Proposed gate for Lead to approve before evaluation: no reduction in material-event recall outside agreed uncertainty; lower total cost and p95 latency at matched coverage/error; reliable abstention on missing evidence; all temporal/provenance gates pass. Do not tune gates after reading the test results. Inconclusive results mean collect more data or retain the baseline.
6. **Separate price experiment:** define `r_h = P(t+h)/P(t)-1` and frozen tolerance `tau_h`: up if `r_h > tau_h`, down if below `-tau_h`, otherwise flat. Missing targets are unknown, not flat. Choose next-session and five-session/week-end calendars separately before training. Compare majority/persistence/logistic with boosting; only add text features if they improve untouched temporal results. Evaluate return errors, interval coverage/width and probabilistic directional skill separately; trading economics require costs and independent review.

Every output should retain source references, decision as-of, input hash, label/horizon definition, model/checkpoint and taxonomy version, raw score, calibration version, calibrated task probability (or null), abstention reason and review status. Retain the full distribution; model confidence, observed regime and future-return probability need different fields. Sparse data remains unknown/unrated; no automatic trades.

## Data/API setup and Lead decisions

**No paid API is needed for the initial local text-classification pilot.** Need approved hardware, usable source archives and reviewed labels. Point-in-time OHLCV, corporate actions, calendar history and data redistribution rights are prerequisites for a later price study. Moomoo OpenD entitlements may supply snapshots but are not by themselves a historical training dataset. Jev benchmarking would need an official TypeSafe account/key, current terms and an explicit cost ceiling; no credentials requested or created here.

Lead decisions: (1) approve the narrow text pilot and frozen success gate; (2) choose deployment hardware/budget and English-first versus US/MY multilingual slices; (3) designate source-of-truth datasets and rights; (4) approve any separate price-label horizon and neutral-band definition; (5) decide whether a paid Jev comparison is worth including. Researcher's conditional preference is baseline + SetFit + Laya first; keep Kev/SemIf as challengers if resources support them.

## Evidence limitations

Sources are mutable primary maintainer/vendor pages retrieved on 1 October 2026 via web search/open and public GitHub API. Exact publication times are unknown except explicit dates above; individual web request timestamps were not instrumented. API observation times were recorded by research agents. Repository/code/card inspection is not security, licensing counsel, operational maturity or model-quality validation. No market data was purchased, models trained, benchmarks executed or production files changed. Lead review remains pending.
