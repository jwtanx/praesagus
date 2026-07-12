# Monitoring & Observability

Status: Draft

Metrics

- Ingestion: per-connector success/failure, latency, items ingested
- ETL: partition processing time, row counts, validation failures
- Features/Models: compute time, success rate, prediction latency
- Alerts: delivery success, retries

Logs & Traces

- Structured logs (JSON) and OpenTelemetry traces.
- Centralized logging to CloudWatch and long-term storage in S3.

Dashboards & Alerts

- Grafana dashboards for key metrics.
- CloudWatch alarms for critical failures and cost spikes.

Incident Response

- Runbooks per connector and per pipeline.
