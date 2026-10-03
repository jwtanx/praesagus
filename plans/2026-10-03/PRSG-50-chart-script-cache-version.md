# PRSG-50 · Version the chart script cache key

Type: bug · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: XS (0.1–0.4 person-day) · Impact: high

## Why
PRSG48 live source matches deployed commit, but browser still ran old mappings after reload. Public script headers allow600seconds caching. Cache is a likely cause, not proven request trace. Users should receive the reviewed chart asset after deployment without needing manual hard reload.

## Approach and decision
Add deterministic content-derived query version to index's local tradingview.js script URL (SHA256 first12hex or full digest). New focused offline test derives the hash from actual script and asserts URL/version correct; this makes stale version fail whenever script bytes change. No timestamp/random/versionperload. Preserve relativefile/GitHubPages paths and no addednetwork/dependency. Existing TradingView DOM fixture injection must recognize the new exactversioned localscript, deriveactualsrc rather than weakening checks. Preserve safe literalwidgetdata/externalfallback and all priorlifecycle/motion tests. No changing tradingview.js/data/template/date/navigation in this ticket. HTML itself may stillcache; explicitlydo notpromise instantcachepurge.

## Frozen scope
Base42b375a71e1c471c87040f72a6d2a61dbd0dc3d7; exact5paths index.html, tests/tradingview_checks.cjs (fixturemoduleinjection only), new tests/chart_asset_version_checks.cjs, this spec and manifest. No overlappingreport/nav/chip/forecastchanges. Reportactuallivefreshnessseparatelyafterpush.

## When it's considered done
- [x] PRSG-50-D1: Hash-bound scriptURL test and existingTA/viewer/navigation regressions pass; missing/stale version rejection demonstrated with synthetic fixture.
- [x] PRSG-50-D2: Lead independently accepts exact5paths and cachelimitations beforeseparatecommit.

## Engineer delivery evidence — 2026-10-03

Status: review; D1 done, D2 pending independent Lead acceptance.

Index loads `./tradingview.js?v=8685023c6a03`, the first 12 hexadecimal characters of the checked-in script's SHA256. The focused test computes the digest from actual bytes, so future script edits require updating the URL. TradingView fixture injection derives the exact versioned local tag from HTML, asserts one match and substitutes the local code; all behavior assertions remain unchanged.

Commands run at repository root, Node 26.7.0 and existing isolated jsdom26, all passed:

- `node tests/chart_asset_version_checks.cjs` — `/tmp/PRSG-50-version.txt`.
- `node tests/tradingview_checks.cjs` — `/tmp/PRSG-50-ta.txt`.
- `node tests/daily_report_viewer_checks.cjs` — `/tmp/PRSG-50-viewer.txt`.
- `node tests/report_navigation_checks.cjs` — `/tmp/PRSG-50-navigation.txt`.

The initial unversioned URL failed the focused check (`/tmp/PRSG-50-version-before.txt`). Synthetic missing/stale versions, changed bytes with unchanged URL, incorrect relative path and duplicate scripts are rejected. No mapping, navigation, report/date/data, motion, dependency or credential changes. Tests are offline; cached HTML may still reference an older URL, and live delivery/cache behavior remains unverified. Changes are uncommitted for Lead review.

## Lead acceptance
Exact five paths independently reviewed; all four exact node commands above independently replayed and passed. Index changes only local asset query; TA fixture injection retains behavior assertions. SHA-bound stale/missing/changed-byte/duplicate rejection verified. Accepted implementation; live cache freshness and provider widget data remain separate checks.
