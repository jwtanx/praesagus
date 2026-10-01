# PRSG-20 — Report logo links home

Type: bug · Modules: frontend · Owner: Lead · Priority: P1 · Effort: XS (0.05–0.1 days) · Impact: low

## Reproduction and accepted fix

Click PRAESAGUS in the daily-report topbar: href ./ reloads the report directory. Expected: navigate to product landing page, preserving the GitHub Pages repository prefix. Change to ../; native link remains keyboard/touch accessible. No other navigation/data changes. Exact four-file scope and frozen base in sibling manifest.

## When it's considered done

- [x] PRSG-20-D1: Logo resolves to landing page with date query removed; desktop/mobile DOM regression and Lead review pass.

2026-10-01 MYT: node tests/daily_report_viewer_checks.cjs passed including desktop/mobile native-logo href and GitHub Pages prefix/query resolution. Lead reviewed four-file diff; git diff --check passed. Browser navigation/deployment not exercised.
