# Praesagus Agent Guidance

This file is the repository's single source of agent instructions. Keep it concise, accurate to the checked-in implementation, and update it when architecture or workflow changes. Instructions here apply repository-wide; nearer `AGENTS.md` files may add scoped guidance.

## Project and current implementation

Praesagus is a market-intelligence research platform. Current repository capabilities include:

- FastAPI services in `backend/` and a Vite/React interface in `frontend/`.
- Configured data connectors in `connectors/`, including SEC, news, and social sources; connector settings live under `ingest/config/`.
- Financial ingestion and monitoring scripts in `scripts/`, including SEC filings, insider activity, company news, financial calendars, and QR reports/watchers.
- Local development with Docker Compose, LocalStack bootstrap, and Terraform scaffolding under `infra/`.
- Research instructions under `skills/`. Skills guide analysis; they are not, by themselves, executable agents or a production answer harness.

The repository does **not** currently contain a hosted LLM answer path, general-purpose agent runtime, persistent answer traces, or a runtime-enforced answer-quality evaluation harness. A read-only Moomoo OpenD adapter and FastAPI routes exist for request/response news search and quote snapshots; they do not provide persistent ingestion, continuous news push, or model-backed analysis. The API's research route must not be described as model-backed unless implementation changes. `harness/research_harness.yaml` is a proposed future contract only; nothing currently loads or enforces it.

Treat `docs/`, scripts, configuration, and tests as evidence of implemented behavior. Label planned work as roadmap, not as current capability. Do not assume cloud services in the architecture notes are provisioned or operational merely because Terraform/docs mention them.

## Engineering practice

- Inspect the relevant implementation and tests before changing behavior. Make the smallest coherent change and preserve unrelated working-tree changes.
- Follow existing interfaces, formatting, and dependency choices. Prefer official APIs and documented connector contracts; respect rate limits, terms, licensing, and authentication boundaries.
- Never put credentials, tokens, private user data, or generated secrets in source, logs, fixtures, or commits. Load secrets from environment/configuration or a secret store; do not print them.
- Preserve raw-source provenance and timestamps. Avoid destructive changes to stored data; use versioned or append-only outputs where appropriate.
- Keep failures visible and bounded: validate inputs, handle upstream errors, use sensible timeouts/retries, and avoid claiming freshness or success without evidence.

## Data, research, and trader safeguards

- Record `source_url` where allowed, source/provider, publication time, retrieval/availability time, timezone, data period, connector, and ingestion time. Separate source facts from interpretation and model-generated text.
- Prefer primary evidence: filings, regulators, exchanges, official company disclosures, central banks, and official statistics. Label secondary reporting, vendor data, proxies, social sentiment, and missing or stale data. Deduplicate syndicated or correlated evidence; do not count repeated views of one event as independent confirmation.
- Preserve the decision-time information set. Never use later information to justify an earlier signal. Keep forecast timestamps and score outcomes separately.
- Use `skills/praesagus-trading-orchestrator/SKILL.md` for applicable investment, trading, portfolio, or event-analysis requests; use `skills/skill-template/SKILL.md` for shared analysis requirements.
- Moomoo news, sentiment, price/technical anomalies, capital flows, and derivatives activity are evidence inputs, not standalone recommendations or proof of informed direction. Check source, timestamp, liquidity, market context, event overlap, and whether the information may already be priced in.
- Treat the Sneaky Pivot setup as an unvalidated hypothesis. Do not call it trade-ready without formal rules, realistic fill/cost assumptions, regime and event filters, risk limits, and robust out-of-sample validation.
- State uncertainty, bull and bear evidence, key disconfirming evidence, and measurable invalidation. Missing required evidence means lower confidence or `NO TRADE`, not invented precision. Separate research conclusions from execution instructions.
- Use the skill's action vocabulary where relevant: `research only`, `watchlist`, `paper trade`, `human approval required`, `execution-ready`, or `NO TRADE`. Live execution requires explicit human approval and independent risk checks; never imply the repository executes trades if it does not.

## Moomoo / OpenD integration boundary

The implemented `connectors/moomoo_opend.py` adapter and `/api/v1/moomoo/news` and `/api/v1/moomoo/quotes` routes are read-only. OpenD must run separately and be reachable at `MOOMOO_OPEND_HOST`/`MOOMOO_OPEND_PORT`; native defaults are `127.0.0.1:11111`, while Compose configures the host gateway by default. News search is request/response, with a per-process rolling limit of 10 calls per 30 seconds; it is not a push feed. Quote results are latest snapshots after a request-scoped subscription, not a continuous stream. Runtime integration needs Moomoo market-data entitlements. This process-local quota does not coordinate across multiple API workers/replicas. Treat option flow and capital-flow data as ambiguous until independently interpreted. Do not expose account credentials or private account data to frontend code, traces, or logs.

## Testing and validation

- Add or update focused tests for behavior changes. Prefer deterministic fixtures and mocked external APIs; tests must not require live credentials or place orders.
- Run the narrow relevant test set, then broader checks when scope warrants. Validate changed configuration and documentation references. Report commands and outcomes accurately; do not claim tests passed if they were not run.
- For ingestion or signal logic, cover malformed/missing data, duplicates, stale/future timestamps, rate-limit/upstream failures, and risk/rejection cases where relevant.
- Keep CI-compatible, repeatable checks. Never weaken or remove a test merely to make a change pass without explaining the reason and replacing its coverage.

## Future answer harness contract

`harness/research_harness.yaml` specifies a design contract for a future answer harness: routing, provenance, traces, deterministic graders, human review, and evaluation-gated improvement. It is **not runtime-enforced**. Do not claim it routes requests, records traces, grades answers, or updates skills until code implements and tests those behaviors.

The future loop must use frozen/replayable evidence and a versioned evaluation set. Corrections may become candidate regression cases; prompt, skill, or model changes require evaluation and human review before adoption. Do not enable autonomous self-training or self-editing of production instructions. Track quality, calibration, latency, and token/call cost so reinforcement cannot optimize a proxy while degrading factuality or risk controls.

## Roadmap (not implemented unless code says otherwise)

- Build persistent, deduplicated OpenD-backed watchlist ingestion and a catalyst brief: retain timestamped source evidence, summarize with linked evidence, and display observed quote response. Validate entitlements, distributed rate limiting, data rights, and economics before treating it as a service.
- Implement the answer harness described in `harness/research_harness.yaml`, initially for one end-to-end research flow with replayable cases and human-reviewed investment judgments.
- Continue improving SEC/QR extraction, alert persistence/deduplication, connector health, feature-store queries, operational runbooks, and deployment automation as scoped by current docs and implementation evidence.
