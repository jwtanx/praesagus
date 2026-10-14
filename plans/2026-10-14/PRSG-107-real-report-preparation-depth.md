# PRSG-107 Preserve full-report provenance through preparation

Type: bug | Modules: financial-data,market-research | Owner: Engineer | Priority: P1 | Effort: XS 0.2–0.4person-days | Impact: high — reusable CLI currently rejects normal real reports before preparation.

## Reproduction and expected outcome

Trader executed committed105CLI exactlyonce on real current-edition Oct14 template, paired evidence/admission omitted, owned0700parent/0600inputs. Exit1 private-input-invalid, no bundle. Universe/calendar passed; template _bounded depth8 rejected80leaves atdepth9 including .sections.outlook.items[0].paragraphs[0].sources[0].label. Even ordinary primary-source provenance triggers failure; neither source facts nor collapsed120rowaudit should be dropped to pass. Private receipt report-20261014-cli-execution/failure-analysis.json independently readLead.105388focused fixtures used shallow narrative and missed actual nested source schema. Preserve failed delivery evidence;105componenttests do not establish real workflow success.

Expected normal real50rowreport with sources and audit can prepare explicit withholding and pass authoritative fullpubliccompact validation; with eligible financial evidence can prepare numeric overlay. Every other49rows/provenance/quote/timestamps must remain unchanged. No new source/financial readiness inferred.

## Accepted frozen bounded repair

Eightpaths only, no artifacts/collector/credentials/skills changes. Separate report-template bound12depth from existing financial evidence/default8depth. Preserve value/string/finite/structure budgets and input2MiB/file/private/nooverwrite/paired guards. Proposed _bounded optional keyword max_depth default8 used onlyfor report-template12; allfinancialevidence/admission/defaultcalls remain8, universe/calendar remain8. Both CLI template read and pure helper template guard must use reportbound. No unbounded recursion, generalized permissive financialparser or provenance flattening. Engineer confirms smallest exactinterface before coding.

## When it is considered done

- [x] PRSG-107-D1: Real published report + source/audit structure reproduces old failure; separate exact bound accepted.
- [x] PRSG-107-D2: Fullreal-template CLI/helper succeeds with explicit withholding, depth13/oversize/nonfinite rejected; evidence9 stillrejects; fullsource/audit/otherrows preserve.
- [ ] PRSG-107-D3: Lead independently reviews all8paths/checks, delivers and Trader successfullyreplays actual committedCLI.

## Checks

Approved Python -m pytest -q tests/test_report_forecast.py tests/test_forecast_scenario.py tests/test_daily_report.py tests/test_daily_report_projection.py ; fullhooks. Use checked-in actualOct14report/currentuniverse/monthlycalendar as deterministic regression with original recorded issue/cutoff and no real provider access. Also deep primarysource paragraph in successful admitted-shaped numeric fixture; do not mirror implementation only. Ledger120 rows must stay intact. Successful real-source numeric issuance remains separate goal; explicit withholding is integration evidence only.

Base frozen f4fd317988dedfab2708c46bea231a95ce4b0884 after106independent761focused/2290fullhookpassed; exact acceptedinterface/scope unchanged.
Lead accepts private PRSG-107-interface.md exactly: _bounded keywordmax_depth choices8/12 only; constantreport12 CLI/helper only, allfinancial/default8; actualcommittedOct14report/universe-five/monthlycalendar read-only regression; D3requiresactualTraderreplay.

## Frozen exact interface and Engineer evidence

Lead accepted `_bounded(value, *, max_depth=8)` with only nonbool integer8/12 choices. Shared REPORT_TEMPLATE_MAX_DEPTH12 applies only to pure helper template and named CLI template loader; all financial/admission/result/row/universe/calendar/default calls remain8. No CLI depth flag. Existing scalar/string/node/pending/file/finite/private/paired/time/write/public-compact guards unchanged. Basef4fd317; eight107paths only, pre-existing Lead-owned108spec/manifest preserved/excluded.

Before repair, committed Oct14report replay reproduced `_bounded(report)==False`, CLI exit1/private-input-invalid/no bundle, original score audit120rows. After repair, authoritative full/public/compact validation and real private CLI return explicit withheld/count0 with original recorded issuance/cutoff. Sources/sections/120auditrows/input bytes/metadata/other49rows remain identical; controlled withholding only overlays SPY and reference count. Nested primary-source admitted-shaped fixture generates and validates without flattening sources. Depth12template accepted,13fails; depth9evidence/admission/universe/calendar/default bounds remain rejected. Oversize/nonfinite/duplicate/private-field/long-string/node-budget and all existing private/nooverwrite/paired regressions retained.

Approved Python3.11 focused four-file command: **411 passed in2.09s**, no skips. Full isolated `-m pytest -q --tb=short --maxfail=3`: **2313 passed,41 dependency deprecation warnings in42.24s**. `git diff --check` and complete eight-path ticket validation passed. No failing107test run; old real CLI failure reproduced before code and retained as regression/evidence. No artifacts/skills/collector/connectors/credentials/current private store changes/access. Primary protected projection hash remains b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f.

Independent Lead review, installed Git hooks/delivery and actual Trader committed-CLI replay remain pending. Successful withheld real-template preparation proves compatibility, not eligible source history, actual numeric targets or publication. No numeric/source admission fabricated.

## Lead code review checkpoint

Lead independently read all8paths and real9depth6742-nodepublicreport; focused411passed2.15s or current exactrun retained separately. Report-only12/defaultfinancial8, allvalue/privacy/fullcompactguards preserved. Actual committedTrader replay pending. D3 remainsopen untilactualTraderreplay, then separate acceptancecommit.
