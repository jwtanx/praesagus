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
HISTORY = {'kind':'history','code':'US.SYN','end':'2026-10-02'}


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


def test_history_job_is_daily_bounded_and_stored_through_worker():
    request=c.job_request(HISTORY)
    assert (request.method,request.path,request.query,request.body)==(
        'GET','/api/v1.0/quote/US.SYN/history-kline','end=2026-10-02&ktype=2&autype=0&num=100',b'')
    plan={**PLAN,'history':[{'code':'US.SYN','end':'2026-10-02'}]}
    assert c.validate_plan(plan)==[JOB,HISTORY]
    row={'time_key':1790899200000,'date':20261001,'time_zone':-240,'close':10.5}
    payload={'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}
    resp=ReadResponse(200,json.dumps(payload).encode())
    calls=[]
    raw=c.execute_job(HISTORY,LOCATOR,credentials=lambda _:('synthetic-api-key',lambda _:b'signature'),
        transport_factory=lambda:lambda req:(calls.append(req) or resp),clock=lambda:OBS)
    parsed=c.parse_reply(raw,HISTORY)
    assert parsed.failure is None and parsed.response.body==resp.body and len(calls)==1
    assert (calls[0].method,calls[0].path,calls[0].query,calls[0].body)==(request.method,request.path,request.query,request.body)


@pytest.mark.parametrize('stamp', [1790899200000, 2**63-1])
def test_contradictory_or_unrepresentable_history_is_discarded_by_worker(stamp, store):
    row={'time_key':stamp,'date':20261002,'time_zone':-240,'close':10.5}
    response=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}).encode())
    calls=[]
    raw=c.execute_job(HISTORY,LOCATOR,credentials=lambda _:('synthetic-api-key',lambda _:b'signature'),
        transport_factory=lambda:lambda req:(calls.append(req) or response),clock=lambda:OBS)
    parsed=c.parse_reply(raw,HISTORY)
    assert len(calls)==1 and parsed.failure=='invalid-response'
    assert parsed.response.status==200 and parsed.response.body==b''
    attempt=store.ingest(c.job_request(HISTORY),parsed.response,run_id='synthetic-history',
                        observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert store.query('history',ING)==[] and list(store.raw_dir.iterdir())==[]
    assert store.attempts(ING)[0]['reason']=='invalid-response'


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
    expected={'credentials':'credentials','transport':'transport','timeout':'timeout',
              'factory':'worker-failed','secret':'invalid-response','malformed':'invalid-response'}
    assert parsed.failure == expected[source] and parsed.response.body == b''
    assert parsed.response.status == (200 if source in ('secret','malformed') else 0)
    assert parsed.observed_at == OBS
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
    duplicate = json.dumps(header).replace('"version": 2','"version": 2, "version": 2').encode()
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


@pytest.mark.parametrize('diagnostics', [False,True])
def test_cli_existing_store_missing_synthetic_credentials(store,tmp_path,diagnostics):
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(PLAN))
    missing=(tmp_path/'missing-credentials').resolve()
    result=subprocess.run([sys.executable,c.ENTRY,'--root',str(store.root),'--plan',str(plan),
        '--credential-directory',str(missing),'--app-key-name','app-key-id','--run-id','synthetic']
        +(['--diagnostics'] if diagnostics else []),capture_output=True,timeout=4)
    assert result.returncode==1 and result.stderr==b''
    summary=json.loads(result.stdout);outcome=summary['outcomes'][0]
    assert outcome['status']=='failed' and outcome['failure']=='credentials' and outcome['attempt_id']
    assert str(missing).encode() not in result.stdout
    assert set(summary)==({'run_id','outcomes','schema_version'} if diagnostics else {'run_id','outcomes'})
    if diagnostics:assert summary['schema_version']==2 and outcome['diagnostic_stage'] is None
    else:assert set(outcome)=={'job_id','status','attempt_id','failure'}
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


def batch_job_and_response(count):
    job={'kind':'snapshot','codes':[f'US.SYN{i}' for i in range(count)]}
    rows=json.loads(response().body)['data']['snapshot_list']
    return job,response([{**rows[0],'code':code} for code in job['codes']])


@pytest.mark.parametrize('count',[1,30])
def test_valid_one_and_thirty_receive_exact_http200(count):
    job,resp=batch_job_and_response(count)
    raw=c.execute_job(job,LOCATOR,credentials=lambda _:('synthetic-api-key',lambda _:b'synthetic-signature'),
                      transport_factory=lambda:lambda _:resp,clock=lambda:OBS)
    parsed=c.parse_reply(raw,job)
    assert parsed.failure is None and parsed.response.status==200 and parsed.response.body==resp.body
    assert parsed.observed_at==OBS


@pytest.mark.parametrize('bad',['null-volume','bool-price','negative-volume','malformed','duplicate','provider','secret'])
def test_received_bad_batch_http200_retained_without_body(bad,store):
    job,resp=batch_job_and_response(30);data=json.loads(resp.body)
    if bad=='null-volume':data['data']['snapshot_list'][-1]['volume']=None
    elif bad=='bool-price':data['data']['snapshot_list'][-1]['last_price']=True
    elif bad=='negative-volume':data['data']['snapshot_list'][-1]['volume']=-1
    elif bad=='provider':data.update(ret_code=-1,ret_msg='synthetic-private-provider-error')
    elif bad=='secret':data['data']['snapshot_list'][-1]['name']='synthetic-api-key'
    body=json.dumps(data).encode()
    if bad=='malformed':body=b'synthetic-private-provider-error'
    elif bad=='duplicate':body=b'{"ret_code":0,"ret_code":1}'
    times=iter([OBS])
    raw=c.execute_job(job,LOCATOR,credentials=lambda _:('synthetic-api-key',lambda _:b'synthetic-signature'),
                      transport_factory=lambda:lambda _:ReadResponse(200,body,{'private-header':'private-value'}),
                      clock=lambda:next(times))
    parsed=c.parse_reply(raw,job)
    assert parsed.failure=='invalid-response' and parsed.response.status==200
    assert parsed.response.body==b'' and parsed.observed_at==OBS
    for secret in (b'synthetic-api-key',b'synthetic-private-provider-error',b'private-value',b'private-header'):
        assert secret not in raw
    attempt=store.ingest(c.job_request(job),parsed.response,run_id='synthetic',observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert attempt.status=='failed' and attempt.raw_hash is None and list(store.raw_dir.iterdir())==[]
    assert store.attempts(ING)[0]['reason']=='invalid-response' and store.query('snapshot',ING)==[]


@pytest.mark.parametrize('invalid_status',[True,0,600])
def test_unvalidated_response_status_not_preserved(invalid_status):
    raw=c.execute_job(JOB,LOCATOR,credentials=lambda _:('synthetic-api-key',lambda _:b'synthetic-signature'),
                      transport_factory=lambda:lambda _:ReadResponse(invalid_status,b'private-provider-error'),clock=lambda:OBS)
    result=c.parse_reply(raw,JOB)
    assert result.failure=='transport' and result.response.status==0 and result.response.body==b''


# PRSG-94 authored deterministic fixtures, never real provider responses.
def stage_history_response(row=None, **outer):
    row = {'time_key':1790899200000,'date':20261001,'time_zone':-240,'close':10} if row is None else row
    return ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'SYNTHETIC-BODY-CANARY',
        'data':{'kline_list':[row]}, **outer}).encode())


def stage_worker(resp, job=HISTORY):
    return c.execute_job(job, LOCATOR, credentials=lambda _:('synthetic-api-key',lambda _:b'synthetic-signature'),
        transport_factory=lambda:lambda _:resp, clock=lambda:OBS)


def unpack_stage_frame(raw):
    size=struct.unpack('!I',raw[:4])[0]
    return json.loads(raw[4:4+size]),raw[4+size:]


def pack_stage_frame(header,body=b''):
    raw=json.dumps(header).encode()
    return struct.pack('!I',len(raw))+raw+body


@pytest.mark.parametrize('resp,stage', [
    (ReadResponse(200,b'\xff{SYNTHETIC-BODY-CANARY'), 'decode-screen'),
    (stage_history_response(token='synthetic-api-key'), 'decode-screen'),
    (stage_history_response(x=LOCATOR['directory']), 'decode-screen'),
    (stage_history_response(pagination={'private':'SYNTHETIC-BODY-CANARY'}), 'envelope-root-fields'),
    (ReadResponse(200,b'[]'), 'envelope-root-type'),
    (stage_history_response(ret_code=True), 'envelope-ret-code-type'),
    (stage_history_response(ret_msg=False), 'envelope-ret-msg-type'),
    (stage_history_response(data=[]), 'envelope-data-type'),
    (stage_history_response(data={'kline_list':[], 'extra':'SYNTHETIC-BODY-CANARY'}), 'envelope-data-fields'),
    (stage_history_response(data={'kline_list':[], 'next_time':True}), 'envelope-next-time'),
    (stage_history_response(data={'kline_list':[], 'volume_precision':19}), 'envelope-volume-precision'),
    (stage_history_response(ret_code=1234567,data=None), 'provider-rejection'),
    (stage_history_response(data={'kline_list':[False]}), 'history-rows'),
    (stage_history_response({'time_key':1790899200000,'time_zone':-240,'close':10}), 'metadata-missing'),
    (stage_history_response({'time_key':2**63-1,'date':20261001,'time_zone':-240,'close':10}), 'metadata-invalid'),
    (stage_history_response({'time_key':1790899200000,'date':20261002,'time_zone':-240,'close':10}), 'date-relation'),
    (stage_history_response({'time_key':1790899200000,'date':20261001,'time_zone':-240,'close':10,'volume':-1}), 'core-validation'),
    (stage_history_response({'time_key':1790899200000,'date':20261001,'time_zone':-240,'close':10,'open':'Infinity'}), 'core-validation'),
])
def test_stage_worker_discards_body_and_propagates_private_outcome(resp,stage,store,capsys):
    raw=stage_worker(resp);header,body=unpack_stage_frame(raw)
    assert header['version']==2 and header['diagnostic_stage']==stage and body==b''
    parsed=c.parse_reply(raw,HISTORY)
    assert parsed.failure=='invalid-response' and parsed.diagnostic_stage==stage
    outcomes=c.collect(store,{'schema_version':1,'codes':[],'news':[],'history':[{'code':'US.SYN','end':'2026-10-02'}]},
        LOCATOR,run_id='synthetic-stage',supervisor=lambda *a,**k:parsed,wall=wall_clock())
    assert outcomes[0].failure=='invalid-response' and outcomes[0].diagnostic_stage==stage
    assert outcomes[0].status=='failed' and outcomes[0].attempt_id
    assert store.attempts(ING)[0]['raw_hash'] is None and store.query('history',ING)==[]
    assert not list(store.raw_dir.iterdir())
    for canary in (b'SYNTHETIC-BODY-CANARY',b'synthetic-api-key',b'synthetic-signature',
                   LOCATOR['directory'].encode(),b'1234567'):
        assert canary not in raw and canary.decode() not in repr(parsed)+repr(outcomes)
    captured=capsys.readouterr();assert captured.out==captured.err==''


@pytest.mark.parametrize('error_kind', ['forged', 'controlled-unknown', 'subclass'])
def test_stage_unknown_exception_never_trusts_arbitrary_attributes(error_kind,monkeypatch):
    class ForgedError(RuntimeError):diagnostic_stage='metadata-missing'
    class Subclass(c.MarketStoreError):pass
    error = (ForgedError('SYNTHETIC-EXCEPTION-CANARY') if error_kind=='forged'
             else Subclass('SYNTHETIC-EXCEPTION-CANARY',diagnostic_stage='date-relation') if error_kind=='subclass'
             else c.MarketStoreError('invalid-response',diagnostic_stage='unrecognized'))
    calls=[]
    def fail(*a,**k):calls.append(1);raise error
    monkeypatch.setattr(c,'normalized',fail)
    raw=stage_worker(stage_history_response())
    header,body=unpack_stage_frame(raw)
    assert len(calls)==1 and body==b'' and header['failure']=='invalid-response'
    assert header['diagnostic_stage']=='unknown' and b'CANARY' not in raw


@pytest.mark.parametrize('job,resp', [(HISTORY,stage_history_response()),
    (HISTORY,stage_history_response(data={'kline_list':[]})),(JOB,response()),
    (NEWS,response(kind='news')),(HISTORY,ReadResponse(403,b'SYNTHETIC-BODY-CANARY'))])
def test_stage_success_empty_nonhistory_and_http_null(job,resp):
    parsed=c.parse_reply(stage_worker(resp,job),job)
    assert parsed.diagnostic_stage is None
    if resp.status==200:assert parsed.failure is None and parsed.response.body==resp.body
    else:assert parsed.failure=='http-failed' and parsed.response.body==b''


@pytest.mark.parametrize('stage', sorted(c.HISTORY_STAGES))
def test_stage_frame_all_fixed_values_and_v1_legacy(stage):
    raw=c.encode_reply(HISTORY,ReadResponse(200,b''),OBS,'invalid-response',diagnostic_stage=stage)
    header,body=unpack_stage_frame(raw)
    assert set(header)=={'version','job_digest','status','observed_at','failure','body_size','retry_after','diagnostic_stage'}
    assert c.parse_reply(raw,HISTORY).diagnostic_stage==stage
    header['version']=1;header.pop('diagnostic_stage')
    parsed=c.parse_reply(pack_stage_frame(header,body),HISTORY)
    assert parsed.failure=='invalid-response' and parsed.diagnostic_stage is None


def test_stage_legacy_success_frame_and_positional_dataclasses():
    header,body=unpack_stage_frame(c.encode_reply(JOB,response(),OBS))
    header['version']=1;header.pop('diagnostic_stage')
    assert c.parse_reply(pack_stage_frame(header,body),JOB).response.body==body
    assert c.WorkerReply(None,None,'deadline',False).cleanup_ok is False
    assert c.WorkerReply(None,None,'deadline',False).diagnostic_stage is None
    assert c.JobOutcome('synthetic','failed',None,'deadline').diagnostic_stage is None


@pytest.mark.parametrize('change', [{'diagnostic_stage':'forged'}, {'diagnostic_stage':[]},
    {'diagnostic_stage':{}}, {'diagnostic_stage':True}, {'diagnostic_stage':'x'*5000},
    {'diagnostic_stage':None}, {'version':3}, {'version':True}, {'version':1},
    {'status':403}, {'failure':'timeout'}, {'failure':None}, {'failure':[]},
    {'extra':'SYNTHETIC-CANARY'}, {'job_digest':'0'*64}, {'body_size':1},
    {'observed_at':'2026-10-02T00:00:00.1234567Z'}, {'retry_after':True}])
def test_stage_frame_mutations_fail_closed_and_supervisor_clears(change):
    header,_=unpack_stage_frame(c.encode_reply(HISTORY,ReadResponse(200,b''),OBS,'invalid-response',
                                              diagnostic_stage='envelope'))
    raw=pack_stage_frame({**header,**change})
    with pytest.raises(ValueError):c.parse_reply(raw,HISTORY)
    result=c.supervise(HISTORY,LOCATOR,popen=synthetic_popen(
        f'import sys;sys.stdin.buffer.read();sys.stdout.buffer.write({raw!r})'))
    assert result.failure=='bad-frame' and result.diagnostic_stage is None and result.response is None


def test_stage_missing_key_duplicate_header_body_and_parent_screening():
    header,_=unpack_stage_frame(c.encode_reply(HISTORY,ReadResponse(200,b''),OBS,'invalid-response',
                                              diagnostic_stage='envelope'))
    missing=dict(header);missing.pop('diagnostic_stage')
    with pytest.raises(ValueError):c.parse_reply(pack_stage_frame(missing),HISTORY)
    duplicate=json.dumps(header).replace('"version": 2','"version": 2, "version": 2').encode()
    with pytest.raises(ValueError):c.parse_reply(struct.pack('!I',len(duplicate))+duplicate,HISTORY)
    header['body_size']=1
    with pytest.raises(ValueError):c.parse_reply(pack_stage_frame(header,b'x'),HISTORY)
    good_header,_=unpack_stage_frame(c.encode_reply(HISTORY,stage_history_response(),OBS))
    unsafe=stage_history_response(token='SYNTHETIC-CANARY').body
    good_header['body_size']=len(unsafe)
    with pytest.raises(ValueError):c.parse_reply(pack_stage_frame(good_header,unsafe),HISTORY)
    # Nonhistory cannot carry a stage even when other fields describe a rejection.
    header.update(job_digest=c.job_digest(JOB),body_size=0)
    with pytest.raises(ValueError):c.parse_reply(pack_stage_frame(header),JOB)


@pytest.mark.parametrize('stage', ['forged', [], {}, 'x'*5000])
def test_stage_injected_supervisor_unknown_stage_becomes_bad_frame(stage,store):
    injected=c.WorkerReply(ReadResponse(200,b''),OBS,'invalid-response',diagnostic_stage=stage)
    outcomes=c.collect(store,{'schema_version':1,'codes':[],'news':[],'history':[{'code':'US.SYN','end':'2026-10-02'}]},
        LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:injected,wall=wall_clock())
    assert outcomes[0].failure=='bad-frame' and outcomes[0].diagnostic_stage is None
    assert store.attempts(ING)[0]['raw_hash'] is None


@pytest.mark.parametrize('case', ['success','nonhistory','body','non200','otherfailure'])
def test_stage_injected_supervisor_contradictions(case,store):
    job=JOB if case=='nonhistory' else HISTORY
    status=403 if case=='non200' else 200
    failure=None if case=='success' else 'timeout' if case=='otherfailure' else 'invalid-response'
    injected=c.WorkerReply(ReadResponse(status,b'x' if case=='body' else b''),OBS,failure,diagnostic_stage='envelope')
    plan=PLAN if job==JOB else {'schema_version':1,'codes':[],'news':[],'history':[{'code':'US.SYN','end':'2026-10-02'}]}
    outcome=c.collect(store,plan,LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:injected,wall=wall_clock())[0]
    assert outcome.failure=='bad-frame' and outcome.diagnostic_stage is None


@pytest.mark.parametrize('replacement', ['storage','clock','cleanup','budget'])
def test_stage_replacement_precedence_and_no_leak_to_later_jobs(replacement,store):
    plan={'schema_version':1,'codes':[],'news':[{'keyword':'synthetic','size':1,'lang':'en'}],
          'history':[{'code':'US.SYN','end':'2026-10-02'}]}
    now=[0.];calls=[]
    class Wrapped:
        def ingest(self,*a,**k):
            if replacement=='storage':raise OSError('SYNTHETIC-PRIVATE-PATH-CANARY')
            result=store.ingest(*a,**k)
            if replacement=='budget':now[0]=301.
            return result
    def run(*a,**k):
        calls.append(1)
        return c.WorkerReply(ReadResponse(200,b''),OBS,'invalid-response',replacement!='cleanup','envelope')
    outcome=c.collect(Wrapped(),plan,LOCATOR,run_id='synthetic',supervisor=run,
        wall=(lambda:OBS.replace('2026','2025')) if replacement=='clock' else wall_clock(),clock=lambda:now[0])
    if replacement=='clock':
        assert outcome[0].failure=='clock-order' and outcome[0].diagnostic_stage is None
    elif replacement=='storage':
        assert outcome[0].failure=='storage-failed' and outcome[0].diagnostic_stage is None
    elif replacement=='cleanup':
        assert outcome[0].failure=='cleanup-failed' and outcome[0].diagnostic_stage is None
        assert outcome[1].status=='unattempted' and outcome[1].diagnostic_stage is None
    else:
        assert outcome[0].failure=='invalid-response' and outcome[0].diagnostic_stage=='envelope'
        assert outcome[1].failure=='run-budget' and outcome[1].diagnostic_stage is None
    assert len(calls)==1 and 'CANARY' not in repr(outcome)


@pytest.mark.parametrize('diagnostics', [False,True])
@pytest.mark.parametrize('failure', [None,'invalid-response','credentials'])
def test_stage_cli_opt_in_shapes_exit_codes_and_privacy(diagnostics,failure,store,tmp_path,monkeypatch,capsys):
    from scripts import market_collect as cli
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(PLAN))
    stage='metadata-missing' if failure=='invalid-response' else None
    outcome=c.JobOutcome('synthetic-job','failed' if failure else 'success','synthetic-attempt',failure,stage)
    monkeypatch.setattr(cli,'collect',lambda *a,**k:[outcome])
    args=['--root',str(store.root),'--plan',str(plan),'--credential-directory',LOCATOR['directory'],
          '--app-key-name','synthetic-app-key-id','--run-id','synthetic-run']
    if diagnostics:args.append('--diagnostics')
    assert cli.main(args)==(1 if failure else 0)
    captured=capsys.readouterr();summary=json.loads(captured.out)
    assert captured.err=='' and LOCATOR['directory'] not in captured.out and str(store.root) not in captured.out
    assert set(summary)==({'run_id','outcomes','schema_version'} if diagnostics else {'run_id','outcomes'})
    value=summary['outcomes'][0]
    assert set(value)==({'job_id','status','attempt_id','failure','diagnostic_stage'} if diagnostics
                       else {'job_id','status','attempt_id','failure'})
    if diagnostics:assert summary['schema_version']==2 and value['diagnostic_stage']==stage


@pytest.mark.parametrize('change', [
    {'failure':[]}, {'failure':'SYNTHETIC-EXCEPTION-CANARY'},
    {'response':ReadResponse(True,b'')}, {'response':ReadResponse(600,b'')},
    {'response':ReadResponse(200,'SYNTHETIC-BODY-CANARY')}, {'cleanup_ok':'SYNTHETIC-CANARY'}])
def test_stage_injected_reply_bounded_types(change,store):
    fields=dict(response=ReadResponse(200,b''),observed_at=OBS,failure='invalid-response',
                diagnostic_stage='envelope')
    injected=c.WorkerReply(**{**fields,**change})
    outcome=c.collect(store,{'schema_version':1,'codes':[],'news':[],'history':[{'code':'US.SYN','end':'2026-10-02'}]},
        LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:injected,wall=wall_clock())[0]
    assert outcome.failure=='bad-frame' and outcome.diagnostic_stage is None and 'CANARY' not in repr(outcome)


@pytest.mark.parametrize('job,status,failure,stage', [
    (HISTORY,200,'invalid-response',None), (HISTORY,200,'invalid-response',[]),
    (HISTORY,200,'invalid-response','forged'), (JOB,200,'invalid-response','envelope'),
    (HISTORY,403,'invalid-response','envelope'), (HISTORY,200,None,'envelope'),
    (HISTORY,200,'timeout','envelope')])
def test_stage_encoder_rejects_impossible_contract(job,status,failure,stage):
    with pytest.raises(ValueError):
        c.encode_reply(job,ReadResponse(status,b''),OBS,failure,diagnostic_stage=stage)


@pytest.mark.parametrize('case', ['bytes','empty','oversized'])
def test_stage_worker_bounded_body_before_decode(case):
    raw=stage_worker(ReadResponse(200,'not-bytes' if case=='bytes' else b'' if case=='empty' else b'x'*(c.MAX_RAW+1)))
    parsed=c.parse_reply(raw,HISTORY)
    assert parsed.failure=='invalid-response' and parsed.diagnostic_stage=='decode-screen'
    assert parsed.response.body==b''


def test_stage_legacy_injected_history_failure_keeps_null(store):
    injected=c.WorkerReply(ReadResponse(200,b''),OBS,'invalid-response')
    outcome=c.collect(store,{'schema_version':1,'codes':[],'news':[],'history':[{'code':'US.SYN','end':'2026-10-02'}]},
        LOCATOR,run_id='synthetic',supervisor=lambda *a,**k:injected,wall=wall_clock())[0]
    assert outcome.failure=='invalid-response' and outcome.diagnostic_stage is None
