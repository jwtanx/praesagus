# Trader daily report

Daily at 08:00 MYT, attached to verified active Trader. Read its startup prompt and skills/daily-market-brief/SKILL.md. Prefer Sol 6.1 Low research subagents and Sol 6.1 Medium for Trader synthesis when available, but do not delay or skip report generation if those settings cannot be selected or verified; use the current supported model and reduce parallelism if needed. Preserve current report coverage, schema, primary-source checks, monthly calendar revisions, confidence and forecast scoring requirements.

Human publication restriction, 21 October 2026: work privately at 08:00, and post
only when at least 35 of the fixed 50 tickers have BOTH an eligible current numeric
price and a supported publicly admitted numeric prediction/range on the same row.
Verify actual rendered current prices and colored prediction chips with recorded
target date/horizon. Keep the full 50 denominator; missing/stale/expired/Unrated or
private-only outputs do not count. Below 70%, keep the edition outside public
artifacts, do not update reports.json/latest, commit/push/deploy or post it, and
continue authorized remedies/outcome review. Preserve old published reports.
No routine ticker-only report or repeated unchanged blocker notification;
scheduled unchanged insufficient coverage uses DONT_NOTIFY. The final public
compact gate remains necessary but currently does not enforce 70% mechanically.
Record unresolved matured forecasts and recheck timing privately when the edition
is withheld; notify only a meaningful change or required human action.

Forecast follow-through is a required completion gate for every run: audit all pending ledger rows whose target venue session has closed, including older unresolved cohorts. Obtain comparable final closes with verifiable source data; preserve URL, venue/listing currency, adjustment basis and timezone-aware `actual_available_at`, update the ledger, and run `harness/forecast_review.py` at the report cutoff. Do not score pre-close snapshots or silently defer mature forecasts. If a final close cannot be verified, deliver the exact blocked cohort/count, affected venues and source/data blocker, plus the next scheduled recheck. The run is complete only when every matured row is scored or explicitly surfaced as blocked. If the target session is still open, state venue-local close and next review timing. Deliver forecast status with the report findings so the human does not need to prompt for an update. This is an instruction for the existing daily schedule, not a continuous price-feed runtime.

Forecast direction must come from independently supported forecast evidence and
the admitted method. Quote-versus-close/SMA proxies and native counts must not
force direction or confidence, even when they agree, and cannot supply targets.
Retain available observations and their timestamps separately; do not invent MY
signals or use proxies to satisfy the publication threshold.

After the final eligible report write, run the committed local validator `python3 scripts/daily-market-brief/validate_report_json.py --date YYYY-MM-DD --public --compact` before delivery or publication; fix failures first. Verify deployment/live dated viewer before success claims. Report material failures or required setup; record actual execution time if late.

Preserve existing delivery authorization and scope from the verified predecessor configuration; migration does not grant broader publication permissions. Lead usage/battery recovery does not remove this schedule. Account exhaustion can still prevent execution; report unavailable evidence honestly.

At each report run, reuse `scripts/market_collect.py` with the verified Python3.11+ collector environment and privately configured existing store/plan/AppKey locator, following the report skill’s reusable REST intake steps. Do not regenerate provider-fetch/signing/Keychain scripts. Preserve truthful collection/cutoff times and missing coverage; the 08:00 wake does not establish pre-08:00 data availability. Use the normal dated report and allowlisted snapshot projection, not the separate private-draft runner. This instruction does not provision inputs or guarantee provider access.
