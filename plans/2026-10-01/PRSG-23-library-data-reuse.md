# PRSG-23 — Audit maintained OSS libraries and data source feasibility

Type: spike · Modules: market-research, financial-data, harness · Owner: Researcher · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: medium-high

Created 2026-10-01 MYT. Base: bb0d302bd4384482e628e5e1e58630e0d68396f4. Impact hypothesis: better evidence quality and reproducible research, not guaranteed returns.

## Decision question and timebox
Within one person-day, select up to three strongest maintained open-source approaches for text classification and supporting market-data handling. Reuse PRSG-21 findings, but verify current releases, activity, actual maintainer identity, code AND checkpoint licenses, archived/security status, dependency/Python compatibility, CPU/GPU requirements and reproducible installation. Stars alone are insufficient; recommend supported stable pins rather than blindly latest releases.
Evaluate scikit-learn baseline, SetFit challenger and whether young Laya merits a pilot; compare alternatives only where needed. Check existing pyproject dependencies before recommending additions. No model downloads, installation, paid queries or benchmark claims.

## Data feasibility
Compare official Moomoo historical bars/news/calendar and existing connectors with faster primary disclosures or permitted news sources. Establish US/MY coverage, completed-session history, adjustment/corporate actions, publication vs first-observed timestamps, polling quotas, retention/redistribution rights and cost unknowns. Unknown request quota or licensing remains unknown. No unsupported fastest-news claim.
Recommend minimum reusable schema/storage/calendar libraries without replacing useful existing forecast review. Include known gaps and no-news/negative-control data collection. SQLite private; no public DB.

## Deliverable
Write docs/research/PRSG-23-library-data-reuse.md only; may update this ticket's progress/check evidence without changing scope, gates or base. Return sourced comparison, preferred pinned approach, unresolved gates and smallest Engineer implementation boundary to Lead. User authorizes return message to Lead. No commits/push, production code or skill edits.

## When it's considered done

- [ ] PRSG-23-D1: Sourced findings and proposed protocol independently reviewed by Lead.

## Progress

Researcher delivered [the sourced audit](../../docs/research/PRSG-23-library-data-reuse.md) on 1 October MYT. Preferred baseline: supported scikit-learn 1.9.1; SetFit 1.2.0 in an isolated environment because its Sentence Transformers requirement conflicts with repository 2.x; Laya 0.3.22 experimental only. Current releases, public advisory responses, checkpoint licenses/revisions, calendars and source quotas reviewed; public advisory absence does not prove security. US/MY Moomoo entitlement, historical completeness, retention/redistribution rights and actual dependency resolution remain gates. Proposed private immutable raw batches + SQLite collector; source timestamp/revision limitations in existing collectors recorded. No installation, model download, provider login, paid query, training, benchmark, code/skill edit or commit/push. Findings and independent Lead review remain pending acceptance.
