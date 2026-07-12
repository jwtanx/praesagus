# Praesagus

Starter repo for the Praesagus market intelligence platform.

Quickstart (local test of Reddit connector) — using Poetry:

```bash
# Install Poetry: https://python-poetry.org/docs/#installation
poetry install
poetry run python -m connectors.examples.reddit_connector

# Run tests
poetry run pytest -q
```

If you prefer pip, a `requirements.txt` file is included for compatibility, but Poetry is the recommended workflow.

Local development with Docker Compose (localstack):

```bash
# Build and start containers
docker-compose up --build

# API will be available at http://localhost:8000
# Bootstrap runs once to create S3 bucket and DynamoDB table in localstack.
```
# praesagus

A quantitative market analysis engine designed to spot institutional trading signals and predict macro trend reversals.

This repo also hosts Cursor Agent Skills for equity research workflows.

## Skills

| Skill | Path | Description |
|-------|------|-------------|
| Elite IPO & Equity Research | `skills/elite-ipo-equity-research/` | Institutional-grade equity research for Bursa Malaysia and global tech stocks/IPOs |

### elite-ipo-equity-research

Produces sell-side quality output including:

- 34-column side-by-side comparison table
- DCF methodology and scenario analysis (Bull / Base / Bear)
- Risk matrix and executive summary
- IPO Investment Score (/100)
- Final recommendation with conviction and allocation guidance
- RM1,500 retail IPO allocation strategy
- Ranked output table

**Trigger terms:** Bursa Malaysia, Malaysian IPOs, ACE/Main/LEAP listings, NASDAQ/NYSE tech stocks, cross-border equity comparisons.

## Installation

Symlink the skill into your personal Cursor skills folder so it is available across all projects:

```bash
ln -s "$(pwd)/skills/elite-ipo-equity-research" ~/.cursor/skills/elite-ipo-equity-research
```

## First-time setup

1. Install dependencies:

```bash
poetry install
```

2. Create local stack services and bootstrap the development environment:

```bash
docker-compose up --build
```

3. Verify local containers:

- Backend API: `http://localhost:8000`
- Airflow webserver: `http://localhost:8080`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

4. Seed local resources if needed:

```bash
poetry run python scripts/bootstrap_localstack.py
```

## Going live

For production deployment, use Terraform to provision the core infrastructure and ECS resources. Ensure the following services are configured:

- S3 buckets for raw, bronze, and silver data
- DynamoDB feature store for aggregated signals and low-latency lookups
- ECS/Fargate task definitions for connector execution
- Airflow/MWAA or scheduler for orchestration
- Secrets Manager for connector credentials
- SQS DLQ for ingestion retries and failure handling

Set production environment variables and secrets in AWS Secrets Manager rather than hardcoding credentials in repo files.

## Data architecture

Raw records are persisted in the data lake on S3. Normalized and partitioned Bronze parquet files are also written to S3, and the aggregated model or feature store entries are stored in DynamoDB for fast online access. This means:

- Raw data is available for replay and lineage in S3
- Bronze/Silver transforms are used for quality, enrichment, and schema normalization
- DynamoDB holds the feature-store or aggregated signal metadata for dashboard/API use

We do not currently have a dbt project in this repo; daily transformations are handled via Airflow / Python ETL templates such as `pipeline/raw_to_bronze.py` and `pipeline/compute_features.py`.

## Usage

In Cursor Agent, invoke the skill by name or ask for analysis of specific stocks/IPOs:

```
Use the elite-ipo-equity-research skill to analyze [Company A], [Company B]
```

Replace the analysis targets placeholder in the skill with your company list, or provide them in your prompt.
