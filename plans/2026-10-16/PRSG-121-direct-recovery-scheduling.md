# PRSG-121 — Direct Recovery Scheduling

Type: skill · Owner: Lead · Priority: P1 · Effort: XS (<0.5 person-days) · Impact: medium — avoid unnecessary approval cards for already authorized recovery.

Created 2026-10-16 MYT.

## Why the ticket is created?

The human explicitly reaffirmed that future resource recovery scheduling needs no additional confirmation. Earlier execution selected a suggestion card before attempting direct creation, leaving recovery inactive.

## Approach

Update the existing Lead skill to attempt direct anchored creation first under standing authorization, verify persisted state, and preserve resource, ownership and uniqueness checks. Resume existing accepted delegation when tools permit.

## Choices

Use the existing automation and messaging tools. A symlink cannot override a tool approval restriction. Fall back to a suggestion only when the tool explicitly requires that supported fallback; never treat a denied call as successful.

## Findings

Fresh readings showed 99% five-hour allowance, 37% weekly allowance and battery100% AC. Attempts to restore both existing Lead schedules and send Engineer/AI Engineer assignments were rejected by the app because approval was required while approval policy was never. No restoration or assignment was delivered. The expired recovery anchor must not be replayed. Skill wording is updated locally; operational recovery remains blocked on app tool permissions.

## Tradeoffs

Standing human authorization removes repeat permission requests but cannot override execution restrictions. Keep unrelated schedules, private data, accepted implementation scope and model gates unchanged. No shell or alternate-agent bypass is allowed.

## Frozen Scope

Lead owns skills/lead/SKILL.md and this spec/manifest at base 0e0c56c068fac1d4bb84bf2a7de23aa25509e2bb. Preserve all unrelated edits and PRSG-116 ownership. No scheduler implementation, authentication change or source activation.

## When it's considered done

- [x] PRSG-121-D1: Direct-create-first wording, metadata/references and resource regressions reviewed.
- [x] PRSG-121-D2: Eligible existing schedules restored and accepted delegation delivered, with actual tool evidence.

## Behavioral Replay

Already authorized recovery: attempt direct create before any suggestion; verify actual returned schedule. Explicit anchored-format fallback: one supported suggestion remains pending. Approval-policy denial: stop the mutation without shell/symlink/agent bypass and report the restriction. Expired anchor at human resume: skip it, refresh resources and restore only eligible original schedules. Actual restore/message denial replayed on 16 October; no success claimed. New anchored creation is not exercised because its old anchor expired and resources recovered.

## Recovery Delivery

After the human lifted session permissions, both original Lead schedules were restored ACTIVE and exact saved status, target, prompt, name and cadence were verified. Trader was unchanged. Engineer received the accepted news implementation assignment and AI Engineer received the disjoint read-only interface review. The expired recovery anchor was skipped. Resource regressions passed84checks and brief-quality checks passed13; metadata and local references were validated. New direct anchored wake creation remains untested, since no current recovery wake is needed.
