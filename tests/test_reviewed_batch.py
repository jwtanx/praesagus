"""Fictional reviewed batches and real local process failures; no providers or fits."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import time
import types

import numpy as np
import pytest

REFERENCE = '2026-10-28'
FLOOR, DEADLINE = 1793246400000, 1793280600000

DIRECTORY = Path(__file__).resolve().parents[1] / 'scripts/stock-research'
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location('reviewed_batch', DIRECTORY / 'run_reviewed_batch.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
from data import GAPS
from market_calendar import MarketCalendar
from model import WINDOW_POLICY
from storage import HISTORY_COLUMNS


def put(path, value, raw=False):
    path.write_bytes(value if raw else batch.canonical(value))
    path.chmod(0o600)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


class FakeModel:
    """Existing model interface only; fitting would fail this test immediately."""
    def __init__(self, invalid=False):
        self.invalid = invalid
        self.calls = 0

    def predict(self, rows):
        self.calls += 1
        values = [[-.03, -.02, -.01], [.01, .02, .03], [-.01, .013, .03]]
        if self.invalid and self.calls == 1:
            values[0] = [.1, -.1, .2]
        array = np.asarray([values for _ in rows], dtype=float)
        return dict(model=array, baseline=array.copy(), valid=np.ones(len(rows), dtype=bool))

    def fit(self, *args, **kwargs):
        raise AssertionError('reviewed batch cannot fit')


@pytest.fixture
def packet(tmp_path, monkeypatch, request):
    root = tmp_path.resolve()
    root.chmod(0o700)
    inputs, models, output = [root / p for p in ('inputs', 'models', 'output')]
    for folder in (inputs, models, output):
        folder.mkdir(mode=0o700)
    folder = models / 'fictional-generation'
    folder.mkdir(mode=0o700)
    calendar = MarketCalendar('2026-01-01', '2026-12-31')
    reference = getattr(request, 'param', REFERENCE)
    from zoneinfo import ZoneInfo
    from datetime import date, timedelta
    floor = int(datetime.combine(date.fromisoformat(reference)+timedelta(days=1), datetime.min.time(), tzinfo=ZoneInfo('America/New_York')).timestamp()*1000)
    deadline = calendar.open_ms(calendar.windows(reference)['1d'][0])
    known, as_of, now = floor+1000, floor+5000, floor+6000
    dates = calendar.trailing_sessions(reference, 51)
    bindings = [dict(code=code, stock_id=i+1, known_at_ms=known, retrieved_at_ms=known)
                for i, code in enumerate(batch.CODES)]
    receipt = dict(identity_bindings=bindings, source_admitted=True, inference_admission=True,
                   training_admission=False, public_admission=False, strong_model_promotion=False,
                   reference=reference, rows_per_code=51, source_revision_held_codes=[],
                   shared_training_dates_by_code=dict.fromkeys(batch.CODES, [d for d in dates if d <= '2026-10-23']),
                   native_currency_literal=None, currency_interpretation='scoped-financial-USD-not-vendor-literal',
                   financial_review_known_ms=known, inference_purpose_review_known_ms=known,
                   lead_interface_admission_known_ms=known, source_completed_at_ms=known)
    instruments = [dict(code=b['code'], stock_id=b['stock_id'], asset_type='STOCK', sector_id='fiction',
                        issuer_group_id='fiction-'+b['code'], listing_verified=True, comparison_basis_verified=True,
                        metadata_known_at_ms=known, signed_leverage=1, instrument_class='stock') for b in bindings]
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=HISTORY_COLUMNS, lineterminator='\n')
    writer.writeheader()
    for code in batch.CODES:
        for i, day in enumerate(dates):
            close = calendar.close_ms(day)
            price = 100 + i*.1
            row = dict.fromkeys(HISTORY_COLUMNS)
            row.update(code=code, session_date=day, open=price, low=price-1, high=price+2, close=price+.5,
                       volume=1000+i, turnover=(1000+i)*price, currency='USD', adjustment='forward-excluding-dividends',
                       source='fiction-only', source_at_ms=close, raw_time_key=close, raw_date=int(day.replace('-', '')),
                       raw_time_zone=-300, time_zone_unit_status='runtime-unverified', time_zone_unit_source_url='https://example.invalid',
                       provider_finality_status='unverified', retrieved_at_ms=known, known_at_ms=known, price_known_at_ms=known,
                       currency_known_at_ms=known, revision_vintage='fiction-v1', completed=True, completion_status='completed',
                       volume_precision=0, currency_source_url='https://example.invalid', currency_evidence_hash='a'*64, currency_status='verified')
            writer.writerow(row)
    refs = dict(history_csv=put(inputs/'history.csv', stream.getvalue().encode(), raw=True),
                receipt=put(inputs/'receipt.json', receipt), instruments=put(inputs/'instruments.json', instruments))
    training_stream = io.StringIO(newline='')
    training_writer = csv.DictWriter(training_stream, fieldnames=HISTORY_COLUMNS, lineterminator='\n')
    training_writer.writeheader()
    training_writer.writerows(r for r in csv.DictReader(io.StringIO(stream.getvalue())) if r['session_date'] <= '2026-10-23')
    training_ref = put(inputs/'training.csv', training_stream.getvalue().encode(), raw=True)
    contract = dict(feature_variant='no-benchmark', window_policy=WINDOW_POLICY,
                    calendar_policy=dict(name='XNYS', version=calendar.version),
                    adjustment_policy=dict(required_basis='forward-excluding-dividends', currency='USD'),
                    training_boundaries=dict(cutoff_ms=floor-100000, max_available_at=floor-100000),
                    calibration_boundaries=None, quality_status='research-only',
                    provenance=dict(policy='research-retrospective', declared_gaps=sorted(GAPS), inputs=[dict(identity_bindings=bindings, file_sha256=training_ref['sha256'])]))
    cr = put(folder/'model_contract.json', contract)
    ar = put(folder/'model.joblib', b'not-a-pickle; fake loader in tests only', raw=True)
    fr = put(folder/'freeze.json', dict(fictional=True))
    manifest = dict(schema_version=1, kind='stock-research-model', strong_model_accepted=False,
                    generated_at=datetime.fromtimestamp((floor-60000)/1000, timezone.utc).isoformat(),
                    artifacts={Path(ref['path']).name: dict(path=Path(ref['path']).name, sha256=ref['sha256'], bytes=ref['bytes'])
                               for ref in (cr, ar, fr)})
    mr = put(folder/'manifest.json', manifest)
    child = put(inputs/'fit-child.json', dict(generation=str(folder), trusted_reload=True, calibrated=False, model_promotion=False,
                 manifest_sha256=mr['sha256'], model_contract_sha256=cr['sha256'], completed_at_ms=floor-50000))
    supervisor = put(inputs/'fit-resource.json', dict(cleanup_verified=True))
    parent = put(inputs/'fit-parent.json', dict(generation=str(folder), approved_research_artifact=True, model_promotion=False,
                  fit_completed_receipt_sha256=child['sha256'], supervisor_receipt_sha256=supervisor['sha256'],
                  model_known_not_before_ms=floor-40000))
    model = dict(folder=str(folder), contract=cr, manifest=mr, artifact=ar, child_fit_approval=child, parent_fit_approval=parent)
    source = dict(kind='reviewed-source-admission', approved=True, reference_session=reference,
                  source_not_before_ms=floor, issue_before_ms=deadline,
                  known_at_ms=known, inputs_sha256={k: v['sha256'] for k, v in refs.items()},
                  qualifications=dict(native_currency=None, financial_currency='USD', provider_formula_certified=False,
                                      dividend_exclusion_certified=False, cash_added=False),
                  basis_evidence={c: dict(request_label_only=True, cash_added=False, provider_formula_certified=False,
                                         dividend_exclusion_certified=False) for c in batch.BASIS_CODES},
                  source_completed_at_ms=known, financial_review_known_ms=known, inference_purpose_review_known_ms=known,
                  lead_interface_admission_known_ms=known)
    refs['source_review'] = put(inputs/'source-review.json', source)
    compat = dict(kind='reviewed-model-compatibility', approved=True, known_at_ms=known, generation=str(folder), reference_session=reference,
                  source_not_before_ms=floor, issue_before_ms=deadline,
                  source_review_sha256=refs['source_review']['sha256'], inputs_sha256=source['inputs_sha256'],
                  model_sha256={k: v['sha256'] for k, v in model.items() if k != 'folder'})
    refs['model_compatibility_review'] = put(inputs/'compatibility-review.json', compat)
    runtime = [dict(repo_path=p, sha256=batch.digest((batch.ROOT/p).read_bytes()), bytes=(batch.ROOT/p).stat().st_size)
               for p in sorted(batch.RUNTIME)]
    # Production starts isolated. Tests temporarily remove unrelated suite imports
    # and use the same verified-buffer loader, restoring pytest's state afterwards.
    monkeypatch.setattr(sys, 'meta_path', list(sys.meta_path))
    for name in ('data', 'storage', 'market_calendar', 'features', 'model', 'inference', 'ranking', 'export'):
        monkeypatch.delitem(sys.modules, name, raising=False)
    bundle = dict(schema_version=1, kind='praesagus-reviewed-inference-bundle', purpose='private-unvalidated-research',
                  read_roots=[str(inputs), str(models)], trusted_model_root=str(models), output_parent=str(output),
                  inputs=refs, model=model, runtime_files=runtime, data_files=[fr, supervisor, training_ref],
                  calendar=dict(name='XNYS', version=calendar.version, start='2026-01-01', end='2026-12-31'),
                  expected_codes=batch.CODES, horizons=batch.HORIZONS, reference_session=reference,
                  as_of_ms=as_of, minimum_known_ms=as_of, source_not_before_ms=floor, issue_before_ms=deadline,
                  limits=batch.LIMITS, feature_variant=dict(metadata=[], dated_metadata={}, benchmark=None), output_policy=batch.POLICY)
    bp = inputs/'bundle.json'
    br = put(bp, bundle)
    review = put(inputs/'release-review.json', dict(approved=True, bundle_sha256=br['sha256'], run_id='fictional', known_at_ms=now, reference_session=reference, source_not_before_ms=floor, issue_before_ms=deadline))
    release = dict(schema_version=1, kind='praesagus-reviewed-inference-release', approved=True, bundle_sha256=br['sha256'],
                   run_id='fictional', not_before_ms=now, expires_at_ms=now+60000, resources_confirmed=True,
                   exclusive_local_run_confirmed=True, review_reference=review)
    rp = inputs/'release.json'
    put(rp, release)
    monkeypatch.setattr(batch, 'now_ms', lambda: now)
    batch.install_runtime(batch.runtime_check(bundle))
    return dict(bundle=bundle, bp=bp, sha=br['sha256'], release=release, rp=rp, output=output,
                source=source, compat=compat, receipt=receipt, contract=contract, calendar=calendar, now=now, inputs=inputs)


def rebind(packet):
    ref = put(packet['bp'], packet['bundle'])
    packet['sha'] = ref['sha256']
    packet['release']['bundle_sha256'] = ref['sha256']
    packet['release']['review_reference'] = put(packet['inputs']/'release-review.json',
        dict(approved=True, bundle_sha256=ref['sha256'], run_id=packet['release']['run_id'], known_at_ms=packet['now'],
             **{k: packet['bundle'][k] for k in ('reference_session', 'source_not_before_ms', 'issue_before_ms')}))
    put(packet['rp'], packet['release'])


def args(packet, *extra):
    return ['--bundle', str(packet['bp']), '--bundle-sha256', packet['sha'], '--release', str(packet['rp']), *extra]


def fake_pipeline(packet, monkeypatch, *, invalid=False):
    import inference
    model = FakeModel(invalid)
    def load(*a, **kw):
        return model, packet['contract'], dict(artifact_known_at_ms=FLOOR-40000,
                    model_sha256=packet['bundle']['model']['artifact']['sha256'],
                    artifact_manifest_sha256=packet['bundle']['model']['manifest']['sha256'],
                    contract_sha256=batch.digest(batch.canonical(packet['contract'])),
                    training_data_sha256='c'*64, quality_status='research-only')
    monkeypatch.setattr(inference, 'load_existing_model', load)
    def supervise(command):
        # Exercise the real worker, CSV reader, causal features, quantile conversion,
        # export and parent approvals. Only loading and OS supervision are replaced.
        status = batch.child_run(packet['bp'], packet['sha'], packet['rp'], packet['output']/'fictional')
        return dict(approved=True, cleanup_verified=True, returncode=status, reason=None, elapsed_seconds=.5,
                    peak_group_rss_bytes=1000000, limits=batch.LIMITS)
    monkeypatch.setattr(batch, 'supervise', supervise)
    return model


def test_synthetic_end_to_end_120_keys_and_hash_bound_approvals(packet, monkeypatch, capsys):
    model = fake_pipeline(packet, monkeypatch)
    assert batch.main(args(packet)) == 0
    delivered = json.loads(capsys.readouterr().out)
    assert delivered['counts'] == dict(keys=120, available=120, withheld=0, qualified=0, actions=['NO TRADE'])
    folder = Path(delivered['generation'])
    model_ref = json.loads((folder/'predictions.json').read_text())['model_ref']
    assert model_ref['trusted_artifact_folder'] == packet['bundle']['model']['folder']
    assert model_ref['snapshot_is_new_model_generation'] is False
    assert model_ref['verified_snapshot_folder'] != model_ref['trusted_artifact_folder']
    assert batch.digest((folder/'forecasts.csv').read_bytes()) == delivered['csv_sha256']
    assert model.calls == 120
    run = folder.parent
    assert batch.digest((run/'child-approved.json').read_bytes()) == delivered['child_approval_sha256']
    assert batch.digest((run/'parent-approved.json').read_bytes()) == delivered['parent_approval_sha256']
    assert (run/'delivery-receipt.json').exists()
    assert batch.main(args(packet)) == 2  # exclusive run ID is never retried
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'run_id_consumed'


def test_crossing_prediction_keeps_120_keys_blanks_and_nonzero_partial(packet, monkeypatch, capsys):
    fake_pipeline(packet, monkeypatch, invalid=True)
    assert batch.main(args(packet)) == 4
    report = json.loads(capsys.readouterr().out)
    assert report['counts']['available'] == 119 and report['counts']['withheld'] == 1
    with (Path(report['generation'])/'forecasts.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 120
    withheld = [r for r in rows if r['status'] == 'unavailable']
    assert len(withheld) == 1 and 'crossing-quantiles' in withheld[0]['reasons']
    assert all(v == '' for k, v in withheld[0].items() if k.startswith(('model_low_', 'model_high_', 'model_terminal_', 'baseline_low_', 'baseline_high_', 'baseline_terminal_')))


def test_check_only_never_loads_model_or_consumes_release(packet, monkeypatch, capsys):
    import inference
    monkeypatch.setattr(inference, 'load_existing_model', lambda *a, **k: pytest.fail('model load'))
    monkeypatch.setattr(batch, 'supervise', lambda *a, **k: pytest.fail('worker spawn'))
    assert batch.main(args(packet, '--check-only')) == 0
    assert json.loads(capsys.readouterr().out)['worker_started'] is False
    assert list(packet['output'].iterdir()) == []
    assert batch.main(['--bundle', str(packet['bp']), '--bundle-sha256', packet['sha'], '--check-only']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'inputs-checked-release-not-checked'


@pytest.mark.parametrize('mutation,reason', [
    (lambda b: b.update(as_of_ms=True), 'input_schema_invalid'),
    (lambda b: b.update(schema_version=True), 'dated_contract_mismatch'),
    (lambda b: b.update(unknown='ignored?'), 'input_schema_invalid'),
    (lambda b: b['limits'].update(work_seconds=60), 'dated_contract_mismatch'),
    (lambda b: b['runtime_files'].append(b['runtime_files'][0]), 'foreign_runtime_import'),
    (lambda b: b['runtime_files'][0].update(repo_path='../elsewhere.py'), 'foreign_runtime_import'),
    (lambda b: b['runtime_files'][0].update(sha256='0'*64), 'runtime_hash_mismatch'),
    (lambda b: b['data_files'].clear(), 'model_or_fit_approval_mismatch'),
    (lambda b: b.update(reference_session='9999-12-31'), 'invalid_or_missing_input'),
    (lambda b: b.update(reference_session='2026-2-3'), 'input_schema_invalid'),
    (lambda b: b.update(reference_session=True), 'input_schema_invalid'),
])
def test_bundle_rejections_before_worker(packet, mutation, reason, monkeypatch, capsys):
    packet['bundle'] = copy.deepcopy(packet['bundle'])
    mutation(packet['bundle'])
    rebind(packet)
    monkeypatch.setattr(batch, 'supervise', lambda *a, **k: pytest.fail('worker spawn'))
    assert batch.main(args(packet)) == 2
    assert json.loads(capsys.readouterr().out)['reason_code'] == reason
    assert not list(packet['output'].iterdir())


@pytest.mark.parametrize('value', [FLOOR-1, DEADLINE, DEADLINE+86400000])
def test_no_pre_finality_expired_or_automatic_rollover(packet, monkeypatch, value, capsys):
    monkeypatch.setattr(batch, 'now_ms', lambda: value)
    assert batch.main(args(packet)) == 2
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'issue_window_closed'


@pytest.mark.parametrize('kind', ['future_review', 'review_hash', 'fit_hash', 'cleanup', 'symlink', 'broad_root', 'missing'])
def test_review_fit_and_file_failures(packet, kind, capsys):
    b = packet['bundle']
    if kind in ('future_review', 'review_hash'):
        source = packet['source'].copy()
        source['known_at_ms'] = packet['now']+1 if kind == 'future_review' else source['known_at_ms']
        if kind == 'review_hash':
            source['inputs_sha256'] = {}
        b['inputs']['source_review'] = put(packet['inputs']/'source-review.json', source)
    elif kind == 'fit_hash':
        p = b['model']['child_fit_approval']['path']
        doc = json.loads(Path(p).read_text())
        doc['manifest_sha256'] = '0'*64
        b['model']['child_fit_approval'] = put(Path(p), doc)
    elif kind == 'cleanup':
        ref = b['data_files'][1]
        put(Path(ref['path']), dict(cleanup_verified=False))
    elif kind == 'symlink':
        p = Path(b['inputs']['history_csv']['path'])
        p.rename(p.with_suffix('.original'))
        p.symlink_to(p.with_suffix('.original'))
    elif kind == 'broad_root':
        b['read_roots'] = [str(Path.home())]
    else:
        Path(b['inputs']['history_csv']['path']).unlink()
    rebind(packet)
    assert batch.main(args(packet)) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'blocked'
    assert not list(packet['output'].iterdir())


def test_duplicate_json_and_nonfinite_rejected():
    for value in (b'{"a":1,"a":2}', b'{"a":NaN}'):
        with pytest.raises(batch.Blocked):
            batch.decode(value)


def test_release_is_non_circular_and_explicitly_hash_checked(packet):
    b, inventory, _, release = batch.preflight(packet['bp'], packet['sha'], packet['rp'])
    assert release['review_reference']['path'] not in inventory.raw
    Path(release['review_reference']['path']).write_text('{}')
    with pytest.raises(batch.Blocked, match='release_review_unlisted'):
        batch.release_check(b, packet['sha'], release, inventory, packet['now'])


def test_actual_subprocess_clean_directory_failure_is_actionable(tmp_path):
    result = subprocess.run([sys.executable, '-I', '-B', str(batch.SCRIPT), '--bundle', str(tmp_path/'missing.json'),
                             '--bundle-sha256', '0'*64], cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    report = json.loads(result.stdout)
    assert report['reason_code'] and report['action']
    assert not result.stderr
    result = subprocess.run([sys.executable, '-I', '-B', str(batch.SCRIPT), '--bundle', str(tmp_path/'missing.json'),
                             '--bundle-sha256', '0'*64, '--as-of', str(FLOOR)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2 and 'unrecognized arguments' in result.stderr
    result = subprocess.run([sys.executable, '-B', str(batch.SCRIPT), '--bundle', str(tmp_path/'missing.json'),
                             '--bundle-sha256', '0'*64], cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert json.loads(result.stdout)['reason_code'] == 'isolated_python_required'


@pytest.mark.parametrize('source,expected', [
    ('import time; time.sleep(.2)', None),
    ('import time; time.sleep(.1); raise SystemExit(7)', None),
    ('import time; time.sleep(10)', 'execution_timeout'),
    ('import time; x=bytearray(40*1024**2); time.sleep(10)', 'resource_limit'),
])
def test_real_process_exit_timeout_and_rss(source, expected):
    limits = dict(work_seconds=.35 if expected == 'execution_timeout' else 2,
                  cleanup_seconds=1, rss_bytes=20*1024**2 if expected == 'resource_limit' else 128*1024**2,
                  threads=1, retries=0)
    receipt = batch.supervise([sys.executable, '-I', '-B', '-c', source], limits=limits)
    assert receipt['cleanup_verified'] is True
    assert receipt['reason'] == expected
    assert receipt['approved'] is (expected is None and 'SystemExit' not in source)
    assert receipt['samples'] > 0 and receipt['peak_group_rss_bytes'] > 0
    assert receipt['elapsed_seconds'] <= limits['work_seconds']+limits['cleanup_seconds']


def test_supervisor_failure_never_approves_or_delivers(packet, monkeypatch, capsys):
    monkeypatch.setattr(batch, 'supervise', lambda *a: dict(approved=False, cleanup_verified=False,
                        reason='cleanup_unverified', returncode=0))
    assert batch.main(args(packet)) == 3
    run = packet['output']/'fictional'
    assert (run/'failure.json').exists() and (run/'supervisor-receipt.json').exists()
    assert not (run/'parent-approved.json').exists() and not (run/'delivery-receipt.json').exists()
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'cleanup_unverified'


def test_verified_buffer_ignores_matching_pyc_and_changed_source(tmp_path, monkeypatch):
    path = tmp_path/'reviewed_probe.py'
    bad = b"raise RuntimeError('UNPINNED_SENTINEL')\n"
    good = b'VERIFIED = True\n'.ljust(len(bad), b' ')
    path.write_bytes(bad)
    py_compile.compile(str(path), doraise=True)
    stamp = path.stat().st_mtime
    path.write_bytes(good)
    os.utime(path, (stamp, stamp))
    # A conventional loader would accept the timestamp/size-matching bad pyc.
    monkeypatch.setattr(sys, 'meta_path', list(sys.meta_path))
    monkeypatch.delitem(sys.modules, 'reviewed_probe', raising=False)
    batch.install_runtime({'reviewed_probe': (str(path), good)})
    # Change source AFTER verification as well; the verified buffer still wins.
    path.write_bytes(bad)
    import reviewed_probe
    assert reviewed_probe.VERIFIED is True
    sys.modules.pop('reviewed_probe', None)


def test_preloaded_module_at_correct_path_still_rejected(packet, monkeypatch):
    foreign = types.ModuleType('inference')
    foreign.__file__ = str(DIRECTORY/'inference.py')
    monkeypatch.setitem(sys.modules, 'inference', foreign)
    with pytest.raises(batch.Blocked, match='foreign_runtime_import'):
        batch.runtime_check(packet['bundle'])


def test_import_finder_rejects_unlisted_local_dependency(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, 'ROOT', tmp_path)
    path = tmp_path/'unlisted_dependency.py'
    path.write_text("raise AssertionError('must not execute')")
    monkeypatch.setattr(sys, 'path', [str(tmp_path), *sys.path])
    monkeypatch.setattr(sys, 'meta_path', list(sys.meta_path))
    batch.install_runtime({})
    with pytest.raises(ImportError, match='foreign_runtime_import'):
        __import__('unlisted_dependency')


def test_observed_detached_descendant_stays_in_scope_and_pid_reuse_does_not():
    owned = {}
    first = {100: (1, 100, 1000, 'birth-a'), 101: (100, 101, 2000, 'birth-b')}
    assert batch.process_scope(first, 100, owned) == {100, 101}
    # Reparented, separate session/process group; retained through observed birth.
    detached = {101: (1, 101, 2000, 'birth-b')}
    assert batch.process_scope(detached, 100, owned) == {101}
    reused = {101: (1, 101, 2000, 'different-birth')}
    assert batch.process_scope(reused, 100, owned) == set()


def test_unobserved_fast_child_never_approves(monkeypatch):
    monkeypatch.setattr(batch, 'process_snapshot', lambda **kw: {})
    receipt = batch.supervise([sys.executable, '-I', '-B', '-c', 'pass'],
                              limits=dict(work_seconds=2, cleanup_seconds=1, rss_bytes=128*1024**2, threads=1, retries=0))
    assert receipt['approved'] is False and receipt['reason'] == 'rss_unobserved'
    assert receipt['observed_process_count'] == 0 and receipt['peak_group_rss_bytes'] == 0


def test_cleanup_monitor_failure_never_approves(monkeypatch):
    original = batch.process_snapshot
    calls = 0
    def failing(**kwargs):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise subprocess.TimeoutExpired('ps', .25)
        return original(**kwargs)
    monkeypatch.setattr(batch, 'process_snapshot', failing)
    result = batch.supervise([sys.executable, '-I', '-B', '-c', 'import time;time.sleep(.2)'],
                             limits=dict(work_seconds=2, cleanup_seconds=1, rss_bytes=128*1024**2, threads=1, retries=0))
    assert result['approved'] is False and result['cleanup_verified'] is False


def test_three_historical_origins_resolve_only_exact_hashes(packet, monkeypatch):
    # Same three origin names as the accepted map, fictional bytes and portable
    # snapshot paths. No current repository origin is opened by this test.
    originals = {}
    entries = []
    snapshots = []
    for i, relative in enumerate(batch.HISTORICAL_ORIGINS):
        snapshot = put(packet['inputs']/('snapshot-'+str(i)+'.txt'), b'fictional accepted origin '+str(i).encode(), raw=True)
        snapshots.append(snapshot)
        originals[relative] = snapshot['sha256']
        entries.append(dict(historical_input_path=relative, original_path=str(batch.ROOT/relative),
                            original_sha256=snapshot['sha256'], snapshot=snapshot))
    mapping = put(packet['inputs']/'resolution-map.json', dict(entries=entries))
    monkeypatch.setattr(batch, 'ARCHIVE_MAP_SHA', mapping['sha256'])
    monkeypatch.setattr(batch, 'HISTORICAL_ORIGINS', originals)
    packet['bundle']['data_files'] += [mapping, *snapshots]
    claims = [dict(path=e['original_path'], sha256=e['original_sha256'], bytes=e['snapshot']['bytes']) for e in entries]
    packet['bundle']['data_files'] += claims
    original_read = batch.read_file
    def checked(path, **kwargs):
        assert str(path) not in {e['original_path'] for e in entries}
        return original_read(path, **kwargs)
    monkeypatch.setattr(batch, 'read_file', checked)
    inventory = batch.Inventory(packet['bundle'])
    for entry in entries:
        inventory.closed(entry)
        assert inventory.hashes[entry['original_path']] == entry['original_sha256']
    bad = copy.deepcopy(entries[0])
    bad['original_sha256'] = '0'*64
    with pytest.raises(batch.Blocked, match='historical_archive_mismatch'):
        inventory.closed(bad)
    packet['bundle']['data_files'][-1] = dict(claims[-1], sha256='0'*64)
    with pytest.raises(batch.Blocked, match='historical_archive_mismatch'):
        batch.Inventory(packet['bundle'])


def test_original_mutation_after_staging_cannot_change_consumed_csv_or_model(packet, monkeypatch, capsys):
    model = fake_pipeline(packet, monkeypatch)
    original = batch.calendar_and_history
    consumed = {}
    def mutate(bundle, inventory, *, csv_path=None):
        assert csv_path is not None
        # Original files are changed only in this fictional fixture after staging.
        Path(bundle['inputs']['history_csv']['path']).write_bytes(b'changed outside staged read')
        Path(bundle['model']['artifact']['path']).write_bytes(b'changed outside staged read')
        assert batch.digest(Path(csv_path).read_bytes()) == bundle['inputs']['history_csv']['sha256']
        staged_model = Path(csv_path).parent/'models/accepted-model/model.joblib'
        assert batch.digest(staged_model.read_bytes()) == bundle['model']['artifact']['sha256']
        result = original(bundle, inventory, csv_path=csv_path)
        consumed['rows'] = len(result[1].rows)
        return result
    monkeypatch.setattr(batch, 'calendar_and_history', mutate)
    assert batch.main(args(packet)) == 3
    assert consumed['rows'] == 1530 and model.calls == 120
    # Post-run recheck detects changed originals, retaining the failed attempt.
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'input_hash_mismatch'
    assert not (packet['output']/'fictional/delivery-receipt.json').exists()


@pytest.mark.parametrize('change', ['expired', 'too_long', 'boolean_clock', 'unapproved', 'wrong_bundle'])
def test_finite_release_semantics(packet, change):
    bundle, inventory, _, release = batch.preflight(packet['bp'], packet['sha'], packet['rp'])
    release = copy.deepcopy(release)
    if change == 'expired':
        release['expires_at_ms'] = packet['now']
    elif change == 'too_long':
        release['expires_at_ms'] = release['not_before_ms']+600001
    elif change == 'boolean_clock':
        release['not_before_ms'] = True
    elif change == 'unapproved':
        release['approved'] = False
    else:
        release['bundle_sha256'] = '0'*64
    with pytest.raises(batch.Blocked):
        batch.release_check(bundle, packet['sha'], release, inventory, packet['now'])


def test_review_availability_and_fit_cleanup_semantic_guards(packet):
    bundle, inventory, _, _ = batch.preflight(packet['bp'], packet['sha'], packet['rp'])
    source = inventory.document(bundle['inputs']['source_review'])
    source['known_at_ms'] = bundle['as_of_ms']+1
    with pytest.raises(batch.Blocked):
        batch.reviews_check(bundle, inventory)
    source['known_at_ms'] = bundle['as_of_ms']
    assert batch.reviews_check(bundle, inventory) is source
    child = inventory.document(bundle['model']['child_fit_approval'])
    child['completed_at_ms'] = bundle['as_of_ms']+1
    with pytest.raises(batch.Blocked):
        batch.fit_check(bundle, inventory)
    child['completed_at_ms'] = FLOOR-50000
    parent = inventory.document(bundle['model']['parent_fit_approval'])
    resource = inventory.by_hash(parent['supervisor_receipt_sha256'])
    resource['cleanup_verified'] = False
    with pytest.raises(batch.Blocked, match='cleanup_unverified'):
        batch.fit_check(bundle, inventory)


def test_late_finish_has_no_parent_or_delivery_approval(packet, monkeypatch, capsys):
    fake_pipeline(packet, monkeypatch)
    supervised = batch.supervise
    def late(command):
        receipt = supervised(command)
        monkeypatch.setattr(batch, 'now_ms', lambda: DEADLINE)
        return receipt
    monkeypatch.setattr(batch, 'supervise', late)
    assert batch.main(args(packet)) == 3
    run = packet['output']/'fictional'
    assert (run/'child-approved.json').exists()
    assert (run/'supervisor-receipt.json').exists()
    assert not (run/'parent-approved.json').exists() and not (run/'delivery-receipt.json').exists()
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'issue_window_closed'


@pytest.mark.parametrize('defect', ['invalid_price', 'historical_metadata'])
def test_invalid_available_export_is_rejected_without_quantile_repair(packet, monkeypatch, capsys, defect):
    import inference
    fake_pipeline(packet, monkeypatch)
    build = inference.build_forecasts
    def broken(*args, **kwargs):
        payload = build(*args, **kwargs)
        if defect == 'invalid_price':
            payload['forecasts'][0]['model']['price_quantiles'][0][0] = -1
        else:
            payload['forecasts'][0]['features']['instrument_class'] = 'stock'
        return payload
    monkeypatch.setattr(inference, 'build_forecasts', broken)
    assert batch.main(args(packet)) == 3
    run = packet['output']/'fictional'
    assert not (run/'child-approved.json').exists() and not (run/'delivery-receipt.json').exists()
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'


@pytest.mark.parametrize('packet,shared_count,midnight_utc_hour,open_utc_hour', [
    ('2026-10-29', 47, 4, 13),
    ('2026-10-30', 46, 4, 14),  # Friday: next open is Monday after DST ends.
    ('2026-11-02', 45, 5, 14),
], indirect=['packet'])
def test_alternative_explicit_reviewed_dates_weekend_dst_no_code_change(
        packet, shared_count, midnight_utc_hour, open_utc_hour, monkeypatch, capsys):
    fake_pipeline(packet, monkeypatch)
    assert batch.main(args(packet)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['counts']['available'] == 120
    payload = json.loads((Path(report['generation'])/'predictions.json').read_text())
    reference = packet['bundle']['reference_session']
    assert reference != REFERENCE and all(r['origin'] == reference for r in payload['forecasts'])
    assert {len(d) for d in packet['receipt']['shared_training_dates_by_code'].values()} == {shared_count}
    assert datetime.fromtimestamp(packet['bundle']['source_not_before_ms']/1000, timezone.utc).hour == midnight_utc_hour
    assert datetime.fromtimestamp(packet['bundle']['issue_before_ms']/1000, timezone.utc).hour == open_utc_hour


@pytest.mark.parametrize('defect', ['reference', 'floor', 'deadline', 'source_review', 'model_compatibility_review', 'release_review', 'shared_dates', 'source_review_floor', 'compatibility_review_deadline'])
def test_unreviewed_or_mismatched_dates_never_roll_forward(packet, monkeypatch, capsys, defect):
    if defect == 'reference':
        packet['bundle']['reference_session'] = '2026-10-29'
    elif defect == 'floor':
        packet['bundle']['source_not_before_ms'] += 3600000
    elif defect == 'deadline':
        packet['bundle']['issue_before_ms'] += 3600000
    elif defect in ('source_review', 'model_compatibility_review', 'source_review_floor', 'compatibility_review_deadline'):
        key = 'source_review' if defect == 'source_review_floor' else 'model_compatibility_review' if defect == 'compatibility_review_deadline' else defect
        ref = packet['bundle']['inputs'][key]
        document = json.loads(Path(ref['path']).read_text())
        if defect == 'source_review_floor':
            document['source_not_before_ms'] += 3600000
        elif defect == 'compatibility_review_deadline':
            document['issue_before_ms'] += 3600000
        else:
            document['reference_session'] = '2026-10-29'
        packet['bundle']['inputs'][key] = put(Path(ref['path']), document)
        if key == 'source_review':
            compat_ref = packet['bundle']['inputs']['model_compatibility_review']
            compat = json.loads(Path(compat_ref['path']).read_text())
            compat['source_review_sha256'] = packet['bundle']['inputs']['source_review']['sha256']
            packet['bundle']['inputs']['model_compatibility_review'] = put(Path(compat_ref['path']), compat)
    elif defect == 'shared_dates':
        # All files/hash reviews remain valid; the semantic intersection is wrong.
        packet['receipt']['shared_training_dates_by_code'][batch.CODES[0]] = []
        packet['bundle']['inputs']['receipt'] = put(Path(packet['bundle']['inputs']['receipt']['path']), packet['receipt'])
        hashes = {k: packet['bundle']['inputs'][k]['sha256'] for k in ('history_csv', 'receipt', 'instruments')}
        packet['source']['inputs_sha256'] = hashes
        packet['bundle']['inputs']['source_review'] = put(Path(packet['bundle']['inputs']['source_review']['path']), packet['source'])
        packet['compat']['inputs_sha256'] = hashes
        packet['compat']['source_review_sha256'] = packet['bundle']['inputs']['source_review']['sha256']
        packet['bundle']['inputs']['model_compatibility_review'] = put(Path(packet['bundle']['inputs']['model_compatibility_review']['path']), packet['compat'])
    rebind(packet)
    if defect == 'release_review':
        path = Path(packet['release']['review_reference']['path'])
        document = json.loads(path.read_text())
        document['reference_session'] = '2026-10-29'
        packet['release']['review_reference'] = put(path, document)
        put(packet['rp'], packet['release'])
    # Check-only exercises every date guard without loading or spawning a model.
    monkeypatch.setattr(batch, 'supervise', lambda *a, **k: pytest.fail('worker spawn'))
    assert batch.main(args(packet, '--check-only')) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'blocked'
    assert not list(packet['output'].iterdir())


@pytest.mark.parametrize('case', ['missing', 'duplicate_candidate', 'duplicate_row'])
def test_training_csv_inventory_intersection_fails_closed(packet, case):
    bundle, inventory, _, _ = batch.preflight(packet['bp'], packet['sha'], packet['rp'])
    expected = packet['contract']['provenance']['inputs'][0]['file_sha256']
    path = next(p for p, h in inventory.hashes.items() if h == expected)
    if case == 'missing':
        del inventory.hashes[path]
    elif case == 'duplicate_candidate':
        inventory.hashes[str(packet['inputs']/'duplicate.csv')] = expected
    else:
        raw = inventory.raw[path]
        inventory.raw[path] = raw + raw.splitlines(keepends=True)[1]
    with pytest.raises(batch.Blocked, match='training_source_inventory'):
        batch.calendar_and_history(bundle, inventory)


def with_label(packet, *, document=None, pointer='/threads_environment/PATH', value='/usr/bin:/bin'):
    document = document or {'threads_environment': {'PATH': value}}
    target = put(packet['inputs']/'historical-metadata.json', document)
    entry = dict(document_sha256=target['sha256'], pointer=pointer, value=value,
                 classification='environment-label', rationale='Historical environment value only; never read or executed.')
    ledger = dict(schema_version=1, kind='reviewed-provenance-path-labels', approved=True,
                  known_at_ms=packet['now']-2000, entries=[entry])
    return target, ledger


def bind_labels(packet, target, ledger):
    ledger_ref = put(packet['inputs']/'path-labels.json', ledger)
    packet['bundle']['data_files'] += [target, ledger_ref]
    source = packet['source']
    source['provenance_path_labels_sha256'] = ledger_ref['sha256']
    packet['bundle']['inputs']['source_review'] = put(Path(packet['bundle']['inputs']['source_review']['path']), source)
    packet['compat']['source_review_sha256'] = packet['bundle']['inputs']['source_review']['sha256']
    packet['bundle']['inputs']['model_compatibility_review'] = put(Path(packet['bundle']['inputs']['model_compatibility_review']['path']), packet['compat'])
    rebind(packet)
    return ledger_ref


def test_exact_reviewed_path_label_is_not_opened_or_executed(packet, monkeypatch, capsys):
    target, ledger = with_label(packet)
    bind_labels(packet, target, ledger)
    read = batch.read_file
    def guarded(path, **kwargs):
        assert str(path) != '/usr/bin:/bin'
        return read(path, **kwargs)
    monkeypatch.setattr(batch, 'read_file', guarded)
    assert batch.main(args(packet, '--check-only')) == 0
    assert json.loads(capsys.readouterr().out)['model_loaded'] is False
    assert not list(packet['output'].iterdir())


@pytest.mark.parametrize('defect', ['approval', 'document_hash', 'pointer', 'value', 'classification', 'rationale',
                                   'duplicate', 'future', 'unbound', 'unknown', 'current_control'])
def test_finite_label_ledger_fails_closed(packet, defect, capsys):
    target, ledger = with_label(packet)
    entry = ledger['entries'][0]
    if defect == 'approval':
        ledger['approved'] = False
    elif defect == 'document_hash':
        entry['document_sha256'] = '0'*64
    elif defect == 'pointer':
        entry['pointer'] = '/threads_environment/OTHER'
    elif defect == 'value':
        entry['value'] = '/different'
    elif defect == 'classification':
        entry['classification'] = 'arbitrary-file-authority'
    elif defect == 'rationale':
        entry['rationale'] = ''
    elif defect == 'duplicate':
        ledger['entries'].append(dict(entry))
    elif defect == 'future':
        ledger['known_at_ms'] = packet['bundle']['as_of_ms']+1
    elif defect == 'unknown':
        entry['execute'] = True
    elif defect == 'current_control':
        entry['document_sha256'] = packet['bundle']['inputs']['receipt']['sha256']
        entry['pointer'] = '/currency_interpretation'
    bind_labels(packet, target, ledger)
    if defect == 'unbound':
        packet['source'].pop('provenance_path_labels_sha256')
        packet['bundle']['inputs']['source_review'] = put(Path(packet['bundle']['inputs']['source_review']['path']), packet['source'])
        rebind(packet)
    assert batch.main(args(packet, '--check-only')) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'blocked'


@pytest.mark.parametrize('document,pointer', [
    ({'ref': {'path': '/unlisted', 'sha256': '0'*64, 'bytes': 1}}, '/ref/path'),
    ({'prior_facts_path': '/unlisted'}, '/prior_facts_path'),
    ({'accepted_history': '/unlisted'}, '/accepted_history'),
    ({'accepted_receipt': '/unlisted'}, '/accepted_receipt'),
    ({'financial_review': '/unlisted'}, '/financial_review'),
    ({'template_draft': '/unlisted'}, '/template_draft'),
    ({'evidence_path': '/unlisted', 'evidence_sha256': '0'*64}, '/evidence_path'),
])
def test_source_references_cannot_be_exempted_as_labels(packet, document, pointer, capsys):
    target, ledger = with_label(packet, document=document, pointer=pointer, value='/unlisted')
    bind_labels(packet, target, ledger)
    assert batch.main(args(packet, '--check-only')) == 2
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'path_label_reference_forbidden'


def test_absolute_hash_map_is_closed_even_when_other_scalar_is_labelled(packet, capsys):
    target, ledger = with_label(packet, document={'/unlisted': '0'*64, 'label': '/historical'}, pointer='/label', value='/historical')
    bind_labels(packet, target, ledger)
    assert batch.main(args(packet, '--check-only')) == 2
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'unlisted_source_reference'


def test_rfc6901_escaping_and_exact_array_index():
    doc = {'a/b~': [{'path': '/label'}]}
    assert batch.pointer_value(doc, '/a~1b~0/0/path')[2] == '/label'
    for pointer in ('/a~1b~0/00/path', '/a~1b~0/-/path', '/a~2b/0/path'):
        with pytest.raises(batch.Blocked, match='path_label_pointer_invalid'):
            batch.pointer_value(doc, pointer)


def test_more_exact_narrow_roots_without_broader_access(packet, capsys):
    for i in range(96):
        root = packet['inputs'].parent/('artifact-parent-'+str(i))
        root.mkdir(mode=0o700)
        packet['bundle']['read_roots'].append(str(root))
    assert len(packet['bundle']['read_roots']) == 98
    rebind(packet)
    assert batch.main(args(packet, '--check-only')) == 0
    assert json.loads(capsys.readouterr().out)['model_loaded'] is False
    assert batch.JSON_LIMIT == 2*1024**2 and batch.FILE_LIMIT == 32*1024**2 and batch.TOTAL_LIMIT == 128*1024**2
    oversized = copy.deepcopy(packet['bundle'])
    oversized['read_roots'] += [str(packet['inputs'].parent/('extra-'+str(i))) for i in range(31)]
    with pytest.raises(batch.Blocked):
        batch.validate_shape(oversized)


def test_legacy_paired_source_hash_must_match_inventory(packet):
    target = put(packet['inputs']/'old-history.csv', b'fictional', raw=True)
    packet['bundle']['data_files'].append(target)
    inventory = batch.Inventory(packet['bundle'])
    with pytest.raises(batch.Blocked, match='paired_source_hash_mismatch'):
        inventory.closed({'accepted_history': target['path'], 'accepted_history_sha256': '0'*64})
