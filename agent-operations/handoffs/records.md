# Private record fields

Read when populating registry or receipt templates. These are contracts for agent bookkeeping, not enforced JSON schemas.

## Registry roles entry

Key is Lead, Trader or Engineer. Fields: `thread_id`, `host_id`, `project_id`, `state`, `model`, `reasoning_effort`, `settings_verified`, `context_path`, `transaction_id`, `schedule_ids`, `pause_reasons`, `verified_at`, `verification_evidence`. For existing-chat adoption preserve verified settings; creation authorized by all omits unknown overrides; never claim requested settings were runtime-verified. IDs and timestamps must come from actual tool results and current time.

## Receipt roles entry

Key is the requested role. Fields: `destination_mode` (current-chat, existing-chat or new-chat), `source_thread_id`, `source_host_id`, `source_title`, `successor_thread_id`, `successor_host_id`, `client_thread_id`, `context_path`, `checkpoint_verified`, `source_idle_verified`, `bootstrap_ack`, `release_ack`, `state`, `rename_result`, `archive_result`, `schedule_transfers`. For no predecessor, source fields are null. Legacy Consultant/Researcher responsibilities have separate entries under `legacy_dependencies`, including continuing owner and retirement blockers.

## Schedule transfer entry

Fields: `source_id`, `source_target_thread_id`, `source_original_status`, `source_pause_reason`, `backup_path`, `backup_sha256`, `destination_id`, `destination_target_thread_id`, `destination_status`, `destination_verified`, `source_removed_or_reassigned_verified`, `confirmation_state`, `activation_eligible`, `activation_result`, `skipped_reason`. Store full supported restorable tool configuration in the private backup; include notification policy, rule/timezone, kind, target and any model/project/execution fields. Source ownership needs tool evidence, not a role-name match. Pending confirmation is a blocker.

## Operation log entry

Fields: `at`, `role`, `action`, `object_id`, `requested_change`, `result`, `readback_evidence`, `next_safe_step`. Record minimal non-secret evidence and private file references; preserve actual failures. After a crash, inventory actual objects before retrying an ambiguous operation. Completed rename/archive result must be backed by tool readback or an explicit unresolved verification limitation.
