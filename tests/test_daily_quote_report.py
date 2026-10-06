"""Synthetic injected collection only; real worker/credentials never invoked."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from datetime import date, timedelta

import pytest
from connectors.moomoo_rest import ReadRequest,ReadResponse
from ingest.market_collector import JobOutcome,job_digest
from ingest.private_market_store import MarketStoreError,canonical
from tests.test_daily_report_projection import inputs,CUTOFF,OBS,STAMP

runner=import_module('scripts.daily-market-brief.run_private_quote_report')
WINDOW='2026-10-01T23:58:00Z'
NOW='2026-10-01T23:59:00Z'


@pytest.fixture
def invocation(inputs,tmp_path):
    store,template,universe,codes=inputs
    base=tmp_path/'input';base.mkdir();reports=base/'daily-market-brief';reports.mkdir()
    calendar=base/'financial-calendar';calendar.mkdir()
    (calendar/'2026-10.json').write_text(canonical({'schema_version':1,'month':'2026-10','timezone':'Asia/Kuala_Lumpur','notes':[],'entries':[]}))
    template_path=reports/'2026-10-02.json';template_path.write_text(canonical(template))
    universe_path=base/'universe.json';universe_path.write_text(canonical(universe))
    output_root=tmp_path/'private-drafts';output_root.mkdir(mode=0o700)
    kwargs=dict(root=str(store.root),template_path=str(template_path),universe_path=str(universe_path),
        locator={'directory':str((tmp_path/'missing-synthetic-credentials').resolve()),'app_key_name':'app-key-id'},
        run_id='daily-synthetic',cutoff=CUTOFF,window_start=WINDOW,output=str(output_root/'draft.json'))
    return inputs,kwargs


def synthetic_collector(kind='complete',seen=None):
    def collect(store,plan,locator,*,run_id,wall,**kwargs):
        if seen is not None:seen.append(deepcopy((plan,locator,run_id)))
        if kind=='exception':raise RuntimeError('/private/synthetic-secret')
        if kind in ('storage-failed','cleanup-failed','clock-order'):
            return [JobOutcome(job_digest({'kind':'snapshot','codes':plan['codes']}),'not-persisted',None,kind),
                    *[JobOutcome(job_digest({'kind':'history',**item}),'not-persisted',None,kind)
                      for item in plan.get('history',[])]]
        codes=plan['codes']
        rows=[{'code':code,'name':'Synthetic','update_time':STAMP,'data_date':'2026-10-01',
               'last_price':10+i,'volume':0} for i,code in enumerate(codes)]
        if kind=='partial':rows=rows[:1]
        if kind in ('empty','failed','transport'):rows=[]
        if kind=='conflict':rows=rows[:1]
        request=ReadRequest('POST','/api/v1.0/quote/snapshot','',canonical({'code_list':codes}).encode(),{},1)
        response=ReadResponse(0 if kind=='transport' else 503 if kind=='failed' else 200,canonical({'ret_code':0,'ret_msg':'ok','data':{'snapshot_list':rows}}).encode())
        stored=store.ingest(request,response,run_id=run_id,observed_at=OBS,
                           ingested_at='2026-10-02T00:00:00.000001Z' if kind=='late' else CUTOFF,origin='synthetic')
        if kind=='corrupt':
            path=store.raw_dir/(stored.raw_hash+'.json');path.chmod(0o600);path.write_bytes(b'corrupt');path.chmod(0o400)
        if kind=='conflict':
            rows[0]['last_price']=99
            store.ingest(request,ReadResponse(200,canonical({'ret_code':0,'ret_msg':'ok','data':{'snapshot_list':rows}}).encode()),
                         run_id=run_id,observed_at=OBS,ingested_at='2026-10-01T23:59:30Z',origin='synthetic')
        outcomes=[JobOutcome(job_digest({'kind':'snapshot','codes':codes}),stored.status,stored.attempt_id,
                           'transport' if kind=='transport' else 'upstream-failed' if kind=='failed' else None)]
        for item in plan.get('history',[]):
            code=item['code'];job={'kind':'history',**item}
            if kind=='complete':
                rows=[]
                for i in range(20):
                    bar_day=date.fromisoformat('2026-09-11')+timedelta(days=i)
                    rows.append({'time_key':STAMP-(20-i)*86400000,'date':int(bar_day.strftime('%Y%m%d')),
                                 'time_zone':-240,'close':float(10+i)})
                request=ReadRequest('GET',f'/api/v1.0/quote/{code}/history-kline',
                    f'end={item["end"]}&ktype=2&autype=0&num=100',b'',{},1)
                response=ReadResponse(200,canonical({'ret_code':0,'ret_msg':'ok','data':{'kline_list':rows}}).encode())
                history=store.ingest(request,response,run_id=run_id,observed_at=OBS,ingested_at=CUTOFF,origin='synthetic')
                outcomes.append(JobOutcome(job_digest(job),history.status,history.attempt_id,None))
            else:
                outcomes.append(JobOutcome(job_digest(job),'failed',None,'upstream-failed'))
        return outcomes
    return collect


def execute(invocation,kind='complete',**changes):
    inputs,args=invocation;args={**args,**changes}
    return runner.run_quote_report(**args,collector=synthetic_collector(kind),wall=lambda:NOW)


def test_complete_exact_plan_one_run_private_50_rows(invocation):
    inputs,args=invocation;seen=[];template_before=Path(args['template_path']).read_bytes()
    result=runner.run_quote_report(**args,collector=synthetic_collector(seen=seen),wall=lambda:NOW)
    expected_history=[{'code':code,'end':'2026-10-01'} for code in inputs[3]]
    assert seen==[({'schema_version':1,'codes':inputs[3],'history':expected_history,'news':[]},args['locator'],'daily-synthetic')]
    assert result['status']=='us-coverage-complete' and result['selected_us']==30 and result['unsupported_my']==20
    draft=json.loads(Path(args['output']).read_text())
    assert len(draft['forecasts'])==50 and sum(r['observed_quote'] is not None for r in draft['forecasts'])==30
    assert all(r['current_price_value'] is None and r['direction']=='unknown' for r in draft['forecasts'])
    trend=draft['forecasts'][0]['moomoo_trend']
    assert trend['status']=='available' and trend['signal']=='bullish' and trend['bar_count']==20
    assert len(trend['bar_dates'])==20 and trend['sma5']>trend['sma20']
    assert draft['metadata']['as_of']==CUTOFF and Path(args['template_path']).read_bytes()==template_before
    assert Path(args['output']).stat().st_mode&0o777==0o400
    serialized=canonical(draft)
    assert args['locator']['directory'] not in serialized and 'raw_body' not in serialized


@pytest.mark.parametrize('kind,selected',[('partial',1),('empty',0),('failed',0),('transport',0),('late',0),('conflict',0)])
def test_degraded_honest_draft_with_no_fallback(invocation,kind,selected):
    result=execute(invocation,kind)
    assert result['status']=='degraded' and result['selected_us']==selected and result['unselected_us']==30-selected
    draft=json.loads(Path(invocation[1]['output']).read_text())
    assert sum(r['observed_quote'] is not None for r in draft['forecasts'])==selected
    if kind=='late':assert result['available_attempt_status_counts']['success']==0
    if kind=='failed':assert result['available_attempt_status_counts']['failed']==1
    if kind=='empty':assert result['available_attempt_status_counts']['all-missing']==1
    if kind=='conflict':assert result['conflicted_us']==1


@pytest.mark.parametrize('kind',['storage-failed','cleanup-failed','clock-order','exception','corrupt'])
def test_fatal_failure_no_draft_no_retries(invocation,kind):
    seen=[]
    with pytest.raises(MarketStoreError) as caught:
        runner.run_quote_report(**invocation[1],collector=synthetic_collector(kind,seen),wall=lambda:NOW)
    assert len(seen)==1 and not Path(invocation[1]['output']).exists()
    assert caught.value.__context__ is None and '/private/synthetic-secret' not in str(caught.value)


@pytest.mark.parametrize('change',['after','at','before-window','window-order','template-mismatch','collision','unsafe-root','reuse','forecast'])
def test_preflight_rejection_before_worker(invocation,change):
    inputs,args=invocation;args=dict(args);now=NOW
    if change=='after':now='2026-10-02T00:00:01Z'
    elif change=='at':now=CUTOFF
    elif change=='before-window':now='2026-10-01T23:57:59Z'
    elif change=='window-order':args['window_start']=CUTOFF
    elif change=='template-mismatch':args['cutoff']='2026-10-02T00:00:01Z'
    elif change=='collision':Path(args['output']).write_bytes(b'sentinel')
    elif change=='unsafe-root':Path(args['output']).parent.chmod(0o755)
    elif change=='reuse':args['run_id']='synthetic'
    else:
        report=json.loads(Path(args['template_path']).read_text());report['forecasts'][0]['direction']='up'
        Path(args['template_path']).write_text(canonical(report))
    def forbidden(*a,**k):pytest.fail('collector called before preflight')
    with pytest.raises(MarketStoreError):runner.run_quote_report(**args,collector=forbidden,wall=lambda:now)
    if change=='collision':assert Path(args['output']).read_bytes()==b'sentinel'


def test_time_advances_to_cutoff_during_preflight_no_worker(invocation):
    times=iter([NOW,CUTOFF])
    with pytest.raises(MarketStoreError):runner.run_quote_report(**invocation[1],collector=lambda *a,**k:pytest.fail('worker'),wall=lambda:next(times))


def test_clock_rollback_preflight_no_worker(invocation):
    times=iter([NOW,'2026-10-01T23:58:59Z'])
    with pytest.raises(MarketStoreError):runner.run_quote_report(**invocation[1],collector=lambda *a,**k:pytest.fail('worker'),wall=lambda:next(times))


def cli_args(args):
    names={'template_path':'template','universe_path':'universe'}
    argv=[]
    for key in ('root','template_path','universe_path','run_id','cutoff','window_start','output'):
        argv.extend(['--'+names.get(key,key.replace('_','-')),args[key]])
    argv.extend(['--credential-directory',args['locator']['directory'],'--app-key-name',args['locator']['app_key_name']])
    return argv


@pytest.mark.parametrize('kind,code',[('complete',0),('partial',1),('empty',1),('failed',1),('transport',1),('late',1)])
def test_cli_summary_degraded_exit_no_values_paths(invocation,capsys,kind,code):
    assert runner.main(cli_args(invocation[1]),collector=synthetic_collector(kind),wall=lambda:NOW)==code
    captured=capsys.readouterr();assert not captured.err
    summary=json.loads(captured.out);assert summary['private_draft_written'] is True
    assert 'price' not in summary and invocation[1]['root'] not in captured.out
    assert invocation[1]['locator']['directory'] not in captured.out


def test_cli_sanitized_fatal_error(invocation,capsys):
    assert runner.main(cli_args(invocation[1]),collector=synthetic_collector('exception'),wall=lambda:NOW)==1
    captured=capsys.readouterr();assert not captured.out and '/private/synthetic-secret' not in captured.err


@pytest.mark.parametrize('kind',['public','symlink'])
def test_public_or_symlink_output_rejected_before_worker(invocation,kind,tmp_path):
    args=dict(invocation[1])
    if kind=='public':
        root=tmp_path/'public';root.mkdir(mode=0o700);args['output']=str(root/'draft.json')
    else:Path(args['output']).symlink_to(tmp_path/'absent')
    with pytest.raises(MarketStoreError):runner.run_quote_report(**args,collector=lambda *a,**k:pytest.fail('worker'),wall=lambda:NOW)


def test_post_cutoff_existing_run_id_rejected_before_worker(invocation):
    inputs,args=invocation
    synthetic_collector('late')(inputs[0],{'schema_version':1,'codes':inputs[3],'news':[]},args['locator'],run_id=args['run_id'],wall=lambda:NOW)
    with pytest.raises(MarketStoreError):runner.run_quote_report(**args,collector=lambda *a,**k:pytest.fail('worker'),wall=lambda:NOW)


def test_cli_argument_error_sanitized(capsys):
    with pytest.raises(SystemExit) as caught:runner.main(['--unknown','/private/synthetic-secret'])
    assert caught.value.code==2 and '/private/synthetic-secret' not in capsys.readouterr().err


@pytest.mark.parametrize('kind',['empty-outcomes','wrong-job'])
def test_collector_contract_mismatch_rejected(invocation,kind):
    def wrong(*a,**k):
        return [] if kind=='empty-outcomes' else [JobOutcome('0'*64,'success','synthetic',None)]
    with pytest.raises(MarketStoreError):runner.run_quote_report(**invocation[1],collector=wrong,wall=lambda:NOW)
    assert not Path(invocation[1]['output']).exists()
