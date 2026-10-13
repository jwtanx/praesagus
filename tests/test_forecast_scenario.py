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


def test_generated_mapping_passes_current_compact_validator_and_same_day_limit(case):
    result=build(case);mapped=f.apply_scenario_to_row(row(),result)
    data=compact_data(mapped,CUTOFF)
    # Invoke the exact compact forecast checks without any report/calendar file I/O.
    validator.validate_compact(Path('authored-fixture.json'),data,f._time(CUTOFF))
    same=build(case,issue='2026-10-22T08:00:00+08:00',cutoff='2026-10-22T08:01:00+08:00')
    assert same['status']=='generated'
    mapped=f.apply_scenario_to_row(row(),same)
    data=compact_data(mapped,'2026-10-22T08:01:00+08:00')
    with pytest.raises(ValueError,match='invalid forecast time/reference/target date'):
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


def test_timezone_dst_calendar_dates_are_checked_against_instants(case):
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


def test_generated_values_reach_actual_viewer_prediction_guard(case):
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
