# Praesagus — Agent Guidance

This repository houses Praesagus: an event-driven, alternative-data market intelligence platform whose mission is to discover consumer behaviour shifts before they're reflected in financial markets.

This AGENT.md provides a concise, durable reference for AI coding agents and engineers onboarding to the project. It describes the long-term vision, architecture, engineering principles, conventions, and immediate priorities.

## Vision

Praesagus discovers products, brands, and behavioural trends early by continuously ingesting and analyzing signals from search, social, e-commerce, developer, news, and regulatory sources. The product empowers research teams and investors with explainable, evidence-backed insights and an AI copilot.

## Project Philosophy

- Prioritize scalability, maintainability, extensibility, cost-efficiency, and observability.
- Design as modular, loosely-coupled services with clear interfaces and contracts.
- Favour official APIs, respect rate limits and site policies, and log provenance and licensing for all data.
- Treat raw data as immutable: never overwrite raw files — always append and version.
- Production safety first: circuit breakers, retries, and fail-isolation for connectors and pipelines.

## High-Level Architecture

Event-driven pipeline with these logical layers:

- Ingestion Layer: connectors that authenticate, discover, fetch, normalize, store, monitor, and retry.
- Raw Data Lake: immutable objects (S3) organized by source and time partitioning.
- Cleaning / Normalization: bronze → silver transformations with schema-validation and lineage.
- Feature Engineering / Feature Store: time-series features for training and real-time inference.
- AI Intelligence Engine: model training, model registry, and inference services.
- Downstream: Alert Engine, Dashboard API, Notification adapters, and Backtesting/Trading adapters.

Services communicate via events (EventBridge / SNS / SQS) and store artifacts in S3, DynamoDB, Aurora, Redshift, and OpenSearch for search/analytics.

## Connector Interface (Reference)

Each connector must implement the same interface so new sources can be added plug-and-play:

- `authenticate()` — obtain and refresh credentials
- `discover()` — enumerate available feeds, topics, or accounts
- `fetch(start, end, cursor)` — retrieve raw payloads
- `normalize(raw)` — map to canonical schema and metadata
- `store(raw, normalized)` — write immutable raw + derived artifacts to storage
- `monitor()` — emit metrics, health checks, and provenance
- `retry()` — resilient retry/backoff strategy and circuit breaker

Connectors must record collection method, licensing, rate limits observed, and terms-of-service compliance metadata with each dataset.

## Scheduling and Execution

- Default cadence: hourly. Support configurable cadences (15m, 5m, daily, weekly).
- Use MWAA/Airflow for orchestration where complex DAGs exist; use short-lived ECS Fargate tasks or Lambda for connector jobs.
- Use step functions for multi-step connector flows requiring ordered steps and retries.

## Storage Layers & Naming

- Raw (immutable): `s3://praesagus/raw/source=<source>/year=YYYY/month=MM/day=DD/hour=HH/uuid.json`
- Bronze: cleaned records with minimal transformation
- Silver: enriched & normalized records with canonical entity IDs
- Gold: curated tables and aggregates for analytics and models

## Data Quality & Observability

- Validate schemas at ingest; maintain a DQ score per partition.
- Emit metrics: freshness, ingested count, duplicate rate, error rate.
- Structured logs and traces (OpenTelemetry) for request-level observability.

## AI & Modeling Principles

- Maintain a model registry and experiment tracking for datasets, code, prompts, and metrics.
- Features are time-series first; store in a feature store designed for lookback and online serving.
- Every signal must be backtestable: provide replayable pipelines and scoring harnesses.
- All model outputs must be accompanied by confidence scores and supporting evidence references (dataset IDs, timestamps, source links where allowed).

## Security & Secrets

- No secrets in code. Use AWS Secrets Manager / Parameter Store.
- Principle of least privilege for IAM roles and access to datasets.
- All access must be logged and auditable.

## Monitoring & Alerting

- Monitor connector success/failure rates, pipeline latencies, storage growth, and cost anomalies.
- Dead-letter queues for failed events and connector messages.
- Alerting via SNS with adapters for Slack, Email, SMS, and Webhook.

## Testing & CI/CD

- Unit tests for connectors and transforms.
- Integration tests using recorded fixtures and local/CI mocks of remote APIs.
- Contract tests for upstream/downstream event schemas.
- Use IaC (Terraform/CloudFormation) with environment promotion (dev → staging → prod).

## Repo Structure (Recommended)

- `/connectors/` — connector implementations and SDK
- `/ingest/` — ingestion orchestration and helper libraries
- `/pipeline/` — data processing and feature engineering jobs
- `/models/` — training scripts, model definitions, and registry integration
- `/api/` — dashboard API and copilot gateway
- `/infra/` — IaC, deployment manifests
- `/docs/` — design docs, runbooks, diagrams
- `/skills/` — task-specific skill modules (existing folder)

## Documentation Standards

- Document every connector: source, access method, rate limits, sample payloads, licensing, and permitted uses.
- Keep runbooks for common operational tasks and incident response.

## Immediate Priorities (MVP)

1. Produce Product Requirements Document (PRD) covering core signals and user personas.
2. Design connector SDK and implement 2 canonical connectors (e.g., Reddit, Google Trends) as examples.
3. Define data lake layout and schema contracts for raw → bronze → silver.
4. Implement a minimal Alert Engine and Dashboard API prototype.

## Definition of Success

- MVP ingests multiple sources reliably and stores immutable raw data.
- Signals computed in the feature store map to explainable model outputs with measurable backtest performance.
- Users can query trends via the Dashboard API and receive evidence-backed explanations.

## Next Steps for Agents

- Draft the PRD and TDD documents as separate files in `/docs/`.
- Build the connector SDK specification and example connectors under `/connectors/`.
- Wire up basic Airflow DAGs or ECS tasks for scheduled ingestion.

---

If you'd like, I will now draft the PRD as `docs/PRD.md` and implement the first connector example. Reply with which deliverable to prioritize next.
