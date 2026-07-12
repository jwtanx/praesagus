# Connector SDK Specification

Status: Draft

Language: Python 3.11

Purpose

- Provide a lightweight SDK to build connectors that follow the canonical lifecycle and integrate with S3, EventBridge, and monitoring.

Core Types

- `RawRecord` — opaque JSON from source
- `NormalizedRecord` — canonical schema with fields: `source`, `source_id`, `timestamp`, `text`, `entities`, `metadata`, `provenance`

Base Interface

```
class BaseConnector:
    def authenticate(self) -> None: ...
    def discover(self) -> List[FeedMetadata]: ...
    def fetch(self, start: datetime, end: datetime, cursor: Optional[str]) -> Iterator[RawRecord]: ...
    def normalize(self, raw: RawRecord) -> NormalizedRecord: ...
    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> StorageResult: ...
    def monitor(self) -> HealthStatus: ...
```

SDK Helpers

- `S3Writer` — atomic writes and partition helpers
- `HTTPClient` — rate-limit aware client with retry policies
- `SchemaValidator` — JSON Schema validation
- `Provenance` — attach metadata automatically
- `metrics` — emit CloudWatch compatible metrics

Packaging

- Distribute as a pip-installable package within the repo and build as part of CI.
