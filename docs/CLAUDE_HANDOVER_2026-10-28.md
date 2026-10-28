# Praesagus handover to Claude or the next maintainer

Snapshot: 28 October 2026, Asia/Kuala_Lumpur. This is a factual restart document, not a completion claim. The human requested this handover and continued work toward usable reporting and batch prediction. Read `AGENTS.md`, the referenced canonical ticket pairs and actual implementation before changing anything. Canonical manifests and Git outrank this snapshot.

## What the user actually wanted

A human runs one documented command and receives a current, attributable prediction CSV in one batch. The requested products include the fixed 50 US/Malaysia names and a separate US100 universe. The 28 October 23:59 MYT deadline is real; an intermediate trained model, partial file, synthetic test or expired forecast does not satisfy it. The user also wants useful daily reports, visible source/freshness/failure states and a team that finishes without repeated prompts.

**At this snapshot the full requested outcome is NOT delivered.** The 28 October 21:30 MYT first-open cutoff for the last frozen US30 inference plan passed without a fresh 120-key CSV. PRSG-153-D3 remains unfinished. Do not backdate a run, relabel historical outputs as current, silently roll dates, lower coverage or call an uncalibrated research model a validated model.

## What is actually usable or verified

| Item | Evidence and limit |
|---|---|
| Existing script pipeline | `scripts/stock-research/run.py` shares a generation across collection, saved-model inference, evaluation and CSV/XLSX export. It does not train automatically. `demo.py` is fictional and cannot count as live delivery. See its README and tests. |
| Historical fixed50 delivery | PRSG-141 actually produced 50 ordered rows: 35 numeric, 15 withheld, zero demo; 22 raw-H1 and 13 cash-return-H1 baseline scenarios. The common reviewed window expired 27 October 17:00 MYT. This proves a past operation, not ongoing freshness, full50 coverage or AI quality. |
| Historical AAPL/SPY model delivery | PRSG-150 trained a new research model and produced eight horizon rows, all NO TRADE and uncalibrated. It is distinct from the baseline output. The original first-open windows have elapsed. |
| Full US30 research model | PRSG-153-D1/D2 independently accepted: 30 names × 754 sessions = 22,620 source rows; 84,060 completed labels; nine HGB estimators; no-benchmark, unknown historical metadata. One actual fit, no tuning/refit loop. |
| Fit/resource evidence | Numerical fit 52.056 seconds; supervisor 113.266 seconds; maximum sampled aggregate RSS 367,542,272 bytes; one thread; zero retries; cleanup verified; both child and parent approval receipts matched. Sampled RSS is not a hard OS memory cap. |
| Model artifact | Private `~/.codex/lead-state/PRSG153/ai/models/2026-10-28_025833/`; model SHA `fc633c3cbfd46f5cafde3792db07b6fa6c8eaea8ec3d0d0c71d14fd5a3ba2b59`; contract SHA `50aff7d51f6b637516d50ae381993f374b7e8593a66e875be95304ecaaf5e169`. Lead receipt: `PRSG153/lead/final-fit-artifact-acceptance.json`. Model-known-not-before 1793127575377 ms UTC. |
| Full source backfill | PRSG-151 four additional series and PRSG-152 remaining24 completed. The six152cohorts used174requests total, zero retries, 18,096 unique code-dates, 144 five-date seams and10,800 exact field comparisons. Source readiness and model quality are different gates. |
| Refresh preparation | PRSG153/engineer completed offline packet; Lead independently ran70tests in4.05s and verified91pinnedfiles. It intentionally rejects the expired source window before worker/credentials/provider access. No actual fresh capture occurred. |
| Ticket pagination | PRSG-142 compact pager was implemented/reviewed; do not reassign the original “all pages shown” bug without reproducing a current regression. |
| Git delivery | Source/model records pushed as585af58/6caef53. Blocked public-report plan pushed asd9a3c64. All17localbranch tips matched GitHub after the last all-branch push. Historical branch pushes were not merges, deployments or evidence of current acceptance. Required main hooks:3,755tests passed,41warnings. New handover/recovery tickets may add later commits. |

The full30 model is **uncalibrated, unvalidated present-cutoff research**. Historical calibration rows and archived prospective outcome rows in its evaluation are zero; assessment is failed-or-insufficient. A successful fit does not demonstrate positive return, calibrated coverage, profitability, or an execution-ready signal. All outputs remain NO TRADE until the unchanged promotion gates and human review are satisfied.

## Immediate continuation: finish one end-to-end result

Continue [PRSG-155](../plans/2026-10-28/PRSG-155-next-reference-us30-batch-delivery.md). This explicitly dates the next run; it does not erase the missed PRSG-153 delivery.

1. Engineer prepares the new source packet in private `PRSG155/engineer`; AI Engineer prepares compatibility, inference and output checks in `PRSG155/ai`. Lead reviews the handoffs and owns integration and actual command verification. No shared writes and no more than two active workers.
2. Verify the latest 51 XNYS sessions ending 28 October, expected 18 August–28 October: 48 dates shared with training through 23 October, and three new dates, 26/27/28 October. Verify the calendar before releasing requests.
3. The new source-finality window is **29 October, 12:00 MYT to before 21:30 MYT**. No live calls before finality or after expiry. No implicit date rollover. Fresh resource checks, source-purpose review and a new finite release are required.
4. Keep the bounded source contract: one basic-info POST for 30 names plus 30 history GETs; 31 requests; 11,130 wire-row ceiling; 10-second HTTP timeout; three seconds between actual starts; 600-second operation plus two seconds for cleanup; zero retries; no other endpoints. Local ceilings do not prove entitlement or provider quota.
5. Review actual overlap, identity, unit, precision, adjustment and knowledge-time changes. Do not repair, rescale, average, drop required names or invent a returned currency. Admit the new inference dataset separately from the training dataset.
6. Run the accepted full30 model once, without refitting, under 60 seconds, 512 MiB sampled memory, one thread and zero retries. Verify both child and parent approvals.
7. Independently verify exactly 120 unique `(code, horizon)` keys, four horizons per name, actual coverage, numeric conversion, blank withheld cells with reasons, immutable output hashes, actual completion knowledge and future-window validity. Quantile crossings remain withheld; do not clip them or refit until the result looks better.
8. Give the user the actual CSV, hash and documented command. Run it from a clean working directory. Commit reviewed code and ticket evidence, push, inspect CI, and distinguish any actual deployment. Tests or a worker handoff are milestones, not completion.

### Durable user command

Inspect existing `run.py`, `predict.py`, `data.py`, `train.py` and `export.py` before adding code. Do not create another calculator or training stack. Engineer proposes a versioned reviewed-bundle schema; Lead reviews it before implementing `run_reviewed_batch.py` if needed. The command must validate hashes, source/admission/currentness, model compatibility and approvals, then use existing inference/export interfaces. Missing, stale, expired or partial inputs need an actionable error and nonzero exit. Never bake private paths or credential locators into code.

Existing generic pipeline syntax, requiring Python 3.11+:

```sh
python scripts/stock-research/run.py --offline \
  --state-dir /absolute/private/data \
  --model-dir /absolute/private/models \
  --model-folder /absolute/private/models/YYYY-MM-DD_HHMMSS
```

Those are placeholders, not a verified full30 command. Confirm the state and model contracts first. The expired command is archived in `PRSG153/engineer/command-proposal-EXPIRED-NOT-A-RELEASE.json`; do not run or hand-edit it. Emitting a CSV without valid fresh inputs does not satisfy the goal.

## All unfinished canonical work

Parents can remain open after a child delivered one historical result. Do not reopen completed children merely to create activity. This table covers every open canonical ticket at the snapshot; exact pending IDs follow it.

| Ticket | Remaining outcome | Actual blocker or gap | Suggested Claude action / owner |
|---|---|---|---|
| PRSG-153 / 155 | Current 120-key US30 model CSV and durable command | Original window missed; next dated refresh, financial review and inference pending | Engineer + AI; Lead integrates and verifies the actual command. Use the sequence above. |
| PRSG-135 | Final manual MVP and acceptance packet | Past 35-numeric baseline is not a current renewal, full50, full100 or strong validation; parent evidence is stale | Lead reconcile with actual 141/150/153 results and record the deadline miss. Attach only verified delivery. |
| PRSG-124-D3 | All 50 US/MY predictions | Past snapshot had 35 numeric baseline rows; missing MY source/action/unit/finality evidence remains | Engineer/Trader maintain a missing-ticker matrix and finish eligible independent work. Do not silently drop names. |
| PRSG-109-D2/D3/D4 | Complete research product, strong quality/hardware acceptance and realized outcomes | Pipeline mechanics exist; full product coverage and current bundle are not proven | Lead verify the clean-directory command; AI owns validation and outcome scoring. Close only demonstrated acceptance. |
| PRSG-113-D2 | Strong-model validation | Historical point-in-time availability and untouched holdout requirements are unmet; current backfills do not substitute | AI obtain genuinely qualifying archives or accumulate untouched prospective observations. Do not repeatedly fit the used holdout. |
| PRSG-138 | Public daily report with at least 35 eligible same-row pairs | Applicable public price/derived-forecast rights for US/MY are not demonstrated; current US-only public contract caps 30 | Lead/Trader establish actual permission or an explicitly permitted alternative, then verify the report, rendering, live delivery and schedule. No approval-flag shortcut. |
| PRSG-61-D4 | Sourced SPY/QQQ report forecasts and outcomes | Snapshot mechanics delivered; frozen horizon, outcome and abstention evidence pending | Trader + AI preserve immutable issuance and outcomes. Private collection is not public permission. |
| PRSG-63-D3 | One interpretable MY OpenD quote under the agreed test | Original provisioning/connectivity/login/entitlement contract unresolved; reconcile this old ticket with later MY REST experiments | Engineer inspect current operator state without exposing secrets. Only a separately authorized bounded read-only attempt; a quote is not training OHLCV. |
| PRSG-82 | Native Moomoo KDJ/MACD/Bollinger event counts | Native groups/counts lack established event/bar timestamps and equivalence; old SDK packing/login issues; close-price proxy was rejected | Engineer establish the current native contract, Trader defines exact event semantics, then build UI. Do not return to the rejected proxy. |
| PRSG-116-D2 | Sentiment calibration and incremental forecast benefit | News/RSS mechanics delivered; causal dataset, permissions, calibration and benefit not shown | AI freeze an admissible dataset and chronological ablation. Keep price-only fallback. Avoid unnecessary model calls. |
| PRSG-2 | Real run/freshness status for four financial scripts | Planned parent; SEC implementation exists on a separately pushed reconciliation branch, not accepted current main | Engineer compare branch with main and replay relevant tests before selective integration. Configuration is not operation. |
| PRSG-3 | Filing details and metric attribution | Acceptance not delivered | Engineer build a small accession/period/unit/amendment-aware vertical slice before UI expansion. |
| PRSG-4 | Authenticated versioned shared watchlist | Authentication, concurrency, persistence and reload acceptance pending | Engineer implement conflict/restart tests and one safe API/UI path. Do not use report names as a discovery universe. |
| PRSG-5 | Alert outbox, retries and delivery visibility | Transactional leases, restart behavior and actual delivery acceptance pending | Engineer use a fake receiver first; verify idempotency, leases and secret redaction before real notifications. |
| PRSG-154 | This handover | Documentation review and delivery | Lead verify every open ticket is indexed, links resolve and no secrets or false completion claims appear. |

## Separate unmet products and proposals

| Direction | State and suggested next step |
|---|---|
| Standalone US100 | Requested but unfinished. Separate 80-company/20-ETF discovery, not report-seeded fixed30. After one working batch, freeze identity, source, liquidity, issuer/ETF and currency coverage. Report names separately from horizon counts. |
| Full US/MY50 | Requested, not achieved by US30 or the 35-row baseline. Keep the 20 MY names explicit; require complete admissible OHLCV, action, unit, basis and currentness evidence per name. |
| Inari / BMS.0166 | Retained checkpoints leave ticker-specific access/current-action evidence unresolved. Inspect the exact endpoint, fields, response and rejection. Distinguish no quote access from insufficient daily history, missing OHLCV/action data or unresolved units/finality. Do not infer that all MY or all Inari data is unavailable. |
| CNN Fear & Greed | Proposal received, not adopted into the accepted model. Needs rights, historical availability and incremental chronological evaluation. |
| Sneaky Pivot | Unvalidated hypothesis. Needs formal rules, costs/fills, regime/event/risk filters and robust out-of-sample evidence. |
| Persistent OpenD ingestion | Roadmap only. Request-scoped quotes/news are not persistent streams. Freeze deduplication, revisions, availability, storage, quotas and reconnect behavior. |
| General research/answer harness | YAML is design-only. No hosted answer path, persistent trace or quality loop is established. Freeze evaluation cases and independent grading before runtime expansion. No autonomous production self-training. |
| Feature store, cloud deployment, SEC/QR/alerts/health | Mixed roadmap/planning. Compose/Terraform/configuration is not deployment proof. Choose one accepted vertical slice after batch delivery and require actual operation/release evidence. |
| Daily-report usefulness | User rejects current output quality. Schema-valid JSON is insufficient. Trader/Designer must inspect an actual dated report for coverage, freshness, sources, rationale, abstention and mobile/keyboard usability. Unsupported targets stay null/Unrated. |

## Exact canonical pending items

Each link points to the authoritative specification and manifest. The handover does not rewrite acceptance.

- **PRSG-2** (planned, Engineer): `PRSG-2-D1`, `PRSG-2-D2`, `PRSG-2-D3`, `PRSG-2-D4`. [Spec](../plans/2026-10-01/PRSG-2-connector-freshness.md) · [Manifest](../plans/2026-10-01/PRSG-2.harness.json).
- **PRSG-3** (planned, Engineer): `PRSG-3-D1`, `PRSG-3-D2`, `PRSG-3-D3`, `PRSG-3-D4`. [Spec](../plans/2026-10-01/PRSG-3-filing-evidence.md) · [Manifest](../plans/2026-10-01/PRSG-3.harness.json).
- **PRSG-4** (planned, Engineer): `PRSG-4-D1`, `PRSG-4-D2`, `PRSG-4-D3`, `PRSG-4-D4`. [Spec](../plans/2026-10-01/PRSG-4-watchlist-management.md) · [Manifest](../plans/2026-10-01/PRSG-4.harness.json).
- **PRSG-5** (planned, Engineer): `PRSG-5-D1`, `PRSG-5-D2`, `PRSG-5-D3`, `PRSG-5-D4`. [Spec](../plans/2026-10-01/PRSG-5-alert-outbox.md) · [Manifest](../plans/2026-10-01/PRSG-5.harness.json).
- **PRSG-61** (in_progress, Engineer): `PRSG-61-D4`. [Spec](../plans/2026-10-05/PRSG-61-trader-moomoo-market-snapshot-dashboard.md) · [Manifest](../plans/2026-10-05/PRSG-61.harness.json).
- **PRSG-63** (in_progress, Lead): `PRSG-63-D3`. [Spec](../plans/2026-10-06/PRSG-63-moomoo-opend-my-quote-feasibility.md) · [Manifest](../plans/2026-10-06/PRSG-63.harness.json).
- **PRSG-82** (blocked, Engineer): `PRSG-82-D1`, `PRSG-82-D3`, `PRSG-82-D4`, `PRSG-82-D5`. [Spec](../plans/2026-10-09/PRSG-82-per-ticker-moomoo-ta-counts.md) · [Manifest](../plans/2026-10-09/PRSG-82.harness.json).
- **PRSG-109** (in_progress, Lead): `PRSG-109-D2`, `PRSG-109-D3`, `PRSG-109-D4`. [Spec](../plans/2026-10-14/PRSG-109-stock-research-program.md) · [Manifest](../plans/2026-10-14/PRSG-109.harness.json).
- **PRSG-113** (in_progress, AI Engineer): `PRSG-113-D2`. [Spec](../plans/2026-10-14/PRSG-113-stock-research-training-validation.md) · [Manifest](../plans/2026-10-14/PRSG-113.harness.json).
- **PRSG-116** (in_progress, AI Engineer): `PRSG-116-D2`. [Spec](../plans/2026-10-14/PRSG-116-stock-research-sentiment.md) · [Manifest](../plans/2026-10-14/PRSG-116.harness.json).
- **PRSG-124** (in_progress, AI Engineer): `PRSG-124-D3`. [Spec](../plans/2026-10-18/PRSG-124-daily-per-ticker-scenarios.md) · [Manifest](../plans/2026-10-18/PRSG-124.harness.json).
- **PRSG-135** (in_progress, Lead): `PRSG-135-D2`, `PRSG-135-D4`. [Spec](../plans/2026-10-23/PRSG-135-october-forecast-mvp-release.md) · [Manifest](../plans/2026-10-23/PRSG-135.harness.json).
- **PRSG-138** (blocked, Lead): `PRSG-138-D1`, `PRSG-138-D2`, `PRSG-138-D3`, `PRSG-138-D4`. [Spec](../plans/2026-10-25/PRSG-138-daily-report-public-eligibility-recovery.md) · [Manifest](../plans/2026-10-25/PRSG-138.harness.json).
- **PRSG-153** (in_progress, AI Engineer): `PRSG-153-D3`. [Spec](../plans/2026-10-27/PRSG-153-full-us30-research-model-batch.md) · [Manifest](../plans/2026-10-27/PRSG-153.harness.json).
- **PRSG-154** (in_progress, Lead): `PRSG-154-D1`, `PRSG-154-D2`. [Spec](../plans/2026-10-28/PRSG-154-claude-handover-and-delivery-audit.md) · [Manifest](../plans/2026-10-28/PRSG-154.harness.json).
- **PRSG-155** (in_progress, Engineer): `PRSG-155-D1`, `PRSG-155-D2`, `PRSG-155-D3`. [Spec](../plans/2026-10-28/PRSG-155-next-reference-us30-batch-delivery.md) · [Manifest](../plans/2026-10-28/PRSG-155.harness.json).

## Candid retrospective

This was not one broken numerical model. Several independent failures accumulated.

**Outcome ownership failed.** Lead let a long sequence of successful subtasks replace the actual clean-directory command, current CSV and useful report. The full30 fit eventually succeeded, but its fresh inference window was missed.

**The critical path was discovered too late.** Source fields, action/price basis, rights, availability, model quality and publication were intertwined. Preparation repeatedly expanded before the smallest real end-to-end path was proven.

**Too much orchestration stayed private and manual.** Per-run wrappers, pins, receipts and approvals preserved integrity but did not become a stable user interface. Metadata checks consumed time without necessarily improving the report. Consolidate reusable interfaces and remove copied coordination; keep meaningful data and validation safeguards.

**Continuation was weak.** Work too often yielded at milestones or unchanged blockers instead of completing ready review, tests, integration, commit, push and command verification. A worker's final answer was treated too often as a stopping point. Save an exact next action and continue accepted work while resources permit.

**Resources were real constraints, poorly budgeted.** Weekly usage exhaustion and low battery interrupted execution. They did not prove every other task was externally blocked. Repeated polls, long context and many QA variants burned budget. Reserve capacity for integration, batch reads, reuse passed checks except required hooks, and keep unchanged notices quiet.

**Scheduling became confused.** Heartbeats consume AI and do not guarantee continuous execution. Original Lead heartbeats were paused and later removed during resource/battery limits. A later other-session project cron reused the same name/ID with a different target/configuration. Do not blindly restore duplicates or assume it is the original thread heartbeat. Verify ownership and actual configuration first.

**Status blurred different outcomes.** Baseline versus AI, 35 numeric versus full50, 120 horizons versus 30 names, private versus public, and training versus validated quality should have been separate from the first delivery. “No material change” obscured what was missing and why.

### Better questions and planning

Ask early only what materially changes the product: minimum first delivery (private CSV or public report), exact universe/horizon/timezone/coverage, acceptable prediction-quality evidence, applicable data rights/entitlements, and where existing operator provisioning is recorded. Once answered, do not repeatedly ask permission for routine authorized implementation, review or push. Read available evidence before asking the user to solve infrastructure details.

Then keep one accountable Lead, at most two active workers, one small vertical slice with a real command and output, acceptance before work, and an explicit dependency graph with time bounds. Review while workers continue disjoint work. Integrate and verify in the same run. A truthful failure file and actionable error are better than a green status without useful numbers, but still do not constitute delivery.

## Safeguards the successor must preserve

- Keep private data, models, credential locators and account payloads outside Git. Code-push authority does not prove provider redistribution rights. All-branch pushes did not publish `~/.codex/lead-state`.
- Preserve original values and failed attempts. JPM/ABT/PG/CAT/GE/FCX have observed cash-linked adjustments. The legacy `forward-excluding-dividends` token is a request/interface label, not proven dividend exclusion or provider formula. CAT's 26 October ex-date affected current-vintage history requested only through 23 October. Do not add another cash return.
- Native currency `None` remains an absent literal. Scoped USD interpretation has a separate later financial-knowledge clock. Never backdate it to price collection.
- Current backfills do not create historical point-in-time data. Strong PRSG-113-D2 retains its exact improvement, calibration, walk-forward, untouched holdout and sample requirements; inspect the ticket. The bounded archive search covered 23 files in three roots without a qualifying candidate. Do not repeat unchanged searches or use repeated fitting to conceal missing evidence.
- Old forecasts/models remain immutable. No clipping, fictional prices, demo relabeling, silent required-name omission, paid access, external contacts or live orders by implication.
- One-use dated approvals cannot authorize every future capture. An accepted model does not make an old forecast window current.
- Use Python 3.11+, versioned hooks and `validate_ticket.py` for every changed path. Run meaningful focused tests and required commit/push hooks. Inspect actual remote SHAs. Do not stage `.DS_Store`. Tests prove checked behavior, not financial forecast quality.

## Private restart pointers

On the existing host, `~/.codex/lead-state/current-released-execution.json` holds exact next actions and owners. `roles.json` and its transfer receipt identify registered roles. `PRSG153/lead/` contains dataset/model/refresh acceptances. `PRSG153/engineer/HANDOFF.md` describes the expired source preparation. `PRSG153/ai/FULL30_MODEL_FIT_DELIVERY.md` describes the actual fit. New155 work belongs in new disjoint directories.

These files are not automatically available on another host. Request an explicitly sanitized portable bundle, not credentials or full account captures, and do not pretend missing artifacts were inspected.

Suggested first instruction for Claude:

> Read this handover, AGENTS.md, PRSG-153 and PRSG-155. Verify current Git and source/model receipts. Continue one batch delivery with unchanged acceptance. Execute all ready authorized work and report the exact remaining dependency. Do not refit, publish private data, backdate or roll dates implicitly. Defer unrelated wishlist work until the end-to-end command is verified.

## Acceptance statement

This handover is complete when the open-ticket inventory matches the canonical registry, links resolve and there are no secrets or invented completion claims. The product is complete only when its actual accepted current output works. These are separate outcomes. The user is free to continue with Claude or another maintainer; this document must make that continuation possible.
