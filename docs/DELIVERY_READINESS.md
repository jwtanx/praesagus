# Delivery readiness inspection

`scripts/stock-research/inspect_delivery.py` derives a private, offline view from
existing immutable artifacts. It prints text or JSON to stdout and never writes
to an input directory. It does not collect data, load a model, invoke a runner,
create approvals, renew admissions, or retry an attempt.

## Run from any working directory

Use Python 3.11 or later and absolute paths:

```sh
python3 -I -B /absolute/repo/scripts/stock-research/inspect_delivery.py \
  --bundle /absolute/private/inspection.json \
  --bundle-sha256 <SHA256-of-inspection.json> \
  --review-at 2026-10-30T01:40:00+08:00 \
  --format text
```

Use `--format json` for full per-name attribution, original method/model,
reference, issue/knowledge timestamps, target, reasons, evidence paths/hash/JSON
pointers, recorded qualification and decision. The explicit inspection time is
separate from all original evidence times. Repeating the command with the same
bytes and inspection time derives the same JSON. Inspection never retimestamps a
forecast or silently advances its reference date.

Exit 0 means all three supplied product generations reconciled. It can include
stale or withheld rows and does **not** mean all requested names have numeric
forecasts. Exit 2 means an honest missing, interrupted, consumed, expired or
incompatible product was found; its disposition and next action are in the view.
Exit 1 means the inspection input itself could not be safely consumed. Stderr is
not used to dump private content or exception paths.

## Locator bundle

An inspection bundle is a list of references, not an admission/status registry.
Store it outside Git with mode 0600, inside an owner-only directory (0700). Its
top-level fields are exactly `schema_version: 1`, `read_roots` and `products`.
Each product appears exactly once. No status, approval, count or handwritten
ticker list is accepted in the locator bundle.

Every reference has exactly these fields:

```json
{"path":"/absolute/private/file.json","sha256":"<64 lowercase hex characters>","bytes":123}
```

Product descriptors:

| Product | Required descriptor fields | Authoritative interface |
| --- | --- | --- |
| `fixed50` | `product`, `manifest`; optional `blockers` reference | Existing `private-forecast-csv` manifest; hash-bound `forecasts.csv` and `private-audit.json`; optional original withholding register |
| `us30` | `product`, `bundle`, `attempt`, `receipt`, `release` | Existing reviewed-inference bundle, exact attempt directory, final delivery receipt, child/parent approvals, supervisor receipt, generation artifacts and finite release/review |
| `standalone100` | `product`, `manifest` | Existing actual `stock-research-run` manifest, all artifact hashes, collection/prediction/export components, universe and export coverage |

For US30, `receipt` may be null when no delivery exists; `release` may be null
only for an undelivered inspection. Never omit an existing final receipt to make
an attempt look unused. For standalone100, a null manifest explicitly means no
actual generation is available. A pilot, fictional/demo export, or a standalone
exports-only manifest cannot establish an actual complete run. Missing names
remain unknown, not fabricated placeholders.

Supply narrow, explicit, owner-only directory roots covering the consumed
references and attempt/generation directories. No recursive search occurs. The
command follows only recognized artifact/review references; it does not traverse
the reviewed bundle's entire source/model graph or deserialize model blobs.

## Meaning of states and counts

- `ready` means a retained numeric **private research output can be inspected**
  and its retained target boundary has not passed. It grants no trade, rights,
  source authentication, calibrated-quality or promotion authority.
- `stale` preserves an authentic historical output. For reviewed numerical
  windows, currentness ends at the first open, matching the existing issuance
  guard. Fixed50 next-close research uses its retained target close. These
  distinct product contracts are not interchangeable.
- `withheld` retains the original reasons and, when supplied and matched, the
  original withholding-register blocker, owner and next action.
- `missing` is an absent forecast key or absent product evidence. A nonexistent
  universe has no invented names.
- `incompatible` means the exact bytes, schema, identity, numeric, reference,
  timestamp, coverage or approval binding failed. Known identities are retained
  only if they can be recovered from independently verified unaffected evidence.

Fixed50 has 50 name/next-close slots. US30 has 30 names and 120 rows for `1d`,
`3d`, `5d`, `next_week`. Standalone100 has **100 main names plus up to 10
ancillary speculative names**; speculative rows never fill main-name shortfalls.
All horizons remain visible. Historical numeric counts, current status counts,
and recorded qualified candidates are separate. No totals across products are
presented as unique securities, because their universes overlap.

## Reconciliation and continuation

An authentic completed generation remains historically completed after its
finite one-use release expires. The expired release grants no future execution.
Completion requires the final receipt, both approvals, supervisor approval and
cleanup, artifact hashes/counts, original release review, original issue window,
and matching run/bundle/generation identities. A CSV by itself is insufficient.

An existing attempt directory is consumed even if the process stopped before
writing its claim. A matching claim without delivery is `consumed-release`; a
directory without a claim is `interrupted`. Preserve all such evidence and
request a new reviewed run ID and finite release through the existing workflow.
There is no automatic resume or retry, and no output from an interrupted attempt
is promoted by this view. A genuinely absent attempt and expired release is
reported separately. Hash mismatches require reconciliation, not a new approval
boolean or a guessed status.

## Checks, limits and remaining obligations

Focused verification:

```sh
python3 -m pytest -q tests/test_delivery_readiness.py
```

Reads are limited to 12 roots, 256 files, 32 MiB per file, 128 MiB total,
32 JSON levels and 300,000 JSON nodes per document. Regular files must be owned
by the caller and mode 0600. Symlinks, duplicate JSON keys, nonfinite values,
bool-as-integer metadata, unknown locator fields and unsafe paths are rejected.
Consumed bytes and paths are checked again before returning. This is not a
filesystem lock or a defense against privileged concurrent mutation.

The adapter checks consumed numeric axes/conversions, typed identity, currency,
basis vocabulary, reference/issue ordering, target shape/consistency and original
approval bindings. It does not independently authenticate financial declarations,
rebuild exchange calendars, re-audit the full original source/model dependency
graph, or prove provider finality. Existing reviews and canonical ticket
specifications/manifests remain authoritative for those obligations. In
particular, a matching hash does not establish a reviewer's identity or renew a
financial admission. Model quality remains the separate evaluation/promotion
obligation.

The retained actual demonstration for PRSG-157 uses the fixed50 20 October
edition and PRSG-155 US30 delivery. At the frozen inspection time of 30 October
2026 01:40 MYT, fixed50 retains 35 historical numeric and 15 withheld rows; US30
retains 120 historical numeric rows with zero qualified candidates. No accepted
actual standalone100 generation was found in the bounded documented default
parent: only pilots and fictional exports were present. That product remains a
missing 100-name obligation; fixtures demonstrate adapter behavior, not actual
delivery. Demonstration bundles/results and exact commands stay private outside
Git. Lead independently accepts operational delivery; specialist reviews and
human promotion/publication authority remain separate.
