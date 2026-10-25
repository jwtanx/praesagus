"""Synthetic store-to-export integration; no network, real source or model claims."""
from copy import deepcopy
import csv
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from connectors.moomoo_rest import ReadResponse
from ingest import forecast_scenario as core
from ingest import market_collector as collector
from ingest import private_forecast_refresh as refresh
from ingest.private_market_store import PrivateMarketStore, MarketStoreError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_authored_cases', ROOT/'tests/test_forecast_scenario.py')
cases = importlib.util.module_from_spec(spec); spec.loader.exec_module(cases)
ISSUE = '2026-10-21T23:00:00+00:00'


def put(path, value):
    path.write_text(json.dumps(value)); path.chmod(0o600)
    return str(path)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))


@pytest.fixture
def setup(tmp_path):
    private = tmp_path.resolve()/'private with spaces'; private.mkdir(mode=0o700)
    reviews = private/'reviews'; reviews.mkdir(mode=0o700)
    outputs = private/'outputs'; outputs.mkdir(mode=0o700)
    store = PrivateMarketStore(private/'store', create=True)
    items = []
    for n in range(50):
        e, _ = cases.make_case()
        e['schema_version'] = 3
        e['classification'] = 'authored_fixture'
        e['method'] = deepcopy(core.GENERIC_METHOD)
        e['narrative'] = dict(bull_case='Authored bull', bear_case='Authored bear', invalidation='Authored invalidation')
        market = 'US' if n < 30 else 'MY'
        ticker = 'SYN'+str(n) if market == 'US' else str(1000+n)
        # These are fake MY identities; their mocked-store tests never call a real provider.
        instrument = e['instrument']
        instrument.update(ticker=ticker, instrument_id='fixture-'+ticker, market=market,
                          currency='USD' if market == 'US' else 'MYR', mic='ARCX' if market == 'US' else 'XKLS')
        e['source']['provider'] = 'moomoo-rest'
        if market == 'MY':
            e['calendar'].update(mic='XKLS', timezone='Asia/Kuala_Lumpur')
            for session in e['calendar']['sessions']:
                session['regular_close_at'] = session['session_date']+'T09:00:00Z'
        e['corporate_actions']['instrument_id'] = instrument['instrument_id']
        e.pop('bars')
        items.append(dict(ticker=ticker, market=market, currency=instrument['currency'],
            code=('US.' if market == 'US' else 'BMS.')+ticker, run_id='fixture-run',
            normalization_version=4, normalization_dialect=None, template=e,
            finality={session['session_date']:session['regular_close_at'] for session in e['calendar']['sessions']}))
    config = dict(schema_version=1, mode='offline_store', store_root=str(store.root),
                  review_directory=str(reviews), output_parent=str(outputs), items=items)
    return private, store, config


def observations(item, *, origin='synthetic'):
    rows = []
    for n, session in enumerate(item['template']['calendar']['sessions'][:21]):
        day = session['session_date']; source_ms = int(datetime.fromisoformat(day+'T00:00:00+00:00').timestamp()*1000)
        meta = dict(observed_at='2026-10-21T21:00:00Z', ingested_at='2026-10-21T21:01:00Z',
                    known_ms=int(datetime.fromisoformat('2026-10-21T21:01:00+00:00').timestamp()*1000),
                    origin=origin, normalization_version=4, raw_hash='a'*64)
        rows.append(dict(record=dict(code=item['code'], date=day, close=100+n, adjustment=0),
            observation=meta, semantic_hash=hashlib.sha256((item['code']+day).encode()).hexdigest(),
            revision=1, eligible_for_temporal_evidence=True, source_ms=source_ms, quality=[]))
    return rows


class FakeStore:
    def __init__(self, config, *, origin='synthetic'):
        self.rows = [row for item in config['items'] for row in observations(item, origin=origin)]
        self.calls = []

    def query(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return deepcopy(self.rows)


def admit(config, receipt):
    for entry in receipt['items']:
        e = entry['evidence']
        if e is None: continue
        _, a = cases.make_case()
        a.update(schema_version=3, purpose=core.PRIVATE_PURPOSE, reviewed_at='2026-10-21T22:00:00Z')
        cases.reseal(e, a)
        put(Path(config['review_directory'])/(core._hash(e)+'.json'), a)


def parsed(result):
    return list(csv.DictReader(__import__('io').StringIO(result['csv_bytes'].decode())))


def test_current_mixed_venues_exact_review_and_original_times(setup):
    _, _, config = setup
    store = FakeStore(config)
    before = deepcopy(config)
    result, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert receipt['status'] == 'insufficient_coverage' and receipt['counts']['review_required'] == 50
    assert receipt['counts']['generated'] == 0
    admit(config, receipt)
    result, reviewed = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert config == before
    assert reviewed['counts'] == dict(total=50, generated=50, withheld=0, is_demo=50,
                                      review_required=0, eligible_generated=0)
    assert reviewed['status'] == 'insufficient_coverage'  # Fictional numbers never meet actual35.
    assert all(row['is_demo'] == 'True' and row['status'] == 'generated' for row in parsed(result))
    assert all(row['reference_session'] == '2026-10-21' and row['target_session'] == '2026-10-22' for row in parsed(result))
    assert result['audit']['rows'][0]['result']['provenance']['audit']['reference_close_at'] != result['audit']['rows'][30]['result']['provenance']['audit']['reference_close_at']
    e = reviewed['items'][0]['evidence']
    assert e['bars'][0]['retrieved_at'] == '2026-10-21T21:00:00Z'
    assert e['bars'][0]['ingested_at'] == '2026-10-21T21:01:00Z'
    assert e['bars'][0]['known_at'] == '2026-10-21T21:01:00.000000+00:00'
    assert e['bars'][0]['source_publication_at'] is None
    expected = core.build_private_forecast_scenario(e, admission=json.loads((Path(config['review_directory'])/(core._hash(e)+'.json')).read_text()), issued_at=ISSUE, report_cutoff=ISSUE)
    assert float(parsed(result)[0]['point']) == expected['estimates']['display_point']
    assert store.calls[0] == (('history', ISSUE), dict(run_id='fixture-run', limit=5000))


def test_synthetic_capture_cannot_be_relabelled_real(setup):
    _, _, config = setup
    for item in config['items']: item['template']['classification'] = 'reviewed_real'
    result, receipt = refresh.prepare(config, issued_at=ISSUE, store=FakeStore(config))
    assert all(entry['evidence']['classification'] == 'authored_fixture' for entry in receipt['items'])
    admit(config, receipt)
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=FakeStore(config))
    assert receipt['counts']['eligible_generated'] == 0


@pytest.mark.parametrize('change,reason', [
    ('missing','history_missing_or_stale'), ('twenty','history_missing_or_stale'),
    ('nineteen','history_missing_or_stale'), ('conflict','history_conflict'),
    ('future','finality_unavailable'), ('finality','finality_unavailable'),
    ('dialect','history_basis_or_time_unavailable'), ('source-time','history_basis_or_time_unavailable'),
    ('calendar','calendar_or_input_unavailable'), ('expired','calendar_or_input_unavailable'),
    ('truncated-calendar','calendar_or_input_unavailable')])
def test_currentness_and_history_failure_ledger(setup, change, reason):
    _, _, config = setup
    store = FakeStore(config)
    if change in ('missing','twenty','nineteen'):
        count = {'missing':21, 'twenty':1, 'nineteen':2}[change]
        store.rows = store.rows[count:]
    elif change == 'conflict':
        row = deepcopy(store.rows[0]); row['semantic_hash'] = 'f'*64; row['record']['close'] = 999
        store.rows.append(row)
    elif change == 'future': store.rows[0]['observation']['ingested_at'] = '2026-10-22T00:00:00Z'
    elif change == 'finality': config['items'][0]['finality'].pop('2026-10-01')
    elif change == 'dialect': store.rows[0]['observation']['normalization_version'] = 6
    elif change == 'source-time': store.rows[0]['eligible_for_temporal_evidence'] = False
    elif change == 'calendar': config['items'][0]['template']['calendar']['complete'] = False
    elif change == 'expired':
        return_result, receipt = refresh.prepare(config, issued_at='2026-10-23T21:00:00Z', store=store)
        assert reason in parsed(return_result)[0]['reasons'] and receipt['counts']['generated'] == 0
        return
    elif change == 'truncated-calendar': config['items'][0]['template']['calendar']['sessions'].pop()
    result, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert len(parsed(result)) == 50 and reason in parsed(result)[0]['reasons']
    assert parsed(result)[0]['point'] == '' and receipt['status'] == 'insufficient_coverage'


@pytest.mark.parametrize('change', ['bar','wrong-review','future-review','rights','actions'])
def test_changed_evidence_and_review_rejection(setup, change):
    _, _, config = setup
    store = FakeStore(config)
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    admit(config, receipt)
    if change == 'bar': store.rows[0]['record']['close'] += 1
    elif change in ('wrong-review','future-review'):
        path = Path(config['review_directory'])/(receipt['items'][0]['evidence_sha256']+'.json')
        a = json.loads(path.read_text())
        if change == 'wrong-review': a['evidence_sha256'] = '0'*64
        else: a['reviewed_at'] = '2026-10-22T22:00:00Z'
        put(path, a)
    elif change == 'rights':
        config['items'][0]['template']['rights']['private_retention_research'] = 'unknown'
    elif change == 'actions': config['items'][0]['template']['corporate_actions']['coverage_end'] = '2026-10-21'
    result, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert parsed(result)[0]['point'] == '' and 'review_required' in parsed(result)[0]['reasons']
    if change in ('rights','actions'):
        # Even a hash-matching authored approval cannot bypass the underlying gate.
        admit(config, receipt)
        result, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
        assert parsed(result)[0]['point'] == ''
        assert ('rights' if change == 'rights' else 'basis_actions') in parsed(result)[0]['reasons']


def test_equal_replays_are_deterministic_and_window_can_survive_weekend(setup):
    _, _, config = setup
    store = FakeStore(config)
    store.rows.append(deepcopy(store.rows[0]))
    _, first = refresh.prepare(config, issued_at=ISSUE, store=store)
    store.rows.reverse()
    _, second = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert first == second
    # A declared next session on26Oct permits unchanged evidence on24/25Oct;
    # this is a synthetic schedule, not an actual exchange calendar assertion.
    for item in config['items']:
        t = item['template']; t['calendar']['sessions'][-1].update(session_date='2026-10-26', regular_close_at='2026-10-26T20:00:00Z')
        t['calendar']['coverage_end'] = t['corporate_actions']['coverage_end'] = '2026-10-26'
    _, before = refresh.prepare(config, issued_at='2026-10-24T21:00:00Z', store=store)
    _, after = refresh.prepare(config, issued_at='2026-10-25T21:00:00Z', store=store)
    assert before['items'][0]['evidence_sha256'] == after['items'][0]['evidence_sha256']


def test_fatal_schema_and_truncation_before_export(setup):
    _, _, config = setup
    for mutate in (lambda c:c['items'].pop(), lambda c:c['items'].__setitem__(1, deepcopy(c['items'][0])),
                   lambda c:c.update(mode='online'), lambda c:c['items'][0].update(code='US.OTHER')):
        invalid = deepcopy(config); mutate(invalid)
        with pytest.raises(refresh.RefreshError): refresh.prepare(invalid, issued_at=ISSUE, store=FakeStore(config))
    store = FakeStore(config); store.rows = [store.rows[0]]*5000
    with pytest.raises(refresh.RefreshError): refresh.prepare(config, issued_at=ISSUE, store=store)
    assert not list(Path(config['output_parent']).iterdir())


def test_actual_store_integrity_mapping_and_missing_names(setup):
    _, store, config = setup
    item = config['items'][0]
    raw_rows = []
    for n, session in enumerate(item['template']['calendar']['sessions'][:21]):
        day = session['session_date']
        stamp = int(datetime.fromisoformat(day+'T12:00:00+00:00').timestamp()*1000)
        raw_rows.append(dict(time_key=stamp, date=int(day.replace('-','')), time_zone=-240, close=100+n))
    raw = json.dumps(dict(ret_code=0, ret_msg='ok', data=dict(kline_list=raw_rows))).encode()
    request = collector.job_request(dict(kind='history', code=item['code'], end='2026-10-21'))
    attempt = store.ingest(request, ReadResponse(200, raw), run_id='fixture-run', observed_at='2026-10-21T21:00:00Z',
                           ingested_at='2026-10-21T21:01:00Z', origin='synthetic', normalization_version=4)
    assert attempt.status == 'success'
    _, receipt = refresh.prepare(config, issued_at=ISSUE)
    assert receipt['items'][0]['evidence']['bars'][0]['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert receipt['items'][1]['evidence'] is None
    admit(config, receipt)
    result, receipt = refresh.prepare(config, issued_at=ISSUE)
    assert receipt['counts']['generated'] == 1 and receipt['counts']['eligible_generated'] == 0
    assert parsed(result)[0]['is_demo'] == 'True'
    raw_path = store.raw_dir/(attempt.raw_hash+'.json')
    raw_path.chmod(0o600); raw_path.write_bytes(b'tampered'); raw_path.chmod(0o400)
    with pytest.raises(MarketStoreError): refresh.prepare(config, issued_at=ISSUE)


def test_real_cli_other_cwd_sanitized_no_network_and_immutable(setup, tmp_path):
    private, _, config = setup
    config_path = put(private/'config with spaces.json', config)
    # Empty verified store gives honest50withheld at the actual wall clock.
    cli = ROOT/'scripts/daily-market-brief/refresh_private_forecast.py'
    proc = subprocess.run([sys.executable, str(cli), '--offline', '--config', config_path], cwd=tmp_path,
                          text=True, capture_output=True, timeout=15)
    assert proc.returncode == 2 and proc.stderr == ''
    summary = json.loads(proc.stdout)
    assert summary['status'] == 'insufficient_coverage' and summary['counts']['total'] == 50
    assert summary['provider_refreshed'] is False and len(summary['sessions']) == 50
    folder = Path(summary['csv_path']).parent
    assert {p.name for p in folder.iterdir()} == {'forecasts.csv','private-audit.json','manifest.json','refresh-review.json'}
    assert folder.stat().st_mode&0o777 == 0o700
    assert all(p.stat().st_mode&0o777 == 0o600 for p in folder.iterdir())
    before = {p.name:p.read_bytes() for p in folder.iterdir()}
    manifest = json.loads((folder/'manifest.json').read_text())
    assert manifest['artifacts']['forecasts.csv']['sha256'] == hashlib.sha256(before['forecasts.csv']).hexdigest()
    for args in ([], ['--config', config_path], ['--offline','--config',str(private/'PRIVATE_CANARY')],
                 ['--online','--config',config_path]):
        proc = subprocess.run([sys.executable, str(cli), *args], cwd=tmp_path, text=True,capture_output=True,timeout=15)
        assert proc.returncode == 1 and proc.stderr == ''
        assert json.loads(proc.stdout) == dict(status='failed',reason='private-refresh-unavailable')
        assert 'PRIVATE_CANARY' not in proc.stdout
    assert {p.name:p.read_bytes() for p in folder.iterdir()} == before


def test_ready_threshold_uses_only_non_demo_generated_rows(setup, monkeypatch):
    _, _, config = setup
    # Mock just the external source-origin declaration, not calculator/review/status.
    # These remain authored test values; this does not prove actual-source eligibility.
    for item in config['items']: item['template']['classification'] = 'reviewed_real'
    store = FakeStore(config, origin='trusted-capture')
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=store); admit(config, receipt)
    for threshold, expected in ((34,'insufficient_coverage'),(35,'ready')):
        subset = deepcopy(config)
        for item in subset['items'][threshold:]: item['run_id'] = 'missing'
        class Selected(FakeStore):
            def query(self, *a, **kw): return [] if kw['run_id'] == 'missing' else store.rows
        _, receipt = refresh.prepare(subset, issued_at=ISSUE, store=Selected(config))
        assert receipt['status'] == expected and receipt['counts']['eligible_generated'] == threshold


def test_write_failure_rolls_back_and_permission_rejections(setup, monkeypatch):
    private, _, config = setup
    path = put(private/'config.json', config)
    # Use real empty store/adapter/exporter, fail the fourth file only.
    original = refresh.io_private._write_file
    def failed(fd, name, value):
        if name == 'refresh-review.json': raise OSError('PRIVATE_CANARY')
        return original(fd, name, value)
    monkeypatch.setattr(refresh.io_private, '_write_file', failed)
    with pytest.raises(OSError): refresh.run(path, issued_at=ISSUE)
    assert not list(Path(config['output_parent']).iterdir())
    Path(path).chmod(0o644)
    with pytest.raises(ValueError): refresh.run(path, issued_at=ISSUE)


@pytest.mark.parametrize('failure', ['permission','symlink','git','missing-store','query-failure'])
def test_private_paths_and_store_setup_fail_closed(setup, failure):
    private, _, config = setup
    if failure == 'permission': Path(config['review_directory']).chmod(0o755)
    elif failure == 'symlink':
        link = private/'linked'; link.symlink_to(config['store_root'], target_is_directory=True)
        config['store_root'] = str(link)
    elif failure == 'git': (Path(config['store_root'])/'.git').mkdir()
    elif failure == 'missing-store': config['store_root'] = str(private/'absent')
    else:
        class Failed:
            def query(self, *a, **kw): raise MarketStoreError('database-integrity-failed')
        with pytest.raises(MarketStoreError): refresh.prepare(config, issued_at=ISSUE, store=Failed())
        return
    with pytest.raises((ValueError,OSError)): refresh.prepare(config, issued_at=ISSUE)
    assert not list(Path(config['output_parent']).iterdir())


def test_export_collision_preserves_prior_bytes(setup, monkeypatch):
    private, _, config = setup
    path = put(private/'config.json', config)
    original = refresh.exporter.write_export
    stamp = datetime.fromisoformat(ISSUE)
    def frozen(parent, result): return original(parent, result, generated_at=stamp)
    monkeypatch.setattr(refresh.exporter, 'write_export', frozen)
    summary = refresh.run(path, issued_at=ISSUE)
    folder = Path(summary['csv_path']).parent
    before = {p.name:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(FileExistsError): refresh.run(path, issued_at=ISSUE)
    assert {p.name:p.read_bytes() for p in folder.iterdir()} == before


def test_cli_ready_exit_and_fatal_sanitization(monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location('refresh_cli_test',ROOT/'scripts/daily-market-brief/refresh_private_forecast.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'run', lambda path: dict(status='ready',counts={'eligible_generated':35}))
    assert cli.main(['--offline','--config','/fictional/config']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'ready'
    def failed(path): raise OSError('PRIVATE_CANARY')
    monkeypatch.setattr(cli, 'run', failed)
    assert cli.main(['--offline','--config','/fictional/config']) == 1
    assert 'PRIVATE_CANARY' not in capsys.readouterr().out


def test_full_fifty_real_store_roundtrip_bounded_private_bundle(setup):
    private, store, config = setup
    from connectors.moomoo_rest import BMS_FIXED20_CODES, BMS_FIXED20_HOURS_DIALECT
    my_codes = sorted(BMS_FIXED20_CODES)
    for n, item in enumerate(config['items']):
        if item['market'] == 'MY':
            ticker = my_codes[n-30].split('.')[1]
            item.update(ticker=ticker, code=my_codes[n-30], normalization_version=6,
                        normalization_dialect=BMS_FIXED20_HOURS_DIALECT)
            item['template']['instrument']['ticker'] = ticker
        item['run_id'] = 'fixture-us' if n < 30 else 'fixture-my'
        raw_rows = []
        for number, session in enumerate(item['template']['calendar']['sessions'][:21]):
            day = session['session_date']
            stamp = int(datetime.fromisoformat(day+'T12:00:00+00:00').timestamp()*1000)
            raw_rows.append(dict(time_key=stamp, date=int(day.replace('-','')),
                                 time_zone=-240 if n < 30 else 8, close=100+number))
        job = dict(kind='history', code=item['code'], end='2026-10-21')
        if n >= 30: job['normalization_dialect'] = BMS_FIXED20_HOURS_DIALECT
        raw = json.dumps(dict(ret_code=0, ret_msg='ok', data=dict(kline_list=raw_rows))).encode()
        attempt = store.ingest(collector.job_request(job), ReadResponse(200,raw),run_id=item['run_id'],
            observed_at='2026-10-21T21:00:00Z', ingested_at='2026-10-21T21:01:00Z',origin='synthetic',
            normalization_version=item['normalization_version'],
            **({'normalization_dialect':item['normalization_dialect']} if n >= 30 else {}))
        assert attempt.status == 'success'
    _, receipt = refresh.prepare(config, issued_at=ISSUE)
    assert receipt['counts']['review_required'] == 50
    admit(config, receipt)
    summary = refresh.run(put(private/'full50.json',config), issued_at=ISSUE)
    assert summary['status'] == 'insufficient_coverage'
    assert summary['counts'] == dict(total=50,generated=50,withheld=0,is_demo=50,
                                     review_required=0,eligible_generated=0)
    folder = Path(summary['csv_path']).parent
    receipt = json.loads((folder/'refresh-review.json').read_text())
    assert len(receipt['observations']) == 50
    for entry in receipt['items']:
        for binding in entry['store_bindings']:
            meta = receipt['observations'][binding['observation_sha256']]
            assert meta['observed_at'] == '2026-10-21T21:00:00Z'
            assert meta['known_ms'] <= int(datetime.fromisoformat(ISSUE).timestamp()*1000)
    assert all(p.stat().st_size <= refresh.exporter.MAX_BYTES for p in folder.iterdir())


@pytest.mark.parametrize('bad', ['malformed','insecure'])
def test_invalid_private_review_is_fatal_before_export(setup,bad):
    _, _, config = setup
    store = FakeStore(config)
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    path = Path(config['review_directory'])/(receipt['items'][0]['evidence_sha256']+'.json')
    if bad == 'malformed': path.write_text('not json'); path.chmod(0o600)
    else: put(path, {}); path.chmod(0o644)
    with pytest.raises(ValueError): refresh.prepare(config, issued_at=ISSUE, store=store)
    assert not list(Path(config['output_parent']).iterdir())


def test_mixed_origin_replays_cannot_hide_synthetic_provenance(setup):
    _, _, config = setup
    for item in config['items']: item['template']['classification'] = 'reviewed_real'
    store = FakeStore(config, origin='trusted-capture')
    replay = deepcopy(store.rows[0]); replay['observation']['origin'] = 'synthetic'
    store.rows.append(replay)
    _, first = refresh.prepare(config, issued_at=ISSUE, store=store)
    store.rows.reverse()
    _, second = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert first == second
    assert first['items'][0]['evidence']['classification'] == 'authored_fixture'
    assert first['items'][1]['evidence']['classification'] == 'reviewed_real'


def unavailable(item):
    item.update(template=None, run_id=None, normalization_version=None,
                normalization_dialect=None, finality=None)


def test_mixed_thirtyfour_supported_and_sixteen_null_templates(setup):
    _, _, config = setup
    store = FakeStore(config)
    # Capture mock rows before removing unavailable inputs; no dummy template is
    # required for those slots in the actual config passed to the adapter.
    for item in config['items'][34:]: unavailable(item)
    identities = [(item['ticker'],item['market']) for item in config['items']]
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    admit(config, receipt)
    result, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    rows = parsed(result)
    assert [(row['ticker'],row['market']) for row in rows] == identities
    assert receipt['counts'] == dict(total=50,generated=34,withheld=16,is_demo=34,
                                     review_required=0,eligible_generated=0)
    assert receipt['status'] == 'insufficient_coverage'
    for row, entry in zip(rows[34:],receipt['items'][34:]):
        assert row['point'] == row['low'] == row['high'] == ''
        assert 'template_missing' in row['reasons'] and 'history_unavailable' in row['reasons']
        assert entry['evidence'] is entry['evidence_sha256'] is None
        assert entry['reference_session'] is entry['target_session'] is None
        assert entry['store_bindings'] == []
    assert len(store.calls) == 2  # One shared necessary selector per invocation.


@pytest.mark.parametrize('missing', ['template','run','both'])
def test_missing_optional_evidence_requires_no_queries_or_invented_facts(setup,missing):
    _, _, config = setup
    before = deepcopy(config)
    for item in config['items']:
        if missing in ('template','both'):
            item.update(template=None,finality=None,normalization_version=None,normalization_dialect=None)
        if missing in ('run','both'):
            item['run_id'] = None
    class Unqueried:
        def query(self,*args,**kwargs): pytest.fail('missing inputs must not query history')
    result, receipt = refresh.prepare(config,issued_at=ISSUE,store=Unqueried())
    assert receipt['counts']['withheld'] == 50 and receipt['observations'] == {}
    for row, entry, original in zip(parsed(result),receipt['items'],before['items']):
        assert row['ticker'] == original['ticker'] and row['point'] == ''
        assert entry['evidence'] is None and entry['reference_session'] is None
        if missing in ('template','both'): assert 'template_missing' in row['reasons']
        if missing in ('run','both'): assert 'history_unavailable' in row['reasons']


@pytest.mark.parametrize('bad', ['template','run','normalization','finality'])
def test_non_null_malformed_optional_inputs_are_still_fatal(setup,bad):
    _, _, config = setup
    if bad == 'template': config['items'][0]['template'] = {}
    elif bad == 'run': config['items'][0]['run_id'] = 'invalid run selector'
    elif bad == 'normalization': config['items'][0]['normalization_version'] = 'invented'
    elif bad == 'finality': config['items'][0]['finality'] = None
    with pytest.raises(refresh.RefreshError): refresh.validate_config(config)


def test_original_store_knowledge_milliseconds_never_shift_earlier(setup):
    _, _, config = setup
    store = FakeStore(config)
    for row in store.rows[:21]:
        row['observation']['ingested_at'] = '2026-10-21T21:01:00.000123+00:00'
        row['observation']['known_ms'] += 1
    _, receipt = refresh.prepare(config, issued_at=ISSUE, store=store)
    bar = receipt['items'][0]['evidence']['bars'][0]
    assert bar['ingested_at'] == '2026-10-21T21:01:00.000123+00:00'
    assert bar['known_at'] == '2026-10-21T21:01:00.001000+00:00'
    between, _ = refresh.prepare(config, issued_at='2026-10-21T21:01:00.000500+00:00', store=store)
    assert 'finality_unavailable' in parsed(between)[0]['reasons']
    # Future knowledge or a knowledge boundary preceding ingestion withholds;
    # the adapter must not replace either with the invocation clock.
    store.rows[0]['observation']['known_ms'] += 86400000
    result, _ = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert 'finality_unavailable' in parsed(result)[0]['reasons']
    store.rows[0]['observation']['known_ms'] -= 86400001
    result, _ = refresh.prepare(config, issued_at=ISSUE, store=store)
    assert 'finality_unavailable' in parsed(result)[0]['reasons']
