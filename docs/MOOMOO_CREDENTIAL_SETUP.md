# Moomoo AppKey and macOS credential setup

This guide matches the delivered PRSG-34 signer/loader and PRSG-37 manual private
collector. Follow it on your own Mac with developer-owned credentials. Setup and
live verification are explicit human operations; reading this guide or importing
the modules performs none of them. Keep keys, passphrases, account details and
private quote data outside Git, reports, screenshots, shared terminals and logs.

## Choose the implemented connection

The REST path uses an AppKey ID and an encrypted Ed25519 private key. It does not
use the OpenD desktop login, OpenD host/port, `PRAESAGUS_API_KEY` (the local FastAPI
key), or `VITE_API_KEY`. The [REST contract](MOOMOO_REST.md) documents signing and
transport restrictions. The OpenD setup in [README](../README.md) remains separate.

Moomoo currently recommends OAuth 2.1 + PKCE and documents traditional AppKey
signing as compatible. Praesagus implements the latter; it has no OAuth token
loader/refresh flow. The official [getting-started guide](https://open.moomoo.com/api/overview/getting-started)
directs AppKey creation through dashboard User Center, public-key upload and
algorithm selection. Choose Ed25519 for this loader; its signer rejects RSA.
These public instructions were checked on **2026-10-05 MYT**, without logging in.

## Prepare a new private directory and encrypted key

Use the project's supported Python >=3.11 environment with its declared crypto
dependency already provisioned. Do not improvise a package installation as a
credential troubleshooting step. Non-macOS secret stores require a separately
reviewed integration; there is no passphrase file/environment fallback.

Select an installed, trusted OpenSSL 3.x executable and check its version:

```sh
/absolute/path/to/trusted/openssl version
```

The path is a placeholder, not an assumed Homebrew location. Older macOS-supplied
OpenSSL/LibreSSL builds may reject `ED25519` as an unsupported algorithm. If that
happens, stop and arrange an approved OpenSSL 3.x distribution, then select its
explicit path. Do not switch to RSA or remove encryption to bypass the error.
OpenSSL documents [Ed25519 generation and cipher encryption](https://docs.openssl.org/3.0/man1/openssl-genpkey/)
and [public-key export/checking](https://docs.openssl.org/3.0/man1/openssl-pkey/).

The following is a **manual key-creation example**, not an offline test. Replace
both absolute paths first. Use a new directory outside the repository, cloud
sync and public serving trees; do not reuse another developer's keys. `mkdir`
fails if the destination exists, and shell redirections refuse existing files.
Run in a private interactive terminal without tracing (`set -x`), recording or
screen sharing. Enter a strong passphrase at OpenSSL's hidden prompts; never
supply it through `-pass`, shell arguments, environment variables or a text file.

```sh
(
  set -eu
  set -C
  umask 077
  prsg_openssl=/absolute/path/to/trusted/openssl
  prsg_credentials=/absolute/private/new-moomoo-credentials
  mkdir -m 700 "$prsg_credentials"
  "$prsg_openssl" genpkey -algorithm ED25519 -aes-256-cbc > "$prsg_credentials/private.pem"
  "$prsg_openssl" pkey -in "$prsg_credentials/private.pem" -pubout > "$prsg_credentials/public.pem"
  chmod 600 "$prsg_credentials/private.pem" "$prsg_credentials/public.pem"
  "$prsg_openssl" pkey -in "$prsg_credentials/private.pem" -check -noout
)
```

Successful `-check -noout` validates the local key; it does not establish portal
registration or entitlement. Never add `-text` or print the private PEM. If any
step fails, inspect only the failure category locally and preserve the partial
files until you decide how to recover; do not rerun over an existing key.

| Local item | Role and requirements |
|---|---|
| Credential directory | Canonical absolute path, current-user ownership, mode `0700`, outside repo/public trees; avoid symlinked parents |
| `private.pem` | Encrypted PKCS8 Ed25519 PEM, owned regular file, mode `0600`, no final symlink, at most 64 KiB; never upload |
| `public.pem` | Public half for portal registration; mode `0600` here; collector does not read it |
| `AppKeyID` | File containing only the issued ASCII AppKey ID, optional single final newline, mode `0600` (collector also permits `0400`); do not confuse it with an account ID |
| Login Keychain item | Stores only the private-key passphrase under the exact identifiers below |

## Register the public key and least permissions

Open the official [dashboard](https://open.moomoo.com/dashboard), sign in yourself,
then use User Center's AppKey creation flow. Upload **only `public.pem`**, select
Ed25519, and retain the issued ID using a local editor in the new `AppKeyID` file.
Avoid shell `echo`/`printf` commands containing the ID, and verify file permissions
without displaying contents. The collector accepts 1–512 ASCII letters, digits,
underscore or dash; its filename argument is explicitly `AppKeyID` in this guide.

The following are local permission recommendations, not a claim that today's
portal has identical labels or controls. Verify the actual options privately:

- Enable Market Quote reads needed for news/snapshots. Do not grant Trade
  Execution. Trade Query is optional for a separately approved account-read use;
  the delivered live transport and collector do not support account/funds/positions.
- If offered, restrict selected accounts to the approved account. Do not paste
  account identifiers into tickets. Leave optional Watchlist permission disabled
  for this workflow: treat it as potentially write-capable, not a read-only grant.
- Choose a bounded expiry and record a private renewal reminder. If optional IP
  allowlisting is offered, a stable reviewed egress address narrows access, while
  changing home/VPN addresses can interrupt reads. Do not broaden it blindly.

Public docs verified creation/algorithm/signing, but authenticated scope labels,
account selection, expiry and IP controls were not observed. If the portal cannot
provide the intended restriction, stop for review rather than assume a scope.
API access is not evidence of public redistribution rights or all-market coverage.

## Save the passphrase in the exact login Keychain item

Open **Keychain Access**, show its sidebar if needed, and select **login**, not
Local Items/iCloud or the separate Passwords app. Create a generic/application
password item (commonly File → New Password Item; labels vary by macOS). Enter:

| GUI field / item attribute | Exact value |
|---|---|
| Keychain Item Name / service | `praesagus.moomoo.private-key-passphrase` |
| Account Name / account | `praesagus-lead` |
| Password | The passphrase entered when creating this encrypted private key |

The account label is a fixed loader identifier, not a request to use Lead's
credentials or a macOS/Moomoo login name. All developers currently use these exact
labels in their own OS user's login Keychain. Review the saved item's Attributes
and kind without revealing its password. If the GUI cannot create this item type,
stop for platform review; an Internet-password item or a similarly named item in
Local Items will not satisfy the loader. GUI creation has not been exercised by
this documentation task; Apple's current [Keychain Access guide](https://support.apple.com/en-mide/guide/keychain-access/welcome/mac)
is the version-specific reference.

Do not run a standalone terminal password-retrieval command. The implementation
captures `/usr/bin/security` output internally with no shell, no stderr logging,
a bounded read and five-second deadline. It selects the current OS user's
`Library/Keychains/login.keychain-db` using the OS user database, not `$HOME`,
and requires the exact service/account above. Missing/locked/denied access has
no alternate Keychain search or plaintext fallback. Significant passphrase spaces
are preserved; only one final CLI newline is removed.

Start with **Confirm before allowing access / Allow Once**. Apple's [access prompt guide](https://support.apple.com/en-ie/guide/keychain-access/kyca1243/mac)
explains the difference between one-time and persistent approval. If explicitly
choosing unattended access, verify the requested item and executable before
Always Allow. This loader invokes `/usr/bin/security`, so approval can trust that
shared executable rather than only one Python script; other processes able to
invoke it may benefit. An unlocked login Keychain and a trusted local machine
remain assumptions. The five-second loader deadline or collector process deadline
can expire while a human prompt waits; repeated timeouts do not justify blanket
access.

Use the item's Access Control tab to review allowed applications and restore
confirmation/remove a trusted application when revoking unattended access, then
save the change. Do not choose **Allow all applications**, silently edit ACLs or
bulk-delete duplicate entries. Apple's [access-control instructions](https://support.apple.com/en-jo/guide/mac-help/kychn002/mac)
describe the item-level settings. Resolve duplicate matching items privately only
after identifying the intended key/passphrase pair and preserving recovery.

## Verify offline first; live reads are a separate manual step

From the repository root, these checked-in tests use synthetic files/keys and
mocked Keychain/network dependencies. They neither query your login Keychain nor
send provider requests:

```sh
python3 -m pytest -q tests/test_moomoo_rest_live.py tests/test_market_collector.py
```

The in-memory crypto fixtures are synthetic; skipped crypto tests are not proof
of signing. The signer decrypts the encrypted PEM in memory and retains the key,
not passphrase/PEM attributes. It signs locally; the request contains AppKey ID,
signature, timestamp and nonce, not the private key or passphrase. Python/OpenSSL
memory is not guaranteed zeroized; debugger/caller access is outside safe repr
and sanitized errors.

A **human-authorized live smoke test** uses the [manual collector](PRIVATE_MARKET_COLLECTOR.md)
after its private store already exists via the separate
[store setup](PRIVATE_MARKET_STORE.md). It makes real read-only requests and writes
private evidence/attempts. It is not a dry run. For the smallest snapshot-only
probe, prepare a nonsecret plan privately with the documented schema:

```json
{"schema_version":1,"codes":["US.SPY"],"news":[]}
```

After reviewing entitlement, scope, egress and private storage, invoke manually:

```sh
python3 scripts/market_collect.py \
  --root /absolute/private/existing-store \
  --plan /absolute/private/snapshot-only-plan.json \
  --credential-directory /absolute/private/new-moomoo-credentials \
  --app-key-name AppKeyID \
  --run-id manual-onboarding-unique-id
```

All paths/run IDs are placeholders; no secret value belongs in argv or the plan.
The collector uses canonical owned/private paths, loads `private.pem` plus the
explicitly named ID in its child, and invokes the exact Keychain loader. It bounds
worker I/O to 20 seconds plus cleanup; total admission/accounting budget is 300
seconds, not a hard SQLite/filesystem deadline. No scheduler or automatic retry
is configured. See the collector contract for full limits.

Review only controlled status/failure and requested coverage privately. Do not
print/query/archive account payloads into shared output, dump responses or publish
quotes. `success`, `partial`, `successful-empty` and `all-missing` are different
coverage states, not broad entitlement/freshness proof. No trade or watchlist
write is part of verification. This guide's author did not run any live probe.

## Troubleshoot without exposing secrets

| Symptom / controlled failure | Private checks and safe next step |
|---|---|
| `credential-unavailable` / collector `credentials` | Exact login/service/account/item kind, unlock state and denied access; GUI approval may exceed deadline. Do not print retrieval output or scan every Keychain. |
| `key-unavailable` / wrong passphrase | Owned `private.pem`, correct encryption/Ed25519, size/mode; re-enter intended passphrase locally. Wrong passphrase and malformed keys share sanitized failure. |
| Public-key mismatch / signature failure | Compare portal public key with a fresh public-only export derived from this private key using a new output filename. Compare locally without private-key text dumps; registration and pairing require manual verification. |
| Expired/revoked ID or permission rejection | Inspect portal status, expiry and least scopes privately. HTTP 401/403/provider failure does not identify the cause by itself; do not enable execution to troubleshoot reads. |
| Missing/all-missing quote or entitlement failure | Confirm requested US symbol and data entitlement; empty coverage alone does not prove an entitlement fault. MY snapshots are unsupported here. |
| Clock/signature error | Check OS time synchronization and matching registered key; core signs exact bytes. No automatic server-time correction or OAuth fallback exists. |
| Rate limit / `rate-limited` | Respect provider quota and sanitized Retry-After; no automatic retry. Local job/size caps are not provider quotas. |
| TLS/transport/deadline failure | Check trusted CA/runtime/egress privately; do not disable TLS verification, follow redirects or log headers to debug. |

## Rotate, revoke and recover

For routine rotation, pause manual consumers, prepare a separate new protected
key directory, register its public half with least permissions and update the
explicit local locator. The fixed Keychain service/account currently supports one
active passphrase selection per OS user: changing it can break old consumers.
Coordinate that change, preserve an approved encrypted recovery copy and privately
verify the new pair through the offline checks and authorized bounded live read.
Only then retire the old AppKey in the portal and remove its local key/item after
confirming it is no longer used. Do not delete a shared matching Keychain item
while another consumer still needs it.

If a key/passphrase is lost, create/register a replacement; an uploaded public
key cannot recover the private key. If compromise is suspected, revoke the AppKey
promptly before routine migration, stop consumers and arrange replacement. Local
file deletion or ACL revocation alone does not revoke the broker AppKey. Encrypted
backups need their own access policy; deletion is not a guaranteed secure erase
on SSDs/backups. No deletion, ACL changes or rotation was performed for this guide.
