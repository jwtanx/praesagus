# PRSG-46 · Ticket dashboard overview and pagination

Type: bug · Modules: frontend, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: medium-high

## Why the ticket is created?
Ticket titles can repeat the leading ticket key because middle-dot headings are not normalized. Overview text is truncated and duplicated in a Why disclosure. The results list lacks pagination.

## Approach and safeguards
Normalize repeated leading matching ticket keys in generated/display titles, preserving original commit subjects/history and embedded/different ticket keys. Display every recorded Why/Approach/Options/Findings/Tradeoffs block safely and without truncation; missing fields remain Not recorded. Remove redundant Why disclosure, keep references below overview and committed references inside audit. Border/pad the existing Technical details disclosure. Show five tickets per page, descending key default, accessible controls, filter/search/sort reset and clamp pages. Keep CSV over all filtered tickets, not just the current page. Preserve audit provenance, historical evidence and safe URL/text checks. Six accepted paths frozen at 5e7ccc14eb368c14f349d78f6ee50e1324705da2; no reports, landing, TA, skills, schedules, credential or ingestion writes.

## When it's considered done
- [x] PRSG-46-D1: Focused audit-builder and desktop/mobile DOM tests demonstrate normalization, full overview, pagination, all-filtered CSV and retained safety/history behavior.
- [x] PRSG-46-D2: Lead independently reviews all six paths and accepts completion.

## Engineer handoff evidence
Engineer exact declared pytest: 70 passed in 14.91s on isolated Python3.12.14; transcript /tmp/PRSG-46-tests.txt. Python3.11 not replayed.
node tests/ticket_dashboard_checks.cjs passed using existing jsdom26 dependency runtime; /tmp/PRSG-46-dom.txt. Additional full-history audit generated outside repository at /tmp/PRSG-46-audit.json (45 committed tickets, base5e7ccc14); node tests/ticket_dashboard_checks.cjs --audit-json /tmp/PRSG-46-audit.json passed, /tmp/PRSG-46-generated-dom.txt. All45 titles verified no repeated leading key, historical subjects unchanged. Desktop/mobile full overview, safe references, border/disclosure, page reset/clamp/focus and all-filtered CSV regressions pass.
Initial DOM replay failed at a pre-existing stale landing Coming soon assertion; replaced it with current checked-in TA link and query-aware file target checks, preserving landing coverage without landing edits. Second replay exposed jsdom inability to resolve var() inside border shorthand; now verifies the parsed CSS border rule and computed padding. Failed transcripts retained at /tmp/PRSG-46-dom-first-replay.txt and /tmp/PRSG-46-dom-second-replay.txt. No Git history rewrite, generated audit tracked, report/landing/TA/schedule/skill edits, live credentials or commit/push. Lead review remains pending.

## Lead acceptance
Lead independently reviewed all six changed/new paths against frozen base5e7ccc14. Existing isolated Python3.12.14 replay of `tests/test_ticket_audit.py`:70 passed in14.69s. Existing jsdom26 runtime replay of `node tests/ticket_dashboard_checks.cjs` and `--audit-json /tmp/PRSG-46-audit.json`:both passed, including45 committed tickets. Title normalization affects display metadata only, not original Git subjects. Full overview text uses safe textContent; pagination retains all-filtered CSV, safe references and audit history. Unchanged landing coverage corrected to its current TA link. No protected-path edits. Independently accepted; Python3.11 and live Pages browser delivery remain separate, unverified checks at acceptance.
