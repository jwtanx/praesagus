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

- [ ] PRSG-35-D1: Guide and README/REST links cover setup, safe verification, troubleshooting and access revocation without exposing secrets.
- [ ] PRSG-35-D2: Lead reviews guide against delivered loader and replays deterministic missing-item/wrong-passphrase cases; commands use placeholders and do not leak secrets.

## Progress

2026-10-02 MYT: logged as P2 from human request. Documentation implementation and onboarding replay pending. Estimated effort is an estimate, not measured.
