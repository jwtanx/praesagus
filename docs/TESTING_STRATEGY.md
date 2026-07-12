# Testing Strategy

Status: Draft

Levels

- Unit tests for transforms and connector logic.
- Integration tests using recorded fixtures or local emulator for external APIs.
- Contract tests for event schemas.
- End-to-end tests: ingest → feature → signal → API.
- Load tests for ingestion throughput.

Test Data

- Use synthetic and recorded real payloads stored in `tests/fixtures`.

Automation

- Run tests in CI on PRs; require passing checks before merge.
