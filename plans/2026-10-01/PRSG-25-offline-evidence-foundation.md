# PRSG-25 — Offline immutable evidence foundation

Type: feature · Modules: financial-data, harness · Owner: Engineer · Priority: P1 · Effort: M (2–4 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Accepted by Lead for the user-authorized 22:50 implementation handoff. Frozen base: bb0d302bd4384482e628e5e1e58630e0d68396f4.

## Decision and research review
PRSG-21/23 favor reusable libraries and explicit provenance; no performance, security or resolved dependency claim is accepted from metadata alone. First implement the standard-library storage substrate (sqlite3, json, hashlib, datetime), with no new dependency or model installation. Preserve harness/forecast_review.py unchanged. PRSG-24 protocol is missing at dispatch: attribution, movers, volume thresholds, forecast horizons and skill learning are deferred, not silently inferred.
PRSG-21/23 remain research review tickets, not implementation. Their documentation is uncommitted and preserved. Existing .DS_Store modification is unrelated and must remain untouched.

## Objective and interfaces
Add harness/evidence_store.py exposing a documented EvidenceStore(root) API to ingest synthetic completed daily bars, news revisions and collection-run outcomes. Add a small offline JSON-batch CLI in that module; no network access or scheduler. Inputs must explicitly declare schema version, synthetic origin, provider, run ID, retrieval/ingestion aware timestamps, rights/status metadata and payload records. Restrict this first API to synthetic data; reject real/provider-live origins. No fixtures under public artifacts/.
Use private caller-specified storage outside repository/public artifacts for generated raw files and SQLite. Document errors, return counts and query/replay interface. Tests use pytest tmp_path.
Preserve exact raw input bytes as content-addressed SHA256 batches; exclusive creation and hash verification on reuse; never overwrite evidence. SQLite normalized rows refer to raw hash. Parameterized queries and transactions, schema version guard and bounded lock failure; no destructive schema reset. Existing content is immutable by API contract, not OS tamper-proof.
Write raw artifact before transactional references; a crash may leave an unreferenced immutable batch, never a committed dangling reference. Detect missing/corrupted raw references on reads. Unknown database schema must fail visibly.

## Bar and news contracts
Bar identity: provider/instrument/venue/interval/session/adjustment basis/bar time. Record currency, exchange timezone, session date, completion/availability/observation/ingestion times. Require explicit completed daily regular bars; reject snapshots as OHLCV. Finite positive prices with low <= open/close <= high, finite nonnegative volume, aware timestamps and no future completion/availability relative to observation. Corporate-action/version metadata retained; no return calculation.
News: provider/item ID, URL where allowed, source tier, raw publication timestamp/timezone, parsed publication nullable, provider availability nullable, first observed and ingestion timestamps, event cluster nullable, content hash/version. Missing publication stays null, never becomes now. Contradictory/future publication is flagged and excluded from as-of eligibility, not silently corrected.
Identical versions are idempotent; changed payloads append revisions. Preserve every observation with first-seen derived without falsely backdating from publication. As-of queries exclude versions first observed after cutoff, and future/unknown required availability; backfilled news cannot become system-known historical evidence. Historical explanations are separate and explicitly labeled.
Collection runs retain declared universe/session, successful-empty, success, partial and failed status plus bounded error reason. No-news observed is distinct from failed/unattempted coverage. Capture ordinary observations as well as movers; this ticket does not select movers or infer causal links.

## Scope and non-goals
Allowed files only: this spec, its canonical manifest, harness/evidence_store.py, tests/test_evidence_store.py and harness/EVIDENCE_STORE.md.
Protected: all other existing code, artifacts, skills, infra, dependencies, verification policy and forecast scorer. No actual raw market data/SQLite committed, no API integration, classifiers, live requests, paid access, model downloads, public export, trading or skill rewrite. Runtime rights/entitlement gates apply to later collection tickets; synthetic implementation needs no market rights.
Engineer may update progress/evidence only; acceptance definitions, scope/base and Lead acceptance changes need Lead approval. No commit/push; return diff and evidence for Lead integration, one ticket per eventual commit.

## When it's considered done

- [x] PRSG-25-D1: Synthetic batches and append-only bar/news/run storage preserve raw hashes and revision provenance with idempotent replay.
- [x] PRSG-25-D2: As-of eligibility and failure distinctions reject temporal leakage, malformed data and corrupted evidence using deterministic offline regressions.
- [x] PRSG-25-D3: Usage/errors/private storage documented, frozen scope validated, forecast regressions pass and Lead independently reviews.

## Checks and delivery
Run python3 -m pytest -q tests/test_evidence_store.py tests/test_forecast_review.py.
Cover duplicate ingestion, revised news/bars, missing/future/naive timestamps, malformed OHLCV/NaN, snapshots/incomplete bars, late backfill, empty-vs-failed/partial runs, rollback on invalid mixed batch, lock/schema errors and corrupted/missing raw batches. Add a documented synthetic US/MY example without asserting live market coverage.
Validate manifest with every owned changed path. Full suite recommended if integration expands, which requires separate scope approval. Checks are not automatically authorized by verification_policy.json: execute focused tests directly, do not change policy to permit new argv.
Report exact commands/results, changed paths, synthetic limitations and pending live-data decisions. Completion requires Lead review, not just passing fixtures.

## Progress
22:50 MYT: Lead froze offline scope; automated tests and implementation pending.


## Engineer handoff evidence

Implemented only the five frozen paths: `harness/evidence_store.py`, `harness/EVIDENCE_STORE.md`, `tests/test_evidence_store.py`, this spec and canonical manifest. Public API stores exact immutable SHA256 JSON bytes plus SQLite bar/news versions, raw-linked observations and declared run outcomes. Synthetic origin and rights declaration are mandatory; private external storage and completed regular daily bars are enforced. Unknown/future/contradictory news remains stored but is ineligible. As-of cutoffs include ingestion knowledge; later observations do not leak into earlier replay. Historical explanations are explicitly labeled.

`python3 -m pytest -q tests/test_evidence_store.py tests/test_forecast_review.py`: **90 passed in 0.57s**. Includes forced mid-transaction database failure with preserved existing references, bounded lock failure with permissible unreferenced raw, unknown/changed schemas, corrupted/missing raw evidence, US/MY synthetic examples and CLI/documentation replay. No external API/credentials/dependency/model/real data used. Full suite not run: integration did not expand. Existing forecast scorer has no diff.

Scoped manifest validation with every exact owned path passed. All acceptance checklist items and Lead review remain pending. No scope/base/gate edits, commit or push. The PRSG-24 research file appeared in the shared workspace during implementation; no attribution/mover decisions were imported into this frozen scope. Pre-existing .DS_Store and PRSG-21–24 files were preserved.

Limitations: timestamps/status/rights are declared synthetic provenance, not live-provider attestation. Raw immutability is an API contract, not OS tamper protection. Private caller storage must also avoid externally hosted/shared folders. News with unknown publication or required availability is conservatively ineligible. Run revisions preserve every distinct raw batch; exact batch replay is idempotent. Market-data entitlements, provider completeness, causal rules and learning remain later decisions.


## Engineer source-vintage follow-up

Lead acceptance 2026-10-01 MYT: full implementation/tests/docs and follow-up inspected; frozen test command independently rerun92passed in0.53s. Earlier fullsuite312passed with5 existingwarnings before the two added cases. Consultant temporal audit/replay found no blocking synthetic-scope issue. All checklist items accepted for this offline foundation only. Historical pending statements below record earlier checkpoints, not current acceptance. Publication/deployment is separate from acceptance.

Consultant consumer-risk regression: added two deterministic bar/news replay cases with newer source-v2 ingested before older backfilled source-v1. All eligible versions and exact raw bytes remain preserved; source-v1 never appears before late ingestion; repeated raw ingestion remains idempotent. Greatest revision is explicitly shown to be older source truth in these fixtures. Documentation now warns that ingestion order is not source chronology and defers authoritative source-vintage resolution to future consumers. No ordering algorithm or API added.

`python3 -m pytest -q tests/test_evidence_store.py tests/test_forecast_review.py`: **92 passed in 0.63s**. Four follow-up paths changed: test, usage documentation, spec progress and manifest test evidence. Frozen scope/base/check definitions and all acceptance/Lead gates retained. No staging, commit or push.
