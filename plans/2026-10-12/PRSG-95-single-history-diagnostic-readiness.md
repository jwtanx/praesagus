# PRSG-95 — One prospective history diagnostic and readiness assessment

Type: spike · Modules: financial-data, market-research · Owner: Trader · Priority: P1 · Effort: XS (0.1–0.2 person-day estimate) · Impact: medium-high — narrows the observed history intake blocker without exposing rejected data or claiming forecast precision.

Created 2026-10-12 MYT. Status: in progress, accepted continuation of the human-selected bounded forecast-input readiness. Frozen base: `b6592257843e35c8017641dfcb5cf4e81d388b1d`. Lead accepts scope and findings; Trader owns financial/access assessment.

## Accepted boundary and timebox

PRSG-94 safe diagnostics are independently accepted, pushed and Pages/ticket delivery verified. Within 15 minutes execute exactly one existing collector invocation containing exactly one US.SPY history job, end2026-10-09, ktype2, autype0, num100; codes/news empty. No start, pagination, extra snapshot/news, extended-time override, retries or follow-up calls. Existing request timeout10s, worker20s, bounded cleanup and run admission300s remain. Reuse existing approved private store and credential/Keychain loader, runtime and operational locators; no replacement client/script, secret-read preflight or secret output. This separately frozen ticket permits that single new attempt under selected readiness work. Stop after any result/error; further requests or repairs need separate accepted scope.

The exact private plan, byte hash, invocation argv/cwd and unique run ID are frozen in Lead private evidence before dispatch. Invoke existing scripts/market_collect.py --diagnostics from the isolated reviewed checkout with approved Python>=3.11 and existing nonsecret locator reference. Record actual access reached yes/no/unknown and distinguish code-path evidence from OS audit. Expected loader uses credential files and login Keychain; disclose actual use in handoff. Lead does not access secrets.

## Evidence and financial gates

Save only bounded CLI schema_version2 summary, exit code, plan/base/runtime hashes and actual launch/completion time bounds in private0700/0600 evidence. With authorized existing-store readback reconcile this run's immutable attempt/accepted rows, receipt/ingestion/known times, accepted count,21-session coverage, reference, raw_hash/archive state and adjustment. Do not retain rejected bodies or dynamic exception/provider messages. No input key/value, row index, private locator/ID or raw provider data in public ticket/report. HTTP200 inferred from recognized stage/frame is code-path evidence if no stored field; CLI itself has no HTTP/timestamps/counts. Stage is ephemeral and cannot reconstruct PRSG-90.

Expected21 distinct completed sessions: Sep11,14–18,21–25,28–30; Oct1–2,5–9, yielding20 adjacent returns. Candidate reference Oct9 regular close; scheduled Arca16:00EDT/20:00UTC is not proof of finalized returned close. Verify positive finite unique ordered expected closes with exact code and date/time_key/explicit offset. Request100/exit0/empty/partial is not coverage evidence; zero accepted is not provider zero-return evidence.

Freeze new collection vintage as actual Oct12MYT-or-later availability; never backfill Oct11 08:06:54 cutoff or revise frozen forecasts. Bar date is not first publication/finality. Unknown provider units/currency, session/finality, rights, authenticity, corporate-action basis and availability remain explicit. ListingUSD is not returned-row currency proof. Separate collector outcome, session/reference coverage and research target readiness verdicts.

Autype0 is unadjusted; the archived baseline uses adjusted20-log-return history and this window spans Sep18 ex-dividend. Passing intake cannot establish comparable adjusted inputs. No inferred dividend correction, method promotion, targets/direction/confidence/calibration claim. Keep current reports Unrated/null where unsupported.

## Ownership and protection

Trader repository write set is empty. Only Lead edits this spec and manifest. Approved private evidence and normal existing private store writes are allowed; no credentials changes, repository code/tests/report/ledger/calendar edits, dependency, client, script, subagent or live execution/trades. Preserve unrelated primary projection and all protected paths. Findings must distinguish reported from independently verified evidence. Valid existing raw responses stay only in private store under its original controls.

## When it's considered done

- [ ] PRSG-95-D1: Exact one-job plan/runtime/bounds validated; one invocation result and actual access disclosure retained privately with no retry.
- [ ] PRSG-95-D2: Separate diagnostic, coverage/reference and target-readiness verdicts with frozen timing/adjustment and explicit unknowns.
- [ ] PRSG-95-D3: Lead independently reconciles sanitized evidence, preserves protected paths and accepts/delivers findings; no forecast performance claim.

## Checks and delivery

Manual frozen-plan validation, one-call evidence, financial gates, preservation and Lead review. No new code tests required. Mandatory ticket validation/commit hooks remain. A failed probe can complete this assessment with blocked readiness; it does not prove integration or forecast success. No further request authorized by completion.
