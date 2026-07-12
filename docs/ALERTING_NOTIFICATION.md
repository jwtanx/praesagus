# Alerting & Notification Design

Status: Draft

Alert Types

- Threshold alerts (e.g., mentions > 300% increase)
- Anomaly alerts (model-based)
- Scheduled digests (daily/weekly)

Delivery Channels

- Email, Webhook, Slack, Discord, SMS (via SNS adapters)

Subscriptions

- Users subscribe to entities, watchlists, or global rules.

Reliability

- Use SNS for fanout; SQS for durable delivery to adapters; DLQs for failed deliveries.

Auditing

- Every alert stores evidence pointers and delivery logs for audit.
