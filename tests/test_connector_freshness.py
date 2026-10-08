"""Synthetic local metadata/HTTP/script fixtures; no live providers or secrets."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.freshness_services import get_freshness
from backend.services import build_pipeline_statuses, build_platform_statuses
from connectors.financial import run_status as status
# Isolate the existing live SEC provider dependency (feedparser is not installed
# in this focused runtime); test the script against a mocked connector only.
import importlib.util
from types import ModuleType
from unittest.mock import patch
provider = ModuleType('connectors.sec_filings')
provider.SecFilingsConnector = object
spec = importlib.util.spec_from_file_location('freshness_sec_script', status.REPO/'scripts/run_sec_filings.py')
script = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'connectors.sec_filings': provider}):
    spec.loader.exec_module(script)

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


@pytest.fixture
def roots(tmp_path, monkeypatch):
    root = (tmp_path / 'status').resolve(); root.mkdir(mode=0o700)
    data = tmp_path / 'data'; data.mkdir()
    monkeypatch.setenv('PRAESAGUS_RUN_STATUS_DIR', str(root))
    monkeypatch.setenv('PRAESAGUS_FINANCIAL_DATA_DIR', str(data))
    return root, data


def filings(**kwargs):
    return get_freshness(now=NOW, **kwargs)['datasets'][0]


def finish(start, end, state='succeeded', code=None, count=0):
    with status.invocation(now=start.isoformat()) as run:
        run.yielded = run.stored = count
        run.finish(state, code, now=end.isoformat())


def test_read_unconfigured_and_other_datasets_not_never_run(roots, monkeypatch):
    monkeypatch.delenv('PRAESAGUS_RUN_STATUS_DIR')
    result = get_freshness(now=NOW)
    assert result['datasets'][0]['ledger'] == 'unconfigured'
    assert all(d['invocation_state'] == 'unknown' for d in result['datasets'])
    assert all(d['last_success'] is None for d in result['datasets'])
    assert all(d['coverage'] is None and d['rejected'] is None for d in result['datasets'])


def test_get_never_creates_root_db_or_marks_abandonment(roots):
    root, data = roots
    before = list(root.iterdir())
    assert filings()['invocation_state'] == 'never-run'
    assert list(root.iterdir()) == before
    with status.invocation(now=(NOW-timedelta(hours=3)).isoformat()):
        pass  # Synthetic interrupted writer: no terminal update.
    raw = (root/status.DB_NAME).read_bytes()
    result = filings()
    assert result['last_attempt']['state'] == 'abandoned'
    assert result['last_attempt']['finished_at'] is None
    assert result['last_success'] is None
    assert (root/status.DB_NAME).read_bytes() == raw


def test_successful_empty_failure_and_stale_are_separate(roots):
    finish(NOW-timedelta(hours=1), NOW-timedelta(minutes=59))
    result = filings()
    assert result['data']['state'] == 'absent'
    assert result['freshness'] == 'recent'
    assert result['last_attempt']['stored'] == 0
    success = result['last_success']
    finish(NOW-timedelta(minutes=2), NOW-timedelta(minutes=1), 'failed', 'fetch-failed')
    result = filings()
    assert result['last_success'] == success
    assert result['last_attempt']['state'] == 'failed'
    assert result['last_attempt']['finished_at'] != success
    result = get_freshness(now=NOW+timedelta(days=3))['datasets'][0]
    assert result['freshness'] == 'stale'


@pytest.mark.parametrize('content,expected', [('[]','empty'), ('{bad','unreadable'), ('{"records":{}}','unreadable'), ('[null]','unreadable')])
def test_dataset_shape(roots, content, expected):
    (roots[1]/'filings.json').write_text(content)
    assert filings()['data']['state'] == expected


def test_source_precision_invalid_future_not_ingest_or_calendar_schedule(roots):
    rows = [{'acceptance_datetime': '2026-10-04T10:00:00Z'},
            {'acceptance_datetime': '2026-10-05'},
            {'acceptance_datetime': '2026-10-06T00:00:00Z'},
            {'acceptance_datetime': '2026-10-05T00:00:00'},
            {'ingest_ts': NOW.isoformat()}]
    path = roots[1]/'filings.json'; path.write_text(json.dumps(rows)); before=path.read_bytes()
    result=filings()['data']
    assert result['latest_data_time']=='2026-10-05' and result['time_precision']=='date'
    assert result['future_times']==1 and result['invalid_times']==2
    assert path.read_bytes()==before
    (roots[1]/'calendar.json').write_text(json.dumps([{'event_date':'2026-12-01','ingest_ts':NOW.isoformat()}]))
    assert get_freshness(now=NOW)['datasets'][3]['data']['latest_data_time'] is None


@pytest.mark.parametrize('policy', ['', 'filings: {}', 'filings: {max_success_age_seconds: true, abandoned_after_seconds: 5}', 'filings: {max_success_age_seconds: -1, abandoned_after_seconds: 5}'])
def test_invalid_policy_unknown(roots, tmp_path, policy):
    finish(NOW-timedelta(hours=1),NOW-timedelta(minutes=59))
    path=tmp_path/'policy.yaml';path.write_text(policy)
    result=filings(policy_path=path)
    assert result['policy'] is None and result['freshness']=='unknown'
    assert result['last_success'] is not None


def test_future_run_not_success(roots):
    finish(NOW+timedelta(hours=1),NOW+timedelta(hours=2))
    result=filings()
    assert result['invocation_state']=='unknown' and result['last_success'] is None


def test_bad_finish_time_and_repeat_fail(roots):
    with status.invocation(now=NOW.isoformat()) as run:
        for value in ['bad', '2026-10-05T12:00:00', (NOW-timedelta(seconds=1)).isoformat()]:
            with pytest.raises(status.StatusError):run.finish('succeeded',now=value)
        run.finish('succeeded',now=NOW.isoformat())
        with pytest.raises(status.StatusError):run.finish('succeeded',now=NOW.isoformat())


def test_retention_pins_last_success_inside_bound(roots):
    finish(NOW-timedelta(days=10),NOW-timedelta(days=10)+timedelta(seconds=1))
    root=roots[0]
    with sqlite3.connect(root/status.DB_NAME) as db:
        db.executemany("INSERT INTO runs(run_id,dataset,started_at,finished_at,state,error_code) VALUES(?,'filings',?,?,'failed','fetch-failed')", [(str(uuid.UUID(int=i+1, version=4)),NOW.isoformat(),NOW.isoformat()) for i in range(1100)])
    finish(NOW-timedelta(minutes=2),NOW-timedelta(minutes=1),'failed','fetch-failed')
    view=status.read_status(root)
    assert len(view['runs'])==1000
    assert sum(r['state']=='succeeded' for r in view['runs'])==1
    assert view['retention']['pruned']==102 and view['retention']['floor']


def test_two_process_lock_and_killed_writer(roots):
    env={**os.environ,'PYTHONPATH':str(status.REPO)}
    code="from connectors.financial.run_status import invocation; import time;\nwith invocation(now='2026-10-05T08:00:00Z'):\n print('ready',flush=True); time.sleep(30)"
    child=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,text=True)
    try:
        import select
        assert select.select([child.stdout],[],[],5)[0]
        assert child.stdout.readline().strip()=='ready'
        with pytest.raises(status.StatusError,match='run-busy'):
            with status.invocation():pass
    finally:
        child.kill();child.wait(timeout=5);child.stdout.close()
    assert filings()['invocation_state']=='abandoned'
    finish(NOW-timedelta(minutes=2),NOW-timedelta(minutes=1))
    rows=status.read_status(roots[0])['runs']
    assert rows[1]['state']=='unknown' and rows[1]['finished_at'] is None


@pytest.mark.parametrize('case',['missing','mode','relative','symlink','repo','empty'])
def test_invalid_root_fails_before_provider_and_get_no_provision(roots, tmp_path, monkeypatch, case):
    root=roots[0]
    values={'missing':str(tmp_path/'missing'),'mode':str(root),'relative':'relative','repo':str(status.REPO),'empty':''}
    if case=='mode':root.chmod(0o755)
    if case=='symlink':
        link=tmp_path/'link';link.symlink_to(root,target_is_directory=True);values[case]=str(link)
    monkeypatch.setenv('PRAESAGUS_RUN_STATUS_DIR',values[case])
    monkeypatch.setattr(sys,'argv',['run_sec_filings.py'])
    monkeypatch.setattr(script,'_ingest',lambda *_:pytest.fail('provider work'))
    assert script.main()==1
    assert filings()['ledger']=='unavailable'
    assert not (tmp_path/'missing').exists()


def test_corrupt_ledger_not_never_run(roots):
    p=roots[0]/status.DB_NAME;p.write_text('corrupt');p.chmod(0o600)
    assert filings()['ledger']=='unavailable' and filings()['invocation_state']=='unknown'


def test_script_unconfigured_preserves_ingest_and_warns(roots, monkeypatch, capsys):
    monkeypatch.delenv('PRAESAGUS_RUN_STATUS_DIR');monkeypatch.setattr(sys,'argv',['run_sec_filings.py'])
    calls=[];monkeypatch.setattr(script,'_ingest',lambda args,run:calls.append(run) or 0)
    assert script.main()==0 and calls==[None]
    assert capsys.readouterr().err=='SEC invocation status unconfigured.\n'


def test_start_failure_no_work_and_terminal_failure_preserves_raw(roots, monkeypatch, capsys):
    monkeypatch.setattr(sys,'argv',['run_sec_filings.py'])
    original=status._initialize
    monkeypatch.setattr(status,'_initialize',lambda _:(_ for _ in ()).throw(status.StatusError()))
    monkeypatch.setattr(script,'_ingest',lambda *_:pytest.fail('work before start'))
    assert script.main()==1
    monkeypatch.setattr(status,'_initialize',original)
    raw=roots[1]/'filings.json'
    def ingest(args,run):
        raw.write_text('[]');run.yielded=run.stored=1;return 0
    monkeypatch.setattr(script,'_ingest',ingest)
    monkeypatch.setattr(status.Invocation,'finish',lambda *_a,**_k:(_ for _ in ()).throw(status.StatusError()))
    assert script.main()==1 and raw.read_text()=='[]'
    assert status.read_status(roots[0])['runs'][0]['state']=='running'
    assert 'raw writes preserved' in capsys.readouterr().err


def test_partial_exception_sanitized(roots, monkeypatch, capsys):
    monkeypatch.setattr(sys,'argv',['run_sec_filings.py'])
    def ingest(args,run):
        run.yielded=2;run.stored=1;run.phase='fetch-failed'
        raise RuntimeError('synthetic-private-token webhook://private')
    monkeypatch.setattr(script,'_ingest',ingest)
    assert script.main()==1
    row=status.read_status(roots[0])['runs'][0]
    assert row['state']=='partial' and row['stored']==1
    assert 'synthetic-private-token' not in capsys.readouterr().err


def test_api_auth_readonly_and_generic_no_fake_times(roots, monkeypatch):
    monkeypatch.setenv('PRAESAGUS_API_KEY','synthetic-api-key')
    client=TestClient(app)
    assert client.get('/api/v1/financial/freshness').status_code==401
    assert client.get('/api/v1/financial/freshness',headers={'X-API-Key':'synthetic-api-key'}).status_code==200
    assert list(roots[0].iterdir())==[]
    platforms=build_platform_statuses();pipeline=build_pipeline_statuses()
    assert all(p['status']=='Configured' and p['last_run'] is None for p in platforms)
    assert pipeline['health']=='unknown'
    assert all(d['last_run'] is None and d['next_run'] is None for d in pipeline['dags'])



@pytest.mark.parametrize('failure', [None, 'authenticate-failed', 'fetch-failed', 'normalize-failed', 'store-failed'])
def test_actual_script_mocked_connector_stages(roots, monkeypatch, failure):
    from types import SimpleNamespace
    class FakeConnector:
        def __init__(self, **kwargs):pass
        def authenticate(self):
            if failure == 'authenticate-failed':raise RuntimeError('synthetic-private-token')
        def fetch(self, start, end):
            if failure == 'fetch-failed':raise RuntimeError('synthetic-private-token')
            yield object()
        def normalize(self, raw):
            if failure == 'normalize-failed':raise RuntimeError('synthetic-private-token')
            return SimpleNamespace(metadata={'form_type':'10-Q','ticker':'FIXTURE','company_name':'Fixture','filing_date':'2026-10-05','accession_number':'synthetic'})
        def store(self, *args, **kwargs):
            if failure == 'store-failed':raise RuntimeError('synthetic-private-token')
            (roots[1]/'filings.json').write_text('[]')
    monkeypatch.setattr(script,'SecFilingsConnector',FakeConnector)
    monkeypatch.setattr(sys,'argv',['run_sec_filings.py','--tickers','FIXTURE'])
    assert script.main()==(1 if failure else 0)
    row=status.read_status(roots[0])['runs'][0]
    assert row['state']==('failed' if failure else 'succeeded')
    assert row['error_code']==failure
    assert row['yielded']==(0 if failure in {'authenticate-failed','fetch-failed'} else 1)
    assert row['stored']==(0 if failure else 1)


def test_schema_corruption_and_private_db_mode(roots):
    finish(NOW,NOW)
    path=roots[0]/status.DB_NAME
    assert path.stat().st_mode & 0o777 == 0o600
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=99')
    assert filings()['ledger']=='unavailable'
    with pytest.raises(status.StatusError):
        with status.invocation():pass



@pytest.mark.parametrize('fields', [
    {'state':'succeeded','error_code':'store-failed'},
    {'state':'failed','error_code':None},
    {'state':'partial','error_code':None},
    {'state':'running','finished_at':'bad'},
    {'state':'running','finished_at':NOW.isoformat()},
    {'state':'running','finished_at':None,'error_code':'fetch-failed'},
    {'state':'unknown','finished_at':None,'error_code':None},
    {'state':'unknown','finished_at':'bad','error_code':'interrupted'},
    {'run_id':'not-a-uuid'}, {'run_id':str(uuid.UUID(int=1))},
    {'yielded':-1}, {'stored':2,'yielded':1}, {'yielded':1.5},
])
def test_contradictory_corrupt_rows_fail_closed(roots, fields, monkeypatch):
    finish(NOW-timedelta(minutes=2),NOW-timedelta(minutes=1))
    path=roots[0]/status.DB_NAME
    with sqlite3.connect(path) as db:
        db.execute('UPDATE runs SET '+','.join(key+'=?' for key in fields),list(fields.values()))
    before=path.read_bytes()
    with pytest.raises(status.StatusError) as caught:status.read_status(roots[0])
    assert caught.value.__cause__ is None and str(caught.value)=='status-unavailable'
    result=filings()
    assert result['ledger']=='unavailable' and result['freshness']=='unknown'
    assert result['last_success'] is None and result['last_attempt'] is None
    monkeypatch.setattr(sys,'argv',['run_sec_filings.py'])
    monkeypatch.setattr(script,'_ingest',lambda *_:pytest.fail('work with corrupt metadata'))
    assert script.main()==1
    assert path.read_bytes()==before


def fixture_handler():
    """Bounded loopback-only HTTP fixture, independent of ASGI server packages."""
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import urlsplit
    calls = [0]
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(2)
        def log_message(self, *_args):pass
        def reply(self, code, payload=None):
            body = b'' if payload is None else json.dumps(payload).encode()
            self.send_response(code)
            self.send_header('Access-Control-Allow-Origin','http://localhost:5179')
            self.send_header('Access-Control-Allow-Methods','GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers','Content-Type, X-API-Key')
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            if body:self.wfile.write(body)
        def do_OPTIONS(self):self.reply(204)
        def do_GET(self):
            if len(self.path)>4096:
                self.reply(414,{'error':'Synthetic request too long'});return
            route=urlsplit(self.path).path
            if route=='/api/v1/financial/freshness':
                calls[0]+=1
                if calls[0]==2:finish(NOW-timedelta(minutes=1),NOW,'failed','fetch-failed')
                if calls[0]>=3:
                    self.reply(503,{'error':'Synthetic status unavailable'});return
                self.reply(200,get_freshness(now=NOW));return
            if route=='/api/v1/financial/catalysts':
                self.reply(200,{'records':[],'count':0,'total':0,'offset':0,'limit':50,'retrieved_at':NOW.isoformat(),'dataset_status':{}});return
            if route=='/api/v1/financial/summary':
                self.reply(200,{'counts':{},'watchlist':[]});return
            if route in {'/api/v1/financial/filings','/api/v1/financial/insider','/api/v1/financial/news','/api/v1/financial/calendar','/api/v1/financial/filters'}:
                self.reply(200,{'records':[],'count':0});return
            self.reply(404,{'error':'Synthetic route unavailable'})
    return Handler


def test_stdlib_http_fixture_sequence_and_cors(roots):
    import http.client
    from http.server import HTTPServer
    import threading
    finish(NOW-timedelta(minutes=3),NOW-timedelta(minutes=2))
    with HTTPServer(('127.0.0.1',0),fixture_handler()) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def read(method='GET',path='/api/v1/financial/freshness'):
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=2)
            try:
                connection.request(method,path)
                response=connection.getresponse();body=response.read()
                assert response.getheader('Access-Control-Allow-Origin')=='http://localhost:5179'
                return response.status,json.loads(body) if body else None
            finally:connection.close()
        try:
            assert read('OPTIONS')[0]==204
            code,first=read();assert code==200
            assert first['datasets'][0]['last_attempt']['state']=='succeeded'
            code,second=read();assert code==200
            assert second['datasets'][0]['last_attempt']['state']=='failed'
            assert second['datasets'][0]['last_success']==first['datasets'][0]['last_success']
            assert read()[0]==503
            assert read(path='/api/v1/financial/filings')[0]==200
        finally:server.shutdown();thread.join(timeout=2)
        assert not thread.is_alive()


def serve_fixture():
    """Optional Lead HTTP drill: temporary synthetic data/ledger, no credentials."""
    import tempfile
    from http.server import HTTPServer
    temp=tempfile.TemporaryDirectory(prefix='prsg2-ui-')
    base=Path(temp.name).resolve();root=base/'status';root.mkdir(mode=0o700)
    data=base/'data';data.mkdir()
    os.environ['PRAESAGUS_RUN_STATUS_DIR']=str(root)
    os.environ['PRAESAGUS_FINANCIAL_DATA_DIR']=str(data)
    (data/'filings.json').write_text('[]')
    finish(NOW-timedelta(minutes=3),NOW-timedelta(minutes=2))
    try:
        with HTTPServer(('127.0.0.1',8016),fixture_handler()) as server:
            server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:pass
    finally:temp.cleanup()


if __name__=='__main__':serve_fixture()
