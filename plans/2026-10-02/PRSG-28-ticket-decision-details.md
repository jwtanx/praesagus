# PRSG-28 — Ticket decision details

Type: feature · Modules: frontend, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-days) · Impact: medium

## Why the ticket is created?
The user cannot quickly understand why a ticket exists from its technical objective and test logs. They explicitly requested a simple expandable explanation in ticket details.

## Approach
Add a closed-by-default native details/summary disclosure titled "Why the ticket is created?" before current checks. Present plain-language purpose, team approach, choices/options, findings and tradeoffs/justification, plus safe source/spec links. Read only committed Git snapshots through the existing audit generator; never manually edit audit.json. Support an optional explicit structured decision context in committed manifests and conservative extraction of named Markdown sections for legacy specs. Missing reasons/choices/findings must be labelled not recorded, not fabricated. Existing objectives may be shown as recorded objective, not as proof of alternatives. Existing PRSG-27 must display its relevant objective/boundary and limitations without implying it forecasts prices. Handle Markdown-only spec updates so newest committed explanation appears; no live LLM summarization/network fetching of source contents.

## Choices and tradeoffs
1. Native details/summary: chosen for small accessible keyboard/touch disclosure, no new dependency.
2. External Markdown viewer only: existing spec link preserved, insufficient quick explanation.
3. LLM-generated rationale: rejected; introduces invented decisions, cost and privacy concerns.
4. Full Markdown HTML rendering: not required; safe text and validated links suffice. Preserve source wording; use concise explicit context where authored.

## Safety and scope
User refinement: keep the overview easy to scan with Why, Approach, Options, Findings and Tradeoffs/Decision. Preserve all existing detailed status metadata, checks, acceptance, review and commit timeline inside one closed-by-default parent disclosure titled "Technical details & audit history", retaining nested detail controls. Title and concise objective remain visible. The requested why disclosure may remain separately expandable; overview labels and brief summaries must be discoverable without digging through test logs. Test the parent collapsed state and retained inner history/evidence.

Frozen base9ba5bcf1cf29b8da35a150ecf8eb5859493a371c. Allowed only this spec/manifest, audit generator, ticket HTML and their existing two tests. Preserve unrelated .DS_Store. No skill/schema-wide migration or mass historical rewrites. External reference links must allow HTTPS only with no credentials, control characters or unsafe protocols; keep GitHub-only commit URL validation unchanged. Never insert untrusted HTML. Existing schema1 audits without context still load. Inconsistent/removed/activity-only records must not expose stale context as an accepted current decision. Distinguish recorded proposal from accepted approach.

## Tests
Real temporary Git fixtures: explicit context, committed-only/uncommitted exclusion, legacy Markdown extraction, Markdown-only update, missing context and malformed input. DOM: disclosure closed/toggle, headings/fallback, URL safety/XSS, old audits, mobile-friendly content, existing filtering/sorting/history/CSV regressions. Run frozen pytest and Node commands; report exact results. Lead accepts independently; Engineer no commit/push.

## When it's considered done

- [x] PRSG-28-D1: Ticket disclosure explains committed reasons and decisions with safe references or explicit missing-evidence states.

## Lead acceptance
2026-10-02 MYT Lead inspected complete six-path diff and independently reran45 audit tests (6.44s), dashboard DOM checks at1280/390 plus committed27-ticket replay, and fullsuite405passed (16.16s,5 existingBoto3/Python3.9 warnings). Closed disclosures preserve nested evidence; visible excerpts and missing fields are explicit; no HTML injection or inferred decisions. Browser visual QA and Pages deployment not verified.


## Engineer handoff evidence

Implemented committed-only optional `decision_context` authored fields `purpose`, `approach`, `choices`, `findings`, `tradeoffs` (text or lists of nonblank text), plus `references` objects with label/URL. Missing fields conservatively reuse recognized named spec sections; absent content stays not recorded. Explicit fields override legacy sections. Invalid optional structure creates a visible inconsistent checkpoint and clears stale current context. References allow public HTTPS without credentials, whitespace/control characters or backslashes; UI independently revalidates. No HTML/Markdown rendering or generated decisions. Manifest and Markdown-only checkpoints refresh explanation and retain historical snapshots. Removed/inconsistent/activity-only current context is suppressed.

Title/objective and five Why/Approach/Options/Findings/Tradeoffs overview fields are outside disclosures. Source excerpts are at most 240 characters and explicitly labelled when shortened; full wording remains in closed native Why disclosure. Existing metadata/checks/acceptance/review/timeline are retained in one closed Technical details & audit history parent with nested disclosures. Acceptance is distinguished from recorded proposal wording. Older schema-1 audits load with explicit missing-context states.

`python3 -m pytest -q tests/test_ticket_audit.py`: **45 passed in 8.36s**. `node tests/ticket_dashboard_checks.cjs`: **passed**, including 1280/390 DOM fixtures, source-text/URL safety, nested disclosures, visible excerpt/fallback and existing controls/history/CSV behavior. Additional generated HEAD integration: `python3 scripts/planning/build_ticket_audit.py --output /tmp/prsg28-ticket-audit.json` generated27 committed tickets at9ba5bcf; `node tests/ticket_dashboard_checks.cjs --audit-json /tmp/prsg28-ticket-audit.json` passed. PRSG-28 remains uncommitted and excluded from generated HEAD data as required. Engineer did not run the full suite or browser visual QA; Lead independently reported full-suite results separately.

Six exact owned paths validated; whitespace clean. All scope/base/check definitions and acceptance/Lead gates unchanged. No staging/commit/push, dependencies or historical migration. .DS_Store preserved. Handoff transfers these six paths to Lead for acceptance/integration; no further Engineer edits planned. Limits: unrecognized legacy headings remain not recorded, long wording requires disclosure expansion, unsafe source links remain plain text/are omitted as links. Recorded findings and review metadata are not independently proven by rendering.
