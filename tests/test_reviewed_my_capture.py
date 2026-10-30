"""Authored offline contracts and real synthetic process negatives; no credentials.

Review/release fixtures below are test data, not financial or source authority.
The original private capability packet is deliberately not a test dependency.
"""
import concurrent.futures
import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/stock-research/run_reviewed_my_capture.py'
spec = importlib.util.spec_from_file_location('reviewed_my156',SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
MS = m.START_MS+3600000


def put(path, value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    path.write_bytes(value if type(value) is bytes else m.encoded(value))
    path.chmod(0o600)
    return m.reference(path)


def source(path):
    raw = path.read_bytes()
    return dict(path=str(path),sha256=m.sha(raw),bytes=len(raw))


def save(f):
    f['ref'] = put(f['root']/'inputs/plan.json',f['plan'])
    p = f['plan']
    f['release'] = put(f['root']/'inputs/release.json',dict(schema_version=1,kind='lead-single-my-release',
        plan_sha256=f['ref']['sha256'],argv_sha256=p['argv_sha256'],run_id=p['run_id'],
        reference=m.REFERENCE,target=m.TARGET,not_before_ms=MS-1000,expires_at_ms=MS+599000,
        resources_confirmed=True,exclusive_provider_window=True,source_authorized=True,limits=m.LIMITS))


@pytest.fixture
def f(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    for name in ('inputs','store','outputs','opaque-fixture'):
        (tmp_path/name).mkdir(mode=0o700)
    monkeypatch.setattr(m,'now_ms',lambda:MS)
    p = dict(schema_version=1,kind='single-my-capture',reference=m.REFERENCE,target=m.TARGET,
        instrument='MY.4707',mic='XKLS',run_id='synthetic-one',
        python=source(Path(sys.executable).resolve()),python_command=str(Path(sys.executable).absolute()),
        runtime_files=[source(ROOT/name) for name in sorted(m.RUNTIME)],
        collector_plan=put(tmp_path/'inputs/collector.json',m.COLLECTOR_PLAN),
        calendar=put(tmp_path/'inputs/calendar.json',dict(schema_version=1,calendar='XKLS',
            timezone='Asia/Kuala_Lumpur',reference=m.REFERENCE,target=m.TARGET,
            required_dates=m.DATES,settled_after_ms=m.START_MS)),
        store_root=str(tmp_path/'store'),output_parent=str(tmp_path/'outputs'),
        locator=dict(directory=str(tmp_path/'opaque-fixture'),app_key_name='fixture-only'),limits=m.LIMITS)
    for field,role in (('purpose','Lead'),('financial','Trader')):
        conditions = (dict(private_history_research=True,public_output=False) if field=='purpose' else
            dict(ordinary_equity=True,financial_currency='MYR',unit='traded_price',adjustment=0,
                 action_placement_reviewed=True,native_provider_currency=None,provider_security_id=None,
                 timezone_basis='hours_hypothesis_not_vendor_confirmed'))
        p[field] = put(tmp_path/f'inputs/{field}.json',dict(schema_version=1,kind=field,reviewer=role,
            approved=True,instrument='MY.4707',reference=m.REFERENCE,target=m.TARGET,
            effective_from='2026-10-01',effective_to=m.TARGET,reviewed_at_ms=MS-1000,conditions=conditions))
    argv = [p['python_command'],str(ROOT/'scripts/market_collect.py'),'--root',p['store_root'],
        '--plan',p['collector_plan']['path'],'--credential-directory',p['locator']['directory'],
        '--app-key-name',p['locator']['app_key_name'],'--run-id',p['run_id'],'--diagnostics',
        '--diagnostic-receipt',str(tmp_path/'outputs'/p['run_id']/'diagnostic.json')]
    p['argv_sha256'] = m.sha(m.encoded(argv))
    result = dict(root=tmp_path,plan=p,argv=argv)
    save(result)
    return result


def context(f):
    started = time.monotonic()
    return m.prepare(f['ref']['path'],f['ref']['sha256'],started),started


def run(f, mode='inspect'):
    return m.operate(f['ref']['path'],f['ref']['sha256'],mode,f['release'])


def contents(root):
    return {str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def forbidden(*args,**kwargs):
    raise AssertionError('No child, provider or credential operation is allowed')


def test_default_inspection_no_import_dispatch_or_private_mutation(f,monkeypatch):
    before = contents(f['root']); modules = set(sys.modules)
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(m,'helpers',forbidden)
    result = run(f)
    assert result==dict(status='HELD',reason='inspection-only-no-source-release',child_started=False)
    assert contents(f['root'])==before and set(sys.modules)==modules
    assert not (f['root']/'store/.reviewed-my-claims').exists()


@pytest.mark.parametrize('change',['venue','instrument','target','reference','bool-version','bool-limit',
    'unknown','collector-other','collector-bool','calendar-date','review-expired','review-future',
    'financial-unit','public-purpose','argv','python-label','runtime-missing','runtime-duplicate','runtime-foreign','hash'])
def test_preflight_rejections_no_dispatch(f,monkeypatch,change):
    p = f['plan']
    if change=='venue':p['mic']='XNYS'
    elif change=='instrument':p['instrument']='MY.1155'
    elif change=='target':p['target']='2026-11-02'
    elif change=='reference':p['reference']='2026-10-30'
    elif change=='bool-version':p['schema_version']=True
    elif change=='bool-limit':p['limits']=p['limits']|dict(retries=False)
    elif change=='unknown':p['override']=True
    elif change.startswith('collector-'):
        doc=copy.deepcopy(m.COLLECTOR_PLAN)
        if change=='collector-other':doc['history'][0]['code']='BMS.1155'
        else:doc['schema_version']=True
        p['collector_plan']=put(Path(p['collector_plan']['path']),doc)
    elif change=='calendar-date':
        doc=json.loads(Path(p['calendar']['path']).read_text());doc['required_dates']=m.DATES[:-1]
        p['calendar']=put(Path(p['calendar']['path']),doc)
    elif change.startswith('review-'):
        doc=json.loads(Path(p['financial']['path']).read_text())
        doc['reviewed_at_ms']=m.START_MS-1 if change=='review-expired' else MS+1
        p['financial']=put(Path(p['financial']['path']),doc)
    elif change=='financial-unit':
        doc=json.loads(Path(p['financial']['path']).read_text());doc['conditions']['financial_currency']='USD'
        p['financial']=put(Path(p['financial']['path']),doc)
    elif change=='public-purpose':
        doc=json.loads(Path(p['purpose']['path']).read_text());doc['conditions']['public_output']=True
        p['purpose']=put(Path(p['purpose']['path']),doc)
    elif change=='argv':p['argv_sha256']='0'*64
    elif change=='python-label':p['python_command']='/tmp/foreign-python'
    elif change=='runtime-missing':p['runtime_files'].pop()
    elif change=='runtime-duplicate':p['runtime_files'][0]=p['runtime_files'][1]
    elif change=='runtime-foreign':p['runtime_files'][0]['path']=str(ROOT/'AGENTS.md')
    elif change=='hash':p['runtime_files'][0]['sha256']='f'*64
    save(f)
    monkeypatch.setattr(m,'helpers',forbidden)
    assert run(f,'execute')['status']=='HELD'
    assert not (f['root']/'store/.reviewed-my-claims').exists()


@pytest.mark.parametrize('current',[m.START_MS-1,m.START_MS,m.END_MS,m.END_MS+1,m.END_MS-27000])
def test_strict_window_and_reserve(f,monkeypatch,current):
    monkeypatch.setattr(m,'now_ms',lambda:current)
    monkeypatch.setattr(m,'helpers',forbidden)
    result=run(f,'execute')
    assert result['reason']=='expired-or-outside-original-window' and not result['child_started']


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":Infinity}'])
def test_strict_json(raw):
    with pytest.raises(m.Held):m.decode(raw)


@pytest.mark.parametrize('change',['plan-mode','input-mode','directory-mode','leaf-link','parent-link','bool-bytes'])
def test_paths_modes_and_refs(f,change):
    p=f['plan']; target=Path(p['purpose']['path'])
    if change=='plan-mode':Path(f['ref']['path']).chmod(0o644)
    elif change=='input-mode':target.chmod(0o644)
    elif change=='directory-mode':target.parent.chmod(0o755)
    elif change=='leaf-link':
        actual=target.with_name('original.json');target.rename(actual);target.symlink_to(actual)
    elif change=='parent-link':
        link=f['root']/'linked';link.symlink_to(target.parent,target_is_directory=True)
        p['purpose']['path']=str(link/target.name);save(f)
    else:p['purpose']['bytes']=True;save(f)
    assert run(f,'execute')['status']=='HELD'
    assert not (f['root']/'store/.reviewed-my-claims').exists()


@pytest.mark.parametrize('change',['future','expired','too-long','bool-version','unknown','wrong-plan',
    'wrong-command','wrong-run','date','resources','exclusive','authority','bool-limits'])
def test_release_rejections(f,monkeypatch,change):
    r=json.loads(Path(f['release']['path']).read_text())
    if change=='future':r['not_before_ms']=MS+1
    elif change=='expired':r['expires_at_ms']=MS
    elif change=='too-long':r['expires_at_ms']=MS+600000
    elif change=='bool-version':r['schema_version']=True
    elif change=='unknown':r['allow_retry']=True
    elif change=='wrong-plan':r['plan_sha256']='0'*64
    elif change=='wrong-command':r['argv_sha256']='0'*64
    elif change=='wrong-run':r['run_id']='different'
    elif change=='date':r['target']='2026-11-02'
    elif change=='resources':r['resources_confirmed']=False
    elif change=='exclusive':r['exclusive_provider_window']=False
    elif change=='authority':r['source_authorized']=False
    else:r['limits']['retries']=False
    f['release']=put(Path(f['release']['path']),r)
    monkeypatch.setattr(m,'helpers',forbidden)
    assert run(f,'execute')['status']=='HELD'
    assert not (f['root']/'store/.reviewed-my-claims').exists()


def test_atomic_single_use_concurrent_and_uncertain_claims(f):
    ctx,started=context(f)
    def reserve(_):
        try:return m.claim(ctx,f['release'],started,MS)
        except FileExistsError:return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(reserve,range(2)))
    assert sum(r is not None for r in results)==1
    assert (ctx['attempt']/'intent.json').exists()
    with pytest.raises(FileExistsError):m.claim(ctx,f['release'],started,MS)
    # Deleting the output does not reset the durable store-level consumed claim.
    (ctx['attempt']/'intent.json').unlink();ctx['attempt'].rmdir()
    with pytest.raises(FileExistsError):m.claim(ctx,f['release'],started,MS)


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),-1])
def test_intent_start_strict(value):
    with pytest.raises(m.Held):m.deadline(value)


def test_continuation_pins_intent_clock_and_consumed_claim(f):
    ctx,started=context(f);intent=m.claim(ctx,f['release'],started,MS)
    same,original=m.continuation(f['ref']['path'],f['ref']['sha256'],f['release'],intent)
    assert same['sha']==ctx['sha'] and original==started
    data=json.loads(Path(intent['path']).read_text());data['started_ms']=MS-10000
    bad=put(Path(intent['path']),data)
    with pytest.raises(m.Held,match='clock-discontinuity'):
        m.continuation(f['ref']['path'],f['ref']['sha256'],f['release'],bad)


def test_exact_command_and_bootstrap_hash_before_execution(f):
    ctx,_=context(f)
    assert ctx['argv']==f['argv']
    argv=m.internal_argv(ctx,'worker',f['release'],dict(path='/private/not-used',sha256='0'*64,bytes=1))
    assert argv[:4]==[f['plan']['python_command'],'-I','-B','-c']
    # Deliberately corrupt the expected hash in the isolated bootstrap; it must
    # fail before even parsing internal stage arguments or touching private paths.
    argv[4]=argv[4].replace(m.sha(ctx['buffers'][str(SCRIPT.relative_to(ROOT))]),'0'*64)
    result=subprocess.run(argv,capture_output=True,text=True,timeout=5)
    assert result.returncode!=0 and 'AssertionError' in result.stderr
    assert not ctx['attempt'].exists()


def test_verified_import_closure_in_fresh_isolated_process(f):
    # This executes imports only. No worker, credential loader or source call.
    code=f'''import importlib.util,sys
s=importlib.util.spec_from_file_location('fixture156',{str(SCRIPT)!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.now_ms=lambda:{MS}
c=m.prepare({f['ref']['path']!r},{f['ref']['sha256']!r},m.time.monotonic())
h,_=m.helpers(c)
collector,store,entry=m.install_runtime(c,h)
assert collector.job_digest(m.JOB)==m.sha(m.encoded(m.JOB))
assert collector.job_request(m.JOB).query=='end=2026-10-29&ktype=2&autype=0&num=100'
assert 'market_calendar' not in sys.modules
assert all(isinstance(sys.modules[n].__loader__,h.BufferLoader) for n in ('ingest','ingest.market_collector','ingest.private_market_store','connectors','connectors.moomoo_rest','connectors.moomoo_rest_live'))
print('verified-imports-only')
'''
    result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr
    assert result.stdout.strip()=='verified-imports-only'


@pytest.mark.parametrize('state',['reused','foreign-group','unknown','denied','absent','owned'])
def test_nested_killer_never_signals_unowned_or_reused_group(monkeypatch,state):
    proc=SimpleNamespace(pid=5678);signals=[]
    row=(1,5678,1000,'original')
    if state=='reused':row=(1,5678,1000,'newbirth')
    if state=='foreign-group':row=(1,5679,1000,'original')
    table={} if state in ('unknown','absent') else {5678:row}
    helper=SimpleNamespace(process_snapshot=lambda **_:table,group_state=lambda _:False if state=='absent' else True)
    def send(group,sig):
        signals.append((group,sig))
        if state=='denied':raise PermissionError()
    monkeypatch.setattr(os,'killpg',send)
    killer=m.guarded_killer(helper,proc,'original')
    if state=='owned':killer(5678,signal.SIGKILL)
    else:
        with pytest.raises((m.Held,PermissionError,ProcessLookupError)):killer(5678,signal.SIGKILL)
    assert len(signals)==(1 if state in ('owned','denied') else 0)


@pytest.mark.parametrize('mutation',['wrong-job','wrong-locator','wrong-digest','bool-version','truncated','extra'])
def test_internal_worker_frame_rejects_before_loader(f,monkeypatch,mutation):
    ctx,started=context(f)
    frame=dict(version=1,job=copy.deepcopy(m.JOB),job_digest=m.sha(m.encoded(m.JOB)),locator=f['plan']['locator'])
    if mutation=='wrong-job':frame['job']['code']='BMS.1155'
    elif mutation=='wrong-locator':frame['locator']=dict(directory='/tmp/foreign',app_key_name='foreign')
    elif mutation=='wrong-digest':frame['job_digest']='f'*64
    elif mutation=='bool-version':frame['version']=True
    elif mutation=='extra':frame['override']=True
    raw=m.encoded(frame);packet=struct.pack('!I',len(raw))+raw
    if mutation=='truncated':packet=packet[:-1]
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(packet)))
    monkeypatch.setattr(m,'helpers',forbidden)
    with pytest.raises(m.Held):m.internal_worker(ctx,started,f['release'],{})
    assert not ctx['attempt'].exists()


def stored_fixture(f):
    from ingest.market_collector import job_request
    from ingest.private_market_store import PrivateMarketStore
    from connectors.moomoo_rest import ReadResponse
    store=PrivateMarketStore(f['plan']['store_root'],create=True)
    rows=[]
    for day in ['2026-09-30']+m.DATES:
        stamp=int(datetime.fromisoformat(day+'T09:00:00+08:00').timestamp()*1000)
        rows.append(dict(date=int(day.replace('-','')),time_key=stamp,time_zone=8,close=10.5))
    observed=datetime.fromtimestamp((MS-500)/1000,timezone.utc).isoformat()
    ingested=datetime.fromtimestamp(MS/1000,timezone.utc).isoformat()
    attempt=store.ingest(job_request(m.JOB),ReadResponse(200,m.encoded(dict(ret_code=0,ret_msg='ok',data=dict(kline_list=rows)))),run_id=f['plan']['run_id'],
        observed_at=observed,ingested_at=ingested,normalization_version=6,normalization_dialect=m.DIALECT)
    assert attempt.status=='success'
    summary=dict(schema_version=2,run_id=f['plan']['run_id'],outcomes=[dict(job_id=m.sha(m.encoded(m.JOB)),
        status='success',attempt_id=attempt.attempt_id,failure=None,diagnostic_stage=None)])
    cutoff=datetime.fromtimestamp((MS+1)/1000,timezone.utc).isoformat()
    return store,summary,cutoff


def test_real_store_integrity_and_attempt_binding_with_older_bars(f):
    ctx,_=context(f);store,summary,cutoff=stored_fixture(f)
    result=m.validate_rows(ctx,summary,store,cutoff)
    assert result['rows']==22 and result['required_closes']==21 and result['financial_admission'] is False
    assert result['attempt_id']==summary['outcomes'][0]['attempt_id']
    # Stored observation has no synthetic id key: the real canonical hash binds it.
    assert 'id' not in store.query('history',cutoff,run_id=f['plan']['run_id'])[0]['observation']
    raw=list((Path(f['plan']['store_root'])/'raw').iterdir())[0]
    # Deliberately tamper only this test's immutable private archive, restoring
    # its original mode so the rejection tests integrity rather than mode alone.
    mode=raw.stat().st_mode&0o777
    raw.chmod(0o600)
    raw.write_bytes(b'corrupt')
    raw.chmod(mode)
    with pytest.raises(Exception):m.validate_rows(ctx,summary,store,cutoff)


def test_hidden_failed_attempt_in_same_run_is_rejected(f):
    from ingest.market_collector import job_request
    from connectors.moomoo_rest import ReadResponse
    ctx,_=context(f);store,summary,cutoff=stored_fixture(f)
    stamp=datetime.fromtimestamp(MS/1000,timezone.utc).isoformat()
    failed=store.ingest(job_request(m.JOB),ReadResponse(503,b''),run_id=f['plan']['run_id'],
        observed_at=stamp,ingested_at=stamp,normalization_version=6,normalization_dialect=m.DIALECT)
    assert failed.status=='failed'
    with pytest.raises(m.Held,match='attempt-count'):m.validate_rows(ctx,summary,store,cutoff)


@pytest.mark.parametrize('change',['partial','empty','all-missing','unknown','other-attempt','other-run',
    'missing','duplicate','future','revised','overflow','close','time-zone','currency-basis','normalization','known-future'])
def test_store_result_rejections_even_when_cli_exit_would_be_zero(f,change):
    ctx,_=context(f);store,summary,cutoff=stored_fixture(f)
    rows=store.query('history',cutoff,run_id=f['plan']['run_id'],limit=101)
    if change in ('partial','empty','all-missing','unknown'):
        summary['outcomes'][0]['status']={'empty':'successful-empty'}.get(change,change)
    elif change=='other-attempt':summary['outcomes'][0]['attempt_id']='0'*64
    elif change=='other-run':summary['run_id']='another'
    elif change=='missing':rows=rows[:-1]
    elif change=='duplicate':rows[-1]['record']['date']=rows[0]['record']['date']
    elif change=='future':rows[-1]['record']['date']='2026-10-30'
    elif change=='revised':rows[-1]['revision']=2
    elif change=='overflow':rows=rows*5
    elif change=='close':rows[-1]['record']['close']=float('nan')
    elif change=='time-zone':rows[-1]['record']['time_zone']=480
    elif change=='currency-basis':rows[-1]['record']['adjustment']=1
    elif change=='normalization':rows[-1]['observation']['normalization_version']=7
    elif change=='known-future':rows[-1]['observation']['known_ms']=MS+1
    def query(*args,**kwargs):
        assert kwargs['run_id']==f['plan']['run_id'] and kwargs['limit']==101
        return rows
    with pytest.raises(m.Held):
        m.validate_rows(ctx,summary,SimpleNamespace(query=query,_connection=store._connection),cutoff)


def test_public_entry_timer_starts_before_argument_parsing(f,monkeypatch):
    clock=[100.]
    monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    original=m.argparse.ArgumentParser.parse_args
    def delayed(self,*a,**k):
        clock[0]+=25
        return original(self,*a,**k)
    monkeypatch.setattr(m.argparse.ArgumentParser,'parse_args',delayed)
    monkeypatch.setattr(m,'helpers',forbidden)
    assert m.main(['--plan',f['ref']['path'],'--plan-sha256',f['ref']['sha256'],'--mode','execute',
                   '--release-ref',m.encoded(f['release']).decode()])==2
    assert not (f['root']/'store/.reviewed-my-claims').exists()


def test_late_public_output_cannot_return_success(f,monkeypatch):
    clock=[100.]
    monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(m,'operate',lambda *a,**k:dict(status='PRIVATE_CANDIDATE',financial_admission=False))
    import builtins
    def late_print(*args,**kwargs):clock[0]+=25
    monkeypatch.setattr(builtins,'print',late_print)
    assert m.main(['--plan',f['ref']['path'],'--plan-sha256',f['ref']['sha256']])==2


def test_preflight_consumes_original_dispatch_budget(f,monkeypatch):
    clock=[100.]
    monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    original=m.prepare
    def delayed(*a):
        ctx=original(*a);clock[0]+=8;return ctx
    monkeypatch.setattr(m,'prepare',delayed)
    observed=[]
    h155,h163=m.helpers(original(f['ref']['path'],f['ref']['sha256'],100.))
    def supervise(argv,limits,helper):
        observed.append(limits)
        return dict(approved=False,returncode=1,cleanup_verified=True,stdout='opaque-fixture',stderr='opaque-fixture')
    monkeypatch.setattr(m,'helpers',lambda _: (h155,SimpleNamespace(supervise=supervise)))
    result=run(f,'execute')
    assert result['status']=='HELD' and len(observed)==1 and 16.9<observed[0]['work_seconds']<17
    receipt=json.loads((f['root']/'outputs/synthetic-one/supervisor.json').read_text())
    assert 'stdout' not in receipt and 'stderr' not in receipt
    assert run(f,'execute')['child_started'] is False


@pytest.mark.parametrize('detached',[False,True])
def test_real_synthetic_timeout_and_detached_descendant_cleanup(f,detached):
    ctx,_=context(f);h155,h163=m.helpers(ctx)
    code=('import time; time.sleep(30)' if not detached else
          'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True); time.sleep(30)')
    result=h163.supervise([sys.executable,'-I','-B','-c',code],
        dict(work_seconds=.6,cleanup_seconds=2,rss_bytes=536870912,threads=1,retries=0),h155)
    assert not result['approved'] and result['reason']=='execution-timeout'
    assert result['cleanup_verified'] and result['elapsed_seconds']<2.6
    if detached:assert len(result['owned_groups'])>=2


def test_real_supervisor_unknown_monitor_remains_held(f,monkeypatch):
    ctx,_=context(f);h155,h163=m.helpers(ctx)
    original=h155.process_snapshot;calls=[0]
    def fail_once(**kwargs):
        calls[0]+=1
        if calls[0]==1:raise ValueError('authored monitor failure')
        return original(**kwargs)
    monkeypatch.setattr(h155,'process_snapshot',fail_once)
    result=h163.supervise([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],
        dict(work_seconds=.6,cleanup_seconds=2,rss_bytes=536870912,threads=1,retries=0),h155)
    assert not result['approved'] and result['reason']=='supervision-failed'
    assert result['cleanup_verified']


def offline_runtime(f,monkeypatch):
    """Real collector/store with an IPC worker replaced by an authored frame.

    Only test subprocesses run. The original credential worker is never called.
    """
    import ingest.market_collector as collector
    import ingest.private_market_store as storage
    from connectors.moomoo_rest import ReadResponse
    storage.PrivateMarketStore(f['plan']['store_root'],create=True)
    rows=[]
    for day in m.DATES:
        rows.append(dict(date=int(day.replace('-','')),time_key=int(datetime.fromisoformat(day+'T09:00:00+08:00').timestamp()*1000),
                         time_zone=8,close=10.5))
    body=m.encoded(dict(ret_code=0,ret_msg='fixture-only',data=dict(kline_list=rows)))
    stamp=datetime.fromtimestamp(MS/1000,timezone.utc).isoformat()
    reply=collector.encode_reply(m.JOB,ReadResponse(200,body),stamp,frame_version=3,normalization_version=6)
    original_collect=collector.collect
    def collect(*args,**kwargs):
        result=original_collect(*args,**kwargs,wall=lambda:stamp)
        f['outcomes']=result
        return result
    adapted=SimpleNamespace(ENTRY=collector.ENTRY,supervise=collector.supervise,collect=collect)
    entry=m.load_module('_fixture_collector',ROOT/'scripts/market_collect.py',(ROOT/'scripts/market_collect.py').read_bytes())
    monkeypatch.setattr(m,'install_runtime',lambda *a:(adapted,storage,entry))
    original_popen=subprocess.Popen
    calls=[]
    f['received']=f['root']/'fixture-frame-size.txt'
    def spawn(argv,**kwargs):
        if argv[:2]==['/bin/ps','-axo']:
            return original_popen(argv,**kwargs)
        assert argv[1:4]==['-I','-B','-c'] and '--internal' in argv and 'worker' in argv
        calls.append(argv)
        # Read the original framed request to EOF, then return an authored
        # response. This exercises the unchanged selector/frame/cleanup path.
        code=('import os,sys;packet=sys.stdin.buffer.read();'
              f'fd=os.open({str(f["received"])!r},os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);'
              'os.write(fd,str(len(packet)).encode());os.close(fd);'
              'sys.stdout.buffer.write('+repr(reply)+');sys.stdout.buffer.flush()')
        return original_popen([sys.executable,'-I','-B','-c',code],**kwargs)
    monkeypatch.setattr(subprocess,'Popen',spawn)
    return calls


def test_offline_complete_collector_ipc_store_and_parent_validation(f,monkeypatch):
    calls=offline_runtime(f,monkeypatch)
    real_helpers=m.helpers
    def helpers(ctx):
        h155,h163=real_helpers(ctx)
        def supervise(argv,limits,helper):
            assert argv[1:4]==['-I','-B','-c'] and limits['work_seconds']<=25
            intent=m.reference(ctx['attempt']/'intent.json')
            code=m.internal_cli(ctx,json.loads(Path(intent['path']).read_text())['started'],f['release'],intent)
            return dict(approved=True,returncode=code,cleanup_verified=True,stdout='',stderr='',limits=limits)
        return h155,SimpleNamespace(supervise=supervise)
    monkeypatch.setattr(m,'helpers',helpers)
    result=run(f,'execute')
    assert result==dict(status='PRIVATE_CANDIDATE',child_started=True,financial_admission=False),[(o.status,o.failure) for o in f.get('outcomes',[])]
    assert len(calls)==1
    attempt=f['root']/'outputs/synthetic-one'
    assert json.loads((attempt/'candidate.json').read_text())['result']['required_closes']==21
    receipt=json.loads((attempt/'completed.json').read_text())
    assert receipt['accepted'] is False and receipt['status']=='unsealed-evidence'
    assert run(f,'execute')['status']=='HELD' and len(calls)==1


def test_worker_final_gate_single_use_and_no_credentials(f,monkeypatch):
    ctx,started=context(f);intent=m.claim(ctx,f['release'],started,MS)
    raw=m.encoded(dict(version=1,job=m.JOB,job_digest=m.sha(m.encoded(m.JOB)),locator=f['plan']['locator']))
    packet=struct.pack('!I',len(raw))+raw
    calls=[]
    def worker(stdin,stdout):
        calls.append(stdin.read())
        return 0
    monkeypatch.setattr(m,'install_runtime',lambda *a:(SimpleNamespace(worker_main=worker),None,None))
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(packet)))
    assert m.internal_worker(ctx,started,f['release'],intent)==0 and calls==[packet]
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(packet)))
    with pytest.raises(FileExistsError):m.internal_worker(ctx,started,f['release'],intent)
    assert len(calls)==1


def test_unobserved_worker_never_receives_authorization_frame(f,monkeypatch):
    calls=offline_runtime(f,monkeypatch)
    ctx,started=context(f);intent=m.claim(ctx,f['release'],started,MS)
    h155,h163=m.helpers(ctx)
    # Fail the initial process observation. Closing stdin must precede the
    # collector's selector loop, so the worker sees EOF instead of a frame.
    monkeypatch.setattr(h155,'process_snapshot',lambda **_: {})
    monkeypatch.setattr(m,'helpers',lambda _: (h155,h163))
    with pytest.raises(m.Held,match='collector-failed'):
        m.internal_cli(ctx,started,f['release'],intent)
    assert len(calls)==1 and f['received'].read_text()=='0'
    assert not (ctx['attempt']/'candidate.json').exists()


def test_release_mutation_after_worker_import_cannot_reach_loader(f,monkeypatch):
    ctx,started=context(f);intent=m.claim(ctx,f['release'],started,MS)
    raw=m.encoded(dict(version=1,job=m.JOB,job_digest=m.sha(m.encoded(m.JOB)),locator=f['plan']['locator']))
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=io.BytesIO(struct.pack('!I',len(raw))+raw)))
    def install(*args):
        Path(f['release']['path']).write_bytes(b'{}')
        return SimpleNamespace(worker_main=forbidden),None,None
    monkeypatch.setattr(m,'install_runtime',install)
    with pytest.raises(m.Held,match='hash-mismatch'):m.internal_worker(ctx,started,f['release'],intent)


def test_late_final_write_leaves_only_unsealed_evidence(f,monkeypatch):
    clock=[time.monotonic()]
    monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    # Use authored rows from a real private test store; skip collection only in
    # this targeted final-write test. The success path above covers actual IPC.
    store,summary,cutoff=stored_fixture(f)
    ctx,_=context(f);verified=m.validate_rows(ctx,summary,store,cutoff)
    real_helpers=m.helpers
    def helpers(ctx):
        h155,_=real_helpers(ctx)
        def supervise(*a):
            m.write(ctx['attempt'],'candidate.json',dict(plan_sha256=ctx['sha'],summary=summary,result=verified))
            return dict(approved=True,returncode=0,cleanup_verified=True,stdout='',stderr='')
        return h155,SimpleNamespace(supervise=supervise)
    monkeypatch.setattr(m,'helpers',helpers)
    monkeypatch.setattr(m,'install_runtime',lambda *a:(None,SimpleNamespace(PrivateMarketStore=lambda _:store),None))
    original_write=m.write
    def late(directory,name,value):
        result=original_write(directory,name,value)
        if name=='completed.json':clock[0]+=25
        return result
    monkeypatch.setattr(m,'write',late)
    result=run(f,'execute')
    assert result['status']=='HELD' and result['reason']=='work-deadline'
    receipt=json.loads((ctx['attempt']/'completed.json').read_text())
    assert receipt['accepted'] is False and receipt['status']=='unsealed-evidence'
