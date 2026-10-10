# PRSG-85 Document safe Moomoo access for agents

Type: docs · Modules: docs · Owner: Lead · Priority: P1 · Effort: XS (0.05–0.1 person-days) · Impact: medium — avoids repeated access-method confusion without exposing operational secrets.

Created2026-10-11 MYT. Human requested a public-safe README explaining configured AppKey access and Keychain use. Lead owns README/spec/manifest only; preserve credentials/private state/code and unrelated projection edit.

Explain gateway-free REST versus OpenD SDK login, existing provisioned AppKeyID/encrypted key/passphrase boundaries, reuse existing credential loader, sanitized diagnostics, and privately supplied locator. No real values, private paths, usernames/account identifiers, request headers/signatures/provider bodies or secrets. AppKeyID is protected-file content; Keychain stores private-key passphrase, not AppKeyID. Document dated bounded authentication/history verification and unresolved indicator mapping without general reliability/entitlement claims. Existing credential onboarding remains for new setup; never regenerate/rotate existing keys merely to troubleshoot.

## When it's considered done

- [x] PRSG-85-D1: README accurately describes both access methods and existing loader reuse with valid local documentation references.
- [x] PRSG-85-D2: Lead reviews complete owned diff as public-safe; no actual secrets/private operational locations exposed.

Lead review: Lead reviewed complete README/spec/manifest diff against existing load_credentials/keychain_passphrase code and prior sanitized live evidence; linked credential/collector/REST docs exist. No secret retrieval performed for documentation. Added text contains no actual keys/passphrases/private locations/usernames/account IDs/provider payloads.
