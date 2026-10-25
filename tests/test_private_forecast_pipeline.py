"""Finite orchestration with fake clocks/supervisors and real synthetic store I/O."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from connectors.moomoo_rest import ReadResponse
from ingest import private_forecast_pipeline as pipeline
from ingest import market_collector as collector

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline_refresh_fixtures',ROOT/'tests/test_private_forecast_refresh.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)


class Clock:
    def __init__(self):self.value=0.;self.sleeps=[]
    def tick(self):return self.value
    def wall(self):return (datetime(2026,10,21,23,tzinfo=timezone.utc)+timedelta(seconds=self.value)).isoformat(timespec='microseconds')
    def sleep(self,seconds):self.sleeps.append(seconds);self.value+=seconds


def put(path,value):
    path.write_text(json.dumps(value));path.chmod(0o600);return str(path)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**kw:pytest.fail('no network'))


@pytest.fixture
def setup(tmp_path):
    private,store,fixed=fixtures.setup.__wrapped__(tmp_path)
    prefix='fixture-run-new'
    for n,item in enumerate(fixed['items']):
        if n<2:
            item['template']['source']['vintage']=prefix+'-'+str(n+1).zfill(3)
        else:fixtures.unavailable(item)
    fixed_path=Path(put(private/'fixed50.json',fixed))
    credentials=private/'empty locator directory';credentials.mkdir(mode=0o700)
    locator=put(private/'locator.json',dict(directory=str(credentials),app_key_name='fictional-key-name'))
    receipts=private/'receipts';receipts.mkdir(mode=0o700)
    plan=dict(schema_version=1,codes=[],news=[],history=[dict(code=item['code'],end='2026-10-21') for item in fixed['items'][:2]])
    plan_path=put(private/'plan.json',plan)
    config=dict(schema_version=1,fixed50_config=str(fixed_path),credential_locator_file=locator,
        plans=[dict(path=plan_path,sha256=pipeline.refresh.core._hash(plan),run_seconds=60,
                    fixed50_sha256=pipeline.refresh.core._hash(fixed))],run_prefix=prefix,
        minimum_start_interval=3.,job_seconds=20.,cleanup_seconds=2.,total_seconds=120.,receipt_parent=str(receipts))
    release=dict(schema_version=1,config_sha256=pipeline.refresh.core._hash(config),not_before='2026-10-21T22:59:00Z',
        expires_at='2026-10-21T23:10:00Z',one_use_id='fixture-claim',source_rights_reference='fictional-release-only',
        reviewers=['Lead','Trader'],runtime_sha256=pipeline.runtime_hashes())
    config_path=put(private/'online.json',config);release_path=put(private/'release.json',release)
    return dict(private=private,store=store,fixed=fixed,config=config,release=release,
                config_path=config_path,release_path=release_path,clock=Clock(),calls=[])


def reseal(s):
    put(Path(s['config']['fixed50_config']),s['fixed'])
    for plan in s['config']['plans']:plan['fixed50_sha256']=pipeline.refresh.core._hash(s['fixed'])
    put(Path(s['config_path']),s['config'])
    s['release']['config_sha256']=pipeline.refresh.core._hash(s['config'])
    s['release']['runtime_sha256']=pipeline.runtime_hashes()
    put(Path(s['release_path']),s['release'])


def worker(s,*,failure=None,empty=False,count=21):
    def supervise(job,locator,*,timeout,cleanup):
        s['calls'].append(dict(job=deepcopy(job),time=s['clock'].tick(),timeout=timeout,cleanup=cleanup))
        s['clock'].sleep(1)
        if failure:return collector.WorkerReply(None,None,failure,failure!='cleanup-failed',normalization_version=4)
        item=next(i for i in s['fixed']['items'] if i['code']==job['code'])
        rows=[]
        for n,session in enumerate(item['template']['calendar']['sessions'][:count]):
            day=session['session_date'];stamp=int(datetime.fromisoformat(day+'T12:00:00+00:00').timestamp()*1000)
            rows.append(dict(time_key=stamp,date=int(day.replace('-','')),time_zone=-240,close=100+n))
        raw=json.dumps(dict(ret_code=0,ret_msg='ok',data=dict(kline_list=[] if empty else rows))).encode()
        return collector.WorkerReply(ReadResponse(200,raw),s['clock'].wall(),None,normalization_version=4)
    return supervise


def run(s,**kwargs):
    return pipeline.execute(s['config_path'],s['release_path'],clock=s['clock'].tick,wall=s['clock'].wall,
        sleep=s['clock'].sleep,supervisor=kwargs.pop('supervisor',worker(s)),**kwargs)


def test_online_paced_real_store_candidates_exact_review_required_no_fallback(setup):
    s=setup;before=Path(s['config']['fixed50_config']).read_bytes()
    summary,status=run(s)
    assert status==2 and summary['status']=='insufficient_coverage' and summary['next_action']=='review_required'
    assert summary['provider_refreshed'] is True and summary['counts']['review_required']==2
    assert summary['counts']['total']==50 and summary['counts']['generated']==0
    assert len(s['calls'])==2 and s['calls'][1]['time']-s['calls'][0]['time']>=3
    assert all(call['timeout']<=20 and call['cleanup']<=2 for call in s['calls'])
    assert Path(s['config']['fixed50_config']).read_bytes()==before
    receipt=json.loads(Path(summary['receipt_path']).read_text())
    assert receipt['provider_calls']==2 and receipt['retries']==0 and receipt['unattempted']==[]
    assert receipt['outcomes'][0]['plan_sha256']==s['config']['plans'][0]['sha256']
    resume=json.loads(Path(summary['resume_config']).read_text())
    assert resume['items'][0]['run_id']=='fixture-run-new-001'
    assert all(i['run_id'] is None for i in resume['items'][2:])
    with Path(summary['csv_path']).open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==50 and all(row['point']=='' for row in rows)
    review=json.loads(Path(summary['review_path']).read_text())
    assert review['items'][0]['evidence']['classification']=='authored_fixture'
    assert review['items'][0]['evidence']['bars'][0]['retrieved_at']==s['clock'].wall().replace('04.000000','01.000000')
    assert not (s['store'].root/'.collector.lock').exists()
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
               for path,digest in summary['artifacts'].items())


@pytest.mark.parametrize('failure',['credentials','rate-limited','timeout','invalid-response','upstream-failed','cleanup-failed'])
def test_first_worker_failure_stops_no_retry_and_preserves_failures(setup,failure):
    s=setup
    summary,status=run(s,supervisor=worker(s,failure=failure))
    assert status==1 and summary['status']=='collection_failed' and len(s['calls'])==1
    receipt=json.loads(Path(summary['receipt_path']).read_text())
    assert receipt['provider_calls']==1 and len(receipt['unattempted'])==1 and receipt['retries']==0
    assert not list(Path(s['fixed']['output_parent']).iterdir())
    assert len(json.loads((Path(summary['receipt_path']).parent/'missing-ledger.json').read_text())['items'])==50


@pytest.mark.parametrize('count',[0,19,20])
def test_partial_or_empty_required_window_stops_collection(setup,count):
    s=setup
    summary,status=run(s,supervisor=worker(s,empty=count==0,count=count))
    assert status==1 and len(s['calls'])==1
    assert summary['reason'] in ('upstream_or_capture_failure','history_or_finality_unavailable')


@pytest.mark.parametrize('change',['hash','fixed-hash','runtime','expiry','early','duplicate','too-many','interval','job','cleanup','plan-budget','global-budget','vintage','end','rights'])
def test_bad_release_plan_and_caps_fail_before_worker(setup,change):
    s=setup
    if change=='hash':s['release']['config_sha256']='0'*64
    elif change=='fixed-hash':s['config']['plans'][0]['fixed50_sha256']='0'*64
    elif change=='runtime':s['release']['runtime_sha256']={}
    elif change=='expiry':s['release']['expires_at']='2026-10-21T22:00:00Z'
    elif change=='early':s['release']['not_before']='2026-10-22T22:00:00Z'
    elif change in ('duplicate','too-many'):
        p=Path(s['config']['plans'][0]['path']);plan=json.loads(p.read_text())
        plan['history']=plan['history']* (2 if change=='duplicate' else 20)
        put(p,plan);s['config']['plans'][0]['sha256']=pipeline.refresh.core._hash(plan)
    elif change=='interval':s['config']['minimum_start_interval']=0
    elif change=='job':s['config']['job_seconds']=21
    elif change=='cleanup':s['config']['cleanup_seconds']=3
    elif change=='plan-budget':s['config']['plans'][0]['run_seconds']=301
    elif change=='global-budget':s['config']['total_seconds']=601
    elif change=='vintage':s['fixed']['items'][0]['template']['source']['vintage']='old'
    elif change=='end':
        p=Path(s['config']['plans'][0]['path']);plan=json.loads(p.read_text());plan['history'][0]['end']='2026-10-20'
        put(p,plan);s['config']['plans'][0]['sha256']=pipeline.refresh.core._hash(plan)
    elif change=='rights':s['fixed']['items'][0]['template']['rights']['history_collection']='unknown'
    # Bind intentional value changes without masking the particular invalid hash.
    bad_release_hash=s['release']['config_sha256'];bad_fixed_hash=s['config']['plans'][0]['fixed50_sha256']
    bad_runtime=s['release']['runtime_sha256']
    reseal(s)
    if change=='hash':s['release']['config_sha256']=bad_release_hash
    if change=='runtime':s['release']['runtime_sha256']=bad_runtime
    if change=='fixed-hash':s['config']['plans'][0]['fixed50_sha256']=bad_fixed_hash;put(Path(s['config_path']),s['config']);s['release']['config_sha256']=pipeline.refresh.core._hash(s['config'])
    put(Path(s['release_path']),s['release'])
    with pytest.raises((ValueError,OSError)):run(s)
    assert s['calls']==[] and not list(Path(s['config']['receipt_parent']).iterdir())


def test_claim_replay_and_store_wide_lock_prevent_duplicate_dispatch(setup):
    s=setup;summary,status=run(s)
    before={p.name:p.read_bytes() for p in Path(summary['csv_path']).parent.iterdir()}
    with pytest.raises(ValueError):run(s)  # Existing exact run IDs, even before claim.
    assert len(s['calls'])==2
    assert before=={p.name:p.read_bytes() for p in Path(summary['csv_path']).parent.iterdir()}


def test_existing_empty_run_cannot_be_reused(setup):
    s=setup;job=dict(kind='history',code=s['fixed']['items'][0]['code'],end='2026-10-21')
    s['store'].ingest(collector.job_request(job),ReadResponse(0,b''),run_id='fixture-run-new-001',
                      observed_at=s['clock'].wall(),ingested_at=s['clock'].wall(),origin='synthetic')
    with pytest.raises(ValueError):run(s)
    assert not s['calls']


@pytest.mark.parametrize('budget',['group','global','expiry'])
def test_pacing_consumes_budget_and_never_dispatches_second_job(setup,budget):
    s=setup
    if budget=='group':s['config']['plans'][0]['run_seconds']=4
    elif budget=='global':s['config']['total_seconds']=4
    else:s['release']['expires_at']='2026-10-21T23:00:04Z'
    s['config']['minimum_start_interval']=5;reseal(s)
    summary,status=run(s)
    assert status==1 and len(s['calls'])==1 and summary['attempted_jobs']==1
    assert s['clock'].tick()<=4


def test_offline_resume_exact_fixture_reviews_never_collects_or_reads_locator(setup,monkeypatch):
    s=setup
    # Ensure distinct immutable generations without sleeping real time.
    original_write=pipeline.refresh.exporter.write_export
    generations=iter([datetime(2026,10,21,23,tzinfo=timezone.utc),datetime(2026,10,21,23,0,10,tzinfo=timezone.utc)])
    monkeypatch.setattr(pipeline.refresh.exporter,'write_export',lambda parent,result:original_write(parent,result,generated_at=next(generations)))
    summary,_=run(s)
    review=json.loads(Path(summary['review_path']).read_text())
    resumed=json.loads(Path(summary['resume_config']).read_text())
    for entry in review['items'][:2]:
        e=entry['evidence'];_,a=fixtures.cases.make_case()
        a.update(schema_version=3,purpose=pipeline.refresh.core.PRIVATE_PURPOSE,reviewed_at=s['clock'].wall())
        fixtures.cases.reseal(e,a)
        put(Path(resumed['review_directory'])/(pipeline.refresh.core._hash(e)+'.json'),a)
    def forbidden(*a,**k):pytest.fail('offline must not collect or preflight credentials')
    monkeypatch.setattr(pipeline,'preflight',forbidden);monkeypatch.setattr(collector,'collect',forbidden)
    original_run=pipeline.refresh.run
    monkeypatch.setattr(pipeline.refresh,'run',lambda path:original_run(path,issued_at=s['clock'].wall()))
    result=pipeline.run_offline(summary['resume_config'])
    assert result['counts']['generated']==2 and result['counts']['is_demo']==2
    assert result['counts']['eligible_generated']==0 and result['status']=='insufficient_coverage'
    assert result['provider_refreshed'] is False and len(s['calls'])==2


def test_cli_other_cwd_modes_and_sanitized_failures(setup,tmp_path):
    s=setup;script=ROOT/'scripts/daily-market-brief/run_current_forecast.py'
    for args in ([],['--online','--config',s['config_path']],['--offline','--online','--config',s['config_path']],
                 ['--offline','--config','/PRIVATE_CANARY'],['--offline','--config',s['config']['fixed50_config'],'--release',s['release_path']]):
        result=subprocess.run([sys.executable,str(script),*args],cwd=tmp_path,capture_output=True,text=True,timeout=15)
        assert result.returncode==1 and result.stderr==''
        assert json.loads(result.stdout)==dict(status='failed',reason='private-pipeline-unavailable')
        assert 'PRIVATE_CANARY' not in result.stdout
    result=subprocess.run([sys.executable,str(script),'--offline','--config',s['config']['fixed50_config']],
        cwd=tmp_path,capture_output=True,text=True,timeout=15)
    assert result.returncode==2 and result.stderr=='' and json.loads(result.stdout)['counts']['total']==50


def test_normalization_contract_mismatch_rejected_before_capture(setup):
    s=setup;s['fixed']['items'][0]['normalization_version']=6;reseal(s)
    with pytest.raises(ValueError):run(s)
    assert not s['calls']


@pytest.mark.parametrize('guard',['claim','lock'])
def test_exclusive_preexisting_claim_or_lock_is_preserved_without_calls(setup,guard):
    s=setup
    path=(Path(s['config']['receipt_parent'])/'.claim-fixture-claim.json' if guard=='claim'
          else s['store'].root/'.collector.lock')
    path.write_text('existing sentinel');path.chmod(0o600)
    with pytest.raises(FileExistsError):run(s)
    assert path.read_text()=='existing sentinel' and not s['calls']
    if guard=='claim':assert not (s['store'].root/'.collector.lock').exists()


def test_second_plan_uses_remaining_global_budget_and_preserves_job_binding(setup):
    s=setup
    first=json.loads(Path(s['config']['plans'][0]['path']).read_text())
    second=deepcopy(first);first['history']=first['history'][:1];second['history']=second['history'][1:]
    put(Path(s['config']['plans'][0]['path']),first)
    s['config']['plans'][0]['sha256']=pipeline.refresh.core._hash(first)
    path=put(s['private']/'second-plan.json',second)
    s['config']['plans'].append(dict(path=path,sha256=pipeline.refresh.core._hash(second),run_seconds=30,
                                     fixed50_sha256=pipeline.refresh.core._hash(s['fixed'])))
    s['config']['total_seconds']=4;s['config']['minimum_start_interval']=5;reseal(s)
    summary,status=run(s)
    assert status==1 and len(s['calls'])==1
    receipt=json.loads(Path(summary['receipt_path']).read_text())
    assert receipt['unattempted'][0]['run_id']=='fixture-run-new-002'
    assert receipt['outcomes'][0]['plan_sha256']==pipeline.refresh.core._hash(first)


def test_clock_rollback_after_first_capture_stops_further_dispatch(setup):
    s=setup;normal=worker(s)
    def backwards(*args,**kw):
        reply=normal(*args,**kw)
        s['clock'].value=-1
        return reply
    summary,status=run(s,supervisor=backwards)
    assert status==1 and len(s['calls'])==1
    assert summary['attempted_jobs']==1 and summary['status']=='collection_failed'


def test_exception_after_actual_dispatch_not_reported_as_unattempted(setup):
    s=setup
    def raised(job,*args,**kw):
        s['calls'].append(job);raise OSError('PRIVATE_CANARY')
    summary,status=run(s,supervisor=raised)
    assert status==1 and summary['attempted_jobs']==1
    receipt=json.loads(Path(summary['receipt_path']).read_text())
    assert len(receipt['dispatches'])==1 and len(receipt['unattempted'])==1
    assert 'PRIVATE_CANARY' not in Path(summary['receipt_path']).read_text()


def test_stale_calendar_after_capture_does_not_roll_approved_endpoint(setup):
    s=setup;s['clock'].value=21*3600-0.5
    s['release']['expires_at']='2026-10-23T00:00:00Z';reseal(s)
    summary,status=run(s)
    assert status==1 and len(s['calls'])==1
    assert s['calls'][0]['job']['end']=='2026-10-21'
    assert not list(Path(s['fixed']['output_parent']).iterdir())
