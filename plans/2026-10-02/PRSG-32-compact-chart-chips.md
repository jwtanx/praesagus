# PRSG-32 Compact chart ticker chips

Type: feature · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.1–0.2 person-days) · Impact: low

## Why the ticket is created?

Human requested slightly smaller ticker chips without reducing touch usability.

## Approach

14px text,8px12px padding; retain44px minimum height and keyboard behavior. Existing widget and report data unchanged.

## Options and tradeoffs

Reduce text and horizontal padding rather than touch target height. No chart preset implementation in this ticket.

## Scope and progress

Base b11f8903d883f6df90e60f8eae54b01606d09a25. Small local implementation preceded metadata capture; scope reviewed before commit, not claimed pre-edit frozen. Preserve unrelated.DS_Store.

## When it's considered done

- [x] PRSG-32-D1: Compact style retains44px touch target and viewer regressions pass.

## Lead acceptance

Lead reduced chip typography to14px and padding8px12px, preserving44px minimum touch height. node tests/tradingview_checks.cjs passed including existing viewer replay; external scripts mocked, visual QA not performed.
