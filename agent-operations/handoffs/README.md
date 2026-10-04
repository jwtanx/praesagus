# Compact handoff files

Copy these templates into `/Users/jwtan/.codex/lead-state/` during an explicitly requested spawn; do not fill them with private state in the repository. The human-started current chat adopts its startup prompt plus a compact summary and links to canonical evidence, not a copy of full chat history. Aim for a few hundred words of narrative; preserve necessary dirty ownership and recovery detail even when longer.

| Template | Private destination | Purpose |
|---|---|---|
| [context.md](context.md) | transfers/TRANSACTION/ROLE-context.md | Accepted goal, decisions, evidence and exact next step |
| [roles.json](roles.json) | roles.json | Verified active peer identities and settings |
| [transfer.json](transfer.json) | transfers/TRANSACTION/receipt.json | Resumable migration phases and per-operation results |

Templates are empty examples, not an active registry or authorization. Populate actual IDs only from verified app evidence. Write the receipt before mutations and record/read back each returned ID or result immediately. Never overwrite unfinished transactions. Keep schedule backups separate/private and store their file paths and SHA-256 hashes in the receipt.

Use `null` for unknown, not guessed IDs/settings. In roles.json, an absent role is unregistered; an accepted-held role must not work. States: held, waiting, active, retired. `waiting` means takeover accepted but blocked on resources, human direction or a recorded dependency; it is not permission to resume. Preserve a retired source in receipts until schedule and archive results are reconciled.

Receipt phases: inventory -> checkpointed -> bootstrapped-held -> schedules-prepared -> cutover-verified -> accepted-held -> sources-retired -> released -> complete. Current-chat readiness/release is recorded by the adopting agent locally; do not message or wait on yourself. These are bookkeeping labels, not a transactional engine. Any failure records blocker, actual last successful operation and next safe step; retries inventory tools before resuming. For all, no requested source retirement or successor release until group cutover is verified. Keep schedules paused through release acknowledgment, then activate only originally active, eligible schedules. Complete can mean safe waiting/paused takeover; say so explicitly.

Read [transfer procedure](../../skills/spawn/references/transfer.md) for exact tool sequencing and legacy roles. Copying a template does not create chats, schedules or private state.

See [record fields](records.md) when filling JSON entries.

Use [message templates](messages.md) for checkpoint, held bootstrap, release and peer updates.
