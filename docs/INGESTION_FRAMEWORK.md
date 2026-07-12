# Ingestion Framework

Status: Draft

Goals

- Pluggable connectors with a consistent lifecycle.
- Resilient, observable ingestion with retries and DLQs.
- Configurable scheduling and rate-limit handling.

Connector Lifecycle

- `authenticate()` — manage credentials
- `discover()` — list available feeds
- `fetch()` — stream raw records
- `normalize()` — canonicalize fields
- `store()` — write raw + normalized
- `monitor()` — emit metrics and health

Scheduling

- Use Airflow for complex DAGs; use scheduled ECS tasks or Lambda for simpler, stateless connectors.
- Prefer launching each connector run as a short-lived ECS Fargate task with `assign_public_ip=True` so each ingestion execution gets a fresh outbound IP and avoids static IP rate-limit / block patterns.

Reliability

- Circuit breakers per connector; DLQs via SQS.
- Exponential backoff and rate-limit awareness.

Provenance

- Every ingest writes metadata including `connector_version`, `method`, `rate_limit_observed`, and `terms_of_service_url`.
