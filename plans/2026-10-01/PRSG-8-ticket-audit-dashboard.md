# PRSG-8 — Searchable ticket audit dashboard

Type: feature · Modules: frontend, harness, docs · Owner: Lead · Priority: P1 · Effort: S (0.5–1.5 person-days) · Impact: medium-high

Created: 2026-10-01 MYT. [Delivery contract](PRSG-8.harness.json).

## Accepted scope and design

Provide a GitHub Pages ticket dashboard, keyword search on title/description, status/type/module/owner filters, sortable keys/dates/priority/effort/impact, ticket detail progress timeline and clickable full commit hashes. CSV export is a flat convenience view, not the canonical audit. Git committed Markdown specs and harness manifests are the source of truth. A deterministic stdlib builder reads full first-parent history and emits artifacts/tickets/audit.json containing current records and every committed progress snapshot/delivery association; deleted plans remain visible in history. Never invent progress between commits or equate code delivery with completed acceptance. Working-tree/uncommitted activity is not audited. Historical titles without prefixes link through changed manifest paths; PRSG-0 prefix-only activity remains labelled activity-only, not a completed ticket. Publish the generated JSON on every plan/code push using full checkout history; exclude generated output from source tracking to avoid self-referential commit hashes.

## Ownership and contracts

Lead: scripts/planning/build_ticket_audit.py, tests/test_ticket_audit.py, workflow/ignore/docs/skill instructions and ticket metadata. Engineer: artifacts/tickets/index.html and tests/ticket_dashboard_checks.cjs only. Audit schema1: repository_url, head_sha, generated_from committed-history, tickets array. Ticket: ticket_key,title,description,status,tags,created_on,updated_at,spec_url,completion_commit (object or null),progress {done,total},checks,acceptance,review,history[]. History entry: commit {sha,subject,committed_at,url},kind,paths,status,progress,checks,acceptance,review; immutable snapshots copied from that revision. Prefix-only ticket stubs use status activity_only; removed plans status removed. URLs use verified HTTPS GitHub repository, valid hashes and encoded paths; render all descriptions/evidence as text, never HTML. CSV formula-like values are neutralized. Labels explain that commit history is audit evidence, not test/factuality proof. Include CSV export and read-only page; do not add issue-tracker/cloud dependencies.

## Validation

Deterministic temporary Git repositories test creation/update/completion/prefix delivery/deletion, commit links, committed-only behavior, invalid JSON/malformed manifests, shallow clone rejection and CSV/UI unsafe text behavior. DOM/browser replay tests keyword/filter/sort and timeline/links; actual mobile viewport if available. Run full pytest, audit generation, ticket validation and scoped diff review. Completion requires accepted checklist evidence, not a commit alone. PRSG-1 remains in_progress until its own acceptance is recorded.

## When it's considered done

- [x] PRSG-8-D1: Committed progress and completion audit links preserve history and reject incomplete history.
- [x] PRSG-8-D2: Search/filter/sort/detail/CSV work with safe text and links on desktop/mobile.
- [x] PRSG-8-D3: Pages generates audit from full history on relevant pushes; workflow/instructions documented.
- [x] PRSG-8-D4: Focused/full tests and Lead review recorded; remote deployment state checked separately.

## Delivery evidence

Local functional delivery accepted2026-10-01 MYT. Full pytest146passed (five existing Python3.9/Boto3 deprecation warnings);23 focused Git-history cases validate progress/completion/base ancestry/Markdown evidence, shallow clones, invalid metadata, deletion/reopen/recovery and first-parent merge limits. DOM replay passes search/filter/sort/detail/CSV safety/JSON download against8 current records. Engineer actual browser1280x720 and390x844 confirms interactions, retained failed checkpoints and no mobile body overflow. Researcher independently reviewed completion integrity fixes and coverage labels. Source audit starts with committed scopecheckpoint bc06bc1; final commit's completion link is generated after commit, never self-inserted. Pages YAML/full-history checkout and planner skill validated. Git/specs/manifests are canonical; JSON is a generated downloadable view and CSV a flat convenience export. Invalid checkpoints remain visible as inconsistent and later fixes preserve history; shallow/corrupt Git reads fail. Remote deployment confirmation follows publication separately.
