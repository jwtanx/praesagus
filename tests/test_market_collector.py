"""Offline synthetic IPC/process/store tests; never use network or login Keychain."""
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time

import pytest
from connectors.moomoo_rest import ReadResponse
from ingest import market_collector as c
from ingest.private_market_store import PrivateMarketStore

OBS = '2026-10-02T00:00:00Z'
ING = '2026-10-02T00:01:00Z'
JOB = {'kind': 'snapshot', 'codes': ['US.SYN']}
LOCATOR = {'directory': str(Path('/tmp/synthetic-collector-credentials').resolve()), 'app_key_name': 'app-key-id'}
PLAN = {'schema_version': 1, 'codes': ['US.SYN'], 'news': []}
NEWS = {'kind': 'news', 'keyword': 'synthetic', 'size': 10, 'lang': 'en'}


def wall_clock():
    times=iter([OBS])
    return lambda:next(times,ING)


def response(rows=None, kind='snapshot'):
    row = {'code': 'US.SYN', 'name': 'Synthetic', 'update_time': 1790899200000,
           'data_date': '2026-10-02', 'last_price': 10, 'volume': 0}
    data = {'snapshot_list': [row] if rows is None else rows} if kind == 'snapshot' else ([] if rows is None else rows)
    return ReadResponse(200, json.dumps({'ret_code': 0, 'ret_msg': 'ok', 'data': data}, indent=2).encode()+b'\n')


def reply(resp=None, **kwargs):
    return c.WorkerReply(resp or response(), OBS, kwargs.get('failure'), kwargs.get('cleanup_ok', True))


@pytest.fixture
def store(tmp_path):
    return PrivateMarketStore(tmp_path/'private-market', create=True)


def test_caps_and_deterministic_jobs():
    plan = {'schema_version': 1, 'codes': [f'US.SYN{i}' for i in range(400)],
            'news': [{'keyword': f'synthetic{i}', 'size': 50, 'lang': 'en'} for i in range(10)]}
    jobs = c.validate_plan(plan)
    assert len(jobs) == 11 and len({c.job_digest(j) for j in jobs}) == 11
    assert c.job_request(jobs[0]).body == json.dumps({'code_list': plan['codes']}, separators=(',', ':')).encode()


@pytest.mark.parametrize('plan', [ {}, {**PLAN, 'extra': 1}, {**PLAN, 'schema_version': True},
    {**PLAN, 'codes': []}, {**PLAN, 'codes': ['MY.SYN']}, {**PLAN, 'codes': ['US.SYN']*2},
    {**PLAN, 'codes': [f'US.S{i}' for i in range(401)]},
    {**PLAN, 'news': [{'keyword':'x', 'size':51, 'lang':'en'}]},
    {**PLAN, 'news': [{'keyword':'x', 'size':True, 'lang':'en'}]},
    {**PLAN, 'news': [{'keyword':'x', 'size':1, 'lang':'en'}]*11},
    {**PLAN, 'news': [{'keyword':'x', 'size':1, 'lang':'en'}]*2},
    {**PLAN, 'news': [{'keyword':'x', 'size':1, 'lang':'en', 'portfolio':1}]}])
def test_bad_plan_before_spawn(plan, store):
    def forbidden(*a, **k):pytest.fail('spawned on invalid input')
    with pytest.raises(ValueError):c.collect(store, plan, LOCATOR, run_id='synthetic', supervisor=forbidden)


@pytest.mark.parametrize('locator', [{}, {**LOCATOR, 'directory':'relative'},
    {**LOCATOR, 'directory':str(c.REPO/'private')}, {**LOCATOR, 'directory':'/tmp/public/private'},
    {**LOCATOR, 'app_key_name':'../key'}, {**LOCATOR, 'app_key_name':'private.pem'}])
def test_locator_rejections(locator):
    with pytest.raises(ValueError):c.validate_locator(locator)


def test_synthetic_credentials_permissions_and_safe_errors(tmp_path):
    root = tmp_path/'credentials';root.mkdir(mode=0o700)
    (root/'private.pem').write_bytes(b'SYNTHETIC ENCRYPTED PEM');(root/'private.pem').chmod(0o600)
    key = root/'app-key-id';key.write_bytes(b'synthetic-app-key\n');key.chmod(0o600)
    locator = {'directory':str(root), 'app_key_name':'app-key-id'}
    def signer(**kwargs):
        assert kwargs['pem_loader']() == b'SYNTHETIC ENCRYPTED PEM'
        assert kwargs['passphrase_loader']() == b'synthetic-passphrase'
        return 'synthetic-signer'
    assert c.load_credentials(locator, signer_factory=signer, passphrase_loader=lambda:b'synthetic-passphrase') == ('synthetic-app-key','synthetic-signer')
    key.chmod(0o400)
    assert c.load_credentials(locator, signer_factory=signer, passphrase_loader=lambda:b'synthetic-passphrase')[0] == 'synthetic-app-key'
    for mode in (0o644, 0o666):
        key.chmod(mode)
        with pytest.raises(ValueError) as error:c.load_credentials(locator, signer_factory=signer)
        assert error.value.__context__ is None and str(root) not in str(error.value)
    key.chmod(0o600);key.write_bytes(b'x'*514)
    with pytest.raises(ValueError):c.load_credentials(locator, signer_factory=signer)
    key.unlink();key.symlink_to(root/'private.pem')
    with pytest.raises(ValueError):c.load_credentials(locator, signer_factory=signer)


def test_private_pem_checked_before_app_key_read(tmp_path, monkeypatch):
    root = tmp_path/'credentials';root.mkdir(mode=0o700)
    (root/'app-key-id').write_bytes(b'synthetic-key');(root/'app-key-id').chmod(0o600)
    called = []
    original_open = os.open
    def checked_open(path, *args, **kwargs):
        called.append(Path(path).name)
        assert Path(path).name != 'app-key-id'
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(c.os, 'open', checked_open)
    with pytest.raises(ValueError):c.load_credentials({'directory':str(root),'app_key_name':'app-key-id'})
    assert called == ['private.pem']


@pytest.mark.parametrize('job,resp', [(JOB,response()), (JOB,response([])), (NEWS,response(kind='news'))])
def test_worker_exact_bytes_and_no_auth_headers(job, resp):
    calls = []
    def transport(request):calls.append(request);return resp
    raw = c.execute_job(job, LOCATOR, credentials=lambda _ :('synthetic-api-key',lambda _: b'synthetic-signature'),
                        transport_factory=lambda:transport, clock=lambda:OBS)
    parsed = c.parse_reply(raw, job)
    assert parsed.failure is None and parsed.response.body == resp.body
    assert len(calls) == 1 and calls[0].headers
    for secret in (b'synthetic-api-key', b'synthetic-signature', b'Authorization', b'X-Nonce', LOCATOR['directory'].encode()):assert secret not in raw


@pytest.mark.parametrize('status,expected', [(429,'rate-limited'), (503,'upstream-failed'), (403,'http-failed')])
def test_http_failures_have_no_provider_body(status, expected):
    raw = c.execute_job(JOB, LOCATOR, credentials=lambda _:('synthetic-api-key',lambda _:b'signature'),
                        transport_factory=lambda:lambda _:ReadResponse(status,b'private-provider-message'), clock=lambda:OBS)
    parsed = c.parse_reply(raw, JOB)
    assert parsed.failure == expected and parsed.response.status == status and parsed.response.body == b''
    assert b'private-provider-message' not in raw


@pytest.mark.parametrize('source', ['credentials','transport','timeout','factory','secret','malformed'])
def test_worker_failure_sanitization(source):
    def fail(*_):raise (TimeoutError('private-exception') if source=='timeout' else RuntimeError('private-exception'))
    def transport(request):
        if source in ('transport','timeout'):return fail()
        if source=='malformed':return ReadResponse(200,b'private-exception')
        rows = json.loads(response().body)['data']['snapshot_list'];rows[0]['name']='synthetic-api-key'
        return response(rows)
    raw = c.execute_job(JOB, LOCATOR,
        credentials=fail if source=='credentials' else lambda _:('synthetic-api-key',lambda _:b'synthetic-signature'),
        transport_factory=fail if source=='factory' else lambda:transport, clock=lambda:OBS)
    parsed = c.parse_reply(raw, JOB)
    assert parsed.failure in c.FAILURES and parsed.response.body == b''
    assert b'private-exception' not in raw and b'synthetic-api-key' not in raw


def test_frame_fail_closed():
    good = c.encode_reply(JOB,response(),OBS)
    size = struct.unpack('!I',good[:4])[0];header = json.loads(good[4:4+size]);body = good[4+size:]
    mutations = [{'job_digest':'0'*64}, {'version':True}, {'extra':'x'}, {'status':True},
                 {'body_size':len(body)+1}, {'failure':'arbitrary exception'},
                 {'observed_at':'2026-10-02T00:00:00.1234567Z'}, {'retry_after':-1}, {'failure':'timeout'}]
    for change in mutations:
        raw_header = json.dumps({**header,**change}).encode()
        with pytest.raises(ValueError):c.parse_reply(struct.pack('!I',len(raw_header))+raw_header+body,JOB)
    for raw in (b'',good[:-1],good+b'x',struct.pack('!I',c.MAX_HEADER+1),b'x'*(c.MAX_OUTPUT+1)):
        with pytest.raises(ValueError):c.parse_reply(raw,JOB)
    duplicate = json.dumps(header).replace('"version": 1','"version": 1, "version": 1').encode()
    with pytest.raises(ValueError):c.parse_reply(struct.pack('!I',len(duplicate))+duplicate+body,JOB)


def test_worker_bad_input_no_output():
    for raw in (b'',struct.pack('!I',c.MAX_INPUT+1),struct.pack('!I',4)+b'{}'):
        output=io.BytesIO();assert c.worker_main(io.BytesIO(raw),output)==1 and output.getvalue()==b''


def synthetic_popen(code, seen=None):
    def launch(command, **kwargs):
        assert command == [sys.executable,c.ENTRY,'--worker']
        assert kwargs['shell'] is False and kwargs['start_new_session'] is True
        assert kwargs['stderr'] == subprocess.DEVNULL
        assert set(kwargs['env']) == {'PATH','PYTHONDONTWRITEBYTECODE'}
        assert LOCATOR['directory'] not in ' '.join(command)
        process = subprocess.Popen([sys.executable,'-c',code],**kwargs)
        if seen is not None:seen.append(process)
        return process
    return launch


def test_real_synthetic_worker_roundtrip():
    frame = c.encode_reply(JOB,response(),OBS)
    code = f'import sys; data=sys.stdin.buffer.read(); assert b"private-market" not in data; sys.stdout.buffer.write({frame!r})'
    result = c.supervise(JOB,LOCATOR,popen=synthetic_popen(code),timeout=2,cleanup=.2)
    assert result.response.body == response().body and result.cleanup_ok


@pytest.mark.parametrize('code,expected', [
    ('import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"bad")','bad-frame'),
    ('import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"\\x00\\x00\\x20\\x00")','bad-frame'),
    ('import sys;sys.stdin.buffer.read();sys.exit(3)','worker-failed'),
    ('import time;time.sleep(20)','deadline'),
    ('import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"x"*3000000)','bad-frame')])
def test_real_synthetic_worker_failures_bounded(code,expected):
    seen=[];start=time.monotonic()
    result=c.supervise(JOB,LOCATOR,popen=synthetic_popen(code,seen),timeout=.3,cleanup=.3)
    assert result.failure == expected and result.response is None and result.cleanup_ok
    assert time.monotonic()-start < 2 and seen[0].poll() is not None


def test_descendant_cleanup(tmp_path):
    marker=tmp_path/'descendant-pid'
    code = f'''import subprocess,sys,signal,time
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'])
open({str(marker)!r},'w').write(str(child.pid))
def stop(*args):
 child.terminate();child.wait(timeout=1);sys.exit(0)
signal.signal(signal.SIGTERM,stop)
time.sleep(20)
'''
    seen=[]
    result=c.supervise(JOB,LOCATOR,popen=synthetic_popen(code,seen),timeout=.5,cleanup=1)
    assert result.failure=='deadline' and result.cleanup_ok and seen[0].poll() is not None
    pid=int(marker.read_text())
    with pytest.raises(ProcessLookupError):os.kill(pid,0)


def test_cleanup_always_kills_group_and_reaps():
    class Process:
        pid=12345
        def __init__(self):self.waits=[];self.done=False
        def wait(self,timeout):
            self.waits.append(timeout)
            if len(self.waits)==1:raise subprocess.TimeoutExpired('synthetic',timeout)
            self.done=True
        def poll(self):return 0 if self.done else None
    process=Process();signals=[]
    assert c.cleanup_process(process,2,killpg=lambda pid,sig:signals.append((pid,sig)))
    assert signals==[(12345,signal.SIGTERM),(12345,signal.SIGKILL)]
    assert all(0<t<=2 for t in process.waits)
    process=Process()
    def rejected(*_):raise PermissionError('private-cleanup-error')
    assert not c.cleanup_process(process,2,killpg=rejected)


@pytest.mark.parametrize('resp,status', [(response(),'success'),(response([]),'all-missing'),
                                       (ReadResponse(429,b''),'failed')])
def test_parent_store_exact_coverage(store,resp,status):
    outcomes=c.collect(store,PLAN,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:reply(resp),wall=wall_clock())
    assert outcomes[0].status==status and outcomes[0].attempt_id is not None
    attempts=store.attempts(ING);assert len(attempts)==1
    if status=='failed':assert attempts[0]['raw_hash'] is None
    else:assert store.raw(attempts[0]['raw_hash'])==resp.body
    assert store.attempts(OBS)==[]  # Post-cutoff ingestion cannot become earlier evidence.


def test_parent_partial_and_empty_news(store):
    plan={**PLAN,'codes':['US.SYN','US.MISSING'],'news':[{'keyword':'synthetic','size':10,'lang':'en'}]}
    outcomes=c.collect(store,plan,LOCATOR,run_id='synthetic',supervisor=lambda job,*a,**k:c.WorkerReply(response(kind=job['kind']),OBS if job['kind']=='snapshot' else ING,None),wall=wall_clock())
    assert [o.status for o in outcomes]==['partial','successful-empty']


@pytest.mark.parametrize('failure', ['credentials','deadline','bad-frame','worker-failed','timeout','cleanup-failed'])
def test_failed_workers_real_attempt_no_raw_and_cleanup_stops(store,failure):
    calls=[]
    plan={**PLAN,'news':[{'keyword':'synthetic','size':10,'lang':'en'}]}
    def run(job,*args,**kwargs):
        calls.append(job);return c.WorkerReply(None,None,failure,failure!='cleanup-failed')
    outcomes=c.collect(store,plan,LOCATOR,run_id='synthetic',supervisor=run,wall=wall_clock())
    assert all(a['raw_hash'] is None for a in store.attempts(ING))
    assert outcomes[0].failure==failure and outcomes[0].status=='failed'
    assert len(calls)==(1 if failure=='cleanup-failed' else 2)
    if failure=='cleanup-failed':assert outcomes[1].status=='unattempted'


@pytest.mark.parametrize('observed,ingested', [(ING,OBS), ('2026-10-02T00:00:00.1234567Z',ING)])
def test_clock_order_rejected_no_persistence(store,observed,ingested):
    outcomes=c.collect(store,PLAN,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:c.WorkerReply(response(),observed,None),wall=lambda:ingested)
    assert outcomes[0].failure=='clock-order' and outcomes[0].attempt_id is None and store.attempts(ING)==[]


def test_storage_failure_stops_no_false_attempt():
    class Broken:
        def ingest(self,*a,**k):raise OSError('private-storage-path')
    calls=[]
    def run(job,*a,**k):calls.append(job);return reply()
    outcomes=c.collect(Broken(),{**PLAN,'news':[{'keyword':'synthetic','size':1,'lang':'en'}]},LOCATOR,
                       run_id='synthetic',supervisor=run,wall=wall_clock())
    assert len(calls)==1 and outcomes[0].failure=='storage-failed' and outcomes[0].attempt_id is None
    assert 'private-storage-path' not in repr(outcomes)


def test_budget_reserves_cleanup_and_no_retries(store):
    now=[0.];calls=[]
    plan={**PLAN,'news':[{'keyword':'synthetic','size':1,'lang':'en'}]}
    def run(job,*a,**kwargs):calls.append(kwargs);now[0]=4.;return reply()
    outcomes=c.collect(store,plan,LOCATOR,run_id='synthetic',supervisor=run,wall=wall_clock(),
                       clock=lambda:now[0],run_seconds=4,cleanup_seconds=2)
    assert calls==[{'timeout':2.,'cleanup':2}] and outcomes[1].failure=='run-budget'
    assert len(store.attempts(ING))==1


def test_storage_overrun_stops_next_job(store):
    now=[0.];calls=[]
    class Slow:
        def ingest(self,*a,**k):
            result=store.ingest(*a,**k);now[0]=301.;return result
    def run(job,*a,**k):calls.append(job);return reply()
    outcomes=c.collect(Slow(),{**PLAN,'news':[{'keyword':'synthetic','size':1,'lang':'en'}]},LOCATOR,
                       run_id='synthetic',supervisor=run,wall=wall_clock(),clock=lambda:now[0])
    assert len(calls)==1 and outcomes[0].attempt_id and outcomes[1].failure=='run-budget'


@pytest.mark.parametrize('kwargs',[{'job_seconds':21},{'cleanup_seconds':3},{'run_seconds':301},{'run_seconds':float('nan')}])
def test_invalid_budgets_before_spawn(store,kwargs):
    with pytest.raises(ValueError):c.collect(store,PLAN,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:pytest.fail('spawned'),**kwargs)


def test_cli_import_and_missing_store_no_io(tmp_path):
    root=tmp_path/'missing-store';plan=tmp_path/'plan.json';plan.write_text(json.dumps(PLAN))
    result=subprocess.run([sys.executable,c.ENTRY,'--root',str(root),'--plan',str(plan),
        '--credential-directory',LOCATOR['directory'],'--app-key-name','app-key-id','--run-id','synthetic'],capture_output=True,timeout=3)
    assert result.returncode==1 and not root.exists() and not result.stdout
    assert str(root).encode() not in result.stderr
    code='import builtins,socket; builtins.open=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("IO")); import ingest.market_collector'
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=3)
    assert result.returncode==0


def test_cross_job_clock_rollback_rejected(store):
    plan={**PLAN,'news':[{'keyword':'synthetic','size':1,'lang':'en'}]}
    outcomes=c.collect(store,plan,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:reply(),wall=wall_clock())
    assert outcomes[0].attempt_id and outcomes[1].failure=='clock-order'
    assert len(store.attempts(ING))==1


def test_private_locator_echo_screened_pre_ipc():
    rows=json.loads(response().body)['data']['snapshot_list'];rows[0]['name']=LOCATOR['directory']
    raw=c.execute_job(JOB,LOCATOR,credentials=lambda _:('short',lambda _:b'synthetic-signature'),
                      transport_factory=lambda:lambda _:response(rows),clock=lambda:OBS)
    assert LOCATOR['directory'].encode() not in raw and c.parse_reply(raw,JOB).failure


def test_parent_revalidates_body_even_valid_frame():
    unsafe=ReadResponse(200,b'{"ret_code":0,"ret_msg":"ok","data":{"snapshot_list":[]},"api_key":"private"}')
    with pytest.raises(ValueError):c.parse_reply(c.encode_reply(JOB,unsafe,OBS),JOB)


def test_zero_admission_records_no_attempt(store):
    outcomes=c.collect(store,PLAN,LOCATOR,run_id='synthetic',run_seconds=1,wall=wall_clock(),
                       supervisor=lambda *a,**k:pytest.fail('spawned'))
    assert outcomes[0].status=='unattempted' and store.attempts(ING)==[]


def test_clock_rollback_during_worker_rejected(store):
    times=iter([ING,OBS])
    outcomes=c.collect(store,PLAN,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:reply(),wall=lambda:next(times))
    assert outcomes[0].failure=='clock-order' and store.attempts(ING)==[]


def test_cli_existing_store_missing_synthetic_credentials(store,tmp_path):
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(PLAN))
    missing=(tmp_path/'missing-credentials').resolve()
    result=subprocess.run([sys.executable,c.ENTRY,'--root',str(store.root),'--plan',str(plan),
        '--credential-directory',str(missing),'--app-key-name','app-key-id','--run-id','synthetic'],capture_output=True,timeout=4)
    assert result.returncode==1 and result.stderr==b''
    summary=json.loads(result.stdout);outcome=summary['outcomes'][0]
    assert outcome['status']=='failed' and outcome['failure']=='credentials' and outcome['attempt_id']
    assert str(missing).encode() not in result.stdout
    attempt=store.attempts('2027-01-01T00:00:00Z')[0]
    assert attempt['raw_hash'] is None and not missing.exists()


def test_final_storage_overrun_visible(store):
    now=[0.]
    class Slow:
        def ingest(self,*a,**k):
            result=store.ingest(*a,**k);now[0]=301.;return result
    outcomes=c.collect(Slow(),PLAN,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:reply(),
                       wall=wall_clock(),clock=lambda:now[0])
    assert outcomes[0].attempt_id and outcomes[0].status=='success' and outcomes[0].failure=='run-budget'


def test_worker_ignores_term_then_group_killed():
    seen=[];signals=[]
    def kill(pid,sig):signals.append(sig);os.killpg(pid,sig)
    code='import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)'
    start=time.monotonic()
    result=c.supervise(JOB,LOCATOR,popen=synthetic_popen(code,seen),timeout=.3,cleanup=.3,killer=kill)
    assert result.failure=='deadline' and result.cleanup_ok and seen[0].poll()==-signal.SIGKILL
    assert signals==[signal.SIGTERM,signal.SIGKILL] and time.monotonic()-start<2


def test_parent_shared_policy_screening():
    rows=json.loads(response().body)['data']['snapshot_list']
    rows[0]['extra']={'authorization':'synthetic-private'}
    with pytest.raises(ValueError):c.parse_reply(c.encode_reply(JOB,response(rows),OBS),JOB)
