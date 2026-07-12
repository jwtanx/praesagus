# System Architecture

Status: Draft

Overview

Praesagus is an event-driven microservice architecture that decouples ingestion, processing, storage, and serving. Components communicate via events and durable storage.

Core Components

- Connectors: small, stateless tasks that fetch from a source and write immutable raw payloads to S3, plus metadata to EventBridge.
- Ingest Orchestrator: schedules and monitors connector tasks (Airflow / MWAA or scheduler + ECS).
- ETL/Transform Jobs: convert raw → bronze → silver, run as batch jobs or Glue/ECS tasks.
- Feature Store: stores time-series features for models and online serving (DynamoDB/Aurora).
- AI Engines: training and inference services; model registry and experiment tracking.
- API & Dashboard: REST API and SPA for visualization and user interaction.
- Alert Engine: consumes scored signals and emits notifications via SNS/webhooks.
- Observability: metrics, structured logs, tracing, and dashboards.

Inter-service Communication

- EventBus: EventBridge for decoupled events.
- Queues: SQS for durable work queues and retries.
- Notifications: SNS for alerts and user-facing notifications.

Data Flow

1. Connector writes raw file to S3 and emits an ingest event.
2. ETL job picks up the raw file, validates schema, and writes Bronze parquet.
3. Enrichment jobs normalize entities, link canonical IDs, and write Silver.
4. Feature jobs compute metrics and write to Feature Store.
5. Scoring jobs compute signals, persist results, and push alert events.
6. API serves results and evidence pointers.

Scalability & Fault Isolation

- Each connector runs in its own Fargate task or lambda with scoped IAM.
- Failures are isolated per connector; retries and DLQs prevent cascade failures.

Security

- Network: VPC for services needing private access; public API via ALB.
- Secrets: AWS Secrets Manager. IAM least-privilege.

Extensibility

- New connectors implement the `BaseConnector` interface and are deployable as containers.
- Event schemas are versioned to prevent breaking consumers.
