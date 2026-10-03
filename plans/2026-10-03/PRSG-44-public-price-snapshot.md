# PRSG-44 · Public price snapshot boundary

Type: feature · Modules: financial-data, frontend, harness · Owner: Engineer · Priority: P1 · Effort: S (0.5–2 person-days) · Impact: high

## Why the ticket is created?
Private quote drafts contain internal IDs and cannot be published wholesale. Human authorized daily price snapshots; raw/deeper data stays private.

## Approach and safeguards
Pure strict allowlist mapper converts one validated trusted-capture point to public_snapshot price-only, preserving actual source/observation/ingestion/known/cutoff timestamps, provider, fixed documentation reference, curated listing USD versus unknown provider currency/session/adjustment/prior close, caller-unverified capture and unconfirmed rights. Documentation URL is a reference, not the fetched response source. No volume, private IDs, raw data, account/credential paths or private_draft. No network, writer changes or automatic publication. Researcher overlays individual points onto an independently authored clean public template. --public validation rejects private structures recursively and unknown snapshot keys. Existing private validation remains available. Unknown provider units keep legacy numeric sort null; independent forecast fields are untouched. No currency conversion, return or license claims. Eight paths accepted by Lead at base 298a18f8de97b95fd7771c23ff640cb3a81b081c; report JSON, collector/connectors, skills and schedules protected.

## When it's considered done
- [x] PRSG-44-D1: Python mapper/validator/private orchestration regressions and DOM rendering/safety/legacy checks pass.
- [x] PRSG-44-D2: Lead independently reviews all eight paths and replay evidence.

## Integration API
map_public_snapshot(quote, cutoff, *, listing_currency) returns a fresh price-only dictionary; it never copies a report or changes forecasts. validate_report(path, report, universe_data=None, *, public=False) supports explicit public enforcement; CLI --public selects it. Researcher removes private draft/observed_quote structures and validates clean final report with --public.

## Engineer handoff evidence
Engineer exact declared pytest: 130 passed in 0.70s, isolated Python3.12.14/cryptography50.0.2; transcript /tmp/PRSG-44-tests.txt. Python3.11 not replayed.
node tests/daily_report_viewer_checks.cjs passed with existing /tmp/praesagus-viewer-test-deps jsdom26; transcript /tmp/PRSG-44-dom.txt. Public price-only display, fixed reference, safe escaping, no private IDs or volume rendered, sorting excludes unknown provider units, independent forecast and prior private/schema2/3 regressions.
Lead independently reviewed all eight paths: exact Python suite130 passed in0.73s on Python3.12.14; existingjsdom DOM checks passed. No live report publication proved. Public screening is explicitly invoked with --public, not automatically enforced by CI; it rejects known private keys recursively and secret-shaped data but cannot authenticate caller capture, prove licensing or detect every sensitive value concealed in authored prose. Clean template review remains required.
