# Daily Report Publication

New or edited daily reports must pass two separate checks: the existing structural
validator and the fixed-universe publication gate. Publication requires at least
35 of the fixed 50 identities to have an eligible numeric current price and an
eligible numeric forecast on the **same row**. The denominator and threshold are
not configurable. Structural validation alone still accepts explicit missing data
and preserves historical archives.

The gate is implemented in `scripts/daily-market-brief/publication_gate.py`.
It calculates no new forecasts for delivery, collects no data, fetches no evidence
URLs, and grants no source rights. It replays the existing deterministic public
scenario validator against supplied reviewed evidence to verify the frozen values.
Reviewer declarations and matching hashes do not independently authenticate
source facts, licenses or reviewers.

## Local Publication Check

Capture the actual validation time in UTC; do not substitute the report's old
`metadata.as_of`. The CLI accepts a cutoff within five minutes of its current
clock as an operational anti-replay check. This tolerance is not a quote-age rule.

```sh
python3 scripts/daily-market-brief/validate_report_json.py \
  --date YYYY-MM-DD --public --compact --publication \
  --publication-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --publication-evidence-dir /absolute/external/private/staging
```

The date must already have a structurally valid report, universe, index and shared
calendar. The gate also enforces public/compact structural validation directly.
It reports a controlled error or eligible-pair count without printing private
input paths, values, provider responses, reviewer details or exceptions.

## Private Staging Contract

Staging is an explicit local or CI prerequisite, **not provisioned by this change**.
Keep it outside this checkout and uploaded public artifacts. Supply an absolute
directory without symlink components, owned by the process user, mode `0700`.
Each selected edition uses exactly `YYYY-MM-DD.json`, a regular owned file in mode
`0600` or `0400`, at most 2 MiB. Every component is opened without following links;
special files, duplicate JSON keys and non-finite JSON constants are rejected.

The file has exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `report_sha256` | SHA-256 of the exact dated report file bytes |
| `rows` | At most 50 distinct entries, each belonging to the fixed universe |

Each row entry has exactly `market`, `ticker`, `currency`, `quote`, `quote_rights`,
`evidence`, `admission`, and `result_sha256`. Missing entries contribute no eligible
pair. Duplicate identities and unrecognized entries reject the evidence bundle.

`evidence` and `admission` use the existing full **public**
`ingest.forecast_scenario.build_forecast_scenario` contracts. Private-purpose
admissions cannot substitute. Replaying with the report's original forecast issue
time and report cutoff must generate a result whose SHA-256 equals
`result_sha256`; hash canonical JSON with sorted keys, ASCII escaping, no NaN,
and separators `(',', ':')`. Applying that result with the existing
`apply_scenario_to_row` must leave the report row exactly unchanged. This binds
the method, confidence, narrative, reference, target, numeric values and time basis
without copying the private audit into public output.

`quote` has exactly these fields:

| Fields | Required binding |
| --- | --- |
| `price`, `currency` | Positive finite displayed `current_price_value` and admitted reference bar |
| `provider`, `source_field`, `source_url` | Existing admitted source/bar; source URL also appears in the report row's public sources |
| `session_date` | Latest completed regular session at the actual publication cutoff |
| `source_at`, `observed_at`, `ingested_at`, `known_at` | Aware ordered timestamps; known by the report cutoff; `source_at` equals the row's `price_as_of` |

The admitted venue calendar must cover publication's local date, contain a future
session and establish the latest completed session. The quote and forecast
reference must use that same session. No arbitrary hours-old heuristic replaces
this calendar check. Forecast issue and all input availability precede the report
cutoff, which precedes publication; the target close must still be in the future.

`quote_rights` is the existing **input** contract of
`ingest.daily_report_projection.validate_market_rights`, checked at actual
publication time for the row's market and fields `quote.price` and
`source.timestamps`. It requires explicit `public-website-display` and
`redistribution` uses, source evidence and unexpired verification. A truthy
`approved` flag, a receipt URL, or `public_derived_forecast` alone cannot replace
this quote-display permission.

## Current Source Limits

The existing quote-rights contract supports `moomoo-rest` and excludes MY. The gate
preserves that restriction. The fixed cohort has 30 US and 20 MY identities, so
**35 eligible public pairs are currently unattainable through these contracts**.
Publication is deliberately rejected until a separately reviewed source/rights
change supplies the missing supported coverage. This is separate from completion
of this enforcement implementation.

The allowlisted price-only `public_snapshot` retains unknown provider currency,
session and adjustment. It remains unsortable with null `current_price_value`;
this gate never promotes it to an admitted numeric price. Tests of the 35/34
aggregation boundary use fictional eligibility sets only. The actual rights
validator tests establish the 30-US ceiling, not a real 35-row public success.

## CI And Pages Selection

Both workflows retain full archive structural validation. CI uses the complete
push `before` commit or the PR base merge-base. Added/modified dated reports and
their market-snapshot companions are checked, including renamed destinations and
unindexed reports. New index entries and a changed `latest` pointer select their
referenced editions; label-only index edits do not reclassify archives. A changed
universe selects the latest report. A missing Git object fails closed.

Pages compares against the last successful `pages.yml` workflow commit on main,
obtained through read-only Actions run metadata. Thus a failed report publication
cannot be smuggled into a later unrelated deployment. The baseline query fails
closed on API errors; it does not fetch source evidence. Initial publication with
no prior successful run checks the latest edition. Manual dispatch also checks
latest, using the new actual cutoff. Unchanged expired archives are not all
re-evaluated at today's time.

The repository variable `PUBLICATION_EVIDENCE_DIR` supplies the explicit runner
path. Setting a variable does not stage, license or authenticate any evidence.
No secret, download, provider call or private artifact uploader is configured.
Missing or unavailable staging fails publication of selected editions; unrelated
deployments with no selected edition require no evidence. Private staging must
never be placed under the uploaded `artifacts/` directory or echoed to logs.

Passing this numerical gate does not establish rendered-chip/detail correctness,
forecast performance, calibration, source authenticity, deployed operation or
trading authority. The existing compact validation, human review and relevant
rendered UI review remain separate delivery gates.
