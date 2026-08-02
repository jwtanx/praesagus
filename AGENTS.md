# Praesagus Architecture and Agent Notes

This document describes the architecture implemented so far in Praesagus, the current product scope, major engineering tradeoffs, known catches, and a detailed future plan.

## Current Architecture Summary

Praesagus is built as a modular, event-driven market intelligence platform with the following core pieces:

- **Standalone tool scripts** for commerce-ready execution without a running backend.
  - `scripts/sec_qr_report.py` — EDGAR QR polling, filing index scraping, XBRL metric extraction, optional local summarization, and SerpApi fallback.
  - `scripts/realtime_qr_watcher.py` — continuous SEC QR watch for new filings with buy/short signal heuristics.
  - `scripts/cli_tools.py` — unified CLI navigation for standalone tools.
  - `scripts/run_sec_filings.py`, `scripts/run_insider_monitor.py`, `scripts/run_company_news.py` — specialized ingestion/monitoring helpers.

- **Connector ecosystem** with a shared SDK pattern and config-driven runner.
  - `connectors/multi_runner.py` reads `ingest/config/platform_connectors.yaml` and executes connectors dynamically.
  - Specific connectors exist for social/news sources and regulatory sources, including `connectors/sec_filings.py` and `connectors/sec_form4_insider.py`.

- **Backend API and dashboard services**.
  - `backend/main.py` exposes API endpoints for trends, dashboard summaries, platforms, pipelines, research, and settings.
  - `backend/services.py` assembles trend and status data from feature store sources.

- **Local development environment**.
  - `docker-compose.yml` and `scripts/bootstrap_localstack.py` bootstrap localstack resources.
  - A minimal Terraform scaffold exists for S3 buckets, DynamoDB feature store, Secrets Manager secret store, and SQS DLQ.

- **Watchlist-driven financial ingestion**.
  - `ingest/config/financial_watchlist.yaml` defines watchlist tickers, companies, priorities, and scraping settings.
  - The watchlist is used by SEC filing ingestion, insider monitoring, and news polling scripts.

## What Has Been Implemented So Far

### Ingestion + Regulatory Tools

- `scripts/sec_qr_report.py` now:
  - polls EDGAR company Atom feeds for SEC filings
  - downloads filing pages and extracts SEC document links
  - protects against non-SEC domains
  - extracts XBRL-based metrics from the SEC API
  - computes pct-change deltas for revenue, net income, and EPS
  - optionally summarizes filings locally using LexRank + embeddings
  - optionally falls back to SerpApi Google AI Overview

- `scripts/realtime_qr_watcher.py` now:
  - polls the SEC `getcurrent` filings feed for 10-Q / 10-K filings
  - deduplicates filings by accession
  - logs a simple buy/short/watch signal based on language heuristics

- Local summarization support is available via `--summarize`.
- SerpApi fallback support is available via `--use-serpapi` and `SERPAPI_KEY`.

### Connector Framework

- `ingest/config/platform_connectors.yaml` centralizes connector catalog metadata.
- A runner can launch connectors based on YAML config rather than hard-coded lists.
- Existing connectors support multiple sources: Reddit, Twitter, Hacker News, YouTube, Google Trends, EDGAR, news RSS, etc.

### API and Frontend Wiring

- The backend exposes higher-level endpoints for dashboard and financial intelligence.
- Frontend pages were wired to these API endpoints, enabling dashboard and trends consumption in the UI.

### Infrastructure and Local Development

- Localstack bootstraps raw/bronze/silver S3 buckets and DynamoDB feature store.
- Docker Compose coordinates frontend, backend, localstack, and ingestion services.
- Terraform scaffold provisioned the core cloud resources, including S3, DynamoDB, Secrets Manager, and SQS DLQ.

## Catch Points and Current Gaps

### Data Extraction and Summarization

- Local summarization is extractive and heuristic-based. It is not a substitute for a true generative model summary.
- `SerpApi` fallback is supported but not free; it should be used sparingly and with caching.
- Filing page parsing currently depends on HTML structure and may break if SEC page layout changes.
- The current metric extraction uses XBRL tags via the SEC API, but it may not always span prior period values or correct accounting tags for all issuers.

### Model / AI Limitations

- There is not yet a hosted local LLM integration in the repository.
- Current summaries are based on local LexRank + sentence embedding retrieval, which is a safe fallback but not always semantically deep.
- There is no integrated `performance_label` classification yet, beyond the extracted raw metrics.

### Monitoring and Alerting

- The existing scripts log terminal output, but there is not yet a centralized alerting pipeline for file-level or signal-level alerts.
- No alert persistence or deduplication exists for repeated insider/news events from the same company.

### Infrastructure and Production Readiness

- Terraform scaffold is present, but ECS task definitions and secrets wiring are still minimal.
- The localstack bootstrap is enough for dev, but not for a full staging/prod workflow.
- There is no fully implemented CI/CD pipeline in the repo for deployment automation.

### Documentation and Operational Visibility

- API endpoint documentation and openapi descriptions are still sparse.
- There is no unified runbook covering daily ingestion monitoring or failure handling.
- The watchlist currently lives in YAML; a UI or backend CRUD layer would improve usability.

## Future Plan (Detailed)

### 1. Harden SEC / QR Processing

- Build a dedicated `qr_processor` module with:
  - robust SEC page parsing and fallback from `index.json`
  - explicit verification of SEC links and XBRL metadata
  - `performance_label` output: `overperformance` / `inline` / `underperformance`
  - normalized earnings metrics and trend scoring
- Add a `scripts/local_summarize_qr.py` or module version that supports both local LLM summarization and fallback retrieval.

### 2. Add Real-time Detectability and Alerts

- Implement earliest-news detector connector and API.
- Implement insider trade monitor connector with first-second alert semantics.
- Add an alerting pipeline with deduplication, webhook/Slack/email adapters, and severity scoring.

### 3. Build Local LLM Support

- Add a local inference adapter using a compact GGUF model on MacBook Neo, e.g. Vicuna/Mistral 7B quantized.
- Support chunked document summarization and RAG retrieval.
- Provide a Colab-friendly notebook or script for one-time model setup and local inference.

### 4. Improve Ingestion Framework

- Extend `ingest/config/platform_connectors.yaml` to include SEC and financial connectors explicitly.
- Add dynamic Airflow/ECS DAG generation for all connectors, including SEC filing jobs and news ingestion.
- Add connector health dashboards and event-driven retry semantics.

### 5. Enhance Feature Store & Analytics

- Complete DynamoDB feature store materialization for signals, trends, and watchlist history.
- Add query endpoints for filings, insider trades, and news with filters.
- Add data retention and archiving policies for stale signals.

### 6. Production-Ready Deployment

- Wire Terraform ECS task definitions with Secrets Manager and environment variables.
- Add observability: Prometheus metrics, Grafana dashboards, tracing, and cost monitoring.
- Establish CI/CD for code, infra, and data pipeline deployments.

### 7. UX / Dashboard Enhancements

- Add watchlist management UI and queryable financial settings.
- Add signal drilldowns linking to source evidence (SEC docs, news links, raw ingestion metadata).
- Add a research workspace for trend summaries and skill-powered insights.

## Recommended Next Action Items

1. Add a `performance_label` in `scripts/sec_qr_report.py` based on XBRL deltas and summary signals.
2. Implement the earliest-news detector connector and its API endpoints.
3. Add local LLM summarization support with a compact GGUF model on MacBook Neo.
4. Wire SerpApi fallback behind a strict usage gate and caching to preserve credits.
5. Add a `docs/AGENT.md`-style runbook for daily operational checks.

## Notes for Agents

- Treat `SEC` connectors as first-party data sources with strict legal and privacy requirements.
- Prefer deterministic, rule-based signal labels when possible; use generative reasoning only for natural-language explanation.
- Always record provenance for `source_url`, `ingest_ts`, and `connector`.
- Keep new connectors shareable via YAML config and avoid hardcoding source lists.

---

`AGENTS.md` is now the single source of truth for architecture, current state, catches, and next-phase planning for the Praesagus repo.
