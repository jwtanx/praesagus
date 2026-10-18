"""Private offline workflow replays; authored admissions never prove real sources."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from ingest import forecast_scenario as f
from ingest.report_forecast import prepare_report_forecast, ReportForecastError, validator, STALE_GAPS

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('authored_scenario_cases', BASE/'tests/test_forecast_scenario.py')
cases = importlib.util.module_from_spec(spec); spec.loader.exec_module(cases)
spec = importlib.util.spec_from_file_location('preparation_cli', BASE/'scripts/daily-market-brief/prepare_forecast_report.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
ISSUE = '2026-10-22T08:00:00.123456+08:00'
CUTOFF = '2026-10-22T08:01:00.654321+08:00'


def packet(cash=False):
    e,a = cases.cash_case() if cash else cases.make_case()
    return e,a


def normal_inputs():
    keys = ['benchmarks','financials','technology','semiconductors','healthcare','consumer-staples',
            'consumer-discretionary','energy','industrials-transport-logistics','materials-plantation']
    groups=[];rows=[]
    for gi,key in enumerate(keys):
        group=dict(key=key,label=key,emoji='F',role='benchmark' if gi==0 else 'sector',
                   classification='Authored fixture',count=5,instruments=[])
        for n in range(5):
            ticker='SPY' if gi==n==0 else f'FIX{gi}X{n}'
            identity=dict(ticker=ticker,name='Authored fixture',country='us',market='US',currency='USD',
                          asset_type='etf' if gi==0 else 'equity',sector_category=key,sector=key,
                          sector_emoji='F',classification='Authored fixture')
            group['instruments'].append(identity)
            row=dict(identity,current_price='Unavailable',current_price_value=None,quote_status='missing',
                     price_as_of='Unavailable',data_gaps=['Quote missing'],sources=[dict(label='Authored source',url='https://example.invalid/news')])
            row.update(f._unavailable(['admission_missing'])['report_fields'])
            rows.append(row)
        groups.append(group)
    universe=dict(schema_version=1,taxonomy_id='authored-v1',effective_from='2026-10-01',count_per_group=5,
                  selection_method='Authored selection',collection_policy='Authored collection',sources=[],groups=groups)
    sections={key:dict(title=key,kicker=key,description=[],tables=[],items=[],notes=[])
              for key in validator.REQUIRED_SECTIONS-{'calendar'}}
    template=dict(schema_version=3,metadata=dict(date='2026-10-22',title='Authored brief',subtitle='Authored brief',
        as_of=CUTOFF,presentation_profile='compact-v1'),summary=[dict(label='Fixture',title='Fixture',summary='Research only')],
        sections=sections,watchlist_config=dict(count_per_group=5,taxonomy_id='authored-v1',groups=[
            {k:g[k] for k in ('key','label','emoji')} for g in groups]),forecasts=rows,
        calendar_ref='../financial-calendar/2026-10.json',footer='Authored research only',
        collection=dict(observed_us=0,observed_my=0,missing_us=50,missing_my=0,trend_available_count=0,
            verified_forecast_reference_count=0,session_direction_counts=dict(bullish=0,bearish=0,neutral=0,unavailable=50)))
    calendar=dict(schema_version=1,month='2026-10',timezone='Asia/Kuala_Lumpur',notes=[],entries=[])
    return template,universe,calendar


def prepare(template=None,evidence=None,admission=None,**kwargs):
    if template is None:template=normal_inputs()[0]
    return prepare_report_forecast(template,evidence=evidence,admission=admission,
        issued_at=kwargs.pop('issued_at',ISSUE),report_cutoff=kwargs.pop('report_cutoff',CUTOFF),
        template_reviewed=kwargs.pop('template_reviewed',True),**kwargs)


def put(path,value):
    path.write_text(json.dumps(value,allow_nan=False));path.chmod(0o600);return str(path)


@pytest.fixture
def private(tmp_path):
    path=tmp_path.resolve()/'private';path.mkdir(mode=0o700);return path


def arguments(private,*,cash=False,evidence=True,mutate=None):
    template,universe,calendar=normal_inputs();e,a=packet(cash)
    values=dict(template=template,universe=universe,calendar=calendar,evidence=e,admission=a)
    if mutate:mutate(values)
    argv=[]
    for key,value in values.items():
        if not evidence and key in ('evidence','admission'):continue
        argv += ['--'+key,put(private/(key+'.json'),value)]
    return argv+['--issued-at',ISSUE,'--cutoff',CUTOFF,'--template-reviewed','--output-directory',str(private/'bundle')]


@pytest.mark.parametrize('cash',[False,True])
def test_full_50_row_preparation_and_cli_validation(private,capsys,cash):
    template,universe,calendar=normal_inputs();e,a=packet(cash);before=deepcopy((template,e,a))
    result=prepare(template,e,a)
    assert (template,e,a)==before and result['status']=='generated'
    assert result['report']['forecasts'][1:]==template['forecasts'][1:]
    assert result['report']['forecasts'][0]['sources']==template['forecasts'][0]['sources']
    assert result['report']['forecasts'][0]['data_gaps']==['Quote missing']
    assert result['report']['metadata']==template['metadata'] and result['report']['summary']==template['summary']
    assert result['report']['collection']['verified_forecast_reference_count']==1
    assert result['audit']['private_audit']['issued_at']==ISSUE
    assert result['report']['forecasts'][0]['forecast_as_of']==ISSUE
    cli.validate_prepared(result['report'],universe,calendar,private)
    assert not list(private.iterdir())
    argv=arguments(private,cash=cash);original={p.name:p.read_bytes() for p in private.iterdir()}
    assert cli.main(argv)==0
    assert json.loads(capsys.readouterr().out)==dict(status='prepared',reasons=[],forecast_generated_count=1)
    assert all((private/name).read_bytes()==raw for name,raw in original.items())
    bundle=private/'bundle';assert bundle.stat().st_mode&0o777==0o700
    for path in bundle.iterdir():assert path.stat().st_mode&0o777==0o600
    report=json.loads((bundle/'prepared-report.json').read_text());audit=json.loads((bundle/'audit.json').read_text())
    assert report==result['report'] and audit==result['audit']
    assert 'evidence_sha256' not in json.dumps(report) and 'example.invalid/cash' not in capsys.readouterr().out


@pytest.mark.parametrize('missing',['both','evidence','admission'])
def test_missing_paired_inputs_prepare_explicit_withholding(private,capsys,missing):
    e,a=packet()
    result=prepare(evidence=e if missing=='admission' else None,admission=a if missing=='evidence' else None)
    assert result['status']=='withheld' and result['reasons']==['admission_missing']
    assert result['report']['collection']['verified_forecast_reference_count']==0
    row=result['report']['forecasts'][0]
    assert row['estimated_mid_case_value'] is None and row['forecast_time_basis'] is None
    assert row['sources']==normal_inputs()[0]['forecasts'][0]['sources']
    argv=arguments(private,evidence=False)
    if missing!='both':argv += ['--'+('evidence' if missing=='admission' else 'admission'),put(private/(missing+'.json'),e if missing=='admission' else a)]
    if missing=='both':
        assert cli.main(argv)==0
        assert json.loads(capsys.readouterr().out)==dict(status='withheld',reasons=['admission_missing'],forecast_generated_count=0)
    else:
        assert cli.main(argv)==1
        assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='arguments-invalid')
        assert not (private/'bundle').exists()


@pytest.mark.parametrize('bad',['fixture','duplicate','absent','currency','review','cutoff','date','profile','stale-gap'])
def test_helper_invalid_context_and_fixture_refusal(bad):
    template=normal_inputs()[0];e,a=packet();kwargs={}
    if bad=='fixture':e['classification']='authored_fixture';cases.reseal(e,a)
    if bad=='duplicate':template['forecasts'][1]=deepcopy(template['forecasts'][0])
    if bad=='absent':template['forecasts'][0]['ticker']='QQQ'
    if bad=='currency':template['forecasts'][0]['currency']='MYR'
    if bad=='review':kwargs['template_reviewed']=False
    if bad=='cutoff':template['metadata']['as_of']=ISSUE
    if bad=='date':template['metadata']['date']='2026-10-21'
    if bad=='profile':template['metadata']['presentation_profile']='legacy'
    if bad=='stale-gap':template['forecasts'][0]['data_gaps'].append('No supported numeric target/range method.')
    with pytest.raises(ReportForecastError,match='^report-forecast-invalid-input$'):prepare(template,e,a,**kwargs)


@pytest.mark.parametrize('gap',sorted(STALE_GAPS))
def test_known_stale_forecast_gaps_refused_only_when_generated(gap):
    template=normal_inputs()[0];template['forecasts'][0]['data_gaps'].append(gap)
    e,a=packet()
    with pytest.raises(ReportForecastError):prepare(template,e,a)
    withheld=prepare(template)
    assert gap in withheld['report']['forecasts'][0]['data_gaps'] and template['forecasts'][0]['data_gaps']==['Quote missing',gap]


@pytest.mark.parametrize('failure',['future','target-event','unknown-amount','coverage'])
def test_skill_evidence_failure_replays(private,capsys,failure):
    def mutate(v):
        e,a=v['evidence'],v['admission']
        if failure=='future':e['bars'][-1]['known_at']='2026-10-23T00:00:00Z'
        if failure=='target-event':e['corporate_actions']['events'][0]['effective_date']='2026-10-22'
        if failure=='unknown-amount':e['corporate_actions']['events'][0]['amount']=None
        if failure=='coverage':e['corporate_actions']['complete']=False
        cases.reseal(e,a)
    argv=arguments(private,cash=True,mutate=mutate)
    assert cli.main(argv)==0
    summary=json.loads(capsys.readouterr().out);assert summary['status']=='withheld' and summary['forecast_generated_count']==0
    assert json.loads((private/'bundle/prepared-report.json').read_text())['forecasts'][0]['estimated_mid_case_value'] is None


@pytest.mark.parametrize('failure',['private-key','calendar','universe','future-universe','coverage','narrative','foreign-target'])
def test_authoritative_validator_failure_writes_nothing(private,capsys,failure):
    def mutate(v):
        if failure=='private-key':v['template']['forecasts'][1]['account_id']='PRIVATE-CANARY'
        if failure=='calendar':v['calendar']['month']='2026-11'
        if failure=='universe':v['universe']['groups'][0]['instruments'][0]['ticker']='QQQ'
        if failure=='future-universe':v['universe']['effective_from']='2026-10-23'
        if failure=='coverage':v['template']['collection']['missing_us']=49
        if failure=='narrative':v['template']['sections']['news']['notes']=[dict(text='<b>bad</b>',sources=[])]
        if failure=='foreign-target':v['template']['forecasts'][1]['estimated_mid_case_value']=1
    argv=arguments(private,mutate=mutate)
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='report-validation-failed')
    assert not (private/'bundle').exists() and not list(private.glob('.forecast-validation-*'))


@pytest.mark.parametrize('bad',['duplicate','nan','infinite-exponent','oversized','symlink','parent-symlink','mode','unowned','deep'])
def test_private_inputs_fail_closed_no_disclosure(private,capsys,monkeypatch,bad):
    argv=arguments(private);path=private/'evidence.json'
    if bad=='duplicate':path.write_text('{"PRIVATE-CANARY":1,"PRIVATE-CANARY":2}')
    if bad=='nan':path.write_text('{"PRIVATE-CANARY":NaN}')
    if bad=='infinite-exponent':path.write_text('{"PRIVATE-CANARY":1e999}')
    if bad=='oversized':path.write_bytes(b'x'*(cli.MAX_JSON+1))
    if bad=='symlink':path.unlink();path.symlink_to(private/'template.json')
    if bad=='parent-symlink':
        alias=private/'alias';alias.symlink_to(private,target_is_directory=True)
        argv[argv.index('--evidence')+1]=str(alias/'evidence.json')
    if bad=='mode':path.chmod(0o644)
    if bad=='unowned':monkeypatch.setattr(cli.os,'getuid',lambda:os.stat(path).st_uid+1)
    if bad=='deep':path.write_text(json.dumps([[[[[[[[[[1]]]]]]]]]]))
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='private-input-invalid')
    assert not (private/'bundle').exists()


@pytest.mark.parametrize('bad',['exists','symlink','public','parent-mode','failed-second-write'])
def test_private_destination_no_overwrite_and_failure_rollback(private,capsys,monkeypatch,bad):
    argv=arguments(private);bundle=private/'bundle'
    if bad=='exists':bundle.mkdir();(bundle/'keep').write_text('PRIVATE-CANARY')
    if bad=='symlink':bundle.symlink_to(private,target_is_directory=True)
    if bad=='public':argv[-1]=str(private/'public'/'bundle')
    if bad=='parent-mode':private.chmod(0o755)
    if bad=='failed-second-write':
        original=cli._write_file
        def failed(fd,name,value):
            if name=='prepared-report.json':raise OSError('PRIVATE-CANARY')
            return original(fd,name,value)
        monkeypatch.setattr(cli,'_write_file',failed)
    assert cli.main(argv)==1
    output=capsys.readouterr().out;assert 'CANARY' not in output and str(private) not in output
    if bad=='exists':assert (bundle/'keep').read_text()=='PRIVATE-CANARY'
    if bad=='failed-second-write':assert not bundle.exists()


def test_cli_arguments_do_not_echo_values(private):
    result=subprocess.run([sys.executable,str(BASE/'scripts/daily-market-brief/prepare_forecast_report.py'),'--PRIVATE-CANARY'],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==1 and result.stderr=='' and 'CANARY' not in result.stdout


def test_prepared_prediction_reaches_existing_js_guard(private):
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable for existing viewer guard')
    e,a=packet(cash=True);row=prepare(evidence=e,admission=a)['report']['forecasts'][0]
    js="""const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[1],'utf8');
const a=html.indexOf('function predictionState('),b=html.indexOf('function targetTiming(',a);
if(a<0||b<0)throw Error('missing guard');
const context={};vm.createContext(context);vm.runInContext(html.slice(a,b),context);
process.stdout.write(JSON.stringify(context.predictionState(JSON.parse(process.argv[2]))));"""
    output=subprocess.run([node,'-e',js,str(BASE/'artifacts/daily-market-brief/index.html'),json.dumps(row)],
                          capture_output=True,text=True,timeout=5,check=True)
    assert json.loads(output.stdout)==dict(direction=row['direction'],target=row['estimated_mid_case'],
                                           range=row['estimated_range'],reason=None)


def next_packet():
    e,a=packet();previous=e['bars'][-1];e['bars']=e['bars'][1:]+[deepcopy(previous)]
    e['bars'][-1].update(session_date='2026-10-22',close_at='2026-10-22T20:00:00Z',close=104,
        settled_at='2026-10-22T20:05:00Z',retrieved_at='2026-10-22T20:10:00.123456Z',
        ingested_at='2026-10-22T20:15:00.123456Z',known_at='2026-10-22T20:20:00.123456Z')
    e['calendar']['sessions'].append(dict(session_date='2026-10-23',regular_close_at='2026-10-23T20:00:00Z'))
    e['calendar']['coverage_end']='2026-10-23';e['calendar']['known_at']='2026-10-22T20:25:00.123456Z'
    e['corporate_actions'].update(coverage_end='2026-10-23',known_at='2026-10-22T20:30:00.123456Z')
    a['reviewed_at']='2026-10-22T20:40:00.123456Z'
    return cases.reseal(e,a)


def test_next_day_replay_requires_fresh_completed_reference(private):
    e,a=packet();today=prepare(evidence=e,admission=a)
    template,universe,calendar=normal_inputs()
    cutoff='2026-10-23T08:01:00.654321+08:00';issue='2026-10-23T08:00:00.123456+08:00'
    template['metadata'].update(date='2026-10-23',as_of=cutoff)
    stale=prepare(template,e,a,issued_at=issue,report_cutoff=cutoff)
    assert stale['status']=='withheld' and 'calendar_window' in stale['reasons']
    e,a=next_packet();tomorrow=prepare(template,e,a,issued_at=issue,report_cutoff=cutoff)
    assert tomorrow['status']=='generated'
    assert tomorrow['report']['forecasts'][0]['forecast_basis']['reference_close_date']=='2026-10-22'
    assert tomorrow['report']['forecasts'][0]['target_date']=='2026-10-23'
    assert today['report']['forecasts'][0]['target_date']=='2026-10-22'
    cli.validate_prepared(tomorrow['report'],universe,calendar,private)


def test_real_cli_subprocess_complete_private_bundle(private):
    argv=arguments(private,cash=True)
    result=subprocess.run([sys.executable,str(BASE/'scripts/daily-market-brief/prepare_forecast_report.py'),*argv],
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and result.stderr==''
    assert json.loads(result.stdout)==dict(status='prepared',reasons=[],forecast_generated_count=1)
    assert str(private) not in result.stdout and (private/'bundle/prepared-report.json').is_file()


def test_valid_quote_and_other_row_reference_preserved(private):
    template,universe,calendar=normal_inputs();e,a=packet()
    for index in (0,1):
        template['forecasts'][index].update(current_price='USD 100',current_price_value=100,quote_status='observed',
                                            price_as_of='2026-10-22T00:00:00Z')
    template['collection'].update(observed_us=2,missing_us=48)
    reference=deepcopy(cases.build((e,a))['report_fields']['forecast_basis'])
    template['forecasts'][1]['forecast_basis']=reference
    prepared=prepare(template,e,a)
    assert prepared['report']['forecasts'][1]==template['forecasts'][1]
    assert prepared['report']['forecasts'][0]['current_price_value']==100
    assert prepared['report']['collection']['verified_forecast_reference_count']==2
    cli.validate_prepared(prepared['report'],universe,calendar,private)


def test_readonly_inputs_and_missing_template_review(private,capsys):
    argv=arguments(private)
    for path in private.iterdir():path.chmod(0o400)
    no_review=[arg for arg in argv if arg!='--template-reviewed']
    assert cli.main(no_review)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='preparation-invalid')
    assert not (private/'bundle').exists()
    assert cli.main(argv)==0
    assert json.loads(capsys.readouterr().out)['status']=='prepared'


def test_failed_bundle_open_rolls_back_reserved_directory(private,monkeypatch):
    result=prepare();original=cli.os.open
    def fail(path,*args,**kwargs):
        if path=='bundle':raise OSError('PRIVATE-CANARY')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(cli.os,'open',fail)
    with pytest.raises(OSError):cli.write_bundle(private/'bundle',result)
    assert not (private/'bundle').exists()


def test_other_checkout_destination_refused(private,capsys):
    argv=arguments(private);checkout=private/'other-checkout';checkout.mkdir(mode=0o700)
    (checkout/'.git').write_text('Authored checkout marker')
    argv[-1]=str(checkout/'bundle')
    assert cli.main(argv)==1 and not (checkout/'bundle').exists()
    assert 'other-checkout' not in capsys.readouterr().out


@pytest.mark.parametrize('option',['--evidence','--admission'])
def test_cli_mismatched_pair_rejected_before_any_read(private,capsys,monkeypatch,option):
    argv=arguments(private,evidence=False)+[option,'/PRIVATE-CANARY/no-read.json']
    def forbidden(*args):raise AssertionError('must not read any input')
    monkeypatch.setattr(cli,'read_private_json',forbidden)
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='arguments-invalid')
    assert not (private/'bundle').exists()


# PRSG-107: replay the committed full report that failed actual Trader CLI intake.
def committed_report_inputs():
    sources=dict(template=BASE/'artifacts/daily-market-brief/2026-10-14.json',
                 universe=BASE/'artifacts/daily-market-brief/watchlist-universe-five.json',
                 calendar=BASE/'artifacts/financial-calendar/2026-10.json')
    return {key:json.loads(path.read_text()) for key,path in sources.items()}


def test_actual_committed_oct14_report_preserves_sources_and_120_row_audit(private,capsys):
    inputs=committed_report_inputs();report=inputs['template'];before=deepcopy(inputs)
    assert not f._bounded(report) and f._bounded(report,max_depth=12)
    assert len(report['forecasts'])==50 and len(report['sections']['score']['tables'][0]['rows'])==120
    issue=report['metadata']['as_of']
    prepared=prepare(report,issued_at=issue,report_cutoff=issue)
    assert prepared['status']=='withheld' and prepared['reasons']==['admission_missing']
    assert inputs==before
    assert prepared['report']['sections']==report['sections']
    assert prepared['report']['forecasts'][1:]==report['forecasts'][1:]
    assert prepared['report']['forecasts'][0]['sources']==report['forecasts'][0]['sources']
    assert all(gap in prepared['report']['forecasts'][0]['data_gaps'] for gap in report['forecasts'][0]['data_gaps'])
    cli.validate_prepared(prepared['report'],inputs['universe'],inputs['calendar'],private)
    argv=[]
    for key,value in inputs.items():argv += ['--'+key,put(private/(key+'.json'),value)]
    frozen={p.name:p.read_bytes() for p in private.iterdir()}
    argv+=['--issued-at',issue,'--cutoff',issue,'--template-reviewed','--output-directory',str(private/'bundle')]
    assert cli.main(argv)==0
    assert json.loads(capsys.readouterr().out)==dict(status='withheld',reasons=['admission_missing'],forecast_generated_count=0)
    actual=json.loads((private/'bundle/prepared-report.json').read_text())
    assert actual==prepared['report'] and actual['metadata']==report['metadata']
    assert actual['sections']==before['template']['sections']
    assert len(actual['sections']['score']['tables'][0]['rows'])==120
    assert all((private/name).read_bytes()==raw for name,raw in frozen.items())


def nested_source_template():
    template=normal_inputs()[0]
    template['sections']['outlook']['items']=[dict(title='Authored issuer source',paragraphs=[dict(
        text='Authored source interpretation',sources=[dict(label='Issuer source',url='https://example.invalid/issuer',
            provider='Authored fixture',published_at=None,retrieved_at=ISSUE,timezone='UTC',
            data_period='Authored period',connector='authored-only')])])]
    return template


def test_numeric_admitted_shaped_nested_source_provenance_preserved(private,capsys):
    template=nested_source_template();e,a=packet(cash=True)
    assert not f._bounded(template)
    prepared=prepare(template,e,a)
    assert prepared['status']=='generated' and prepared['report']['sections']==template['sections']
    argv=arguments(private,cash=True)
    put(private/'template.json',template)
    assert cli.main(argv)==0 and json.loads(capsys.readouterr().out)['forecast_generated_count']==1
    actual=json.loads((private/'bundle/prepared-report.json').read_text())
    assert actual['sections']['outlook']==template['sections']['outlook']
    assert actual['forecasts'][1:]==template['forecasts'][1:]


def at_depth(depth):
    value=0
    for _ in range(depth):value=[value]
    return value


@pytest.mark.parametrize('depth',[12,13])
def test_template_only_depth_limit_helper_and_cli(private,capsys,depth):
    template=nested_source_template();template['depth_extension']=at_depth(depth-1)
    if depth==12:
        assert prepare(template)['status']=='withheld'
    else:
        with pytest.raises(ReportForecastError):prepare(template)
    argv=arguments(private,evidence=False);put(private/'template.json',template)
    assert cli.main(argv)==(0 if depth==12 else 1)
    summary=json.loads(capsys.readouterr().out)
    assert summary['status']==('withheld' if depth==12 else 'failed')
    if depth==13:assert summary['reason']=='private-input-invalid' and not (private/'bundle').exists()


@pytest.mark.parametrize('input_name',['evidence','admission','universe','calendar'])
def test_non_template_cli_inputs_keep_depth8(private,capsys,input_name):
    argv=arguments(private)
    path=private/(input_name+'.json');data=json.loads(path.read_text())
    data['depth_extension']=at_depth(8);put(path,data)
    assert f._bounded(data,max_depth=12) and not f._bounded(data)
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='private-input-invalid')
    assert not (private/'bundle').exists()


@pytest.mark.parametrize('bad',['nonfinite','oversize','duplicate','private-field','long-string','nodes'])
def test_deeper_template_retains_existing_value_size_and_privacy_guards(private,capsys,bad):
    template=nested_source_template();argv=arguments(private,evidence=False);put(private/'template.json',template)
    path=private/'template.json'
    if bad=='nonfinite':path.write_text('{"x":1e999}')
    if bad=='oversize':path.write_bytes(b' '*(cli.MAX_JSON+1))
    if bad=='duplicate':path.write_text('{"x":1,"x":2}')
    if bad=='private-field':
        template['sections']['outlook']['items'][0]['paragraphs'][0]['sources'][0]['account_id']='PRIVATE-CANARY';put(path,template)
    if bad=='long-string':
        template['sections']['outlook']['items'][0]['paragraphs'][0]['sources'][0]['label']='x'*2049;put(path,template)
    if bad=='nodes':
        template['large_extension']=[0]*100000;put(path,template)
    assert cli.main(argv)==1
    summary=json.loads(capsys.readouterr().out)
    assert summary==dict(status='failed',reason='report-validation-failed' if bad=='private-field' else 'private-input-invalid')
    assert not (private/'bundle').exists()


# PRSG-124 generic per-ticker batch; all inputs remain fictional reviewed-real-shaped.
from ingest.report_forecast import prepare_report_forecasts, BATCH_INPUT_GAPS


def generic_packet(ticker='FIX0X1',market='US',cash=False):
    e,a,_,_=cases.generic_case(market=market,cash=cash)
    e['instrument']['ticker']=ticker
    identity='authored-'+market+'-'+ticker
    e['instrument']['instrument_id']=identity;e['corporate_actions']['instrument_id']=identity
    for bar in e['bars']:bar['instrument_id']=identity
    return cases.reseal(e,a)


def batch_item(ticker='FIX0X1',market='US',cash=False):
    e,a=generic_packet(ticker,market,cash)
    return dict(ticker=ticker,market=market,currency='USD' if market=='US' else 'MYR',evidence=e,admission=a)


def batch_prepare(template=None,items=None,**kwargs):
    return prepare_report_forecasts(normal_inputs()[0] if template is None else template,
        batch=dict(schema_version=1,items=[] if items is None else items),issued_at=ISSUE,report_cutoff=CUTOFF,
        template_reviewed=True,**kwargs)


def mixed_inputs():
    template,universe,calendar=normal_inputs()
    for target in (template['forecasts'][2],universe['groups'][0]['instruments'][2]):
        target.update(ticker='1155',market='MY',currency='MYR',country='my')
    template['collection'].update(missing_us=49,missing_my=1)
    return template,universe,calendar


def batch_arguments(private,items=None,template_inputs=None):
    template,universe,calendar=normal_inputs() if template_inputs is None else template_inputs
    argv=[]
    for name,value in dict(template=template,universe=universe,calendar=calendar,
                           batch=dict(schema_version=1,items=[] if items is None else items)).items():
        argv+=['--'+name,put(private/(name+'.json'),value)]
    return argv+['--issued-at',ISSUE,'--cutoff',CUTOFF,'--template-reviewed','--output-directory',str(private/'bundle')]


def test_batch_distinct_us_my_raw_cash_reference_calendars_public_validation(private,capsys):
    inputs=mixed_inputs();template,universe,calendar=inputs
    items=[batch_item(),batch_item('1155','MY',cash=True)]
    before=deepcopy((template,items));result=batch_prepare(template,items)
    assert (template,items)==before and result['status']=='partial'
    assert result['counts']==dict(intended=50,provided=2,generated=2,withheld=48,missing_entries=48,
                                 missing_pairs=48,missing_evidence=48,missing_admission=48)
    us,my=result['report']['forecasts'][1:3]
    assert us['forecast_status']==my['forecast_status']=='available'
    assert us['forecast_time_basis']['schema_version']==my['forecast_time_basis']['schema_version']==2
    assert us['forecast_time_basis']['ticker']=='FIX0X1' and my['forecast_time_basis']['ticker']=='1155'
    assert us['forecast_time_basis']['venue_timezone']=='America/New_York'
    assert my['forecast_time_basis']['venue_timezone']=='Asia/Kuala_Lumpur'
    assert us['forecast_time_basis']['target_close_at']!=my['forecast_time_basis']['target_close_at']
    assert 'not executable' in us['scenario'] and 'not executable' in my['scenario']
    assert us['forecast_basis']['bull_case']==items[0]['evidence']['narrative']['bull_case']
    assert result['report']['collection']['verified_forecast_reference_count']==2
    cli.validate_prepared(result['report'],universe,calendar,private)
    argv=batch_arguments(private,items,inputs);assert cli.main(argv)==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['status']=='prepared' and summary['forecast_generated_count']==2 and summary['counts']==result['counts']
    assert json.loads((private/'bundle/audit.json').read_text())==result['audit']


def test_batch_all_fifty_have_separate_identity_audits_and_counts(private):
    template,universe,calendar=normal_inputs()
    items=[batch_item(row['ticker']) for row in template['forecasts']]
    result=batch_prepare(template,items)
    assert result['status']=='generated' and result['counts']['generated']==50
    assert result['counts']['withheld']==result['counts']['missing_entries']==0
    assert len(result['audit']['rows'])==50
    assert {a['ticker'] for a in result['audit']['rows']}=={r['ticker'] for r in template['forecasts']}
    assert all(a['private_audit']['instrument']['ticker']==a['ticker'] for a in result['audit']['rows'])
    cli.validate_prepared(result['report'],universe,calendar,private)


@pytest.mark.parametrize('missing',['entry','evidence','admission','both'])
def test_batch_missing_pair_has_row_reason_and_never_reuses_previous_numbers(missing):
    template=normal_inputs()[0];item=batch_item()
    old=f.build_forecast_scenario(item['evidence'],admission=item['admission'],issued_at=ISSUE,report_cutoff=CUTOFF)
    target=template['forecasts'][1];target.update(old['report_fields']);before=deepcopy(target)
    if missing in ('evidence','both'):item['evidence']=None
    if missing in ('admission','both'):item['admission']=None
    result=batch_prepare(template,[] if missing=='entry' else [item])
    row=result['report']['forecasts'][1];audit=result['audit']['rows'][1]
    assert row['forecast_status']=='unavailable' and row['direction']=='unknown'
    assert all(row[k] is None for k in ('estimated_mid_case_value','range_low_value','range_high_value',
        'forecast_basis','forecast_time_basis','forecast_as_of','target_date','forecast_observations'))
    assert row['sources']==before['sources'] and row['current_price']==before['current_price']
    assert template['forecasts'][1]==before
    expected=['batch_entry_missing'] if missing=='entry' else ['evidence_missing','admission_missing'] if missing=='both' else [missing+'_missing']
    assert audit['input_reasons']==expected and audit['core_reasons']==['admission_missing']
    assert all(BATCH_INPUT_GAPS[r] in row['data_gaps'] for r in expected)


@pytest.mark.parametrize('bad',['duplicate','unknown','cross-currency','cross-evidence','cross-admission','item-extra',
    'item-missing','wrapper-extra','wrapper-version-bool','too-many','duplicate-template','malformed-evidence'])
def test_batch_fatal_identity_shape_and_duplicate_errors_precede_calculation(private,capsys,monkeypatch,bad):
    template=normal_inputs()[0];item=batch_item();batch=dict(schema_version=1,items=[item])
    if bad=='duplicate':batch['items'].append(deepcopy(item))
    elif bad=='unknown':item['ticker']='UNKNOWN'
    elif bad=='cross-currency':item['currency']='MYR'
    elif bad=='cross-evidence':item['evidence']['instrument']['ticker']='SPY';cases.reseal(item['evidence'],item['admission'])
    elif bad=='cross-admission':item['admission']=batch_item('SPY')['admission']
    elif bad=='item-extra':item['PRIVATE-CANARY']='private'
    elif bad=='item-missing':item.pop('admission')
    elif bad=='wrapper-extra':batch['extra']=True
    elif bad=='wrapper-version-bool':batch['schema_version']=True
    elif bad=='too-many':batch['items']=[item]*51
    elif bad=='duplicate-template':template['forecasts'][2]=deepcopy(template['forecasts'][1])
    elif bad=='malformed-evidence':item['evidence']=[]
    module=sys.modules[prepare_report_forecasts.__module__]
    def forbidden(*args,**kwargs):raise AssertionError('fatal preflight must precede core calculation')
    monkeypatch.setattr(module,'build_forecast_scenario',forbidden)
    with pytest.raises(ReportForecastError,match='^report-forecast-invalid-input$'):
        prepare_report_forecasts(template,batch=batch,issued_at=ISSUE,report_cutoff=CUTOFF,template_reviewed=True)
    argv=batch_arguments(private);put(private/'template.json',template);put(private/'batch.json',batch)
    assert cli.main(argv)==1
    summary=json.loads(capsys.readouterr().out)
    assert summary==dict(status='failed',reason='preparation-invalid') and not (private/'bundle').exists()
    assert 'CANARY' not in json.dumps(summary)


@pytest.mark.parametrize('option',['--evidence','--admission'])
def test_batch_legacy_options_are_exclusive_before_any_input_read(private,capsys,monkeypatch,option):
    argv=batch_arguments(private)+[option,'/PRIVATE-CANARY/never-read']
    monkeypatch.setattr(cli,'read_private_json',lambda *a,**k:pytest.fail('no input read'))
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='arguments-invalid')


@pytest.mark.parametrize('bad',['oversized','depth13','nan','duplicate-json','symlink','mode'])
def test_batch_cli_bounds_privacy_and_no_write(private,capsys,bad):
    argv=batch_arguments(private);path=private/'batch.json'
    if bad=='oversized':path.write_bytes(b'x'*(cli.MAX_JSON+1))
    elif bad=='depth13':path.write_text(json.dumps(dict(schema_version=1,items=[],extra=at_depth(12))))
    elif bad=='nan':path.write_text('{"schema_version":1,"items":[],"x":NaN}')
    elif bad=='duplicate-json':path.write_text('{"schema_version":1,"items":[],"items":[]}')
    elif bad=='symlink':path.unlink();path.symlink_to(private/'template.json')
    else:path.chmod(0o644)
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='private-input-invalid')
    assert not (private/'bundle').exists()


def test_batch_helper_byte_budget_and_cli_depth12_only(private,monkeypatch):
    batch=dict(schema_version=1,items=[batch_item()]);module=sys.modules[prepare_report_forecasts.__module__]
    monkeypatch.setattr(module,'BATCH_MAX_BYTES',len(json.dumps(batch,separators=(',',':')).encode())-1)
    with pytest.raises(ReportForecastError):
        prepare_report_forecasts(normal_inputs()[0],batch=batch,issued_at=ISSUE,report_cutoff=CUTOFF,template_reviewed=True)
    path=private/'depth.json';put(path,dict(x=at_depth(11)))
    assert cli.read_private_json(str(path),max_depth=12)==dict(x=at_depth(11))
    with pytest.raises(ValueError):cli.read_private_json(str(path))


def test_batch_preserves_sources_quotes_gaps_sections_and_rolls_back_failed_write(private,capsys,monkeypatch):
    template,universe,calendar=normal_inputs();items=[batch_item()]
    template['forecasts'][1].update(current_price='USD 100',current_price_value=100,quote_status='observed',price_as_of=ISSUE)
    template['collection'].update(observed_us=1,missing_us=49)
    before=deepcopy(template);result=batch_prepare(template,items)
    assert template==before and result['report']['sections']==before['sections']
    for original,mapped in zip(before['forecasts'],result['report']['forecasts']):
        assert mapped['sources']==original['sources'] and mapped['current_price']==original['current_price']
        assert all(g in mapped['data_gaps'] for g in original['data_gaps'])
    argv=batch_arguments(private,items,(template,universe,calendar))
    original_write=cli._write_file
    def fail(fd,name,value):
        if name=='prepared-report.json':raise OSError('PRIVATE-CANARY')
        return original_write(fd,name,value)
    monkeypatch.setattr(cli,'_write_file',fail)
    assert cli.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='private-write-failed')
    assert not (private/'bundle').exists()


def test_batch_gate_failure_withholds_only_its_intended_instrument():
    first=batch_item();second=batch_item('FIX0X2')
    second['evidence']['rights']['public_derived_forecast']=False;cases.reseal(second['evidence'],second['admission'])
    result=batch_prepare(items=[first,second])
    assert result['counts']['generated']==1 and result['audit']['rows'][1]['status']=='generated'
    assert result['audit']['rows'][2]['status']=='withheld' and 'rights' in result['audit']['rows'][2]['reasons']
    assert result['report']['forecasts'][2]['estimated_mid_case_value'] is None


def test_empty_batch_cli_withholds_all_rows_and_clears_last_old_forecast(private,capsys):
    template,universe,calendar=normal_inputs();last=template['forecasts'][-1]
    item=batch_item(last['ticker'])
    last.update(f.build_forecast_scenario(item['evidence'],admission=item['admission'],issued_at=ISSUE,
                                         report_cutoff=CUTOFF)['report_fields'])
    argv=batch_arguments(private,[],(template,universe,calendar))
    assert cli.main(argv)==0
    summary=json.loads(capsys.readouterr().out)
    assert summary['status']=='withheld' and summary['forecast_generated_count']==0
    assert summary['counts']['missing_entries']==summary['counts']['missing_pairs']==50
    report=json.loads((private/'bundle/prepared-report.json').read_text())
    assert all(row['estimated_mid_case_value'] is None and row['forecast_time_basis'] is None for row in report['forecasts'])
    assert len(json.loads((private/'bundle/audit.json').read_text())['rows'])==50


def test_real_batch_cli_subprocess_uses_frozen_generic_identity(private):
    argv=batch_arguments(private,[batch_item()])
    result=subprocess.run([sys.executable,str(BASE/'scripts/daily-market-brief/prepare_forecast_report.py'),*argv],
        capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and result.stderr=='' and str(private) not in result.stdout
    summary=json.loads(result.stdout)
    assert summary['forecast_generated_count']==1 and summary['counts']['withheld']==49
    row=json.loads((private/'bundle/prepared-report.json').read_text())['forecasts'][1]
    assert row['forecast_time_basis']['ticker']==row['ticker']=='FIX0X1'


@pytest.mark.parametrize('market',['US','MY'])
def test_generic_batch_row_reaches_existing_viewer_guard(private,market):
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable for existing viewer guard')
    inputs=mixed_inputs();item=batch_item('1155','MY') if market=='MY' else batch_item()
    result=batch_prepare(inputs[0],[item]);row=result['report']['forecasts'][2 if market=='MY' else 1]
    js="""const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[1],'utf8');
const a=html.indexOf('function predictionState('),b=html.indexOf('function targetTiming(',a);
const context={};vm.createContext(context);vm.runInContext(html.slice(a,b),context);
process.stdout.write(JSON.stringify(context.predictionState(JSON.parse(process.argv[2]))));"""
    output=subprocess.run([node,'-e',js,str(BASE/'artifacts/daily-market-brief/index.html'),json.dumps(row)],
        capture_output=True,text=True,timeout=5,check=True)
    assert json.loads(output.stdout)==dict(direction=row['direction'],target=row['estimated_mid_case'],
        range=row['estimated_range'],reason=None)
