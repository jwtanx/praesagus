# PRSG-35 · Moomoo AppKey and secure Keychain onboarding runbook

Type: docs · Modules: docs, connectors · Owner: Lead · Priority: P2 · Effort: XS (0.2–0.4 person-days) · Impact: medium

## Why the ticket is created?

A new developer cannot reproduce the secure credential setup from checked-in documentation. docs/MOOMOO_REST.md describes the offline protocol but explicitly leaves credential loading and live transport as separate gates. Session knowledge must become a safe, repeatable onboarding guide.

## Approach

After today's accepted impactful delivery work, document the implemented PRSG-34 credential contract in docs/MOOMOO_CREDENTIAL_SETUP.md and link it from README.md and docs/MOOMOO_REST.md. Recheck actual implementation before documenting executable commands; do not describe planned features as working.

Cover:
- Official portal AppKey creation and public-key registration; Market Quote and Trade Query for reads, optional Watchlist permission including its write capability. Trade Execution stays disabled. Account selection, expiry, rotation and optional IP allowlisting tradeoffs.
- Supported OpenSSL/version check and encrypted Ed25519 key generation with interactive passphrase entry, public-key export and safe verification. Explain the older macOS OpenSSL/LibreSSL ED25519 error and a supported alternative without assuming a Homebrew binary exists.
- Private directory outside the repository, directory0700/files0600, AppKeyID/private.pem/public.pem filenames and each role. Use developer-local paths, not another developer's credentials. No overwriting existing keys, committed secrets, plaintext passphrase file or passphrase in shell arguments/history/environment.
- Login Keychain generic/application password via secure GUI, exact service praesagus.moomoo.private-key-passphrase and account praesagus-lead; loader identifiers must match. Explain login versus Local Items and avoid duplicate-item cleanup until the correct entry is safely verified.
- Retrieval occurs inside the loader without printing the passphrase; decrypt private key in memory, sign locally and send AppKey ID/signature, not private key/passphrase. Do not provide a standalone terminal command that prints the secret.
- Access Control: confirm each access versus Always Allow for a specific trusted executable/item; risks of other processes invoking that executable, unlocked-keychain assumptions, how to revoke trusted access. Never recommend Allow all applications or silently change ACLs.
- Redacted offline and bounded read-only smoke tests; missing/locked item, wrong passphrase, mismatched public key, expiry, scope, entitlement, clock/signature and rate-limit failures. No account/quote payload disclosure or trade tests.
- Rotation/revocation, lost-key recovery and safe deletion only after verification; API access does not authorize public quote redistribution.

## Options and tradeoffs

Encrypted private key plus login Keychain supports unattended local signing after explicit access approval while retaining encrypted disk storage. Prompt-every-time is safer against unattended access but unsuitable for unattended jobs. Unencrypted keys and plaintext passphrase files are not the recommended onboarding path. Platform support remains macOS-specific; non-macOS developers need a separately reviewed secret-store integration.

## Findings

Initial repository search found no complete AppKeyID/Keychain saving runbook. PRSG-34 is now delivered at068e679; existing REST documentation describes the live contract but is not a full GUI onboarding guide. PRSG-37 adds a manually invoked private collector atd399944. Final instructions must match these delivered interfaces. No real credentials belong in this ticket or documentation.

## Dependencies and sequencing

Deferred until today's accepted high-impact work is delivered or Lead explicitly reprioritizes. PRSG-34 provides the actual loader contract; PRSG-33 UI work must not be interrupted. This ticket is planned, not assigned for immediate implementation and not a new timed automation.

## When it's considered done

- [x] PRSG-35-D1: Guide and README/REST links cover setup, safe verification, troubleshooting and access revocation without exposing secrets.
- [x] PRSG-35-D2: Lead reviews guide against delivered loader and replays deterministic missing-item/wrong-passphrase cases; commands use placeholders and do not leak secrets.

## Progress

2026-10-02 MYT: logged as P2 from human request. Documentation implementation and onboarding replay pending. Estimated effort is an estimate, not measured.

## Accepted implementation scope — 2026-10-05 MYT

Lead reprioritized this existing human-requested documentation maintenance. Historical owner Lead; delegated writer Engineer. Frozen base `6d37934376c90da01334e3cf569ea8524eb16ab2`; accepted writes exactly the five manifest paths. All other paths protected. Implementation in progress; original creation date/key preserved. Official public source verification and mocked missing-item/wrong-passphrase replay only; no real credentials, Keychain/provider access, key generation, installs or trade/watchlist writes. No commit/push; Lead review pending. This assignment supersedes the earlier deferred sequencing note.

## Engineer documentation delivery — 2026-10-05 MYT

2026-10-05 MYT Engineer review: docs/MOOMOO_CREDENTIAL_SETUP.md covers explicit private paths/modes, encrypted Ed25519 PKCS8 generation with interactive prompts and no-overwrite redirection, public upload, exact login Keychain identifiers/access/revocation, offline versus manual live collector, failures and rotation. README/REST links added. Reviewed delivered loader, collector/CLI/private path checks and existing tests; all local Markdown file links resolve and actual changed paths equal exact five-path scope, git diff --check passed. Public sources verified: https://open.moomoo.com/api/overview/getting-started (OAuth recommended, compatible AppKey creation/public upload/Ed25519); https://docs.openssl.org/3.0/man1/openssl-genpkey/ and https://docs.openssl.org/3.0/man1/openssl-pkey/; https://support.apple.com/en-ie/guide/keychain-access/kyca1243/mac and https://support.apple.com/en-jo/guide/mac-help/kychn002/mac (prompt/access controls); https://support.apple.com/en-mide/guide/keychain-access/welcome/mac . Authenticated portal scope/expiry/IP labels and GUI item creation not observed; guide explicitly marks these limits and requires private verification. No real credential/Keychain/provider access, keys generated by author, installs, mutations, secret output, commit or push.

2026-10-05 MYT: PATH selects /Users/jwtan/.codex/venvs/praesagus-tests-311/bin (Python3.11.17); python3 -m pytest -q tests/test_moomoo_rest_live.py tests/test_market_collector.py at repository root: 160 passed in1.92s, no skips. Existing mocks cover nonzero/missing Keychain result, wrong passphrase, exact identifiers, cleanup, significant spaces and safe errors plus collector credential/path failures. Synthetic in-memory crypto and temporary fixtures only; no real credentials or provider calls. No full-suite or live-onboarding claim.

State: review; D1 evidenced, D2/Lead review pending. Historical owner Lead and creation date 2026-10-02 retained; Engineer delegated writer. Original deferred notes above are historical. Frozen base/accepted scope unchanged. No application/test edits or full-suite rerun. Live onboarding and authenticated scope controls remain manual unverified boundaries.

## Lead acceptance — 2026-10-05 MYT

2026-10-05 MYT Lead final acceptance: read new guide and all four tracked diffs; compared exact loader service/account, private PEM/Ed25519, REST transport and collector CLI/manual boundaries. Independently reopened official Moomoo getting-started and OpenSSL genpkey references; OAuth-recommended/compatible-AppKey distinction and separate OpenD login verified. Independent persistent Python3.11 focused python3 -m pytest -q tests/test_moomoo_rest_live.py tests/test_market_collector.py: 160 passed in 1.93s, no skips. Five-path scope and diff-check validation passed. D2 accepted without further guide changes. Authenticated portal controls, GUI creation and live entitlement remain unverified; no Engineer commit/push.

State: complete; historical Lead ownership and frozen base retained. Lead owns commit/push integration. Earlier pending-state delivery notes remain historical evidence.
