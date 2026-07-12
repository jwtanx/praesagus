# Praesagus — Technical Design Document (TDD)

Status: Draft

## Overview

This TDD describes system components, interfaces, data flow, storage choices, and the connector SDK design for the Praesagus MVP.

## Components

- Connector Service (SDK + implementations)
- Orchestrator: Airflow (MWAA) or scheduler to run connectors and transformation jobs
- Object Store: S3 (raw + transforms)
- Processing: ECS Fargate tasks or Glue jobs for ETL
- Feature Store: DynamoDB or Aurora/Postgres for time-series features
- Search / Analytics: OpenSearch for text search and aggregations
- API / Dashboard: FastAPI or Flask for REST + React single-page UI
- Messaging: EventBridge / SNS / SQS for events and alerts

## Dataflow

1. Connector fetches raw payloads and writes immutable JSON to `s3://praesagus/raw/...`.
2. Connector emits an ingest event to EventBridge with metadata and S3 URIs.
3. ETL job picks up raw files, validates schema, writes Bronze parquet files, and writes normalization metrics.
4. Feature jobs compute time-series features and store them in the Feature Store.
5. AI scoring jobs consume features, compute signals, store scored results and evidence pointers.
6. API reads scores and evidence to serve dashboard and alerts.

## Connector SDK (High-level)

Language: Python (3.11+)

Core interface:

- `class BaseConnector:`
  - `def authenticate(self) -> None`
  - `def discover(self) -> List[FeedMetadata]`
  - `def fetch(self, start: datetime, end: datetime, cursor: Optional[str]) -> Iterator[RawRecord]`
  - `def normalize(self, raw: RawRecord) -> NormalizedRecord`
  - `def store(self, raw: RawRecord, normalized: NormalizedRecord) -> StorageResult`
  - `def monitor(self) -> HealthStatus`

Helpers provided by SDK:

- S3 writer with atomic write helpers and partitioning utility
- Retry/backoff helpers
- Rate-limit-aware HTTP client
- Schema validation utility (JSON Schema)
- Provenance metadata wrapper

## Schema Contracts

- Raw: store provider's raw JSON plus connector metadata and collection method.
- Normalized: canonical fields like `source`, `source_id`, `timestamp`, `text`, `entities`, `metadata`, `provenance`.

## Storage Choices Rationale

- S3 for raw: immutable, cheap, and integrates with AWS analytics tools.
- Parquet for Bronze/Silver: columnar, efficient for analytics.
- DynamoDB for feature store: low-latency online reads; Postgres/Aurora for complex queries and historical backtests.
- OpenSearch for full-text search and aggregations.

## Observability

- Emit Prometheus-compatible metrics via CloudWatch exporter.
- Structured logs (JSON) and OpenTelemetry traces.

## Security

- Secrets from AWS Secrets Manager.
- IAM roles scoped to least privilege for each service.

## Deployment & CI

- Build connectors into container images; push to ECR.
- Use Terraform for infra provisioning and MWAA configuration.
- CI pipeline: lint → unit tests → build image → deploy to dev as staging.

## Next Work Items

- Implement `connectors/base.py` with the `BaseConnector` interface.
- Create example connectors: `reddit` and `google_trends`.
- Add Airflow DAG templates for scheduled ingestion.
