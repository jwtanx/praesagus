#!/usr/bin/env python3
"""Offline delivery inspection. Never imports runners, providers or model code."""
import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat

FILE_LIMIT = 32 * 1024 * 1024
TOTAL_LIMIT = 128 * 1024 * 1024
HORIZONS = ('1d', '3d', '5d', 'next_week')
PRODUCTS = {'fixed50': 50, 'us30': 30, 'standalone100': 100}


class Invalid(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Invalid(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def exact_keys(value, required, optional=()):
    need(type(value) is dict and set(required) <= value.keys()
         and value.keys() <= set(required) | set(optional), 'unknown-or-missing-fields')


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def decode(raw):
    def constant(_):
        raise Invalid('nonfinite-json')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        stack = [(value, 0)]
        nodes = 0
        while stack:
            item, depth = stack.pop()
            nodes += 1
            need(depth <= 32 and nodes <= 300000, 'json-budget')
            if isinstance(item, dict):
                stack.extend((v, depth + 1) for v in item.values())
            elif isinstance(item, list):
                stack.extend((v, depth + 1) for v in item)
            elif type(item) is float:
                need(math.isfinite(item), 'nonfinite-json')
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Invalid('invalid-json') from None


def stamp(value):
    try:
        dt = datetime.fromisoformat(value)
        need(dt.tzinfo is not None, 'timezone-required')
        return int(dt.timestamp() * 1000)
    except (TypeError, ValueError, OverflowError):
        raise Invalid('invalid-timestamp') from None


def millis(value):
    need(type(value) is int and 0 < value < 2**53, 'invalid-timestamp')
    return value


def day(value):
    need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'invalid-session-date')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Invalid('invalid-session-date') from None


def number(value, positive=False):
    need(type(value) in (int, float) and math.isfinite(value)
         and (not positive or value > 0), 'invalid-numeric-field')
    return value


def numeric_contract(source, payload):
    """Bounded consumed-field checks from export.py; no model/calendar execution."""
    need(type(source.get('schema_version')) is int and source['schema_version']==1, 'forecast-schema')
    instrument = source['instrument']
    identity = source['stock_id']
    need(type(identity) in (str, int) and type(identity) is type(instrument['stock_id'])
         and identity == instrument['stock_id'] and instrument['code'] == source['code']
         and source['code'].startswith('US.'), 'instrument-identity-mismatch')
    need(type(source['validation']['qualified']) is bool
         and source['decision']['action'] in ('BUY', 'SELL', 'WATCH', 'NO TRADE'), 'decision-contract')
    origin = day(source['origin'])
    window = source['window']
    sessions = window['sessions']
    need(type(sessions) is list and 1 <= len(sessions) <= 5
         and sessions == sorted(set(sessions)), 'invalid-window-sessions')
    need(all(day(s) > origin for s in sessions) and window['start'] == sessions[0]
         and window['end'] == sessions[-1], 'invalid-window-sessions')
    length = {'1d': 1, '3d': 3, '5d': 5}.get(source['horizon'])
    need(length is None or len(sessions)==length, 'invalid-window-length')
    need(type(window['started']) is bool and window['started'] == (payload['as_of_ms'] >= window['first_open_ms']), 'invalid-window-started')
    need(datetime.fromtimestamp(window['first_open_ms']/1000, timezone.utc).date() <= day(window['end']), 'invalid-window-time')
    reference = source.get('reference')
    if reference is not None:
        need(reference['currency'] == 'USD' and reference['adjustment'] in
             ('unadjusted', 'forward-excluding-dividends', 'back-excluding-dividends')
             and reference['session_date'] == source['origin'], 'reference-currency-basis-or-session')
        price = number(reference['close'], True)
        for key in ('known_at_ms', 'retrieved_at_ms', 'price_known_at_ms', 'currency_known_at_ms', 'source_at_ms'):
            need(millis(reference[key]) <= payload['as_of_ms'], 'future-reference')
    if source['status'] != 'available':
        need(source.get('model') is None and source.get('baseline') is None, 'withheld-has-numbers')
        return
    need(reference is not None, 'numeric-reference-missing')
    for family in ('model', 'baseline'):
        values = source[family]
        need(values['targets'] == ['low_return', 'high_return', 'terminal_logreturn']
             and values['quantiles'] == [.05, .5, .95]
             and all(type(q) in (int, float) for q in values['quantiles']), 'quantile-axis-contract')
        prices, relative = values['price_quantiles'], values['relative_quantiles']
        for matrix in (prices, relative):
            need(type(matrix) is list and len(matrix)==3 and all(type(axis) is list and len(axis)==3
                 and all(type(x) in (int, float) and math.isfinite(x) for x in axis)
                 and axis[0] <= axis[1] <= axis[2] for axis in matrix), 'invalid-quantiles')
        for axis in range(3):
            for q in range(3):
                expected = price * (1+relative[axis][q]) if axis<2 else price*math.exp(relative[axis][q])
                need(number(prices[axis][q], True) and math.isfinite(expected)
                     and math.isclose(prices[axis][q], expected, rel_tol=1e-10, abs_tol=1e-10), 'price-conversion-mismatch')
        need(relative[0][1] <= relative[1][1] and values['predicted_low'] == prices[0][1]
             and values['predicted_high'] == prices[1][1], 'extrema-mismatch')
        returns = values['terminal_return_quantiles']
        need(type(returns) is list and len(returns)==3 and all(
             math.isclose(number(returns[q]), math.expm1(relative[2][q]), rel_tol=1e-10, abs_tol=1e-10)
             for q in range(3)), 'terminal-return-mismatch')


def safe_path(value):
    need(type(value) is str and len(value) <= 4096, 'invalid-path')
    p = Path(value)
    need(p.is_absolute() and '..' not in p.parts and str(p) == value, 'invalid-path')
    for part in (p, *p.parents):
        need(not part.is_symlink(), 'symlink-forbidden')
    return p


class Reader:
    """Only explicitly declared roots; no recursive discovery or dynamic imports."""
    def __init__(self, roots):
        need(type(roots) is list and 1 <= len(roots) <= 12, 'read-roots')
        self.roots = [safe_path(r) for r in roots]
        for root in self.roots:
            s = root.stat()
            need(root.is_dir() and len(root.parts) >= 4 and s.st_uid == os.getuid()
                 and stat.S_IMODE(s.st_mode) == 0o700, 'private-root-required')
        self.cache = {}
        self.total = 0

    def path(self, value):
        p = safe_path(value)
        need(any(p.is_relative_to(r) for r in self.roots), 'outside-read-roots')
        return p

    def raw(self, value):
        p = self.path(value)
        if str(p) in self.cache:
            return self.cache[str(p)]
        need(len(self.cache) < 256, 'file-count-budget')
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            s = os.fstat(stream.fileno())
            need(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid()
                 and stat.S_IMODE(s.st_mode) == 0o600, 'private-file-required')
            need(s.st_size <= FILE_LIMIT, 'file-size-budget')
            raw = stream.read(FILE_LIMIT + 1)
            end = os.fstat(stream.fileno())
            need(len(raw) <= FILE_LIMIT and (s.st_ino, s.st_size, s.st_mtime_ns)
                 == (end.st_ino, end.st_size, end.st_mtime_ns), 'file-changed')
        self.total += len(raw)
        need(self.total <= TOTAL_LIMIT, 'total-byte-budget')
        self.cache[str(p)] = raw
        return raw

    def ref(self, ref):
        exact_keys(ref, ('path', 'sha256', 'bytes'))
        need(type(ref['bytes']) is int and 0 <= ref['bytes'] <= FILE_LIMIT
             and type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'invalid-reference')
        raw = self.raw(ref['path'])
        need(len(raw) == ref['bytes'] and digest(raw) == ref['sha256'], 'hash-or-size-mismatch')
        return raw

    def document(self, ref):
        return decode(self.ref(ref))

    def linked(self, path, expected):
        raw = self.raw(str(path))
        need(type(expected) is str and digest(raw) == expected, 'hash-or-size-mismatch')
        return decode(raw)

    def unchanged(self):
        # Recheck consumed files, including path/symlink/perms; not a filesystem lock.
        for name, old in list(self.cache.items()):
            del self.cache[name]
            self.total -= len(old)
            need(self.raw(name) == old, 'file-changed')


def evidence(ref, pointer=''):
    return dict(path=ref['path'], sha256=ref['sha256'], pointer=pointer)


def row(code, horizon, ref):
    need(type(code) is str and re.fullmatch(r'[A-Za-z0-9._-]{1,64}', code), 'invalid-identity')
    return dict(code=code, horizon=horizon, status='missing', blocker='forecast-missing',
                owner='Engineer', next_action='Locate the immutable generation and its exact receipt; do not execute a run.',
                evidence=evidence(ref), method=None, reference=None, issued_at=None, target=None,
                qualified=False, execution_authorized=False)


def finish(product, rows, disposition, action, **extra):
    keys = [(r['code'], r['horizon']) for r in rows]
    need(len(keys) == len(set(keys)), 'duplicate-identity-or-horizon')
    names = len({r['code'] for r in rows if r.get('panel') != 'speculative'})
    need(names <= PRODUCTS[product], 'product-denominator-exceeded')
    return dict(product=product, expected_names=PRODUCTS[product], named_names=names,
                unnamed_slots=PRODUCTS[product] - names, horizon_rows=len(rows),
                status_counts=dict(sorted(Counter(r['status'] for r in rows).items())),
                disposition=disposition, next_action=action, rows=rows,
                ready_scope='retained-private-research-inspection-only',
                quality='research evidence only; no quality, promotion, rights or trading approval inferred', **extra)


def apply_time(item, issue, deadline, now):
    need(issue <= now and issue < deadline, 'future-or-invalid-issuance')
    if item['status'] == 'ready' and now >= deadline:
        item.update(status='stale', blocker='forecast-window-started-or-ended', owner='AI Engineer',
                    next_action='Keep the historical output; obtain a separately reviewed current edition if needed.')


def numerical_rows(payload, codes, ref, now):
    need(type(payload.get('schema_version')) is int and payload['schema_version']==1
         and payload.get('kind')=='stock-research-forecast-bundle', 'prediction-schema')
    need(type(codes) is list and len(codes) == len(set(codes)), 'duplicate-identity')
    need(type(payload.get('forecasts')) is list and len(payload['forecasts']) <= 4000, 'forecast-row-budget')
    issue, cutoff = millis(payload['issued_at_ms']), millis(payload['as_of_ms'])
    need(cutoff <= issue <= now, 'future-or-invalid-issuance')
    indexed = {}
    windows = {}
    origins = set()
    for index, source in enumerate(payload['forecasts']):
        key = (source['code'], source['horizon'])
        need(source['code'] in codes and source['horizon'] in HORIZONS and key not in indexed, 'unexpected-or-duplicate-forecast')
        need(source.get('forecast_id') == digest(canonical({k: v for k, v in source.items() if k != 'forecast_id'})), 'forecast-id-mismatch')
        need(source['issued_at_ms'] == issue and source['as_of_ms'] == cutoff
             and source['model_ref'] == payload['model_ref']
             and source['input_data_sha256'] == payload['data_sha256'], 'forecast-attribution-mismatch')
        item = row(source['code'], source['horizon'], ref)
        item.update(evidence=evidence(ref, '/forecasts/' + str(index)), method=payload['model_ref'],
                    reference=source.get('reference'), issued_at=issue, target=source['window'],
                    original_status=source['status'], reasons=source.get('reasons', []),
                    validation=source.get('validation'), decision=source.get('decision'),
                    qualified=source.get('validation', {}).get('qualified') is True)
        window = source['window']
        first, last = millis(window['first_open_ms']), millis(window['last_close_ms'])
        need(first <= last and window['horizon'] == source['horizon'], 'invalid-target-window')
        reference = source.get('reference')
        if reference is not None:
            need(millis(reference['known_at_ms']) <= cutoff, 'future-reference')
        numeric_contract(source, payload)
        origins.add(source['origin'])
        need(len(origins) == 1, 'mixed-reference-sessions')
        previous = windows.setdefault(source['horizon'], window)
        need(previous == window, 'inconsistent-target-window')
        if source['status'] == 'available':
            need(source.get('model') is not None and source.get('baseline') is not None, 'numeric-output-missing')
            need(issue < first, 'issued-after-window-start')
            item.update(status='ready', blocker=None, owner=None,
                        next_action='Inspect the retained research output; preserve its original qualifications.')
        elif source['status'] in ('unavailable', 'invalid'):
            item.update(status='withheld', blocker=';'.join(source.get('reasons', [])) or source['status'],
                        owner='AI Engineer', next_action='Resolve the recorded input/model blocker under its existing ticket; no retry here.')
        else:
            raise Invalid('unknown-forecast-status')
        apply_time(item, issue, first, now)
        indexed[key] = item
    return [indexed.get((code, horizon), row(code, horizon, ref)) for code in codes for horizon in HORIZONS]


def artifacts(reader, manifest_ref):
    manifest = reader.document(manifest_ref)
    need(type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1, 'manifest-version')
    base = Path(manifest_ref['path']).parent
    entries = manifest.get('artifacts')
    need(type(entries) is dict and len(entries) <= 64, 'manifest-artifacts')
    refs = {}
    for name, info in entries.items():
        need(re.fullmatch(r'[A-Za-z0-9_-]+\.(json|csv|xlsx|joblib)', name) and name != 'manifest.json', 'artifact-name')
        exact_keys(info, ('sha256', 'bytes'), ('path',))
        need(info.get('path', name) == name, 'artifact-path')
        ref = dict(path=str(base / name), sha256=info['sha256'], bytes=info['bytes'])
        # Hash model blobs without deserializing them.
        reader.ref(ref)
        refs[name] = ref
    return manifest, refs


def fixed50(reader, descriptor, now):
    exact_keys(descriptor, ('product', 'manifest'), ('blockers',))
    manifest, refs = artifacts(reader, descriptor['manifest'])
    need(manifest.get('kind') == 'private-forecast-csv' and manifest.get('is_demo') is False, 'incompatible-fixed50-manifest')
    audit = reader.document(refs['private-audit.json'])
    need(set(manifest['counts']) == {'generated', 'is_demo', 'total', 'withheld'}
         and all(type(v) is int and v >= 0 for v in manifest['counts'].values()), 'coverage-count-types')
    need(audit['input_sha256'] == manifest['input_sha256'] and audit['counts'] == manifest['counts'], 'audit-binding-mismatch')
    csv_reader = csv.DictReader(io.StringIO(reader.ref(refs['forecasts.csv']).decode()))
    need(csv_reader.fieldnames and len(csv_reader.fieldnames) == len(set(csv_reader.fieldnames))
         and len(csv_reader.fieldnames) <= 128, 'csv-header-contract')
    csv_rows = list(csv_reader)
    need(all(None not in c and None not in c.values() for c in csv_rows), 'csv-row-contract')
    need(len(csv_rows) == len(audit['rows']) == 50, 'fixed50-denominator')
    blockers = {}
    if descriptor.get('blockers'):
        for b in reader.document(descriptor['blockers']):
            key = (b['market'], b['ticker'])
            need(key not in blockers, 'duplicate-blocker')
            blockers[key] = b
    rows = []
    generated = 0
    for index, (c, a) in enumerate(zip(csv_rows, audit['rows'])):
        need((c['market'], c['ticker']) == (a['market'], a['ticker']), 'audit-identity-mismatch')
        result = a['result']
        need(c['result_sha256'] == digest(canonical(result)), 'result-binding-mismatch')
        need(c['status'] == result['status'] and c['issued_at'] == audit['issued_at'], 'audit-status-or-time-mismatch')
        code = c['market'] + '.' + c['ticker']
        item = row(code, 'next-close', refs['private-audit.json'])
        item.update(evidence=evidence(refs['private-audit.json'], '/rows/' + str(index)),
                    method=c['method_id'] or None, reference=c['reference_session'] or None,
                    issued_at=c['issued_at'], target=c['target_session'] or None,
                    original_status=c['status'], original_reasons=c['reasons'],
                    evidence_sha256=a.get('evidence_sha256'), admission_sha256=a.get('admission_sha256'))
        issue = stamp(c['issued_at'])
        need(issue <= now, 'future-issuance')
        if c['status'] == 'generated':
            generated += 1
            need(c['is_demo'] == 'False' and c['evidence_sha256'] == a['evidence_sha256']
                 and c['admission_sha256'] == a['admission_sha256'], 'admission-binding-mismatch')
            original = result['provenance']['audit']
            need(all(c[k] == str(original[k]) for k in ('method_id', 'issued_at', 'reference_session',
                 'reference_close_at', 'target_session', 'target_close_at', 'evidence_sha256', 'admission_sha256')),
                 'audit-attribution-mismatch')
            need(stamp(c['reference_close_at']) <= stamp(audit['report_cutoff']) <= issue,
                 'future-reference')
            instrument = result['instrument']
            need(instrument['market'] == c['market'] and instrument['ticker'] == c['ticker']
                 and instrument['currency'] == c['currency'] == ('USD' if c['market']=='US' else 'MYR')
                 and c['market'] in ('US', 'MY'), 'fixed50-currency-or-identity')
            need(day(c['reference_session']) < day(c['target_session']), 'fixed50-session-order')
            estimates = result['estimates']
            low, point, high = (number(estimates[k], True) for k in ('low', 'point', 'high'))
            need(low <= point <= high and all(c[field] == f"{number(estimates['display_'+field], True):.2f}"
                 for field in ('low', 'point', 'high')), 'fixed50-estimate-mismatch')
            need(c['reference_close'] == str(original['reference_close'])
                 and number(original['reference_close'], True) and c['currency'] == estimates['currency'],
                 'fixed50-reference-mismatch')
            item.update(status='ready', blocker=None, owner=None,
                        next_action='Inspect retained private research; caller admissions are not independently authenticated.')
            apply_time(item, issue, stamp(c['target_close_at']), now)
        elif c['status'] == 'withheld':
            need(all(c.get(k, '') == '' for k in ('point', 'low', 'high')), 'withheld-has-numbers')
            b = blockers.pop((c['market'], c['ticker']), None)
            item.update(status='withheld', blocker=b['blocker'] if b else c['reasons'],
                        owner=b['owner'] if b else 'Trader / AI Engineer',
                        next_action=b['next_action'] if b else 'Resolve exact evidence/admission reasons; never fill missing forecasts.')
            if b:
                item['blocker_evidence'] = evidence(descriptor['blockers'])
        else:
            raise Invalid('unknown-fixed50-status')
        rows.append(item)
    need(not blockers and manifest['counts'] == dict(generated=generated, is_demo=0, total=50, withheld=50-generated), 'coverage-count-mismatch')
    return finish('fixed50', rows, 'completed', 'Preserve this immutable edition; currentness is shown separately.',
                  historical_counts=manifest['counts'], source_authentication=manifest.get('source_status'),
                  original_manifest=evidence(descriptor['manifest']))


def us30(reader, d, now):
    exact_keys(d, ('product', 'bundle', 'attempt', 'receipt', 'release'))
    bundle = reader.document(d['bundle'])
    need(type(bundle.get('schema_version')) is int and bundle['schema_version']==1
         and bundle.get('kind')=='praesagus-reviewed-inference-bundle', 'us30-bundle-schema')
    codes = bundle['expected_codes']
    need(len(codes) == 30 and len(set(codes)) == 30 and bundle['horizons'] == list(HORIZONS), 'us30-identity-contract')
    attempt = reader.path(d['attempt'])
    need(attempt.parent == Path(bundle['output_parent']), 'attempt-parent-mismatch')
    release = reader.document(d['release']) if d['release'] else None
    release_state = 'absent'
    if release is not None:
        need(release.get('bundle_sha256') == d['bundle']['sha256'] and release.get('run_id') == attempt.name
             and release.get('approved') is True, 'release-binding-mismatch')
        need(type(release.get('schema_version')) is int and release['schema_version']==1
             and release.get('kind')=='praesagus-reviewed-inference-release'
             and release.get('resources_confirmed') is True and release.get('exclusive_local_run_confirmed') is True,
             'release-schema-or-confirmations')
        review = reader.document(release['review_reference'])
        need(review.get('approved') is True and review['run_id'] == attempt.name
             and review['bundle_sha256'] == d['bundle']['sha256']
             and review['reference_session'] == bundle['reference_session']
             and review['source_not_before_ms'] == bundle['source_not_before_ms']
             and review['issue_before_ms'] == bundle['issue_before_ms'], 'release-review-mismatch')
        start, end = millis(release['not_before_ms']), millis(release['expires_at_ms'])
        need(0 < end-start <= 600000, 'release-window-invalid')
        release_state = 'expired' if now >= end else 'not-yet-valid' if now < start else 'finite-current'
    claim_path = attempt / 'claim.json'
    claimed = claim_path.exists()
    consumed = attempt.exists()
    if claimed:
        claim = decode(reader.raw(str(claim_path)))
        need(claim == dict(run_id=attempt.name, bundle_sha256=d['bundle']['sha256']), 'claim-binding-mismatch')
    if d['receipt'] is None:
        need(not (attempt / 'delivery-receipt.json').exists(), 'unlisted-delivery-receipt')
        rows = [row(c, h, d['bundle']) for c in codes for h in HORIZONS]
        disposition = ('consumed-release' if claimed else 'interrupted' if consumed else
                       'expired-release' if release_state == 'expired' else 'not-delivered')
        for item in rows:
            item.update(blocker=disposition, next_action='Preserve the attempt; request a new reviewed run ID and finite release. Never reuse or retry this attempt.')
        return finish('us30', rows, disposition, rows[0]['next_action'], release_state=release_state,
                      attempt_consumed=consumed, original_bundle=evidence(d['bundle']))
    need(release is not None, 'release-evidence-missing')
    need(claimed and Path(d['receipt']['path']) == attempt / 'delivery-receipt.json', 'receipt-attempt-mismatch')
    receipt = reader.document(d['receipt'])
    child = reader.linked(attempt / 'child-approved.json', receipt['child_approval_sha256'])
    parent = reader.linked(attempt / 'parent-approved.json', receipt['parent_approval_sha256'])
    supervisor = reader.linked(attempt / 'supervisor-receipt.json', parent['supervisor_receipt_sha256'])
    need(all(v.get('approved_forecast_use') is True for v in (receipt, child, parent))
         and supervisor.get('approved') is True and supervisor.get('cleanup_verified') is True, 'approval-or-cleanup-missing')
    need(all(type(v.get('schema_version')) is int and v['schema_version']==1 for v in (child, parent)), 'approval-schema')
    generation = reader.path(receipt['generation'])
    need(generation.parent == attempt and all(v['generation'] == str(generation) for v in (child, parent)), 'generation-binding-mismatch')
    need(all(v['bundle_sha256'] == d['bundle']['sha256'] for v in (receipt, child, parent))
         and child['run_id'] == parent['run_id'] == attempt.name
         and parent['child_approval_sha256'] == receipt['child_approval_sha256'], 'approval-binding-mismatch')
    need(child['artifact_hashes'] == parent['artifact_hashes']
         and set(child['artifact_hashes']) == {'predictions.json', 'forecasts.csv', 'coverage.json', 'manifest.json'}, 'artifact-approval-mismatch')
    docs = {}
    for name, expected in child['artifact_hashes'].items():
        raw = reader.raw(str(generation / name))
        need(digest(raw) == expected, 'hash-or-size-mismatch')
        if name.endswith('.json'):
            docs[name] = decode(raw)
    need(receipt['csv_sha256'] == child['artifact_hashes']['forecasts.csv'], 'csv-receipt-mismatch')
    manifest_ref = dict(path=str(generation/'manifest.json'), sha256=child['artifact_hashes']['manifest.json'],
                        bytes=len(reader.raw(str(generation/'manifest.json'))))
    manifest, refs = artifacts(reader, manifest_ref)
    need(manifest.get('kind') == 'stock-research-reviewed-batch'
         and manifest.get('bundle_sha256') == d['bundle']['sha256']
         and manifest.get('as_of_ms') == bundle['as_of_ms'], 'manifest-bundle-mismatch')
    payload = docs['predictions.json']
    need(payload['as_of_ms'] == bundle['as_of_ms'] == child['as_of_ms']
         and payload['issued_at_ms'] == child['issued_at_ms']
         and child['reference_session'] == bundle['reference_session'], 'issuance-binding-mismatch')
    completed = millis(receipt['completed_at_ms'])
    need(payload['issued_at_ms'] <= completed <= now, 'future-completion')
    need(millis(bundle['source_not_before_ms']) <= payload['as_of_ms'] <= payload['issued_at_ms']
         <= completed < millis(bundle['issue_before_ms'])
         and millis(review['known_at_ms']) <= payload['issued_at_ms'], 'original-window-or-review-time')
    if release:
        need(start <= payload['issued_at_ms'] <= completed < end, 'completion-outside-release')
    rows = numerical_rows(payload, codes, refs['predictions.json'], now)
    need(all(r['reference'] is None or r['reference']['session_date'] == bundle['reference_session']
             for r in rows), 'bundle-reference-mismatch')
    counts = dict(keys=len(rows), available=sum(r['original_status']=='available' for r in rows),
                  withheld=sum(r['original_status']!='available' for r in rows),
                  qualified=sum(r['qualified'] for r in rows),
                  actions=sorted({r['decision']['action'] for r in rows}))
    need(all(type(v[k]) is int and v[k] >= 0 for v in (receipt['counts'], child['counts'], docs['coverage.json'])
             for k in ('keys', 'available', 'withheld', 'qualified')), 'coverage-count-types')
    need(counts == receipt['counts'] == child['counts']
         and docs['coverage.json'] == counts | dict(research_only=True, promotion=False, training=False), 'coverage-count-mismatch')
    need(receipt['status'] == ('complete' if counts['available']==120 else 'partial'), 'completion-status-mismatch')
    return finish('us30', rows, 'completed' if counts['available']==120 else 'partial',
                  'Reuse this retained delivery for inspection. A consumed release never authorizes another run.',
                  historical_counts=counts, release_state=release_state, attempt_consumed=True,
                  completed_at_ms=completed, original_issue_ms=payload['issued_at_ms'], original_as_of_ms=payload['as_of_ms'],
                  original_release=evidence(d['release']), original_release_review=evidence(release['review_reference']),
                  original_receipt=evidence(d['receipt']), original_bundle=evidence(d['bundle']))


def standalone(reader, d, now):
    exact_keys(d, ('product', 'manifest'))
    if d['manifest'] is None:
        return finish('standalone100', [], 'missing',
                      'Engineer: locate the canonical standalone generation and coverage; no names or completion inferred.')
    manifest, refs = artifacts(reader, d['manifest'])
    need(manifest.get('kind') == 'stock-research-run' and manifest.get('is_demo') is False
         and manifest.get('components_schema_version') == 1, 'incompatible-standalone-manifest')
    required = {'collection': {'universe.json', 'coverage.json'}, 'prediction': {'predictions.json'},
                'exports': {'forecasts.csv', 'export_coverage.json'}}
    # Mirror storage.COMPONENT_REQUIRED without importing its provider-adjacent callers.
    required['collection'] |= {'history.csv', 'history_revisions.csv', 'state.json',
                               'metadata_input.json', 'identity_bindings.json', 'calendar.json'}
    required['prediction'] |= {'outcomes.json'}
    required['exports'] |= {'master.csv', 'top20.csv', 'research.xlsx'}
    need(set(manifest['components']) == set(required), 'component-set')
    owned = set()
    for name, files in required.items():
        component = manifest['components'][name]
        exact_keys(component, ('schema_version', 'status', 'artifacts', 'compatibility_id'))
        need(type(component['schema_version']) is int and component['schema_version']==1
             and component['status'] in ('complete', 'partial', 'research-only', 'unavailable')
             and type(component['compatibility_id']) is str and bool(component['compatibility_id']), 'component-contract')
        names = component['artifacts']
        need(type(names) is list and len(names)==len(set(names)) and files <= set(names)
             and set(names) <= refs.keys() and not owned.intersection(names), 'component-artifacts-missing')
        owned.update(names)
        if name == 'collection':
            need(component['compatibility_id'] == manifest['compatibility_id'], 'component-compatibility')
    need(stamp(manifest['generated_at']) <= now, 'future-generation')
    universe = reader.document(refs['universe.json'])
    instruments = universe['main'] + universe['speculative']
    codes = [r['code'] for r in instruments]
    payload = reader.document(refs['predictions.json'])
    rows = numerical_rows(payload, codes, refs['predictions.json'], now)
    speculative = {r['code'] for r in universe['speculative']}
    need(len(universe['speculative']) <= 10, 'speculative-budget')
    for item in rows:
        item['panel'] = 'speculative' if item['code'] in speculative else 'main'
    coverage = reader.document(refs['export_coverage.json'])
    available = sum(r.get('original_status') == 'available' for r in rows)
    need(coverage['main_instruments'] == len(universe['main'])
         and coverage['speculative_instruments'] == len(universe['speculative'])
         and coverage['available_numerical_forecasts'] == available, 'coverage-count-mismatch')
    return finish('standalone100', rows, 'completed-generation',
                  'Inspect coverage shortfalls and per-name blockers; generation completion does not establish 100-name delivery.',
                  main_names=len(universe['main']), speculative_names=len(universe['speculative']),
                  historical_coverage=coverage, original_manifest=evidence(d['manifest']))


def known_incompatible_rows(reader, d, blocker):
    """Recover identities only from independently hash-verified unaffected evidence."""
    try:
        if d['product'] == 'us30':
            source = reader.document(d['bundle'])
            codes, horizons, ref = source['expected_codes'], HORIZONS, d['bundle']
            need(len(codes) == 30, 'identity-count')
        elif d.get('manifest'):
            manifest = reader.document(d['manifest'])
            name = 'private-audit.json' if d['product']=='fixed50' else 'universe.json'
            info = manifest['artifacts'][name]
            ref = dict(path=str(Path(d['manifest']['path']).parent/name), sha256=info['sha256'], bytes=info['bytes'])
            source = reader.document(ref)
            if d['product']=='fixed50':
                codes, horizons = [a['market']+'.'+a['ticker'] for a in source['rows']], ('next-close',)
            else:
                codes, horizons = [a['code'] for a in source['main']+source['speculative']], HORIZONS
        else:
            return []
        need(len(codes) <= PRODUCTS[d['product']]+(10 if d['product']=='standalone100' else 0)
             and len(set(codes)) == len(codes), 'identity-count')
        rows = [row(c, h, ref) for c in codes for h in horizons]
        for item in rows:
            if d['product']=='standalone100':
                item['panel'] = 'speculative' if item['code'] in {a['code'] for a in source['speculative']} else 'main'
            item.update(status='incompatible', blocker=blocker, owner='Engineer',
                        next_action='Reconcile the failed evidence binding; preserve the attempt and do not retry it.')
        return rows
    except (Invalid, OSError, KeyError, TypeError, ValueError):
        return []


def inspect(bundle_path, bundle_sha256, review_at):
    now = stamp(review_at)
    # The locator bundle is itself owner-only and bounded, never an admission ledger.
    p = safe_path(str(bundle_path))
    initial = Reader([str(p.parent)])
    raw = initial.raw(str(p))
    need(digest(raw) == bundle_sha256, 'bundle-hash-mismatch')
    bundle = decode(raw)
    exact_keys(bundle, ('schema_version', 'read_roots', 'products'))
    need(type(bundle['schema_version']) is int and bundle['schema_version']==1, 'bundle-version')
    need(type(bundle['products']) is list and len(bundle['products'])==3
         and {d['product'] for d in bundle['products']} == set(PRODUCTS), 'product-set')
    reader = Reader(bundle['read_roots'])
    results = []
    for d in bundle['products']:
        try:
            result = {'fixed50': fixed50, 'us30': us30, 'standalone100': standalone}[d['product']](reader, d, now)
        except (Invalid, OSError, KeyError, TypeError, ValueError, OverflowError, IndexError) as error:
            code = str(error) if isinstance(error, Invalid) else 'missing-or-malformed-evidence'
            result = finish(d['product'], known_incompatible_rows(reader, d, code), 'incompatible',
                            'Engineer: preserve originals and reconcile the exact evidence binding before any new execution.',
                            blocker=code)
        results.append(result)
    reader.unchanged()
    initial.unchanged()
    return dict(schema_version=1, review_at=review_at, bundle_sha256=bundle_sha256,
                mode='offline-read-only', products=results,
                read_files=len(reader.cache), read_bytes=sum(map(len, reader.cache.values())),
                limitations=['Pins establish byte identity, not reviewer/source authenticity.',
                             'No admission, release, provider request, model load, inference or retry performed.',
                             'Currentness uses the retained target bounds; no calendar or live-data renewal.',
                             'No filesystem lock or protection against privileged concurrent mutation.'])


def render(result):
    lines = ['Praesagus delivery inspection — ' + result['review_at'], 'Private research only. Read-only; no execution authority.']
    for p in result['products']:
        lines.append('\n%s: %s; %s/%s names, %s unnamed; %s horizon rows' %
                     (p['product'], p['disposition'], p['named_names'], p['expected_names'], p['unnamed_slots'], p['horizon_rows']))
        lines.append('States: ' + json.dumps(p['status_counts'], sort_keys=True))
        lines.append('Next: ' + p['next_action'])
        if p.get('blocker'):
            lines.append('Blocker: ' + p['blocker'])
        for r in p['rows']:
            lines.append('%s %s | %s | %s | %s | %s' %
                         (r['code'], r['horizon'], r['status'], r['blocker'] or '-', r['owner'] or '-', r['next_action']))
            target = r['target']
            if isinstance(target, dict):
                target = target.get('start', '?') + '..' + target.get('end', '?')
            reference = r['reference']
            if isinstance(reference, dict):
                reference = reference.get('session_date')
            lines.append('  reference=%s issue=%s target=%s evidence=%s%s' %
                         (reference, r['issued_at'], target, r['evidence']['path'], r['evidence']['pointer']))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--bundle-sha256', required=True)
    parser.add_argument('--review-at', required=True, help='Explicit timezone-aware inspection time; never changes evidence time.')
    parser.add_argument('--format', choices=('json', 'text'), default='text')
    args = parser.parse_args(argv)
    try:
        result = inspect(args.bundle, args.bundle_sha256, args.review_at)
        print(json.dumps(result, sort_keys=True, allow_nan=False) if args.format=='json' else render(result), end='\n' if args.format=='json' else '')
        return 0 if all(p['disposition'] not in ('incompatible', 'missing', 'not-delivered', 'expired-release', 'consumed-release', 'interrupted') for p in result['products']) else 2
    except (Invalid, OSError, KeyError, TypeError, ValueError):
        print(json.dumps(dict(status='inspection-unavailable', reason='invalid-or-inaccessible-inspection-input')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
