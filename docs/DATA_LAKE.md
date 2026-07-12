# Data Lake Design

Status: Draft

Principles

- Immutable raw data: never overwrite raw objects.
- Time-partitioned layout for efficient reads and lifecycle management.
- Schema evolution via versioned contracts and compatibility checks.

Layout

- s3://praesagus/raw/source=<source>/year=YYYY/month=MM/day=DD/hour=HH/<uuid>.json
- s3://praesagus/bronze/source=<source>/year=YYYY/month=MM/day=DD/part-<N>.parquet
- s3://praesagus/silver/<dataset>/year=YYYY/... (parquet)

Metadata & Catalog

- Glue Catalog to register datasets and partitions.
- Each object carries `provenance` JSON including `connector`, `collection_method`, `source_url`, `license`, and `ingest_ts`.

Retention

- Raw: default 3 years (configurable) with lifecycle transition to Glacier.
- Bronze/Silver: tiered retention; gold tables retained per business need.

Access Patterns

- Batch ETL reads entire partitions.
- Interactive queries use Athena/OpenSearch for low-latency slices.
