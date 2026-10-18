# Private Forecast CSV

This manual tool exports the reviewed private-purpose scenario API to local CSV and audit files. It never collects data, trains, creates admission, updates the dashboard or publishes a report.

**Private research only. The uncalibrated next-close model range is not whole-window intraday extrema or measured 95 percent coverage. Numbers are not executable prices or evidence of forecast accuracy.** The standalone 100-name trained forecasting objective remains separate.

Use the same approved Python environment as the calculation API. An operator must supply separately reviewed source/evidence and an admission whose `purpose` is exactly `private_research_only`. The required history-collection and private-retention permissions must be supported. Unknown public-derived rights stay unknown; this export never grants public use or manufactures a rights bridge. Digests and reviewer declarations do not independently authenticate source facts or authority.

## Singleton

The parent already exists outside every Git checkout/public folder, is owned by the current user and has mode0700. Input JSON files are owner-only0600 or0400 with no symlink components. Supply actual reviewed issuance and cutoff values; do not backdate a new observation.

```sh
python scripts/daily-market-brief/prepare_private_forecast.py \
  --evidence /absolute/private/evidence.json \
  --admission /absolute/private/admission.json \
  --issued-at 2026-10-18T12:00:00Z \
  --cutoff 2026-10-18T12:01:00Z \
  --output-parent /absolute/private/forecast-exports
```

The dates above illustrate syntax, not an issued forecast. Legacy schema1/2 evidence is SPY/US/USD only; generic schema3 binds its own exact ticker/market/currency. Singleton evidence must identify the instrument. A null admission yields an explicit withheld row. For missing evidence, use a batch entry carrying the intended identity.

## Batch

Use `--batch /absolute/private/batch.json` instead of BOTH singleton flags, retaining the explicit issuance/cutoff/output-parent options. Mixed modes fail before input reads. Batch exact schema:

```sh
python scripts/daily-market-brief/prepare_private_forecast.py \
  --batch /absolute/private/batch.json \
  --issued-at 2026-10-18T12:00:00Z \
  --cutoff 2026-10-18T12:01:00Z \
  --output-parent /absolute/private/forecast-exports
```

```json
{"schema_version":1,"items":[{"ticker":"1155","market":"MY","currency":"MYR","evidence":null,"admission":null}]}
```

This example intentionally withholds; it supplies no source evidence or admission. Each entry has exactly those five keys. Up to50 unique ticker/market identities are allowed, with supported US/USD or MY/MYR pairs. Evidence must match the intended identity and admission hash; legacy SPY and generic inputs cannot be cross-mapped. A non-null admission must carry explicit private purpose. Missing pair members yield reasons and blank numeric cells. Malformed/duplicate/unsupported/cross-bound entries abort before writes. An empty batch yields a header-only CSV and zero counts.

Batch total JSON is capped at2MiB/depth12 with existing finite-value/node/string limits; singleton evidence/admission retain the existing per-file2MiB/depth8 reader limits. Output files are each bounded to2MiB. Other source/calendar/action/availability/rights/method gates remain in the private core. A present file does not guarantee a generated number.

## Output and limits

A new `YYYY-MM-DD_HHMMSS` directory uses the **actual export creation time in UTC**, separate from input issuance/cutoff. A same-second collision fails, preserving prior bytes. The directory is0700 and these files are0600:

- `forecasts.csv`: identity/status/reasons, classification and `is_demo`, reference and target dates/prices, two-decimal display point/low/high, direction, method/observations, source/public-rights status and hashes. Missing numbers are blank. Text cells with spreadsheet-formula prefixes are apostrophe-escaped; real numeric negatives remain numeric.
- `private-audit.json`: full-precision private API results and provenance, per-row original evidence/admission/result digests, issuance/cutoff and counts. Raw provider responses and the original evidence/admission bodies are not copied. Input digests use sorted compact ASCII JSON, so they bind the parsed values, not input-file whitespace.
- `manifest.json`: purpose, UTC creation time, model/source limitations, input digest, counts and exact CSV/audit file byte hashes. Authored fixtures retain `fixture_only`/`is_demo`; a fixture export proves mechanics only.

No overwrites, automatic retries or mutable latest-model/report pointers are created. Writes are individually atomic and rolled back on ordinary write errors; the three-file bundle is **not crash-atomic**. Keep original source/admission evidence private and retain prior generations. Actual source admission, model quality, public rights and report delivery remain separate reviews.
