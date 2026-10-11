# PRSG-89 — Show one clear prediction chip per ticker

Type: feature · Modules: frontend, harness, skills, market-research · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day, estimate) · Impact: medium-high — directly addresses the human's repeated request for a simple direction, target and range display; adoption improvement is unmeasured.

Created 2026-10-11 MYT. Status: in progress; Lead accepted and froze this scope after the human requested continuation. Frozen implementation base: `f791145861698967df31861a326779417a6bb05c`.

## Human selection and problem

The human selected the recommended Single chip option on 11 October, using the 8 October report as the presentation reference. The current viewer shows separate unavailable indicator counts and a forecast chip, with target/range text outside it. The expected result is one general prediction chip per ticker, with supporting evidence available on demand. No provider branding appears in rendered report wording, including expanded explanations. This changes presentation, not financial forecasts or model policy.

PRSG-87/88 remain completed records of earlier accepted requirements. This ticket supersedes their chip presentation only; their provenance, accessible audit, collection reuse and final-validation safeguards remain. PRSG-82 remains blocked on its actual indicator contract and is not a dependency for this display.

## Exact display contract

- One interactive chip combines direction, target price and range. Example copied from the archived 8 October SPY row: `↑ Bullish · US$781.37 · US$764.19–798.94`. A visible adjacent line says `Target: 9 Oct 2026 · 3 sessions`. The historical report date stays visible; these figures must never be presented as a current forecast.
- Map recorded directions `up/down/flat/unknown` to `Bullish/Bearish/Sideways/Unrated`. Preserve the recorded direction, target numbers, units, target date and horizon. No quote-versus-close or indicator count derives or changes a prediction.
- An unavailable row reads `Unrated · target unavailable · range unavailable`, with `Target date unavailable` if unknown. No zero, empty range, invented date or inferred confidence. Partial malformed/unsupported numeric evidence must fail closed and expose the reason in details.
- Click, tap, Enter and Space open/close details. Show evidence confidence and reason, original issuance cutoff, reference date/value/basis, exact recorded method, horizon/target, bull/bear cases, invalidation, source links and missing/coverage reasons. Source links retain real destinations; raw stored provenance is unchanged. Use general link labels instead of branding in visible wording.
- Apply the same one-chip contract to compact and legacy reports. Remove the separate bullish/bearish observation chips and forced quote/SMA substitutes from the prediction column. Keep independently observed prices, calendar and full audit accessible. Confidence/reason move into details rather than becoming extra chips.
- At 390-pixel mobile width the chip wraps within its cell without clipping its contents or creating new page overflow. At 1280 pixels the target/range is readable. Keyboard focus and accessible names convey the direction, values, date and expansion state without requiring color.

## Approach and assignments

Engineer implements viewer and deterministic DOM regressions. After viewer review, Trader reviews the disjoint report-workflow wording and any latest-report narrative revision; Lead integrates those changes sequentially. No two owners edit the same file concurrently. The production forecast method, financial inputs, confidence values, forecast ledger and old report JSON remain immutable. A latest-report narrative revision, if needed, must keep its original cutoff and financial payload, record the actual revision time, and pass the final public/compact validation after the last write.

The accepted paths are in the matching manifest. The frozen base is the verified shared main revision above. Engineer owns viewer/tests and check evidence; Trader owns the disjoint skill/reference/latest-report narrative files. Lead retains final scope approval and integration. The existing unrelated `ingest/daily_report_projection.py` edit remains protected; do not stage, stash or reset it. Skill metadata/reference validation and replay must exercise missing history, agreeing quote proxies and archived rated data: the new UI must not invent or promote a forecast in any case.

## When it's considered done

- [x] PRSG-89-D1: Exactly one chip per ticker displays recorded direction, target, range and visible target date/horizon across compact and legacy reports; no visible provider branding or substitute signal counts.
- [x] PRSG-89-D2: Rated, flat, unavailable, malformed and escaped-text fixtures pass; real desktop/mobile and keyboard/tap checks confirm readable, accessible expansion and functioning filters/sort/pagination.
- [x] PRSG-89-D3: Report workflow and any narrative revision match the selected display; collector reuse, final validation, original financial values, provenance, history and ledger are preserved.
- [ ] PRSG-89-D4: Lead reviews every owned path, verifies checks and immutable payloads, records commit/push/deployment separately and verifies exact deployed revision before completion.

## Verification and delivery limits

Required checks are listed in the manifest and remain pending until demonstrated. Reuse `tests/compact_report_viewer_checks.cjs` for compact and legacy states and `tests/test_daily_report.py` for report contracts. Use the existing final public/compact report validator and real-browser checks, not only screenshots or builds. Before delivery run required hooks in an isolated checkout if the unrelated projection edit affects shared checks.

The 11 October report currently has 50 Unrated forecasts. UI work does not populate targets. Supported current targets require a separate bounded history/readiness review by Trader, then an accepted implementation contract. Reuse the existing collector; freeze reference, adjustment/currency, completed-session cutoff, forecast horizon and target venue/session before calculating anything. Unsupported markets remain explicitly unavailable. PRSG-81 research and PRSG-83 synthetic eligibility work do not prove predictive accuracy or constitute a live outcome pipeline.

No secret access, provider call, model replacement, outcome backfill, schedule activation or report-data rewrite is needed for this display ticket. The human explicitly resumed the quarter-hour schedule on 11 October; resource and two-idle-run guards remain active. The later precision phase requires prospective, chronological outcomes with leakage checks and separate direction/point/range metrics; no accuracy or calibration claim can be made from the UI change.

## Planning checkpoint

11 October evening: Lead inspected the viewer and existing DOM replay, audited PRSG-79–88 specs/manifests, and recorded the selected direction. The human authorized continuation and quarter-hour resumption. Lead froze the accepted scope; implementation and financial/workflow review are being assigned to the registered team. This is not delivered code or a completed ticket.

## Lead-approved scope clarification

11 October: inspected the wider `tests/daily_report_viewer_checks.cjs` replay and confirmed superseded quote/SMA label, separate forecast-element and branded benchmark assertions conflict with the selected shared compact/legacy presentation. Add that exact file to Engineer scope and its Node command as a required check for D1/D2. Replace only the obsolete presentation assertions with the one-chip contract; retain escaping, public-snapshot redaction, reference href, cutoff availability, archive notice, filters/sort/calendar and unchanged technical-view behavior coverage. Malformed legacy fixtures must be rejected or made eligible with explicitly complete synthetic forecast metadata; do not weaken missing-data safeguards. Frozen base, financial method, acceptance IDs and Trader paths remain unchanged.

## Engineer check evidence — 2026-10-11T19:06:44+08:00

The shared compact/legacy table now renders one native-details prediction chip and an adjacent recorded date/horizon. Confidence, issuance cutoff, reference, exact recorded numeric-method wording, bull/bear cases, invalidation, missing coverage and original source destinations remain accessible inside details. Display-only provider wording is generalized; meaningful source titles and news headlines remain. Invalid or unsupported numeric/unit evidence is Unrated with an explanation; no stored forecast is generated or changed. Historical USD/US$ and MYR/RM display units are preserved.

- `node tests/compact_report_viewer_checks.cjs`: passed, including compact and legacy fixtures at 1280/390 widths, malformed and escaped cases, source destination preservation, pagination/filter/sort, and all 12 saved reports. The 8 October SPY row retains US$781.37 / US$764.19–US$798.94 and 9 October / 3 sessions.
- `node tests/daily_report_viewer_checks.cjs`: passed. Obsolete quote/SMA/brand table assertions were replaced; privacy, calendar, cutoff, archive, filter/sort and unchanged technical-view checks remain.
- Approved Python `-m pytest -q tests/test_daily_report.py`: 102 passed in 0.12s.
- Final public/compact validator: passed for 50 forecasts, 65 calendar events and 12 indexed dates at report SHA256 `2dd9f21df648821bb1d2886648dcdd0749abf66141cb003ba14118f5262c5714`. Repeat after any subsequent report write.
- `git diff --check`: passed. Protected checkout paths have no frozen-base diff. Primary protected projection remains SHA256 `b9f307894a6038e350037adf21261919a961d61d5deed976a2ff3f042d37f89f`. Financial/numeric targets, confidence values, raw provenance, original cutoff and collection equal the frozen report; the other 11 report JSON files are byte-identical.

Initial replay failures exposed delayed explicit expansion-state updates and the archived MYR-prefix formatting; both were corrected and replayed. Test-only navigation inventory and visible-text extraction were also corrected to exercise every archive without treating script source or the word “futures” as visible provider branding. These intermediate failures were not acceptance evidence.

Lead's real 1280/390 browser, native Enter/Space/tap/overflow checks, Trader workflow review and final integration/delivery acceptance remain pending. No commits, pushes, provider calls, secret access, forecast-policy changes or broad hooks were performed by Engineer. Local preview is available on 127.0.0.1:8789 from this isolated checkout while the preview process remains running.

## Lead independent review checkpoint

2026-10-11T19:11:42.217595+08:00 — reviewed all8owned paths. Final compact/legacy/archive replay, full legacy/technical/calendar/privacy replay,102focused report tests, skill metadata/local references and final publiccompact report gate passed. Real1280Enter/Space and390mobiletap/aria/no-pageoverflow passed on archived and current reports. Final source-title repair retained meaningful headings and exact hrefs; obsolete hardcoded native-status prose removed. Financial payload/collection/originalcutoff/full120scorecard and other11reports/index/calendar/ledger/protected projection bytes preserved. Only60reviewed revision/prose/reason leaves changed in latest report. Saved08prompt now matches selected chip/finalcompact gate with sameACTIVE/target/cadence. D1–D3 accepted; D4/release remains pending mandatoryhooks, commit/push and exact deployed revision verification. No secret/provider access during this ticket.
