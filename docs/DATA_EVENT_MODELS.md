# Data & Event Models

Status: Draft

Event Types

- `ingest.raw.created` — emitted when a raw file is written to S3. Payload: `{s3_uri, source, partition, connector, ingest_ts, provenance}`
- `ingest.normalized.completed` — after Bronze/Silver write. Payload: `{dataset, s3_uri, schema_version, row_count}`
- `feature.computed` — when feature job completes. Payload: `{feature_set, time_window, store_location}`
- `signal.scored` — when AI/heuristic scoring produces a signal. Payload: `{entity_id, score, confidence, evidence_refs}`
- `alert.triggered` — when a rule or model threshold fires. Payload: `{alert_id, subscribers, payload}`

Canonical Normalized Record Schema (v1)

- `source`: string
- `source_id`: string
- `timestamp`: ISO8601
- `text`: string
- `language`: string
- `entities`: [{`type`, `value`, `confidence`}]
- `metadata`: object
- `provenance`: {`connector`, `connector_version`, `collection_method`, `source_url`, `license`, `ingest_ts`}

Versioning & Compatibility

- Events and schemas must include `schema_version` and follow semver for breaking changes.

Storage Pointers

- Everywhere, use S3 URIs for raw objects and parquet artifacts. Use consistent prefixes and partitions.
