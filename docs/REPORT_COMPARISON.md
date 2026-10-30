# Compare saved reports and choose a chart

Open the Daily Market Brief viewer and expand **What changed? Compare two saved
reports** beneath the report summary. Choose an Earlier report and a Later report
from the saved-date index, then choose **Compare reports**. Both fields start
unselected; reports need not be on adjacent calendar days. Equal, reversed,
missing and unindexed dates cannot start a comparison.

The comparison is independent of the ordinary report date, section selector and
active chart. Its heading records both dates, revisions, exact original cutoffs
and links to both saved reports. Changing either comparison date immediately
clears the old results and requires another explicit comparison. Changing the
ordinary displayed report date preserves the chosen pair and comparison during
the page session. No comparison preference is written to local storage or a URL.

## What the comparison means

The view groups recorded differences into:

1. Coverage and watchlist membership, matched by market and ticker. Absence means
   “Not present — reason not recorded”; it never establishes a sale, delisting,
   cancellation or resolved concern. Quote coverage counts eligible saved point
   observations and unavailable observations per market, without computing price
   changes or returns.
2. Forecast records, using the same guarded prediction display as the existing
   viewer. Supported state, currency, target/range, target date, horizon, status,
   method, confidence/rationale, scenario, reference session, bull/bear cases,
   invalidation and recorded gaps are compared. Unsupported targets remain
   Unrated/unavailable. Original issue times stay visible as context; an issue
   timestamp alone does not produce a finding.
3. Public research text and recorded source-reference sets by the existing seven
   section IDs. Descriptions, titled cards/paragraphs, tables and notes retain
   complete compared text. Source URL/label sets are deduplicated and sorted;
   retrieval/provider timestamp noise is ignored. Text is whitespace-normalized.

The first group with differences opens automatically. Individual record
disclosures keep every complete Earlier/Later projection available without
forcing fifty full forecast records open at once. There is no first-five limit
or hidden omission. Each record links to its original report section.

Different saved daily forecasts are not automatically revisions, corrections,
market moves or evidence of accuracy. Counts describe changed records, not
independent new facts. Shared monthly calendar revisions are deliberately not
compared: a report date does not freeze the mutable calendar reference.

Missing/unsupported section fields are explicitly **Not comparable**, not zero
differences. Duplicate or malformed instrument identities make the instrument
comparison ambiguous; no first duplicate is chosen. An unavailable earlier or
later report yields an error with no partial comparison or fallback date. An
unchanged result means no differences in the supported compared fields, not
unchanged markets or complete source coverage.

## Static chart selection

In **Technical analysis**, search locally by ticker, company, market or an already
curated chart alias. A native Instrument select chooses a candidate; **Show
chart** commits that choice. Native keyboard exploration and search typing do
not reload the chart. Enter in the search field does not submit a chart.

The wrapping **Chart selected** line always identifies the active chart, even
when search excludes it. With no matches, Show chart is disabled while the
current chart and external fallback remain available. **Clear** restores all
report instruments and returns focus to search. A report-date change resets the
search/candidate and selects the first valid instrument from the new report.
Switching views keeps the same report's selection/search while tearing down and
restarting the hosted widget through the existing lifecycle.

Automatic tape movement, duplicate decorative choices, animation frames,
hover/contact tracking and idle resume have been removed. The existing curated
US/Bursa mappings, literal alias encoding, unknown-identity search fallback,
15-second widget timeout, stale-load guards, attribution and inactive-view/
destroy cleanup remain. A hosted frame does not establish data availability or
delay. Historical SMA evidence, timestamped quote direction and recorded forecast
direction remain distinct and are identified in selected-item context.

## Implementation and checks

The comparison has its own generation and AbortController, separate from report,
calendar and market-snapshot loading. Submission fetches only the two selected
indexed report JSON files. It never fetches their sources, a comparison calendar,
a provider endpoint or a model. Normal report/calendar/chart behavior remains
independent. Parsed report JSON is limited to 4 MiB of serialized content;
instrument sets are limited to 1,000 rows and research groups to 2,000 text parts
and 500 distinct sources. These are local comparison limits, not a streaming
network-body budget or a financial admission process.

Text uses the existing public presentation/HTML-escape helpers; source links use
the existing HTTP(S) safety helper and do not render unsafe destinations. No raw
report/private provenance object is dumped into the comparison. The original
saved JSON, index, forecast ledger, calendar, source and model files are unchanged.
The TradingView script's HTML cache key is derived from its SHA-256 bytes.

Focused commands (existing isolated `jsdom@26` dependency; see the test headers):

```sh
node tests/report_comparison_checks.cjs
node tests/ticker_tape_loop_checks.cjs
node tests/tradingview_checks.cjs
node tests/compact_report_viewer_checks.cjs
node tests/daily_report_viewer_checks.cjs
node tests/chart_asset_version_checks.cjs
```

The historical `ticker_tape_loop_checks.cjs` filename now verifies the accepted
static behavior, not removed motion. TradingView/daily tests retain financial
display, identity, source, calendar, error and lifecycle coverage.

The actual local preview compared saved 20 and 21 October 2026 reports: 50
instrument records have changed recorded coverage/rationale/scenario fields and
five sections have changed text. Membership and source-reference sets are
unchanged; no public numeric forecast is invented. Browser checks at
390/768/1440 found no page-level horizontal overflow, with stacked mobile pairs,
paired larger layouts, 44px controls, explicit keyboard chart commitment and
search/no-match/Clear context preservation. Screenshots and exact receipts stay
private outside Git. The hosted frame loaded during preview, while its data/
delay remained explicitly unverified. Native 200% browser zoom, a formal screen
reader audit and a usability study were not performed; viewport tests do not
substitute for them. Independent Lead/Designer review and publication/deployment
verification remain separate delivery stages.
