# Migration messages

Use only during an explicit human spawn invocation. Fill concrete fields from verified receipt/context; these templates are not messages to send during skill authoring. Avoid private account data or raw logs. Each message includes transaction ID to prevent confusing a retry with new work.

## Predecessor checkpoint request

The human requested replacement of ROLE in transaction TRANSACTION. Please finish your current atomic step, then stop new delegation/edits and save a compact checkpoint at PRIVATE_CONTEXT_PATH. Include accepted goal/authority, ticket/spec/harness paths, HEAD, exact dirty-file ownership, commands/results, pending decisions and the next safe step. Confirm when idle and whether any schedules or collaborators remain in flight. Do not discard changes or start another task. The coordinator will verify takeover before renaming/archiving this chat.

## Existing destination bootstrap

You are the replacement ROLE for transaction TRANSACTION in the Praesagus project. Read ACTUAL_STARTUP_PROMPT and PRIVATE_CONTEXT_PATH; the coordinator also includes the actual startup prompt text and reviewed compact summary below. For the calling destination read/apply this locally and record self-readiness; do not message yourself. For another existing destination send this as an authorized bootstrap message. This template does not authorize chat creation. Peer identities and schedules will be verified before release. Remain held: do not edit files, delegate, publish, create/activate schedules or continue predecessor work. Acknowledge checkpoint read, role, pending ownership, held state and any material gaps. Acknowledge requested model/effort separately from anything you can independently verify. Human-authorized project coordination permits this acknowledgment and later peer handoffs; it does not broaden execution/publication authority.

Append actual startup prompt text and compact verified summary, not placeholder instructions or full conversation history.

## Release request

Transaction TRANSACTION has verified context/role cutover. Your verified role is ROLE; final peer map and private registry are at PRIVATE_REGISTRY_PATH, receipt at PRIVATE_RECEIPT_PATH. Predecessor state and schedule statuses are recorded there. Accept responsibility and acknowledge release. For the calling destination, record self-release locally instead of messaging/waiting on yourself. Schedules remain paused until the coordinator records this acknowledgment and activates only eligible originally active entries. Continue EXACT_AUTHORIZED_NEXT_STEP only after release; preserve human/resource pauses and owned-file boundaries. If blocked, acknowledge waiting with the concrete dependency. Do not set up duplicate schedules. A schedule trigger must check active role/transaction state and exit while held or retired.

## Peer-map update

The human-requested transaction TRANSACTION replaced REQUESTED_ROLES. Read the verified peer map at PRIVATE_REGISTRY_PATH. Use these IDs for future project handoffs; do not message retired predecessors or reassign their still-busy work. Preserve your existing scope and pauses. Report an ownership conflict to the coordinator rather than guessing.
