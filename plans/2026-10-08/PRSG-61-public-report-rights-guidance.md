# PRSG-61 — Align daily report workflow with public-data rights safeguards

Type: skill · Modules: skills, market-research · Owner: Lead · Priority: P2 · Effort: S (0.5–1 person-day) · Impact: medium; preserves private analysis continuity while preventing unsupported Moomoo snapshot fields from entering a public report.

Created 2026-10-08 MYT. This is a narrow follow-up because PRSG-44 is complete and protects skill files.

## Objective and boundary

Keep private Moomoo snapshot analysis from becoming an accidental public disclosure. Report research and validation may continue without waiting for a rights investigation. A public Pages report may contain Moomoo snapshot fields only when current operator-provisioned evidence explicitly covers the market, each field, public display, and redistribution. `rights_status: unconfirmed` is metadata, not permission.

No connector, report JSON, HTML viewer, publication, account, or provider changes are in scope. The October 8 report remains unchanged and contains no `public_snapshot` fields.

## Frozen scope

Base SHA: `14407bdb1df85044390083989400d56d51fb4961`. Write only `skills/daily-market-brief/SKILL.md` and this ticket's Markdown/manifest. All other paths are protected. Owner and reviewer: Lead.

## When it's considered done

- [x] PRSG-61-D1: Skill instructions allow private research to continue but condition public snapshot fields on explicit current rights evidence.
- [x] PRSG-61-D2: October 8 report passes public validation with no public snapshot fields; the existing colored viewer renders the schema-3 report and shared calendar.
- [x] PRSG-61-D3: Skill metadata and references validate; Lead reviews the final wording against AGENTS.md and PRSG-44.

## Evidence and limits

`python3 scripts/daily-market-brief/validate_report_json.py --date 2026-10-08 --public` passed. Browser preview at the local report viewer showed the October 8 schema-3 report with its existing colored layout; all 50 rows were Unrated with missing reference-price reasons. No public snapshot fields were present. The viewer HTML was unchanged. Both skill folders passed the bundled `skill-creator/scripts/quick_validate.py`; this verifies skill structure, not licensing or runtime enforcement. No rights evidence was supplied, so public Moomoo snapshot eligibility remains unproven and such fields must remain omitted.
