# Next Steps Review

Status: Actions completed and recommended next priorities.

Completed so far:

- `AGENT.md`, `PRD.md`, `TDD.md` and key architecture docs created.
- Connector SDK scaffolded (`connectors/base.py`, `connectors/utils.py`).
- Example Reddit connector added under `connectors/examples/` with a basic unit test.
- CI workflow added (.github/workflows/ci.yml) configured to use Poetry and run tests.
- Terraform infra scaffold added under `infra/` with an S3 bucket example.

Immediate next priorities (recommended):

1. Implement S3 writer using `boto3` with atomic write semantics and tests.
2. Implement real Reddit connector using OAuth and Pushshift/APIs, with rate-limit handling.
3. Add Airflow DAG templates in `ingest/` and sample ETL job to transform raw → bronze.
4. Implement a minimal FastAPI service in `backend/` to serve computed signals.
5. Wire up monitoring (CloudWatch metrics) and add a CloudWatch/Grafana dashboard.

Operational tasks:

- Configure Terraform backend and apply to a dev AWS account.
- Configure CI secrets (Poetry credentials optional, AWS creds for infra-only in separate pipeline).

How to run locally:

```bash
poetry install
poetry run pytest -q
poetry run python -m connectors.examples.reddit_connector
```
