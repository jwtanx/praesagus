# PRSG-48 · Correct US and Bursa chart identities

Type: bug · Modules: frontend · Owner: Engineer · Priority: P1 · Effort: S (0.5–1 person-day) · Impact: high

## Why
Human request11: MY chart links incorrectly use numeric broker codes; most US names also lack curated exchanges. Existing tradingview.js maps only7US symbols and guesses MYX numeric codes. Outcome: all50 current watchlist identities resolve to reviewed TradingView symbols without guessing unsupported rows.

## Approach
Use Researcher's official symbol-page verified30US/20MY allowlist. US: AMEX SPY/IWM; NASDAQ QQQ,AAPL,MSFT,GOOGL,NVDA,AVGO,WMT,TSLA,LIN; NYSE JPM,GS,V,TSM,LLY,JNJ,ABT,PG,KO,HD,MCD,XOM,COP,SLB,CAT,GE,UPS,FCX,NEM. MY mappings:0820EA F4GBM-EA;0800EA ABFMY1;1155 MAYBANK;1023 CIMB;0277 CLOUDPT;0259 SNS;0166 INARI;0097 VITROX;5225 IHH;5878 KPJ;4707 NESTLE;3689 F&N;5296 MRDIY;4715 GENM;6033 PETGAS;5681 PETDAG;5246 WPRTS;3816 MISC;1961 IOICORP;5285 SDG. Prefix MYX for reviewed MY identities. Evidence: official `https://www.tradingview.com/symbols/EXCHANGE-NAME/` pages individually checked by Researcher2026-10-03; symbol-page existence is not proof of hosted-widget data entitlement.

## Options and decision
Map every reviewed identity for external links and permit documented hosted-widget attempts with permanent external fallback. Do not promise successful MY widgets: loading iframe does not prove quotes/data. Unknown symbols use generic symbol search, never guessed numeric MYX or US exchange. Query encodeURIComponent once; literal widget JSON symbol remains unencoded. F&N must survive as MYX:F&N in JSON and MYX%3AF%26N in query. Keep provider attribution, delayed/current disclosure, generation/race/error cleanup and hosted timeout. No ticker-motion or report/forecast/data changes in this ticket.

## Frozen scope
Basec651ca72cd80fd0755377b4e64b6b4c86cc2cddc; exact4paths tradingview.js, existing tradingview_checks.cjs, this spec and manifest. Preserve all motion/lifecycle/safety tests; update only mapping/fallback expectations and add full50mapping/unknown/ampersand/hyphen regressions. Provider availability remains unverified until real browser review; no credentials or new dependencies.

## When it's considered done
- [x] PRSG-48-D1: Exact TradingView and daily viewer DOM regressions pass, all50identity/encoding and unknown fallback checks covered.
- [x] PRSG-48-D2: Lead independently accepts four-path implementation and explicit widget-availability limitations.

## Engineer evidence and limits
node tests/tradingview_checks.cjs passed with existing isolated jsdom26 runtime; /tmp/PRSG-48-ta.txt. All30US/20MY current universe identities checked against the frozen research allowlist; raw widget JSON and once-encoded external URLs, F&N/hyphen, unknown/prototype/cross-market search fallback and explicit unverified availability covered. Existing lifecycle/race/motion/held-contact/safety and embedded daily viewer regressions retained.
node tests/daily_report_viewer_checks.cjs passed; /tmp/PRSG-48-viewer.txt. No live widget/network/provider credentials used; these offline checks do not prove TradingView symbol-page availability, hosted entitlement, quote availability or data delay.
Mapped fallback labels show the named TradingView identity. Hosted attempts preserve a permanent external link; loading/frame-added messages explicitly leave data availability unverified. No changes to report/index data, forecasts, motion algorithm, provider timeout, credentials, dependencies or schedules. No commit/push. Lead independent review remains pending.

## Lead acceptance
Full four-path diff independently reviewed againstc651ca7; both exact node commands independently replayed with existing jsdom26 and passed. All50lookup values match frozen research allowlist; F&N/hyphen literal widget JSON and once-encoded URLs, unknown/prototype/cross-market fallback, existing lifecycle/motion safety retained. Accepted implementation. Live deployment, widget entitlement and quote/data delay remain separate checks; no actual market-data availability claim from iframe/test success.
