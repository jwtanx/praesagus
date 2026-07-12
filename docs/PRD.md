# Praesagus — Product Requirements Document (PRD)

Status: Draft

## Objective

Deliver an MVP of Praesagus that reliably ingests multiple alternative data sources, computes early consumer trend signals, and exposes evidence-backed insights via an API and lightweight dashboard.

## Primary Users / Personas

- Quant Researcher: needs reproducible signals, backtestable features, and access to raw data.
- Product Manager / Strategist: needs trend summaries, alerting, and supporting evidence for decision-making.
- Retail Investor / Analyst: wants actionable, explainable insights and watchlists.

## Key Problems to Solve

- Detect emerging consumer trends earlier than public markets.
- Keep provenance and explainability for every signal.
- Provide reproducible pipelines and backtesting for candidate signals.

## MVP Success Metrics

- Ingest 5+ diverse sources (e.g., Reddit, Google Trends, YouTube, Amazon reviews, Github) reliably for 30 days.
- Store immutable raw data in S3 with partitioning and metadata.
- Produce at least three signal types (mention velocity, search momentum, sentiment acceleration).
- Expose a Dashboard API that returns top trending entities with evidence references.
- Automated alerts for configurable thresholds (email/webhook).

## MVP Scope

- Data Sources: Reddit (push through API or Pushshift), Google Trends, YouTube (API), Amazon Reviews (public scraping where allowed), GitHub (API).
- Ingestion: Connector SDK and two example connectors implemented and scheduled hourly.
- Storage: S3 raw layer, Bronze normalized layer in Parquet, simple feature store in DynamoDB or Postgres.
- Processing: Batch transformations (bronze → silver) implemented as Airflow DAGs or scheduled tasks.
- AI: Lightweight signal scoring (heuristic + simple ML) with confidence and evidence links.
- API: REST API to query trends, evidence, and signal scores.
- Dashboard: Minimal UI (single-page) to view top trends and drill into evidence.
- Alerts: Email and webhook delivery for top-N or threshold-based alerts.

## Non-functional Requirements

- Scalability: connectors must scale horizontally and be stateless.
- Observability: metrics and traces for ingestion and transforms.
- Security: secrets in Secrets Manager; least-privilege IAM.
- Compliance: record source, license, and collection method for every dataset.

## Data & Privacy Considerations

- Respect robots.txt and TOS; prefer official APIs.
- Do not store PII unless explicitly required and permitted — redact when necessary.

## Milestones (2-week sprints)

1. Sprint 1: AGENT.md, PRD, basic repo scaffolding, connector SDK spec.
2. Sprint 2: Implement Reddit + Google Trends connectors; S3 raw storage; Airflow DAG skeleton.
3. Sprint 3: Bronze normalization; simple feature store and signal computations.
4. Sprint 4: Dashboard API, minimal UI, alerting plumbing.
5. Sprint 5: Backtesting harness and model registry integration.

## Open Questions

- Which data store for the feature store: DynamoDB (low-latency) vs Aurora/Postgres (richer queries)?
- Budget for third-party paid APIs (e.g., paid Google Trends API alternatives).

## Appendix: Minimal API Endpoints (MVP)

- `GET /api/v1/trends?source=all&since=2026-07-01` — list top entities and scores
- `GET /api/v1/evidence?entity=product_x` — list raw records and links
- `POST /api/v1/alerts` — create alert subscription
