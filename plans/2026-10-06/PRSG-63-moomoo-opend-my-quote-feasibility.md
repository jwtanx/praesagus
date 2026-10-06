# PRSG-63 — Moomoo OpenD Malaysian quote feasibility spike

Type: spike · Modules: connectors, financial-data, docs · Owner: Lead · Priority: P2 · Effort: S (1–2 person-days; two-day review window, excluding operator provisioning) · Impact: medium; determines whether existing read-only quote access can truthfully represent one Malaysian quote, with low current feasibility confidence. Created 2026-10-06 MYT.

## Decision question and objective

Can the existing request/response Moomoo OpenD quote path return one valid Malaysian symbol snapshot with enough provider identity and timestamp context to represent it accurately, while preserving current US behavior and failing closed when OpenD, transport, or entitlement is unavailable?

This is a time-boxed feasibility spike. Current local readiness is blocked: a local-only TCP connect to configured `127.0.0.1:11111` returned `ConnectionRefusedError`. A later live test depends on the operator installing and starting OpenD, logging in through the operator-controlled OpenD setup, and confirming MY quote entitlement. This ticket does not authorize installing or launching OpenD, credential access, a live request, or implementation. Any live test requires a separate safe check after the operator provisions OpenD.

## Repository evidence and limits

At frozen base `6d87c154dff3b3ec7c15e41ea971210c1c547e91`, `connectors/moomoo_opend.py` implements `get_quotes(codes)`: it opens a request-scoped quote context using `MOOMOO_OPEND_HOST` / `MOOMOO_OPEND_PORT` (defaults `127.0.0.1:11111`), subscribes to the requested codes, fetches quote rows, and closes the context. `GET /api/v1/moomoo/quotes` accepts market-qualified codes and returns `records`, `count`, and an API `retrieved_at`; connection failures map to HTTP 503 and OpenD API failures to HTTP 502. The connector is read-only. Existing tests use fake contexts/connectors and establish mocked US quote behavior only. This repository evidence does not establish that OpenD supports a particular MY symbol in this environment, current account entitlement, or the live provider response schema.

A TCP refusal establishes only that no listener accepted a connection on the configured loopback endpoint at check time. It is not evidence of entitlement failure, unsupported symbol, or provider rejection. No OpenD API call, quote request, credential inspection, or OpenD launch occurred for this plan.

PRSG-62 is a separate provisional proposal concerning direct REST snapshots. This ticket evaluates only the existing OpenD path. Do not change, merge, or treat PRSG-62 as evidence for OpenD behavior.

## Options and tradeoffs

1. **Keep MY unavailable on OpenD.** Safest if no operator-provisioned OpenD/entitlement or no matching, timestamped MY row is available. Preserve current US route behavior and report MY as unavailable/unsupported only when the evidence supports that classification.
2. **Record a bounded OpenD feasibility result without changing the contract.** After the operator setup and separate safe-check authorization, issue at most one read-only request for one pre-agreed MY test symbol. This distinguishes basic transport and response feasibility at low scope, but cannot establish broad market coverage, reliability, or data rights.
3. **Propose a separately reviewed implementation.** Only if the bounded result contains a matching, interpretable MY quote row and sufficient timestamp/provenance fields. A follow-up ticket must freeze code/tests/scope and receive explicit implementation authorization. Do not implement within this spike.

## Evidence contract for a separately authorized later check

Use one pre-agreed, non-account MY market-qualified test symbol and one read-only OpenD quote request. Record only sanitized evidence needed for review:

- requested market-qualified symbol and provider-returned symbol; a mismatch is not success;
- provider quote timestamp exactly as returned, including its documented or observed precision/meaning when established;
- market, provider market date, session, and currency only when returned by the provider; missing fields remain unknown;
- request start/end and local retrieval timestamps with timezone, kept distinct from the provider quote timestamp;
- outcome category and transport/entitlement evidence sufficient to distinguish: local connection unavailable, explicit provider/entitlement failure, valid empty result, malformed response, mismatched symbol, or matching quote row.

Do not retain or print credentials, raw payloads, private account data, or unrelated symbols. Do not retry. Do not infer market/session/currency, official-close status, freshness, entitlement, or support from missing fields or a generic error. A connection refusal is `OpenD unavailable` at the configured endpoint, not `no entitlement`. Classify entitlement failure only when an explicit provider response supports that conclusion; otherwise preserve the outcome as provider/API failure with cause unknown.

Fail closed: report success only for exactly the requested symbol with a usable provider quote timestamp and the observed fields needed to interpret the row. Empty rows remain empty; transport failure, explicit entitlement rejection, provider/API error, malformed data, symbol mismatch, or unusable timestamp must never produce a quote value or a success claim. Preserve HTTP 503 for unavailable OpenD and HTTP 502 for provider/API failures unless a separately accepted contract change is later made. Keep REST US behavior unchanged.

## Scope and boundaries

This ticket authorizes planning and evidence review only. `implementation_authorized=false`; no code, tests, API routes, REST code, UI/dashboard, persistence, forecast, news, schedules, report artifacts, public output, credential access, OpenD start/install, or provider request is authorized by this ticket. No API call or live test may occur until OpenD is operator-provisioned and a separate safe check explicitly authorizes the bounded request.

For this planning handoff, only these files are in the write scope:

- `plans/2026-10-06/PRSG-63-moomoo-opend-my-quote-feasibility.md`
- `plans/2026-10-06/PRSG-63.harness.json`

All other paths are protected, including `connectors/moomoo_opend.py`, backend/frontend code, tests, reports, the PRSG-62 proposal, and all existing PRSG-2/PRSG-60 work. Lead accepted this planning-only write scope on 2026-10-06 MYT. `implementation_authorized=false` remains in force; this acceptance does not authorize follow-on implementation.

## When it's considered done

- [x] PRSG-63-D1: Lead accepts the planning-only scope, frozen base `6d87c154dff3b3ec7c15e41ea971210c1c547e91`, and explicit `implementation_authorized=false` boundary. Evidence: Lead review recorded 2026-10-06 MYT; only the two PRSG-63 planning files are in scope.
- [x] PRSG-63-D2: The current local readiness blocker and its limits are recorded accurately; no claim of MY entitlement or provider support is made from TCP refusal.
- [ ] PRSG-63-D3: After operator provisioning and a separate safe-check authorization only, one bounded MY OpenD quote attempt is either recorded against the evidence contract above or left blocked with the exact operator/setup blocker. No request occurs as part of this planning handoff.
- [x] PRSG-63-D4: Lead records the currently supportable decision: the configured OpenD endpoint is unavailable until operator-provisioned OpenD is listening, so there is no MY live result and any follow-on implementation remains blocked pending the bounded evidence and separate accepted scope. PRSG-62 and US REST behavior remain outside this spike. Evidence: Lead review, 2026-10-06 MYT; local readiness at `127.0.0.1:11111` previously returned `ConnectionRefusedError`.

## Validation and handoff

Planning-only validation: `python3 scripts/planning/validate_ticket.py plans/2026-10-06/PRSG-63.harness.json --changed-file plans/2026-10-06/PRSG-63-moomoo-opend-my-quote-feasibility.md --changed-file plans/2026-10-06/PRSG-63.harness.json` and `git diff --check`. No implementation tests or provider calls are in scope here.

**Operator setup required before a separate safe check:** install OpenD through the operator's normal approved process, start it, log in under operator control, ensure it listens at the configured `127.0.0.1:11111` endpoint (or have the operator provide the configured host/port), and confirm MY quote entitlement for the one agreed test symbol. Do not request or inspect credentials in this spike. If setup or entitlement is absent, leave the live criterion blocked and report that evidence only.

**Lead decision:** planning-only scope accepted; ticket remains in progress. Operator must install and start OpenD, log in under operator control, ensure it listens at the configured host/port (currently `127.0.0.1:11111`), and confirm MY quote entitlement for the one agreed test symbol. D3 remains pending until a separate safe check is authorized after provisioning. Any implementation requires a new accepted scope and explicit authorization.
