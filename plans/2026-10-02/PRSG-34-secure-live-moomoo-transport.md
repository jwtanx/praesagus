# PRSG-34 · Secure private live Moomoo REST signer and transport for bounded quote/news reads

Type: feature · Modules: connectors, financial-data · Owner: Lead · Priority: P1 · Effort: S (0.5–2 estimated person-days) · Impact: high

## Why the ticket is created?

Human reports missing quote/direction evidence and oversized TA controls on October 2. Improve readability and validated data access without manufacturing forecasts.

## Approach

Reuse PRSG-31 injectable core. Add Ed25519 signer with encrypted private.pem and passphrase retrieved in memory from exact login Keychain service praesagus.moomoo.private-key-passphrase/account praesagus-lead. Private AppKeyID directory stays outside repository. TLS verified exact official host, no redirects/proxies by default, bounded timeout/response, no provider/secret logging, redacted controlled errors, no execution routes or mutations. Deterministic injected secret loader and HTTP tests first. Explicit human-authorized bounded live US snapshot/news probes only after offline tests. Store any live evidence privately, never public report/account fixture. MY symbol/entitlement and redistribution remain gates. No unattended ingestion schedule until validated. Existing cryptography availability is not a repository dependency declaration: document/install-compatible dependency choice if needed and seek accepted scope change before dependency file edits.

## Options and tradeoffs

Reuse current hosted chart and REST core rather than replace them. Compact visual controls retain accessible interaction size. Verified observations do not imply validated predictions. Private live access does not grant public redistribution rights.

## Findings

Current report has six quoted rows of fifty; targets remain unsupported. PRSG-31 core is offline-only. Authentication calendar probe succeeded, but quotes and MY access still require validation.

## When it's considered done

- [x] PRSG-34-D1: Offline security regressions pass, private bounded live quote probe outcome recorded without secrets, entitlement and data-rights limitations explicit.

## Progress

Lead accepted bounded manual reads after full code review, independent isolated202tests0.27s and private US.SPY quote probe. DNS/header hard deadline, Python3.11/fullPoetry, MY/news coverage and public rights remain gates; unattended ingestion and report integration are not delivered.

2026-10-02 09:32 MYT Lead review: accepted scope amendment adds pyproject.toml and requirements.txt for cryptography declaration; no tracked Poetry lockfile found. Engineer may update those dependencies and validate in an isolated target-Python environment if available, without modifying system packages. Lead independently reran 202 tests (0.38s) on current Python3.9/cryptography49. A bounded authenticated US.SPY snapshot returned one row with price and volume present; no values or secrets printed/published. First probe had a local summary-shape error after the request; corrected summary and second probe succeeded. Full acceptance pending dependency validation and transport review; no unattended ingestion established.

Scope accepted by Lead from existing human authorization at base 52c60bb78e5d890b052151990a393aa581c3b4b1; implementation checks pending. Unrelated .DS_Store belongs to existing work and is excluded.


2026-10-02 MYT — Delegated Engineer completed only offline capabilities:
`connectors/moomoo_rest_live.py`, `tests/test_moomoo_rest_live.py`, additions to
`docs/MOOMOO_REST.md` and PRSG-34 evidence. Lead retains accountable owner,
integration, dependency approval and private live probes. No PRSG-33/other ticket
changes by this delegation, no actual credentials or broker/Keychain calls.

Added explicit injectable encrypted Ed25519 signer; exact login Keychain
service/account subprocess loader with bounded stdout/deadline/cleanup;
outside-repo owned private.pem read; direct verified TLS fixed-host quote/news
transport, no proxies/redirects/mutations, bounded socket/chunk reads and controlled
secret-safe repr/errors. Exact frozen command passed **198 tests in 0.32s**, no
skips (Python3.9.6/cryptography49.0.0 locally available). Real Ed25519 verification
uses only synthetic key material in memory; all external capabilities faked.

Dependency proposal sent Lead: pyproject.toml cryptography = "^50.0.2";
requirements.txt cryptography>=50.0.2,<51; approved applicable lockfile update.
No dependencies installed/edited. Python3.11/50.0.2 compatibility still requires
reviewed environment verification. Transport limits live capability to news and
snapshot reads; account/watchlist routes remain disabled by this capability.
Important gate: stdlib blocking DNS and trickled response headers are not subject
to hard total cancellation despite bounded socket operations/chunk deadlines.
CA trust includes local Python/OpenSSL configuration (no certificate pinning),
Python/OpenSSL key memory not guaranteed zeroized, parent directory races outside
file-level checks. These limitations are explicit in docs and require Lead review
before unattended use. Manual/live evidence and PRSG-34-D1 remain pending;
manifest ownership/status retained for Lead integration. No staging/commit/push.

Final offline regression run: **202 passed in 0.29s**, no skips. Added wrong-owner,
certificate-failure, body-chunk deadline and HOME-independent login path checks.
Exact Keychain home derives from current UID's OS user database, not environment.
All five delegated paths pass manifest/scope and owned whitespace validation.
Private live outcome, dependency declaration and target Python3.11 environment
checks remain reserved for Lead.

2026-10-02 MYT — Accepted dependency amendment completed by Engineer:
`cryptography >=50.0.2,<51` now declared identically in Poetry and requirements.
Official package metadata rechecked; stable50.0.2/Python>=3.9. No tracked lockfile
exists and none added. Python3.11 unavailable at standard explicit locations and
project venv; used bundled Python3.12.14 in a fresh outside-repo temporary venv,
installing only cryptography50.0.2, pytest8.4.2 and their small binary dependencies.
No global changes/full project/model installs. Exact frozen argv with venv-first
PATH: **202 passed in0.89s**, no skips. `pip check`, TOML parse and equal dependency
range validation passed. Target3.11/full Poetry resolution remain unverified.

Docs distinguish Engineer offline tests from Lead-reported independent202-test
rerun0.38s and authenticated US.SPY one-row probe (price/volume present; no values,
secrets or public data publication). They retain the first local summary-shape
failure and corrected successful probe, preserving evidence history. Engineer
performed no live calls/actual credential access. Timing/CA/memory/file-parent
limitations remain explicit. Seven-path scope and whitespace validation passed;
Lead final review/live/acceptance pending, no staging/commit/push.
