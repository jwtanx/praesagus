# Repository Structure

Status: Draft

Top-level layout

- `connectors/` — connector SDK and implementations
- `ingest/` — orchestration and DAGs
- `pipeline/` — ETL and feature computation jobs
- `models/` — training code and registry hooks
- `backend/` — REST API and minimal dashboard
- `infra/` — Terraform modules and IaC
- `docs/` — design docs and runbooks
- `tests/` — unit and integration tests

Guidelines

- Keep connectors small and isolated.
- Reuse SDK helpers; avoid duplicated code across connectors.
