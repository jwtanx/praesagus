# 005 — Durable alert delivery

State: planned, not assigned. Target: users relying on company-news and insider webhooks. Effort: 4–7 person-days. Expected impact: high reliability for alert-dependent workflows; does not improve the validity of underlying trading signals.

## Baseline and selected design

`alerting/financial_alerts.py` returns a status code or None; there is no durable delivery record. Store a local SQLite outbox for the single-host MVP using stdlib sqlite3, with a stable logical alert key, payload version, event/source ID, destination alias, creation/attempt times, state, attempt_count, next_attempt_at and sanitized failure category. Resolve destination secrets from environment/configuration at send time, never persist webhook URLs/tokens. Review minimal payload retention/access before use.

Insert logical alerts idempotently before sending. Worker claims pending entries transactionally, uses lease expiry for interrupted work, and performs bounded HTTP retries with timeout, exponential backoff and jitter. Retry timeouts, 429 (bounded Retry-After), and transient 5xx; most other 4xx become terminal failed. Cap attempts and elapsed retry window. Receiver-supported idempotency keys reduce delivery duplicates; timeout-after-acceptance can still cause repeated deliveries. Document at-least-once attempts rather than guaranteed exactly-once delivery.

Provide read-only delivery history/filter endpoints and visible pending/retrying/sent/failed states. A replay operation requires authenticated authorization, reuses the same logical key, and records who/why only when identity exists; API-key auth alone provides no per-user attribution. Do not add automatic trading or expand recipients. Deduplicate ingestion separately from delivery semantics.

## Acceptance and measurement

Fixtures cover restart after enqueue, crash after claim, lease expiry, concurrent workers, duplicate events, 429/5xx/timeouts/permanent failures, secret redaction, and successful response with uncertain receiver side effects. No live webhooks in tests. Include explicit bounded retention and handling of schema upgrades without destroying pending entries.

Metric: every queued fixture alert ends in a visible sent/failed/retrying state after simulated restart, with one logical alert per event/destination/version. Track delivery lag and failure causes without claiming receiver consumption. Work breakdown: schema/leases 1–1.5 days; dispatcher integration 1–2; API/UI 1; replay/failure tests 1–1.5; docs/review 0.5–1. Dependencies: destination contract, idempotency support, retention, and single-host worker lifecycle. Rollout to a local fake receiver first; rollback pauses dispatcher and preserves pending records for review.
