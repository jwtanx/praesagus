# Praesagus Enhancement Wishlist

This wishlist captures enhancement ideas for the current Praesagus implementation and the initial product vision. Each item is rated by complexity and impact, with a suggested solution and potential risk.

## Rating Guide
- Complexity: Low / Medium / High
- Impact: Low / Medium / High

## Wishlist Table

| Item | Category | Complexity | Impact | Possible Solution | Possible Risk |
|---|---|---|---|---|---|
| Harden SEC QR extraction and document parsing | Data Ingestion | Medium | High | Build dedicated `qr_processor` module, validate all downloaded URLs against `sec.gov`, use SEC index JSON as fallback | SEC page layout changes, fragile HTML parsing, parsing failures |
| Add `performance_label` for filings | Signal Engineering | Low | Medium | Compute label from XBRL deltas, revenue/net income/EPS trend rules, and text sentiment heuristics | Incorrect labels from noisy or missing financial metrics |
| Local LLM summarization support | AI / Summarization | Medium | High | Add compact GGUF model adapter for MacBook Neo (e.g. Vicuna/Mistral 7B quantized) with chunked summarization | Local model performance, installation friction, tokenization bugs |
| SerpApi fallback with caching and rate limits | External Fallback | Low | Medium | Use `SERPAPI_KEY`, cache external responses in `.state/serpapi_cache.json`, cap calls per run | API usage cost, quota exhaustion, stale cached content |
| Earliest-news detector connector | Ingestion | Medium | High | Add RSS/News connector with source prioritization and event timestamping | Missing early sources, duplication, false positives |
| SEC Form 4 insider trading monitor | Ingestion | Medium | High | Build connector for `sec_form4_insider`, persist trades, compute first-second alerts | Filing latency, missing insider context, noise |
| Email/webhook alert persistence and dedupe | Notifications | Medium | High | Store alert state in DynamoDB/local JSON, dedupe repeated signals, support SMTP/Webhook adapters | duplicate/overflood alerts, state storage drift |
| Watchlist CRUD and user-configurable sources | UX / Product | Medium | High | Add backend endpoints + UI for watchlist management, persist watchlist in config/database | inconsistent watchlist sync, stale watchlist data |
| Connectors config catalog and dynamic runner | Architecture | Medium | Medium | Expand `ingest/config/platform_connectors.yaml` and support dynamic connector discovery | config drift, unsupported connector types |
| Airflow/ECS orchestration for scheduled connectors | Orchestration | High | High | Add Airflow DAG templates or ECS task runner for connectors, use scheduler to run jobs | orchestration complexity, deployment overhead |
| Raw / Bronze / Silver data lake schema validation | Data Platform | Medium | High | Implement immutable S3 raw writes + bronze normalization jobs + silver schema checks | schema drift, data quality failures |
| DynamoDB feature store and online feature materialization | Feature Store | High | High | Store time-series features in DynamoDB, materialize signals for API consumption | DynamoDB cost, hot partitions, feature sync issues |
| Backend API for trend / filing queries | API | Medium | High | Build FastAPI endpoints for filings, signals, trend charts, metadata | API versioning, query performance |
| Dashboard and research UI | UX | Medium | High | Add lightweight dashboard pages for trend signals, filings, watchlists, alerts | UI churn, frontend/backend integration gaps |
| Monitoring and observability | Ops | Medium | High | Add metrics, logging, tracing, connector health dashboards, localstack monitoring | alert fatigue, instrumentation overhead |
| CI/CD for tests, docs, and deploy | DevOps | Medium | High | Add GitHub Actions/other pipeline for lint/tests/docker builds/infra deployment | pipeline maintenance, credential management |
| Secrets and least-privilege IAM | Security | Medium | High | Move credentials to Secrets Manager/env vars, enforce role scopes | secrets exposure, access failures |
| Backtesting / signal evaluation harness | Analytics | High | Medium | Add replay engine for signal performance against historical data | data completeness, backtest validity |
| Provenance and evidence linking | Data Governance | Medium | High | Track `source_url`, `ingest_ts`, `connector`, and attach evidence to each signal | metadata bloat, compliance complexity |
| Support more alternative data connectors | Ingestion | Medium | Medium | Add connectors for Reddit, Twitter, Hacker News, YouTube, Google Trends, Stack Overflow | API changes, rate limits, data licensing |
| Local developer tooling and runbooks | Productivity | Low | Medium | Add `Makefile` targets, CLI helpers, docs for local workflows | stale docs, tool drift |
| Document runbook for SEC ingestion operations | Documentation | Low | Medium | Create operational guide for failure handling, source validation, restart procedures | missing updates, outdated runbook |
| Add data retention / archiving policies | Data Ops | Medium | Medium | Implement TTL/archival rules for stale raw and derived data | accidental data loss, compliance gaps |
| Add model registry / experiment tracking | AI Ops | High | Medium | Track models, prompts, datasets, version experiments | management overhead, integration complexity |
| Add feature/alert explainability | Product | Medium | High | Surface why a signal fired with supporting XBRL metrics and text snippets | confusing explanations, overfitting to evidence |
| Add entity resolution and knowledge graph | AI / Data | High | Medium | Build entity linking for companies, tickers, topics, relationships | complexity, scaling, correctness |
| Add nightly data refresh and reconciliation | Data Ops | Medium | High | Re-run ingestion/reconciliation for missing filings, stale signals | duplicate ingestion, reconciliation drift |
| Add local aggregator for weekly/monthly trend summaries | Analytics | Low | Medium | Summarize connector outputs into weekly trend reports | summary accuracy, stale summaries |
| Add secure SEC queue and backfill support | Ingestion | Medium | Medium | Use SQS or local queue for SEC fetch retries and backfill workflows | queue failures, ordering issues |
| Add automated entity sentiment scoring | AI | Medium | Medium | Compute sentiment from filings/news across entities | sentiment noise, model drift |
| Add optional external API provider adapters | Platform | Medium | Medium | Plug in third-party sources with configuration and adapter wrappers | API vendor lock-in, cost |

## Notes

This wishlist is intentionally broad and includes both near-term and longer-term ideas. The highest-value next steps are those that improve data reliability, visibility, and the ability to derive evidence-backed signals from SEC and alternative data.
