# PRSG-132 — Manual Private Forecast CSV Launcher

Type: feature · Modules: financial-data, docs · Owner: Engineer · Priority: P1 · Effort: XS (0.2–0.4 person-days, estimate) · Impact: medium — give the user a stable checked-in manual command for reviewed private inputs, replacing repeatedly assembled issuance/cutoff arguments.

## Why the ticket is created?

The user requests runnable scripts and a CSV. PRSG-127 already supplies a private CSV/audit exporter, but its CLI requires explicit issuance/cutoff timestamps and several long arguments. Actual per-name input review remains separate. This ticket makes that reviewed-input export easy to run again; it does not claim the standalone 100-name program or all fixed50 inputs are ready.

Success means one documented local command accepts two explicit paths, derives actual UTC issuance/cutoff once, delegates all calculation/admission/output guards to the existing exporter and reports generated/withheld counts plus the exact CSV path returned by the existing writer. Functional fixture tests measure that behavior; no time-saving estimate or numerical-quality lift is claimed.

## Approach

Add scripts/daily-market-brief/run_private_forecast.sh, docs/MANUAL_FORECAST_CSV.md and tests/test_manual_forecast_launcher.py. The shell command accepts exactly --batch REVIEWED_PRIVATE_JSON and --output-parent EXISTING_PRIVATE_DIRECTORY, plus help. Reject duplicate, unknown, missing or empty arguments before export. Do not add timestamp, provider, model, admission-creation or target-roll options.

Locate the checkout from the script so invocation works outside the repository cwd. Resolve one executable path from this checkout's git config praesagus.testPython; when unset, use python3 from PATH as the existing test hook does. Check Python >=3.11 before exporting. A configured unavailable/unsupported interpreter fails rather than silently falling back. Quote executable and path arguments as individual values, with no eval, shell command interpolation or word splitting. Preserve spaces and literal shell metacharacters in arguments.

Read datetime.now(timezone.utc) exactly once for issuance and cutoff and pass that identical aware timestamp to the existing exporter. Export bundle creation time remains the existing writer's actual clock, separate from issuance/cutoff; do not predict its folder from a previous clock read. Interpreter/process failures propagate nonzero; adapter errors retain the exporter's sanitized failure-stage JSON/nonzero semantics without exception text or input contents, while valid all-withheld exports retain success exit and counts. Missing/malformed input, expired targets, source/rights/calendar/action gaps and private-path/collision failures keep their existing withheld/failure behavior. Never rewrite inputs, roll a target, reseal admission, manufacture freshness or retry collisions.

### Selected Interface — Embedded Python Adapter

The original prepare_private_forecast.py main prints status/counts and deliberately omits private paths. tests/test_private_forecast_csv.py asserts that the private parent is absent from its stdout. Exact CSV path output is therefore not available by merely forwarding the unchanged CLI.

Lead selected this reversible design before implementation, within the three-file implementation scope: an embedded Python adapter in the launcher imports the existing exporter, reuses its descriptor-safe private reader, prepare_export and write_export functions unchanged, and prints the existing status/counts JSON shape with an additional csv_path from write_export's actual returned directory. It accepts batch mode only. This deliberately calls the existing APIs instead of main's argv CLI; Lead explicitly accepted that design choice on 21 October. Lead subsequently accepted the final five-path ticket scope and released implementation. Do not wrap or monkeypatch core functions, scan directories for guessed outputs, or duplicate calculation/admission logic.

Alternative: add an explicit opt-in output-path flag to the existing exporter CLI, preserving its default private-path omission. That would require a separately reviewed scope amendment to the exporter and its existing tests. A plain shell wrapper forwarding main preserves exact CLI behavior but can only show counts and the parent/pattern, not the exact created CSV path. Lead chose the unchanged-API adapter. The opt-in flag and counts-only alternatives are not selected; Lead subsequently accepted the five-path scope; implementation is released.

## Choices

Prefer a small checked-in launcher and manual guide over an ephemeral command, a second calculator or a capture/export framework. Reuse the git interpreter configuration instead of introducing another runtime selector. One actual UTC timestamp avoids independently sampled issue/cutoff values. Keep the original exporter and numerical/private admission core protected unless Lead explicitly approves the opt-in CLI alternative. The selected adapter returns the writer's exact path rather than inferring a UTC directory name across a second boundary. It calls private_io.read_private_json(batch, max_depth=12), prepare_export(payload, batch_mode=True, issued_at=stamp, report_cutoff=stamp) and write_export(output_parent, result), reusing existing parent/path and write validation. No runtime monkeypatching or duplicate calculator is introduced.

Document the stable command with quoted illustrative absolute private paths and no real account/credential paths. Explain existing owner0700 parent, owner0600/0400 input and no-symlink/outside-Git restrictions, batch schema/reference to docs/PRIVATE_FORECAST_CSV.md, generated/withheld counts, exact bundle files, collision/failure behavior and fixture-only evidence. Show the existing scripts/market_collect.py command separately with placeholders and its independent release/source-review requirements; the launcher never invokes it. Link scripts/stock-research/run.py and its README for the broader collection/saved-model inference/evaluation/export program, distinguishing missing-model/coverage limitations and training as separate work.

## Findings

At base a2884f525a59a97a3bd6a73bb48c01e2e1712048, highest canonical manifest ID is131;132 is unused. Compact active registry includes PRSG-109/113/116/124; none allows the three proposed implementation paths. PRSG-127 is complete and its exporter currently validates bounded reviewed batches, private descriptors/permissions, calculation gates and immutable UTC bundles, then prints only status/counts. The private output path omission is tested. The configured interpreter is Python3.11.17, via praesagus.testPython. Those were the inspected proposal baseline. The selected launcher is now implemented without exporter/core changes. The first focused run passed75 tests in2.93s; after adding an explicit subprocess network-attempt sentinel, final focused75 passed in2.81s. Fictional generated/expired/missing fixtures and unchanged original CLI privacy are covered; actual source admission and forecast quality are not inferred.

Expired targets are not repaired by a later export. Existing issued-at/cutoff and scenario temporal validation remain authoritative. A real fixture export means executing the actual exporter/writer against authored fictional evidence in a private temporary directory, not collecting provider data or minting actual source admission. No external research is needed to decide these local interface facts.

## Tradeoffs

The API adapter supplies an exact path with no core file edits but duplicates a small amount of CLI orchestration and needs Lead's explicit acceptance of the interface deviation. An opt-in CLI flag centralizes orchestration but widens the reviewed source/test surface. Counts-only forwarding is smallest but leaves the user locating the file manually. None grants source rights, validates forecast quality or establishes a ready 100-name universe. Local output includes a private filesystem path only through the explicitly invoked launcher; the existing CLI retains its default path omission.

## Frozen Proposal and Dependencies

Base a2884f525a59a97a3bd6a73bb48c01e2e1712048. Engineer owns this proposal and, after Lead accepts scope, the three exact implementation paths and these two records. Dependencies: completed PRSG-127 private exporter and PRSG-126 private API; operational PRSG-124 per-name evidence/admission review remains independent. No capture/source/provider calls, credentials, training, model/policy/normalization changes, public outputs or live trades. Preserve baseline unrelated .DS_Store.

At proposal time only the two132 ticket records were authorized; Lead then explicitly released implementation of the exact five-path scope. Lead independently reviewed both records and accepted this exact five-path scope at the frozen base. Status review, scope accepted; Engineer D1 is complete, documentation D2 awaits independent guide review and D3 remains pending. Lead selected the embedded unchanged-API adapter; Lead independently accepted the exact five-path scope and released implementation; completion review remains pending. No worker dispatch, commit, push or deployment follows from this proposal. Lead independently reviews complete changes and mandatory hooks for delivery.

## Checks and Regression Boundary

After accepted scope, run the configured Python3.11 interpreter with -m pytest -q tests/test_manual_forecast_launcher.py tests/test_private_forecast_csv.py. Focused launcher cases: interpreter executable path with spaces; literal argument boundaries/metacharacters with no shell execution; invocation from unrelated cwd; missing/duplicate/unknown options; configured missing/old Python and unset-config discovery; a single UTC clock sample shared by issue/cutoff; exact exporter failure propagation and no extra call/retry.

Use a mocked interpreter/executable or isolated import/clock boundary for deterministic launch tests without adding a production time override. Exercise the real existing private exporter and writer with an authored valid batch (generated/fixture_only), an expired-target batch (withheld and no numeric forecast), and malformed/missing inputs (existing failure). Assert output counts/path match actual CSV/audit/manifest and preserved input hashes, with network attempts denied in the fixture process. Do not alter the fixtures' source truth merely to make a stale target pass. The original private-path omission regressions must keep passing.

Run scripts/planning/validate_ticket.py for the manifest and every changed file, scripts/planning/check_ticket_briefs.py, git diff --check, and Lead's required commit/push hooks on integration. The supplied-path validator does not discover the full diff or enforce filesystem writes. harness/verification_policy.json does not allow these new check argv pairs, so do not claim verify_ticket auto-executed them; execute focused checks normally and retain actual evidence. Full hooks remain delivery checks, not a request to rerun unchanged suites during planning.

## When it's considered done

- [x] PRSG-132-D1: Reviewed launcher interface accepts explicit batch/output paths, uses the approved Python and single UTC issuance/cutoff, preserves literal arguments/failure behavior, and delegates unchanged private calculation/admission/writer guards with passing focused regressions.
- [x] PRSG-132-D2: Manual guide supplies the stable command, generated/withheld counts and reviewed output-location behavior, separates collection from export, and points to the broader program without source/universe/model readiness claims.
- [x] PRSG-132-D3: Lead independently accepts the selected interface and exact scope, reviews diff/check evidence and required delivery hooks, and confirms private/core boundaries before integration.

## Proposal Validation — 21 October

Manifest and both changed record paths passed scripts/planning/validate_ticket.py. Current modern brief-quality validation and git diff --check passed. Only these two132 records were added; unrelated baseline .DS_Store is preserved. Configured interpreter validation reported Python3.11.17. Focused launcher tests and all implementation/delivery checks are not run at proposal time because the launcher was not yet implemented and final scope review was pending. Lead selected the unchanged-API adapter after the initial proposal; no implementation acceptance follows by implication. All acceptance items remain pending.

## Engineer Handoff — Pending Lead Completion Review

Implemented the shell launcher, embedded unchanged-API adapter, guide and focused regression module. The original exporter, secure reader, scenario core and their tests are unchanged. The local launcher returns only status/counts/exact csv_path on successful export; all adapter exceptions return a sanitized stage without traceback or private batch content. Its shell entrypoint supports the configured executable path, quoted literal path arguments and unrelated cwd.

Exact focused command from the manifest:75 passed in2.81s (first run75 passed2.93s). The final test-only change adds a file sentinel to fail even if a network exception were caught; no network attempt occurred. Shell syntax, full five-path manifest validation and modern brief quality passed. D1 is marked complete on Engineer evidence; D2 guide review and D3 independent acceptance remain pending. Full commit/push hooks are not run by Engineer because no commit/push is authorized. No source capture, credentials, model/training/policy change, real-data export, commit, push or deployment occurred in this ticket.

## Lead Acceptance — 21 October

Lead independently inspected all five files and frozen handoff hashes, accepted the embedded adapter and guide, and ran the exact focused command: **75 passed in 2.98s**. The actual launcher produced 12 generated, zero withheld and zero demo rows from separately reviewed private inputs at 2026-10-20T17:14:35 UTC. This proves the reviewed manual path executes; it does not establish full50/100 readiness or numerical performance. Original exporter/core and baseline .DS_Store remain unchanged. Complete scope validation and mandatory delivery hooks apply at commit/push; exact results retained in private delivery receipt. All three acceptance items accepted; status complete.
