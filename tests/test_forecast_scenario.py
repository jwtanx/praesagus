"""Authored reviewed-real-shaped fixtures prove plumbing, never real admission."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from ingest import forecast_scenario as f

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scenario_report_validator',BASE/'scripts/daily-market-brief/validate_report_json.py')
sys.path.insert(0,str(BASE/'scripts/daily-market-brief'))
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
sys.path.pop(0)
ISSUE='2026-10-21T21:00:00Z'
CUTOFF='2026-10-21T22:00:00Z'


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def reseal(e,a):
    i,s,c,x,r,m=(e[k] for k in ('instrument','source','calendar','corporate_actions','rights','method'))
    subsets=dict(identity_units={'instrument':i,'source':s},calendar_window=c,bar_provenance=e['bars'],
                 close_convention=s,basis_actions={'source':s,'corporate_actions':x},rights=r,method=m)
    a.update(evidence_sha256=sha(e),method_sha256=sha(m),classification=e['classification'])
    for key,value in subsets.items():a['decisions'][key]['contract_sha256']=sha(value)
    return e,a


def make_case():
    # Dates, venue calendar, source/rights and reviews are all authored, not fetched.
    instrument=dict(instrument_id='fixture-SPY',ticker='SPY',market='US',mic='ARCX',currency='USD',unit='traded_price',
                    effective_from='2026-01-01',effective_to='2027-01-01',mapping_version='fixture-v1',source_url='https://example.invalid/listing')
    source=dict(provider='fixture-vendor',source_field='close',estimand='vendor_regular_close',basis='unadjusted',
                scale_id='raw-scale',vintage='frozen-v1',convention_id='fixed-revision-cutoff',
                convention='operational_revision_cutoff',source_url='https://example.invalid/contract')
    sessions=[];bars=[]
    for n in range(22):
        day=(date(2026,10,1)+timedelta(days=n)).isoformat();close=day+'T20:00:00Z'
        sessions.append(dict(session_date=day,regular_close_at=close))
        if n<21:
            bars.append(dict(instrument_id='fixture-SPY',session_date=day,close_at=close,close=100*math.exp(.001*n),
                currency='USD',unit='traded_price',basis='unadjusted',scale_id='raw-scale',vintage='frozen-v1',
                source_url='https://example.invalid/close',source_sha256='a'*64,source_publication_at=None,
                settled_at=day+'T20:05:00Z',retrieved_at=day+'T20:10:00Z',ingested_at=day+'T20:15:00Z',known_at=day+'T20:20:00Z'))
    calendar=dict(version='authored-calendar-v1',mic='ARCX',timezone='America/New_York',coverage_start='2026-10-01',
                  coverage_end='2026-10-22',complete=True,source_url='https://example.invalid/calendar',
                  known_at='2026-10-01T00:00:00Z',sessions=sessions)
    actions=dict(instrument_id='fixture-SPY',source_url='https://example.invalid/actions',source_sha256='b'*64,
                 known_at='2026-10-21T20:30:00Z',coverage_start='2026-10-01',coverage_end='2026-10-22',complete=True,events=[])
    rights=dict(history_collection='permitted',private_retention_research='permitted',public_derived_forecast='permitted',
                evidence_reference='authored-rights-only',source_sha256='c'*64,known_at='2026-10-01T00:00:00Z')
    e=dict(schema_version=1,classification='reviewed_real',instrument=instrument,source=source,calendar=calendar,
           bars=bars,corporate_actions=actions,rights=rights,method=deepcopy(f.METHOD))
    a=dict(schema_version=1,classification='reviewed_real',evidence_sha256='',method_sha256='',
           reviewed_at='2026-10-21T20:40:00Z',reviewers=['Lead','Trader'],decisions={key:dict(decision='accepted',
               evidence_reference='authored-review-only',contract_sha256='') for key in f.GATES})
    return reseal(e,a)


@pytest.fixture
def case():return make_case()


def build(case,issue=ISSUE,cutoff=CUTOFF):
    e,a=case;before=deepcopy(case)
    out=f.build_forecast_scenario(e,admission=a,issued_at=issue,report_cutoff=cutoff)
    assert case==before
    assert set(out)=={'status','reasons','report_fields','private_audit'}
    assert set(out['report_fields'])==f.FIELDS
    json.dumps(out,allow_nan=False)
    return out


def row():
    return dict(ticker='SPY',market='US',country='us',currency='USD',name='Fixture SPY',asset_type='etf',sector='Fixture',
                sector_category='fixture',sector_emoji='F',current_price='Unavailable',current_price_value=None,
                quote_status='missing',price_as_of='Unavailable',sources=[{'label':'Fixture source','url':'https://example.invalid/news'}],
                data_gaps=['Existing quote missing'],public_snapshot={'fixture':'preserve'},moomoo_trend={'fixture':'preserve'},
                universe_order=7)


def test_generated_formula_baselines_and_mapper_isolation(case):
    result=build(case)
    assert result['status']=='generated'
    a=result['private_audit'];p=result['report_fields']
    assert a['mu']==pytest.approx(.001,abs=1e-15)
    assert a['point']==pytest.approx(100*math.exp(.021))
    assert a['baseline_point']==pytest.approx(100*math.exp(.020))
    assert a['observations']==20 and a['horizon_sessions']==1
    assert a['low']<=a['point']<=a['high']
    assert p['forecast_basis']['reference_close']==a['reference_close']
    assert p['direction']=='up' and p['confidence']=='low'
    assert p['estimated_mid_case']==f"USD {p['estimated_mid_case_value']:.2f}"
    assert p['estimated_range']==f"USD {p['range_low_value']:.2f}–USD {p['range_high_value']:.2f}"
    original=row();before=deepcopy(original);saved=deepcopy(result)
    mapped=f.apply_scenario_to_row(original,result)
    assert original==before and result==saved
    for key,value in original.items():
        if key not in f.FIELDS:assert mapped[key]==value
    mapped['sources'].clear();mapped['public_snapshot']['fixture']='changed';mapped['forecast_basis']['bull_case']='changed'
    assert original==before and result==saved


@pytest.mark.parametrize('drift,direction',[(-.001,'down'),(0.,'flat'),(.001,'up')])
def test_sign_before_rounding(case,drift,direction):
    e,a=case
    for n,b in enumerate(e['bars']):b['close']=100*math.exp(drift*n)
    result=build(reseal(e,a))
    assert result['report_fields']['direction']==direction
    if drift==0:assert result['private_audit']['sample_sd']==0 and result['report_fields']['range_low_value']==100


def test_authored_fixture_calculates_but_mapper_refuses(case):
    e,a=case;e['classification']='authored_fixture'
    result=build(reseal(e,a));assert result['private_audit']['classification']=='fixture_only'
    with pytest.raises(f.ScenarioValidationError,match='^scenario-invalid-input$'):f.apply_scenario_to_row(row(),result)


def test_withheld_mapper_preserves_deduplicated_quote_gaps(case):
    e,a=case;e['rights']['public_derived_forecast']='unknown'
    result=build(reseal(e,a));assert result['status']=='withheld' and 'rights' in result['reasons']
    original=row();mapped=f.apply_scenario_to_row(original,result)
    twice=f.apply_scenario_to_row(mapped,result)
    assert twice['data_gaps']==mapped['data_gaps']
    assert 'Existing quote missing' in mapped['data_gaps']
    assert f.REASONS['rights'] in mapped['data_gaps']
    assert mapped['estimated_mid_case_value'] is mapped['range_low_value'] is mapped['range_high_value'] is None
    assert mapped['direction']=='unknown' and original==row()


@pytest.mark.parametrize('mutate,reason',[
 (lambda e:e['instrument'].update(currency='UNKNOWN'),'identity_units'),
 (lambda e:e['instrument'].update(ticker='QQQ'),'identity_units'),
 (lambda e:e['calendar'].update(complete=False),'calendar_window'),
 (lambda e:e['calendar'].update(mic='XNAS'),'calendar_window'),
 (lambda e:e['calendar']['sessions'].pop(10),'calendar_window'),
 (lambda e:e['bars'][0].update(session_date='2026-09-30'),'bar_provenance'),
 (lambda e:e['bars'][0].update(currency='MYR'),'bar_provenance'),
 (lambda e:e['bars'][0].update(close=True),'bar_provenance'),
 (lambda e:e['bars'][-1].update(known_at='2026-10-21T22:00:00Z'),'bar_provenance'),
 (lambda e:e['bars'][-1].update(settled_at='2026-10-21T22:00:00Z'),'close_convention'),
 (lambda e:e['source'].update(convention='unknown'),'close_convention'),
 (lambda e:e['corporate_actions'].update(complete=False),'basis_actions'),
 (lambda e:e['corporate_actions'].update(coverage_end='2026-10-21'),'basis_actions'),
 (lambda e:e['source'].update(basis='split_adjusted'),'basis_actions'),
 (lambda e:e['rights'].update(history_collection='denied'),'rights'),
 (lambda e:e['rights'].update(private_retention_research='unknown'),'rights'),
 (lambda e:e['rights'].update(public_derived_forecast='unknown'),'rights'),
 (lambda e:e['method'].update(ddof=0),'method'),
 (lambda e:e['method'].update(observations=True),'method'),
])
def test_seven_gates_withhold(case,mutate,reason):
    e,a=case;mutate(e)
    result=build(reseal(e,a))
    assert result['status']=='withheld' and reason in result['reasons']
    assert result['private_audit'] is None
    assert result['report_fields']['forecast_status']=='unavailable'


@pytest.mark.parametrize('kind',['split','distribution','other_basis_change'])
def test_action_in_lookback_or_through_target_blocks(case,kind):
    e,a=case;e['corporate_actions']['events']=[dict(effective_date='2026-10-22',kind=kind,
        source_url='https://example.invalid/action',source_sha256='d'*64)]
    assert 'basis_actions' in build(reseal(e,a))['reasons']


@pytest.mark.parametrize('mutate',[lambda e:e['bars'].pop(),lambda e:e['bars'].append(deepcopy(e['bars'][-1])),
 lambda e:e.update(extra=1),lambda e:e['source'].update(extra=1),lambda e:e['bars'][0].update(extra=1),
 lambda e:e['calendar']['sessions'][0].update(extra=1),lambda e:e['method'].update(extra=1)])
def test_closed_schema_missing_and_extra(case,mutate):
    e,a=case;mutate(e)
    assert build(reseal(e,a))['reasons']==['schema']


def test_missing_admission_and_tampered_binding(case):
    e,a=case
    assert f.build_forecast_scenario(e,admission=None,issued_at=ISSUE,report_cutoff=CUTOFF)['reasons']==['admission_missing']
    e['bars'][0]['close']+=1
    assert 'admission_binding' in build(case)['reasons']


@pytest.mark.parametrize('field,value',[('reviewed_at','2026-10-21T20:00:00Z'),('reviewed_at','2026-10-21T22:00:00Z'),
 ('reviewers',['Trader']),('classification','authored_fixture')])
def test_review_record_cannot_predate_inputs_or_self_approve(case,field,value):
    case[1][field]=value
    assert build(case)['status']=='withheld'


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0,-1,10**400])
def test_nonfinite_extreme_closes_fail_safely(case,value):
    case[0]['bars'][0]['close']=value
    out=build(case)
    assert out['status']=='withheld' and out['private_audit'] is None


def test_overflow_and_display_underflow_withhold(case):
    e,a=case
    for n,b in enumerate(e['bars']):b['close']=1e300 if n%2 else 1e-300
    assert 'arithmetic' in build(reseal(e,a))['reasons']
    for b in e['bars']:b['close']=1e-8
    assert build(reseal(e,a))['reasons']==['rounding_unrepresentable']


def test_strict_time_and_listing_stale_reference(case):
    e,a=case
    assert build(case,issue='2026-10-21')['reasons']==['admission_time']
    assert 'admission_time' in build(case,cutoff='2026-10-21T20:00:00Z')['reasons']
    # A new completed session must not be silently bridged by yesterday's21bars.
    e['calendar']['sessions'].append(dict(session_date='2026-10-23',regular_close_at='2026-10-23T20:00:00Z'))
    e['calendar']['coverage_end']='2026-10-23'
    out=build(reseal(e,a),issue='2026-10-22T21:00:00Z',cutoff='2026-10-22T22:00:00Z')
    assert 'bar_provenance' in out['reasons']


def test_venue_local_date_and_early_close_evidence(case):
    e,a=case
    e['calendar']['sessions'][5]['regular_close_at']='2026-10-06T17:00:00Z'
    e['bars'][5]['close_at']='2026-10-06T17:00:00Z'
    assert build(reseal(e,a))['status']=='generated'
    e['calendar']['sessions'][5]['regular_close_at']='2026-10-06T02:00:00Z'
    assert 'calendar_window' in build(reseal(e,a))['reasons']


@pytest.mark.parametrize('change',['row','result-extra','fields-extra','wrong-values','wrong-classification'])
def test_mapper_refuses_wrong_identity_or_tampered_result(case,change):
    result=build(case);target=row()
    if change=='row':target['ticker']='QQQ'
    elif change=='result-extra':result['extra']='unsafe'
    elif change=='fields-extra':result['report_fields']['current_price_value']=777
    elif change=='wrong-values':result['report_fields']['estimated_mid_case_value']=777
    else:result['private_audit']['classification']='fixture_only'
    with pytest.raises(f.ScenarioValidationError,match='^scenario-invalid-input$'):f.apply_scenario_to_row(target,result)


def compact_data(mapped,as_of):
    # In-memory report skeleton uses current validator, no saved report or publication.
    base=dict(mapped);base.pop('public_snapshot');base.pop('moomoo_trend');base.pop('universe_order')
    other=deepcopy(base);other.update(ticker='fixture2',name='Fixture2');other.update(f._unavailable(['admission_missing'])['report_fields'])
    rows=[]
    for n in range(5):
        value=deepcopy(other);value['ticker']=f'FIX{n}';rows.append(value)
    rows[0]=base
    sections={key:dict(title=key,kicker=key,description=[],tables=[],items=[],notes=[]) for key in validator.REQUIRED_SECTIONS-{'calendar'}}
    return dict(schema_version=3,metadata=dict(date=as_of[:10],title='Fixture',subtitle='Fixture',as_of=as_of),
        summary=[dict(label='Fixture',title='Fixture',summary='Fixture')],sections=sections,
        watchlist_config=dict(count_per_group=5,groups=[dict(key='fixture',label='Fixture',emoji='F')]),
        forecasts=rows,calendar_ref='../financial-calendar/2026-10.json',footer='Research only',
        collection=dict(observed_us=0,observed_my=0,missing_us=5,missing_my=0,trend_available_count=0,
            verified_forecast_reference_count=1,session_direction_counts=dict(bullish=0,bearish=0,neutral=0,unavailable=5)))


def test_generated_mapping_passes_compact_validator_with_same_day_future_close(case):
    result=build(case);mapped=f.apply_scenario_to_row(row(),result)
    data=compact_data(mapped,CUTOFF)
    # Invoke the exact compact forecast checks without any report/calendar file I/O.
    validator.validate_compact(Path('authored-fixture.json'),data,f._time(CUTOFF))
    same=build(case,issue='2026-10-22T08:00:00+08:00',cutoff='2026-10-22T08:01:00+08:00')
    assert same['status']=='generated'
    mapped=f.apply_scenario_to_row(row(),same)
    data=compact_data(mapped,'2026-10-22T08:01:00+08:00')
    validator.validate_compact(Path('authored-fixture.json'),data,f._time('2026-10-22T08:01:00+08:00'))


def test_complete_report_validation_with_generated_fields(case,tmp_path):
    result=build(case)
    data=compact_data(f.apply_scenario_to_row(row(),result),CUTOFF)
    data['metadata']['presentation_profile']='compact-v1'
    data['watchlist_config']['groups'][0]['key']='semiconductors'
    for value in data['forecasts']:value['sector_category']='semiconductors'
    folder=tmp_path/'daily-market-brief';folder.mkdir()
    calendar=tmp_path/'financial-calendar';calendar.mkdir()
    (calendar/'2026-10.json').write_text(json.dumps(dict(schema_version=1,month='2026-10',timezone='Asia/Kuala_Lumpur',notes=[],entries=[])))
    # Only an authored calendar fixture is written outside Git; no report is saved.
    assert validator.validate_report(folder/'2026-10-21.json',data,compact=True)[:2]==(5,0)


@pytest.mark.parametrize('change',['numeric-bool','audit-count-bool','audit-price','case-text'])
def test_mapper_refuses_semantic_tampering(case,change):
    result=build(case)
    if change=='numeric-bool':result['report_fields']['range_low_value']=True
    elif change=='audit-count-bool':result['private_audit']['horizon_sessions']=True
    elif change=='audit-price':result['private_audit']['point']+=1
    else:result['report_fields']['forecast_basis']['bull_case']='Invented news'
    with pytest.raises(f.ScenarioValidationError):f.apply_scenario_to_row(row(),result)


def test_multiple_withheld_gates_keep_compact_confidence_short(case):
    e,a=case
    e['instrument']['currency']='unknown';e['rights']['history_collection']='unknown'
    e['source']['convention']='unknown';e['corporate_actions']['complete']=False
    out=build(reseal(e,a))
    assert out['status']=='withheld'
    assert len(out['report_fields']['confidence_reason'].split())<=40
    mapped=f.apply_scenario_to_row(row(),out)
    assert all(f.REASONS[code] in mapped['data_gaps'] for code in out['reasons'])


def test_unknown_publication_and_action_or_currency_evidence_not_defaulted(case):
    assert all(b['source_publication_at'] is None for b in case[0]['bars'])
    assert build(case)['status']=='generated'
    e,a=case;e['source']['basis']=None;e['bars'][0]['currency']=None
    result=build(reseal(e,a))
    assert result['status']=='withheld'
    assert 'basis_actions' in result['reasons'] and 'bar_provenance' in result['reasons']


def test_future_source_publication_and_reversed_bar_order_fail(case):
    e,a=case;e['bars'][0]['source_publication_at']='2026-10-22T20:00:00Z'
    assert 'bar_provenance' in build(reseal(e,a))['reasons']
    e['bars'][0]['source_publication_at']=None;e['bars'].reverse()
    assert 'bar_provenance' in build(reseal(e,a))['reasons']


@pytest.mark.parametrize('cash',[False,True])
def test_timezone_dst_calendar_dates_are_checked_against_instants(case,cash):
    if cash:
        case=cash_case();case[0]['corporate_actions']['events']=[]
    e,a=case
    # This authored calendar crosses New York's November DST transition.
    for n,(session,bar) in enumerate(zip(e['calendar']['sessions'][:21],e['bars'])):
        day=(date(2026,10,14)+timedelta(days=n)).isoformat()
        hour='21' if day>='2026-11-01' else '20'
        session.update(session_date=day,regular_close_at=day+f'T{hour}:00:00Z')
        bar.update(session_date=day,close_at=day+f'T{hour}:00:00Z',settled_at=day+f'T{hour}:05:00Z',
            retrieved_at=day+f'T{hour}:10:00Z',ingested_at=day+f'T{hour}:15:00Z',known_at=day+f'T{hour}:20:00Z')
    e['calendar']['sessions'][-1]=dict(session_date='2026-11-04',regular_close_at='2026-11-04T21:00:00Z')
    e['calendar'].update(coverage_start='2026-10-14',coverage_end='2026-11-04')
    e['corporate_actions'].update(coverage_start='2026-10-14',coverage_end='2026-11-04',known_at='2026-11-03T21:30:00Z')
    a['reviewed_at']='2026-11-03T21:40:00Z'
    result=build(reseal(e,a),issue='2026-11-03T22:00:00Z',cutoff='2026-11-03T23:00:00Z')
    assert result['status']=='generated' and result['private_audit']['target_close_at']=='2026-11-04T21:00:00+00:00'


def test_bounded_resources_and_cycle_withhold():
    cyclic={};cyclic['self']=cyclic
    out=f.build_forecast_scenario(cyclic,admission={},issued_at=ISSUE,report_cutoff=CUTOFF)
    assert out['reasons']==['schema']
    e,a=make_case();e['source']['provider']='x'*2049
    assert build((e,a))['reasons']==['schema']


@pytest.mark.parametrize('cash',[False,True])
def test_generated_values_reach_actual_viewer_prediction_guard(case,cash):
    if cash:case=cash_case()
    node=shutil.which('node')
    if node is None:pytest.skip('Node runtime unavailable; run viewer guard replay in review environment')
    mapped=f.apply_scenario_to_row(row(),build(case))
    js="""const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[1],'utf8');
const a=html.indexOf('function predictionState('),b=html.indexOf('function targetTiming(',a);
if(a<0||b<0)throw Error('missing guard');
const context={};vm.createContext(context);vm.runInContext(html.slice(a,b),context);
const row=JSON.parse(process.argv[2]);const good=context.predictionState(row);
row.estimated_range=row.estimated_range.replace('–',' – ');const bad=context.predictionState(row);
process.stdout.write(JSON.stringify({good,bad}));"""
    result=subprocess.run([node,'-e',js,str(BASE/'artifacts/daily-market-brief/index.html'),json.dumps(mapped)],
                          capture_output=True,text=True,timeout=5,check=True)
    states=json.loads(result.stdout)
    assert states['good']==dict(direction=mapped['direction'],target=mapped['estimated_mid_case'],range=mapped['estimated_range'],reason=None)
    assert states['bad']['direction']=='unknown'


def test_generated_time_basis_is_derived_and_withheld_null(case):
    result=build(case);audit=result['private_audit'];basis=result['report_fields']['forecast_time_basis']
    assert basis==dict(schema_version=1,method_id=f.METHOD['method_id'],venue_timezone='America/New_York',
        calendar_version=case[0]['calendar']['version'],reference_close_at=audit['reference_close_at'],target_close_at=audit['target_close_at'])
    assert f.build_forecast_scenario(case[0],admission=None,issued_at=ISSUE,report_cutoff=CUTOFF)['report_fields']['forecast_time_basis'] is None


@pytest.mark.parametrize('mutate',[
 lambda r:r['report_fields']['forecast_time_basis'].update(target_close_at='2026-10-22T21:00:00Z'),
 lambda r:r['report_fields']['forecast_time_basis'].update(calendar_version='tampered-calendar'),
 lambda r:r['report_fields']['forecast_time_basis'].update(venue_timezone='UTC'),
 lambda r:r['private_audit'].update(calendar_version='tampered-calendar'),
 lambda r:r['report_fields']['forecast_time_basis'].update(schema_version=True),
 lambda r:r['report_fields']['forecast_time_basis'].update(extra='private'),
])
def test_mapper_crosschecks_public_time_against_private_audit(case,mutate):
    result=build(case);mutate(result)
    with pytest.raises(f.ScenarioValidationError):f.apply_scenario_to_row(row(),result)


def test_equivalent_close_offset_representation_links_to_audit(case):
    result=build(case)
    basis=result['report_fields']['forecast_time_basis']
    basis.update(reference_close_at='2026-10-21T16:00:00-04:00',target_close_at='2026-10-22T16:00:00-04:00')
    mapped=f.apply_scenario_to_row(row(),result)
    assert f.validate_forecast_time_basis(mapped,CUTOFF)


def test_same_date_future_close_complete_report(case,tmp_path):
    issue='2026-10-22T08:00:00+08:00';cutoff='2026-10-22T08:01:00+08:00'
    result=build(case,issue=issue,cutoff=cutoff)
    data=compact_data(f.apply_scenario_to_row(row(),result),cutoff)
    data['metadata']['presentation_profile']='compact-v1';data['watchlist_config']['groups'][0]['key']='semiconductors'
    for value in data['forecasts']:value['sector_category']='semiconductors'
    folder=tmp_path/'daily-market-brief';folder.mkdir();calendar=tmp_path/'financial-calendar';calendar.mkdir()
    (calendar/'2026-10.json').write_text(json.dumps(dict(schema_version=1,month='2026-10',timezone='Asia/Kuala_Lumpur',notes=[],entries=[])))
    assert validator.validate_report(folder/'2026-10-22.json',data,compact=True)[:2]==(5,0)


def cash_case():
    e,a=make_case();e['schema_version']=a['schema_version']=2;e['method']=deepcopy(f.CASH_METHOD)
    e['corporate_actions']['events']=[dict(event_id='authored-cash-1',effective_date='2026-10-11',kind='cash_distribution',
        amount=2.0,currency='USD',unit='gross_cash_per_share',source_url='https://example.invalid/cash',source_sha256='d'*64,
        source_publication_at=None,retrieved_at='2026-10-10T12:00:00Z',ingested_at='2026-10-10T12:01:00Z',known_at='2026-10-10T12:02:00Z')]
    return reseal(e,a)


def test_cash_formula_independent_proxy_and_raw_anchor():
    case=cash_case();e,a=case
    result=build(case);audit=result['private_audit'];prices=[b['close'] for b in e['bars']]
    expected=[math.log((prices[n]+(2 if n==10 else 0))/prices[n-1]) for n in range(1,21)]
    mean=sum(expected)/20;sd=math.sqrt(sum((v-mean)**2 for v in expected)/19)
    assert audit['mu']==pytest.approx(mean,abs=1e-15)
    assert audit['sample_sd']==pytest.approx(sd,abs=1e-15)
    assert audit['reference_close']==prices[-1]
    assert audit['point']==pytest.approx(prices[-1]*math.exp(mean))
    assert audit['low']==pytest.approx(prices[-1]*math.exp(mean-1.959964*sd))
    assert audit['high']==pytest.approx(prices[-1]*math.exp(mean+1.959964*sd))
    assert audit['method_id']==f.CASH_METHOD['method_id']
    assert result['report_fields']['forecast_model']==f.CASH_MODEL
    assert 'reinvestment proxy' in result['report_fields']['scenario']
    mapped=f.apply_scenario_to_row(row(),result)
    assert mapped['data_gaps']==row()['data_gaps'] and mapped['sources']==row()['sources']
    assert mapped['confidence']=='low'


@pytest.mark.parametrize('change',[
 {'amount':None},{'amount':0},{'amount':-1},{'amount':True},{'amount':float('inf')},
 {'currency':'MYR'},{'unit':'net_cash_per_share'},{'kind':'split'},{'kind':'distribution'},
 {'kind':'payment_date'},{'effective_date':'2026-10-22'},{'effective_date':'2026-10-23'},
 {'effective_date':'not-date'},{'event_id':''},{'source_url':'http://example.invalid'},
 {'source_sha256':'unknown'},{'known_at':'2026-10-22T12:00:00Z'},
 {'known_at':'2026-10-21T20:35:00Z'}, {'ingested_at':'2026-10-10T11:59:00Z'},
 {'source_publication_at':'2026-10-10T12:01:00Z'}, {'source_publication_at':'2026-10-10'},
 {'retrieved_at':None},{'known_at':'2026-10-10T12:02:00'}, {'extra':'unsupported'},
])
def test_cash_event_fail_closed(change):
    e,a=cash_case();e['corporate_actions']['events'][0].update(change)
    # Nonfinite evidence is malformed before JSON binding; no invented serialization.
    if change.get('amount')==float('inf'):
        assert build((e,a))['status']=='withheld';return
    reseal(e,a);result=build((e,a))
    assert result['status']=='withheld' and result['report_fields']['estimated_mid_case_value'] is None
    assert result['report_fields']['forecast_time_basis'] is None


@pytest.mark.parametrize('field',['amount','effective_date','source_sha256','known_at'])
def test_cash_event_tamper_invalidates_admission(field):
    e,a=cash_case();event=e['corporate_actions']['events'][0]
    event[field]={'amount':3,'effective_date':'2026-10-12','source_sha256':'e'*64,'known_at':'2026-10-10T12:03:00Z'}[field]
    assert 'admission_binding' in build((e,a))['reasons']


def test_cash_duplicates_aggregation_and_first_close():
    e,a=cash_case();event=e['corporate_actions']['events'][0]
    e['corporate_actions']['events'].append(deepcopy(event));reseal(e,a)
    assert 'basis_actions' in build((e,a))['reasons']
    e['corporate_actions']['events'][1]['event_id']='authored-cash-2';reseal(e,a)
    doubled=build((e,a))
    one,ad=cash_case();one['corporate_actions']['events'][0]['amount']=4;reseal(one,ad)
    assert doubled['private_audit']['mu']==build((one,ad))['private_audit']['mu']
    e,a=cash_case();e['corporate_actions']['events'][0]['effective_date']='2026-10-01';reseal(e,a)
    assert build((e,a))['private_audit']['mu']==build(make_case())['private_audit']['mu']


@pytest.mark.parametrize('mutation',['coverage','schema','method','fixture','publication'])
def test_cash_complete_review_and_method_safeguards(mutation):
    e,a=cash_case()
    if mutation=='coverage':e['corporate_actions']['complete']=False
    if mutation=='schema':a['schema_version']=1
    if mutation=='method':e['method']=deepcopy(f.METHOD)
    if mutation=='fixture':e['classification']='authored_fixture'
    if mutation=='publication':e['corporate_actions']['events'][0]['source_publication_at']='2026-10-10T11:00:00Z'
    reseal(e,a);result=build((e,a))
    if mutation in ('fixture','publication'):
        assert result['status']=='generated'
        if mutation=='fixture':
            with pytest.raises(f.ScenarioValidationError):f.apply_scenario_to_row(row(),result)
    else:assert result['status']=='withheld'


def test_cash_empty_reviewed_coverage_matches_raw_arithmetic():
    e,a=cash_case();e['corporate_actions']['events']=[];reseal(e,a)
    cash=build((e,a));raw=build(make_case())
    for key in ('mu','sample_sd','point','low','high'):assert cash['private_audit'][key]==raw['private_audit'][key]
    assert set(raw['private_audit'])==f.AUDIT


@pytest.mark.parametrize('tamper',['method_id','model','audit_method','zone','target'])
def test_cash_mapper_exact_identity_and_linkage(tamper):
    result=build(cash_case())
    if tamper=='method_id':result['report_fields']['forecast_time_basis']['method_id']=f.METHOD['method_id']
    if tamper=='model':result['report_fields']['forecast_model']=f.MODEL
    if tamper=='audit_method':result['private_audit']['method_id']=f.METHOD['method_id']
    if tamper=='zone':result['report_fields']['forecast_time_basis']['venue_timezone']='UTC'
    if tamper=='target':result['report_fields']['forecast_time_basis']['target_close_at']=ISSUE
    with pytest.raises(f.ScenarioValidationError):f.apply_scenario_to_row(row(),result)


def test_cash_same_date_future_close_complete_report(tmp_path):
    issue='2026-10-22T08:00:00+08:00';cutoff='2026-10-22T08:01:00+08:00'
    data=compact_data(f.apply_scenario_to_row(row(),build(cash_case(),issue=issue,cutoff=cutoff)),cutoff)
    data['metadata']['presentation_profile']='compact-v1';data['watchlist_config']['groups'][0]['key']='semiconductors'
    for value in data['forecasts']:value['sector_category']='semiconductors'
    folder=tmp_path/'daily-market-brief';folder.mkdir();calendar=tmp_path/'financial-calendar';calendar.mkdir()
    (calendar/'2026-10.json').write_text(json.dumps(dict(schema_version=1,month='2026-10',timezone='Asia/Kuala_Lumpur',notes=[],entries=[])))
    assert validator.validate_report(folder/'2026-10-22.json',data,compact=True)[:2]==(5,0)


def test_cash_missing_session_and_withheld_gap_preservation():
    e,a=cash_case();e['bars'][10]['session_date']='2026-10-12';reseal(e,a)
    result=build((e,a));assert 'bar_provenance' in result['reasons']
    mapped=f.apply_scenario_to_row(row(),result)
    assert mapped['sources']==row()['sources'] and row()['data_gaps'][0] in mapped['data_gaps']
    assert f.apply_scenario_to_row(mapped,result)['data_gaps']==mapped['data_gaps']


@pytest.mark.parametrize('digits',range(1,7))
def test_microsecond_receipts_preserved_without_rounding(digits):
    e,a=make_case();suffix='123456'[:digits]
    issue=f'2026-10-21T21:00:00.{suffix}Z';cutoff=f'2026-10-21T22:00:00.{suffix}Z'
    e['bars'][-1]['known_at']=f'2026-10-21T20:20:00.{suffix}Z';reseal(e,a)
    result=build((e,a),issue=issue,cutoff=cutoff)
    assert result['status']=='generated'
    assert result['report_fields']['forecast_as_of']==issue
    assert result['private_audit']['issued_at']==issue and result['private_audit']['report_cutoff']==cutoff
    assert f._time(issue).microsecond==int(suffix.ljust(6,'0'))


@pytest.mark.parametrize('field',['issuance','cutoff','review','bar-known','action-known','calendar-known'])
def test_seven_digit_receipts_rejected(field):
    e,a=make_case();issue=ISSUE;cutoff=CUTOFF
    if field=='issuance':issue='2026-10-21T21:00:00.1234567Z'
    if field=='cutoff':cutoff='2026-10-21T22:00:00.1234567Z'
    if field=='review':a['reviewed_at']='2026-10-21T20:40:00.1234567Z'
    if field=='bar-known':e['bars'][-1]['known_at']='2026-10-21T20:20:00.1234567Z'
    if field=='action-known':e['corporate_actions']['known_at']='2026-10-21T20:30:00.1234567Z'
    if field=='calendar-known':e['calendar']['known_at']='2026-10-01T00:00:00.1234567Z'
    reseal(e,a);assert build((e,a),issue=issue,cutoff=cutoff)['status']=='withheld'


def test_microsecond_future_order_not_floored():
    e,a=make_case();a['reviewed_at']='2026-10-21T21:00:00.000002Z'
    reseal(e,a)
    assert 'admission_time' in build((e,a),issue='2026-10-21T21:00:00.000001Z')['reasons']


@pytest.mark.parametrize('configured',[True,False,0,9,13,'12',12.0,None])
def test_depth_configuration_only_fixed_nonbool8_or12(configured):
    assert not f._bounded({},max_depth=configured)


def test_financial_evidence_default_depth_not_expanded():
    e,a=make_case();value=0
    for _ in range(8):value=[value]
    e['depth_extension']=value
    assert not f._bounded(e) and f._bounded(e,max_depth=12)
    assert build((e,a))['reasons']==['schema']
    e,a=make_case();a['depth_extension']=value
    assert not f._bounded(a) and f._bounded(a,max_depth=12)
    assert build((e,a))['reasons']==['schema']
