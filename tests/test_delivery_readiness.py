"""Offline contract and failure tests; no provider/model dependencies."""
import copy
import csv
import importlib.util
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/stock-research/inspect_delivery.py'
spec = importlib.util.spec_from_file_location('inspect_delivery', SCRIPT)
view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(view)
NOW = '2026-10-30T01:00:00+08:00'
MS = view.stamp(NOW)


def put(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else view.canonical(value)
    path.write_bytes(raw)
    path.chmod(0o600)
    return dict(path=str(path), sha256=view.digest(raw), bytes=len(raw))


def csv_bytes(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def forecast(code, horizon):
    from datetime import date, timedelta
    origin = date(2026, 10, 28)
    sessions = [(origin+timedelta(days=n+2)).isoformat() for n in range({'1d':1, '3d':3, '5d':5, 'next_week':5}[horizon])]
    relative = [[-.1, 0, .1]]*3
    import math
    values = dict(targets=['low_return', 'high_return', 'terminal_logreturn'], quantiles=[.05, .5, .95],
                  price_quantiles=[[90, 100, 110], [90, 100, 110], [100*math.exp(x) for x in relative[2]]],
                  relative_quantiles=relative, terminal_return_quantiles=[math.expm1(x) for x in relative[2]],
                  predicted_low=100, predicted_high=100)
    r = dict(schema_version=1, code=code, horizon=horizon, issued_at_ms=MS-1000, as_of_ms=MS-2000,
             stock_id=123, instrument=dict(code=code, stock_id=123), origin=origin.isoformat(),
             model_ref={'quality_status': 'research-only'},
             reference=dict(known_at_ms=MS-3000, retrieved_at_ms=MS-3000, price_known_at_ms=MS-3000,
                            currency_known_at_ms=MS-3000, source_at_ms=MS-3000, currency='USD',
                            adjustment='unadjusted', close=100, session_date=origin.isoformat()),
             input_data_sha256='d'*64,
             model=copy.deepcopy(values), baseline=copy.deepcopy(values),
             reasons=[], status='available', validation={'qualified': False},
             decision={'action': 'NO TRADE'}, window=dict(first_open_ms=MS+1000,
             last_close_ms=MS+2000, horizon=horizon, sessions=sessions,
             start=sessions[0], end=sessions[-1], started=False))
    r['forecast_id'] = view.digest(view.canonical(r))
    return r


def build_us(root):
    attempt = root / 'runs' / 'one-use'
    generation = attempt / '2026-10-30_010000'
    codes = ['US.N%02d' % n for n in range(30)]
    bundle = dict(schema_version=1, kind='praesagus-reviewed-inference-bundle',
                  expected_codes=codes, horizons=list(view.HORIZONS), output_parent=str(attempt.parent),
                  as_of_ms=MS-2000, reference_session='2026-10-28', source_not_before_ms=MS-3000, issue_before_ms=MS+1000)
    bundle_ref = put(root/'us-bundle.json', bundle)
    payload = dict(schema_version=1, kind='stock-research-forecast-bundle', forecasts=[forecast(c, h) for c in codes for h in view.HORIZONS],
                   data_sha256='d'*64, issued_at_ms=MS-1000, as_of_ms=MS-2000, model_ref={'quality_status': 'research-only'})
    counts = dict(keys=120, available=120, withheld=0, qualified=0, actions=['NO TRADE'])
    refs = {'predictions.json': put(generation/'predictions.json', payload),
            'coverage.json': put(generation/'coverage.json', counts | dict(research_only=True, promotion=False, training=False)),
            'forecasts.csv': put(generation/'forecasts.csv', b'code\nUS.N00\n')}
    manifest = dict(schema_version=1, kind='stock-research-reviewed-batch', as_of_ms=MS-2000,
                    bundle_sha256=bundle_ref['sha256'], artifacts={
        k: dict(bytes=v['bytes'], sha256=v['sha256'], path=k) for k, v in refs.items()})
    refs['manifest.json'] = put(generation/'manifest.json', manifest)
    hashes = {k: v['sha256'] for k, v in refs.items()}
    put(attempt/'claim.json', dict(run_id=attempt.name, bundle_sha256=bundle_ref['sha256']))
    child = dict(schema_version=1, approved_forecast_use=True, bundle_sha256=bundle_ref['sha256'], generation=str(generation),
                 run_id=attempt.name, as_of_ms=MS-2000, issued_at_ms=MS-1000,
                 reference_session='2026-10-28', artifact_hashes=hashes, counts=counts)
    child_ref = put(attempt/'child-approved.json', child)
    supervisor_ref = put(attempt/'supervisor-receipt.json', dict(approved=True, cleanup_verified=True))
    parent = dict(schema_version=1, approved_forecast_use=True, bundle_sha256=bundle_ref['sha256'], generation=str(generation),
                  run_id=attempt.name, artifact_hashes=hashes, child_approval_sha256=child_ref['sha256'],
                  supervisor_receipt_sha256=supervisor_ref['sha256'])
    parent_ref = put(attempt/'parent-approved.json', parent)
    receipt = dict(approved_forecast_use=True, bundle_sha256=bundle_ref['sha256'], generation=str(generation),
                   child_approval_sha256=child_ref['sha256'], parent_approval_sha256=parent_ref['sha256'],
                   completed_at_ms=MS-500, counts=counts, csv_sha256=hashes['forecasts.csv'], status='complete')
    receipt_ref = put(attempt/'delivery-receipt.json', receipt)
    review_ref = put(root/'review.json', dict(approved=True, bundle_sha256=bundle_ref['sha256'], run_id=attempt.name,
                     reference_session=bundle['reference_session'], source_not_before_ms=bundle['source_not_before_ms'],
                     issue_before_ms=bundle['issue_before_ms'], known_at_ms=MS-2000))
    release_ref = put(root/'release.json', dict(schema_version=1, kind='praesagus-reviewed-inference-release',
                      bundle_sha256=bundle_ref['sha256'], run_id=attempt.name, review_reference=review_ref,
                      resources_confirmed=True, exclusive_local_run_confirmed=True,
                      approved=True, not_before_ms=MS-2000, expires_at_ms=MS+500))
    return dict(product='us30', bundle=bundle_ref, attempt=str(attempt), receipt=receipt_ref, release=release_ref)


def build_fixed(root):
    rows, audit_rows = [], []
    for n in range(50):
        status = 'generated' if n < 35 else 'withheld'
        result = dict(status=status)
        a = dict(market='US' if n < 30 else 'MY', ticker='N%02d' % n, result=result,
                 evidence_sha256='a'*64, admission_sha256='b'*64)
        rows.append(dict(market=a['market'], ticker=a['ticker'], status=status,
                         result_sha256=view.digest(view.canonical(result)), issued_at=NOW,
                         target_close_at='2026-10-31T01:00:00+08:00', target_session='2026-10-30',
                         reference_session='2026-10-29', method_id='next_close_baseline', is_demo='False',
                         currency='USD' if n<30 else 'MYR', reference_close='100', point='100.00', low='90.00', high='110.00',
                         reference_close_at='2026-10-29T01:00:00+08:00',
                         evidence_sha256=a['evidence_sha256'], admission_sha256=a['admission_sha256'],
                         reasons='' if n < 35 else 'admission_missing'))
        result['provenance'] = dict(audit={k: rows[-1][k] for k in ('method_id', 'issued_at', 'reference_session',
                  'reference_close_at', 'target_session', 'target_close_at', 'evidence_sha256', 'admission_sha256', 'reference_close')})
        result['provenance']['audit']['reference_close'] = 100
        result['instrument'] = dict(market=a['market'], ticker=a['ticker'], currency=rows[-1]['currency'])
        result['estimates'] = dict(low=90, point=100, high=110, display_low=90, display_point=100,
                                   display_high=110, currency=rows[-1]['currency'])
        if status=='withheld':
            rows[-1].update(point='', low='', high='')
        rows[-1]['result_sha256'] = view.digest(view.canonical(result))
        audit_rows.append(a)
    counts = dict(generated=35, is_demo=0, total=50, withheld=15)
    refs = {'private-audit.json': put(root/'fixed/private-audit.json',
            dict(rows=audit_rows, counts=counts, input_sha256='c'*64, issued_at=NOW, report_cutoff=NOW)),
            'forecasts.csv': put(root/'fixed/forecasts.csv', csv_bytes(rows))}
    manifest = dict(schema_version=1, kind='private-forecast-csv', is_demo=False,
                    input_sha256='c'*64, counts=counts, source_status='caller_admission_not_independently_authenticated',
                    artifacts={k: dict(bytes=v['bytes'], sha256=v['sha256']) for k, v in refs.items()})
    return dict(product='fixed50', manifest=put(root/'fixed/manifest.json', manifest))


def build_standalone(root, count=100, speculative=0):
    codes = ['US.S%03d' % n for n in range(count+speculative)]
    payload = dict(schema_version=1, kind='stock-research-forecast-bundle', forecasts=[forecast(c, h) for c in codes for h in view.HORIZONS],
                   data_sha256='d'*64, issued_at_ms=MS-1000, as_of_ms=MS-2000, model_ref={'quality_status': 'research-only'})
    universe = dict(main=[{'code': c} for c in codes[:count]], speculative=[{'code': c} for c in codes[count:]])
    coverage = dict(main_instruments=len(universe['main']), speculative_instruments=len(universe['speculative']),
                    available_numerical_forecasts=len(codes)*4)
    values = {'universe.json': universe, 'coverage.json': {}, 'predictions.json': payload,
              'forecasts.csv': b'code\n', 'export_coverage.json': coverage}
    component_files = {
        'collection': ['universe.json', 'coverage.json', 'history.csv', 'history_revisions.csv', 'state.json',
                       'metadata_input.json', 'identity_bindings.json', 'calendar.json'],
        'prediction': ['predictions.json', 'outcomes.json'],
        'exports': ['forecasts.csv', 'export_coverage.json', 'master.csv', 'top20.csv', 'research.xlsx']}
    for name in sum(component_files.values(), []):
        values.setdefault(name, b'')
    refs = {k: put(root/'standalone'/k, v) for k, v in values.items()}
    components = {k: dict(schema_version=1, status='complete', artifacts=files, compatibility_id='test-contract')
                  for k, files in component_files.items()}
    manifest = dict(schema_version=1, kind='stock-research-run', is_demo=False, components_schema_version=1,
                    generated_at=NOW, compatibility_id='test-contract', components=components,
                    artifacts={k: dict(bytes=v['bytes'], sha256=v['sha256'], path=k) for k, v in refs.items()})
    return dict(product='standalone100', manifest=put(root/'standalone/manifest.json', manifest))


@pytest.fixture
def setup(tmp_path):
    tmp_path.chmod(0o700)
    products = [build_fixed(tmp_path), build_us(tmp_path), build_standalone(tmp_path)]
    bundle = dict(schema_version=1, read_roots=[str(tmp_path)], products=products)
    return tmp_path, bundle


def inspect(setup, at=NOW):
    root, bundle = setup
    ref = put(root/'inspection.json', bundle)
    return view.inspect(ref['path'], ref['sha256'], at)


def test_all_products_and_denominators(setup):
    result = inspect(setup)
    fixed, us, standalone = result['products']
    assert fixed['historical_counts']['generated'] == 35
    assert fixed['status_counts'] == {'ready': 35, 'withheld': 15}
    assert us['named_names'] == 30 and us['horizon_rows'] == 120
    assert us['status_counts'] == {'ready': 120} and us['historical_counts']['qualified'] == 0
    assert standalone['named_names'] == 100 and standalone['horizon_rows'] == 400
    assert all(not r['execution_authorized'] for p in result['products'] for r in p['rows'])
    assert result['mode'] == 'offline-read-only'


def test_historical_completion_survives_expiry_and_staleness(setup):
    us = inspect(setup, '2026-11-01T01:00:00+08:00')['products'][1]
    assert us['disposition'] == 'completed' and us['release_state'] == 'expired'
    assert us['status_counts'] == {'stale': 120}
    assert us['historical_counts']['available'] == 120


def test_missing_standalone_no_invented_names(setup):
    setup[1]['products'][2]['manifest'] = None
    p = inspect(setup)['products'][2]
    assert p['named_names'] == 0 and p['unnamed_slots'] == 100 and not p['rows']


def test_standalone_shortfall(setup):
    setup[1]['products'][2] = build_standalone(setup[0], 12)
    p = inspect(setup)['products'][2]
    assert p['named_names'] == 12 and p['unnamed_slots'] == 88 and p['horizon_rows'] == 48


def test_speculative_names_do_not_fill_main100(setup):
    setup[1]['products'][2] = build_standalone(setup[0], 90, 10)
    p = inspect(setup)['products'][2]
    assert p['named_names'] == p['main_names'] == 90 and p['unnamed_slots'] == 10
    assert p['speculative_names'] == 10 and p['horizon_rows'] == 400


def test_full100_plus10_supported(setup):
    setup[1]['products'][2] = build_standalone(setup[0], 100, 10)
    p = inspect(setup)['products'][2]
    assert p['disposition'] == 'completed-generation'
    assert p['main_names'] == p['named_names'] == 100 and p['speculative_names'] == 10
    assert p['unnamed_slots'] == 0 and p['horizon_rows'] == 440


def repin_us(setup, mutation):
    d = setup[1]['products'][1]
    attempt = Path(d['attempt'])
    generation = attempt/'2026-10-30_010000'
    payload = json.loads((generation/'predictions.json').read_text())
    mutation(payload['forecasts'][0], payload)
    for row in payload['forecasts']:
        row['forecast_id'] = view.digest(view.canonical({k:v for k,v in row.items() if k!='forecast_id'}))
    pred = put(generation/'predictions.json', payload)
    counts = dict(keys=len(payload['forecasts']), available=sum(r['status']=='available' for r in payload['forecasts']),
                  withheld=sum(r['status']!='available' for r in payload['forecasts']),
                  qualified=sum(r['validation']['qualified'] for r in payload['forecasts']),
                  actions=sorted({r['decision']['action'] for r in payload['forecasts']}))
    coverage = put(generation/'coverage.json', counts | dict(research_only=True, promotion=False, training=False))
    manifest = json.loads((generation/'manifest.json').read_text())
    manifest['artifacts']['predictions.json'].update(sha256=pred['sha256'], bytes=pred['bytes'])
    manifest['artifacts']['coverage.json'].update(sha256=coverage['sha256'], bytes=coverage['bytes'])
    mref = put(generation/'manifest.json', manifest)
    child = json.loads((attempt/'child-approved.json').read_text())
    child['counts'] = counts
    child['artifact_hashes'].update({'predictions.json': pred['sha256'], 'manifest.json': mref['sha256'], 'coverage.json':coverage['sha256']})
    cref = put(attempt/'child-approved.json', child)
    parent = json.loads((attempt/'parent-approved.json').read_text())
    parent['artifact_hashes'] = child['artifact_hashes']
    parent['child_approval_sha256'] = cref['sha256']
    pref = put(attempt/'parent-approved.json', parent)
    receipt = json.loads(Path(d['receipt']['path']).read_text())
    receipt.update(child_approval_sha256=cref['sha256'], parent_approval_sha256=pref['sha256'],
                   counts=counts, status='complete' if counts['available']==120 else 'partial')
    d['receipt'] = put(Path(d['receipt']['path']), receipt)


@pytest.mark.parametrize('case', ['bool', 'string', 'axes', 'crossed', 'conversion', 'currency', 'basis',
    'reference', 'window-length', 'window-start', 'window-time', 'identity', 'input-hash', 'duplicate', 'withheld-numbers'])
def test_hash_consistent_invalid_payload_rejected(setup, case):
    def mutate(row, payload):
        if case in ('bool', 'string'):
            row['model']['price_quantiles'][0][0] = True if case=='bool' else '90'
        elif case=='axes':
            row['model']['targets'] = ['terminal_logreturn']
        elif case=='crossed':
            row['model']['price_quantiles'][0] = [110, 100, 90]
        elif case=='conversion':
            row['model']['price_quantiles'][0][0] = 80
        elif case in ('currency', 'basis'):
            row['reference']['currency' if case=='currency' else 'adjustment'] = 'INR' if case=='currency' else 'unknown'
        elif case=='reference':
            row['reference']['session_date'] = '2026-10-27'
        elif case=='window-length':
            row['window']['sessions'].append('2026-10-31')
        elif case=='window-start':
            row['window']['start'] = '2026-10-31'
        elif case=='window-time':
            row['window']['first_open_ms'] += 1
        elif case=='identity':
            row['instrument']['stock_id'] = '123'
        elif case=='input-hash':
            row['input_data_sha256'] = 'e'*64
        elif case=='duplicate':
            payload['forecasts'][1] = copy.deepcopy(row)
        else:
            row['status'] = 'unavailable'
    repin_us(setup, mutate)
    p = inspect(setup)['products'][1]
    assert p['disposition'] == 'incompatible' and p['status_counts'] == {'incompatible':120}


def test_partial_delivery_preserves_withholding(setup):
    def mutate(row, payload):
        row.update(status='unavailable', model=None, baseline=None, reasons=['history-missing'])
    repin_us(setup, mutate)
    p = inspect(setup)['products'][1]
    assert p['disposition'] == 'partial'
    assert p['historical_counts']['available'] == 119 and p['historical_counts']['withheld'] == 1
    assert p['status_counts'] == {'ready':119, 'withheld':1}
    assert p['rows'][0]['blocker']=='history-missing'


def test_hash_consistent_unverified_cleanup_rejected(setup):
    d = setup[1]['products'][1]
    attempt = Path(d['attempt'])
    sref = put(attempt/'supervisor-receipt.json', dict(approved=True, cleanup_verified=False))
    parent = json.loads((attempt/'parent-approved.json').read_text())
    parent['supervisor_receipt_sha256'] = sref['sha256']
    pref = put(attempt/'parent-approved.json', parent)
    receipt = json.loads(Path(d['receipt']['path']).read_text())
    receipt['parent_approval_sha256'] = pref['sha256']
    d['receipt'] = put(Path(d['receipt']['path']), receipt)
    assert inspect(setup)['products'][1]['blocker']=='approval-or-cleanup-missing'


@pytest.mark.parametrize('field,value', [('currency','INR'), ('point','999.00'), ('low','True'),
    ('reference_close','0'), ('target_session','2026-10-28'), ('target_close_at','2026-10-29T01:00:00+08:00')])
def test_hash_consistent_invalid_fixed_csv_rejected(setup, field, value):
    d = setup[1]['products'][0]
    base = Path(d['manifest']['path']).parent
    rows = list(csv.DictReader(io.StringIO((base/'forecasts.csv').read_text())))
    rows[0][field] = value
    csvref = put(base/'forecasts.csv', csv_bytes(rows))
    manifest = json.loads(Path(d['manifest']['path']).read_text())
    manifest['artifacts']['forecasts.csv'].update(sha256=csvref['sha256'], bytes=csvref['bytes'])
    d['manifest'] = put(Path(d['manifest']['path']), manifest)
    assert inspect(setup)['products'][0]['disposition'] == 'incompatible'


@pytest.mark.parametrize('file', ['predictions.json', 'forecasts.csv', 'coverage.json', 'manifest.json'])
def test_tampered_artifact_never_completed(setup, file):
    attempt = Path(setup[1]['products'][1]['attempt'])
    (attempt/'2026-10-30_010000'/file).write_bytes(b'{}')
    p = inspect(setup)['products'][1]
    assert p['disposition'] == 'incompatible' and p['blocker'] == 'hash-or-size-mismatch'
    assert p['named_names'] == 30 and p['status_counts'] == {'incompatible': 120}


@pytest.mark.parametrize('file', ['child-approved.json', 'parent-approved.json', 'supervisor-receipt.json', 'claim.json'])
def test_missing_approval_or_claim(setup, file):
    (Path(setup[1]['products'][1]['attempt'])/file).unlink()
    assert inspect(setup)['products'][1]['disposition'] == 'incompatible'


def test_consumed_release_safe_action(setup):
    d = setup[1]['products'][1]
    Path(d['receipt']['path']).unlink()
    d['receipt'] = None
    p = inspect(setup)['products'][1]
    assert p['disposition'] == 'consumed-release' and p['horizon_rows'] == 120
    assert 'Never reuse or retry' in p['next_action']


def test_expired_unconsumed_release(setup):
    d = setup[1]['products'][1]
    shutil.rmtree(d['attempt'])
    d['receipt'] = None
    p = inspect(setup, '2026-10-30T01:00:01+08:00')['products'][1]
    assert p['disposition'] == 'expired-release' and not p['attempt_consumed']


def test_interrupted_before_claim_still_consumes_attempt(setup):
    d = setup[1]['products'][1]
    Path(d['receipt']['path']).unlink()
    Path(d['attempt'], 'claim.json').unlink()
    d['receipt'] = None
    p = inspect(setup)['products'][1]
    assert p['disposition'] == 'interrupted' and p['attempt_consumed']


def test_unlisted_receipt_rejected(setup):
    setup[1]['products'][1]['receipt'] = None
    assert inspect(setup)['products'][1]['blocker'] == 'unlisted-delivery-receipt'


def test_release_mismatch(setup):
    d = setup[1]['products'][1]
    release = json.loads(Path(d['release']['path']).read_text())
    release['run_id'] = 'other'
    d['release'] = put(Path(d['release']['path']), release)
    assert inspect(setup)['products'][1]['blocker'] == 'release-binding-mismatch'


@pytest.mark.parametrize('change', ['symlink', 'permissions', 'outside', 'bool-bytes', 'bad-pin'])
def test_reference_rejections(setup, tmp_path, change):
    d = setup[1]['products'][0]
    ref = d['manifest']
    path = Path(ref['path'])
    if change == 'symlink':
        target = path.with_name('original.json')
        path.rename(target)
        path.symlink_to(target)
    elif change == 'permissions':
        path.chmod(0o644)
    elif change == 'outside':
        ref['path'] = '/tmp/does-not-need-to-exist.json'
    elif change == 'bool-bytes':
        ref['bytes'] = True
    else:
        ref['sha256'] = '0'*64
    assert inspect(setup)['products'][0]['disposition'] == 'incompatible'


@pytest.mark.parametrize('change', ['unknown', 'duplicate-product', 'bool-version', 'bad-time', 'wrong-pin'])
def test_bundle_rejections(setup, change):
    root, bundle = setup
    at = NOW
    if change == 'unknown':
        bundle['approved'] = True
    elif change == 'duplicate-product':
        bundle['products'][2] = copy.deepcopy(bundle['products'][1])
    elif change == 'bool-version':
        bundle['schema_version'] = True
    elif change == 'bad-time':
        at = '2026-10-30'
    ref = put(root/'inspection.json', bundle)
    with pytest.raises(view.Invalid):
        view.inspect(ref['path'], '0'*64 if change=='wrong-pin' else ref['sha256'], at)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'not json'])
def test_malformed_json(raw):
    with pytest.raises(view.Invalid):
        view.decode(raw)


def test_future_evidence_rejected(setup):
    result = inspect(setup, '2026-10-29T01:00:00+08:00')
    assert all(p['disposition']=='incompatible' for p in result['products'])


def test_budget_and_fifo_rejections(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    ref = put(tmp_path/'file.json', b'12345')
    monkeypatch.setattr(view, 'FILE_LIMIT', 4)
    with pytest.raises(view.Invalid, match='file-size-budget'):
        view.Reader([str(tmp_path)]).raw(ref['path'])
    fifo = tmp_path/'pipe'
    os.mkfifo(fifo, 0o600)
    with pytest.raises(view.Invalid, match='private-file-required'):
        view.Reader([str(tmp_path)]).raw(str(fifo))


def test_mutation_recheck(tmp_path):
    tmp_path.chmod(0o700)
    ref = put(tmp_path/'a.json', b'123')
    reader = view.Reader([str(tmp_path)])
    reader.ref(ref)
    put(tmp_path/'a.json', b'456')
    with pytest.raises(view.Invalid, match='file-changed'):
        reader.unchanged()


def test_cli_clean_directory_read_only(setup, tmp_path):
    root, bundle = setup
    bundle['products'][2]['manifest'] = None
    ref = put(root/'inspection.json', bundle)
    before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    command = [sys.executable, '-I', '-B', str(SCRIPT), '--bundle', ref['path'], '--bundle-sha256', ref['sha256'],
               '--review-at', NOW, '--format', 'json']
    result = subprocess.run(command, cwd='/tmp', capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert json.loads(result.stdout)['products'][1]['historical_counts']['available'] == 120
    assert before == {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert not result.stderr


def test_no_execution_imports():
    import ast
    tree = ast.parse(SCRIPT.read_text())
    imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
    assert not set(imports) & {'subprocess', 'socket', 'requests', 'joblib', 'pickle', 'inference', 'provider'}


def test_text_includes_owner_and_next_action(setup):
    text = view.render(inspect(setup))
    assert '35' in text and '100/100' in text and 'US.N00' in text
    assert 'Trader / AI Engineer' in text and 'Resolve exact evidence' in text
