"""Versioned report contract tests independent of live report content/providers."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts/daily-market-brief'
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location('report_validator', SCRIPT_DIR / 'validate_report_json.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
sys.path.pop(0)


@pytest.fixture
def report(tmp_path):
    folder = tmp_path / 'daily-market-brief'
    folder.mkdir()
    shared = tmp_path / 'financial-calendar'
    shared.mkdir()
    (shared / '2026-10.json').write_text(json.dumps({'schema_version': 1, 'month': '2026-10',
        'timezone': 'Asia/Kuala_Lumpur', 'notes': [], 'entries': []}))
    groups = [{'key': key, 'label': key, 'emoji': 'S'} for key in ('technology', 'semiconductors')]
    rows = []
    for group in groups:
        for n in range(5):
            row = dict(market='US', country='us', asset_type='equity', ticker=group['key']+str(n), name='Fixture',
                sector=group['label'], sector_category=group['key'], sector_emoji='S', currency='USD',
                current_price='USD 10', price_as_of='2026-10-01T08:00:00+08:00', direction='unknown',
                direction_label='Unknown', estimated_mid_case='Unavailable', estimated_range='Unavailable',
                scenario='Research only', current_price_value=10, estimated_mid_case_value=None,
                range_low_value=None, range_high_value=None, forecast_status='unavailable',
                quote_status='observed', data_gaps=['No validated target'], confidence='unavailable',
                confidence_reason='No forecast method evidence', sources=[])
            rows.append(row)
    data = dict(schema_version=3, metadata={'date': '2026-10-01', 'title': 'Fixture', 'subtitle': 'Fixture',
        'as_of': '2026-10-01T08:00:00+08:00'}, summary=[{'label': 'Fixture', 'title': 'Fixture', 'summary': 'Fixture'}],
        sections={key: {'title': key, 'kicker': key, 'description': [], 'tables': [], 'items': [], 'notes': []}
            for key in validator.REQUIRED_SECTIONS-{'calendar'}},
        watchlist_config={'count_per_group': 5, 'groups': groups}, forecasts=rows,
        calendar_ref='../financial-calendar/2026-10.json', footer='Research only')
    return folder / '2026-10-01.json', data


def test_five_name_shared_calendar(report):
    path, data = report
    assert validator.validate_report(path, data)[:2] == (10, 0)

def test_rated_spy_forecast_needs_frozen_basis(report):
    from ingest.daily_report_projection import forecast_basis_error
    forecast={'ticker':'SPY','direction':'up','forecast_as_of':'2026-10-01T07:55:00+08:00',
      'target_date':'2026-10-02','forecast_basis':{'reference_close_date':'2026-09-30',
      'reference_close':100.0,'reference_source':'https://example.org/close','horizon_type':'next_session',
      'bull_case':'Fixture demand evidence','bear_case':'Fixture rate risk','invalidation':'Below 95'}}
    assert forecast_basis_error(forecast,'2026-10-01T08:00:00+08:00') is None
    assert forecast_basis_error({**forecast,'forecast_basis':{}},'2026-10-01T08:00:00+08:00')
    late={**forecast,'forecast_basis':{**forecast['forecast_basis'],'reference_close_date':'2026-10-02'}}
    assert forecast_basis_error(late,'2026-10-01T08:00:00+08:00')


@pytest.mark.parametrize('change', ['count', 'inline', 'confidence', 'reason', 'unknown_target', 'bad_ref', 'missing_calendar'])
def test_reject_bad_contract(report, change):
    path, data = report
    if change == 'count':
        data['forecasts'].pop()
    elif change == 'inline':
        data['calendar'] = {'events': []}
    elif change == 'confidence':
        data['forecasts'][0]['confidence'] = '90%'
    elif change == 'reason':
        data['forecasts'][0]['confidence_reason'] = ''
    elif change == 'unknown_target':
        data['forecasts'][0]['estimated_mid_case_value'] = 100
    elif change == 'bad_ref':
        data['calendar_ref'] = '../../private.json'
    else:
        (path.parent / data['calendar_ref']).unlink()
    with pytest.raises(ValueError):
        validator.validate_report(path, data)


def observed_point(cutoff):
    return dict(price=10,volume=0,source_at='2026-09-30T23:59:00Z',observed_at='2026-09-30T23:59:00Z',
        ingested_at='2026-10-01T00:00:00Z',known_at='2026-10-01T00:00:00Z',cutoff=cutoff,
        origin='synthetic',currency=None,session=None,adjustment=None,prior_close=None,
        gaps=['currency_unknown','session_unknown','adjustment_unknown','prior_close_unknown'],
        provenance=dict(provider='moomoo-rest',connector='moomoo-rest-capture',capture_authenticity='caller-supplied-unverified',
            rights_status='unconfirmed'))


def test_optional_observed_quote_preserves_legacy_contract(report):
    path,data=report;row=data['forecasts'][0]
    row.update(observed_quote=observed_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    assert validator.validate_report(path,data)[:2]==(10,0)


@pytest.mark.parametrize('change',['sortable','currency','forecast','precision','future','raw','account','missing-gap','known-order'])
def test_invalid_observed_quote_rejected(report,change):
    path,data=report;row=data['forecasts'][0]
    row.update(observed_quote=observed_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    q=row['observed_quote']
    if change=='sortable':row['current_price_value']=10
    elif change=='currency':q['currency']='USD'
    elif change=='forecast':row['direction']='up'
    elif change=='precision':q['source_at']='2026-09-30T23:59:00.1234567Z'
    elif change=='future':q['ingested_at']='2026-10-01T00:00:01Z'
    elif change=='raw':q['raw_body']='private'
    elif change=='account':q['provenance']['account_id']='private'
    elif change=='missing-gap':q['gaps']=[]
    else:q['known_at']='2026-09-30T23:59:00Z'
    with pytest.raises(ValueError):validator.validate_report(path,data)


def public_point(cutoff):
    from ingest.daily_report_projection import map_public_snapshot
    quote=observed_point(cutoff);quote['origin']='trusted-capture'
    return map_public_snapshot(quote,cutoff,listing_currency='USD')


def add_public_point(data):
    row=data['forecasts'][0]
    row.update(public_snapshot=public_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    return row


def test_public_point_and_independent_forecast(report):
    path,data=report;row=add_public_point(data)
    row.update(direction='up',direction_label='Up',forecast_status='available',confidence='low',
               estimated_mid_case_value=12,range_low_value=9,range_high_value=14)
    assert validator.validate_report(path,data,public=True)[:2]==(10,0)


@pytest.mark.parametrize('change',['unknown-key','volume','private-id','units','rights','reference','future','sortable','MY','wrong-listing'])
def test_public_snapshot_rejects_bad_contract(report,change):
    path,data=report;row=add_public_point(data);q=row['public_snapshot']
    if change=='unknown-key':q['extra']='private'
    elif change=='volume':q['volume']=0
    elif change=='private-id':q['attempt_id']='a'*64
    elif change=='units':q['provider_currency']='USD'
    elif change=='rights':q['rights_status']='licensed'
    elif change=='reference':q['reference_url']='https://example.invalid/response'
    elif change=='future':q['source_at']='2026-10-03T00:00:00Z'
    elif change=='sortable':row['current_price_value']=10
    elif change=='MY':row['market']='MY'
    else:row['currency']='MYR'
    with pytest.raises(ValueError):validator.validate_report(path,data,public=True)


@pytest.mark.parametrize('key',['private_draft','observed_quote','attempt_id','raw_hash','semantic_hash','run_id',
                               'credential_path','account_id','raw_body','quote_provenance','provenance','api_key'])
def test_public_report_recursively_rejects_private_keys(report,key):
    path,data=report;add_public_point(data)
    data['sections']['news']['notes'].append({'nested':[{'deeper':{key:'synthetic-private'}}]})
    with pytest.raises(ValueError):validator.validate_report(path,data,public=True)


def test_public_mode_rejects_private_draft_but_private_validation_unchanged(report):
    path,data=report;row=data['forecasts'][0]
    data['metadata']['private_draft']=True
    row.update(observed_quote=observed_point(data['metadata']['as_of']),current_price_value=None,quote_status='missing')
    assert validator.validate_report(path,data)[:2]==(10,0)
    with pytest.raises(ValueError):validator.validate_report(path,data,public=True)


def test_public_cli_selects_boundary(report,monkeypatch):
    path,data=report;calls=[]
    universe={'effective_from':'2026-10-01','taxonomy_id':'fixture','groups':[]}
    data['watchlist_config']['taxonomy_id']='fixture'
    monkeypatch.setattr(sys,'argv',['validate_report_json.py','--public','--date','2026-10-01',
                                  '--reports-dir',str(path.parent),'--universe',str(path.parent/'universe.json')])
    monkeypatch.setattr(validator,'read_json',lambda p:universe if p.name=='universe.json' else {'reports':[]} if p.name=='reports.json' else data)
    monkeypatch.setattr(validator,'validate_universe',lambda *args:([],{}))
    def checked(path,report,context,*,public=False):
        calls.append(public);return 10,0,{}
    monkeypatch.setattr(validator,'validate_report',checked)
    monkeypatch.setattr(validator,'validate_index',lambda *args:None)
    validator.main();assert calls==[True]


@pytest.fixture
def compact_report(report):
    path, data = report
    data['metadata']['presentation_profile'] = 'compact-v1'
    for row in data['forecasts']:
        row.update(current_price='Unavailable', current_price_value=None, quote_status='missing',
                   direction_label='Unrated', target_date=None)
    data['collection'] = dict(observed_us=0, observed_my=0, missing_us=10, missing_my=0,
        session_direction_counts=dict(bullish=0, bearish=0, neutral=0, unavailable=10),
        trend_available_count=0, verified_forecast_reference_count=0)
    return path, data


def rated_row(data):
    row=data['forecasts'][0]
    row.update(direction='up', direction_label='Up', forecast_status='available', confidence='low',
        estimated_mid_case_value=12, range_low_value=9, range_high_value=14,
        forecast_model='Frozen synthetic drift v1', forecast_observations=20, forecast_horizon_sessions=1,
        forecast_as_of='2026-10-01T07:55:00+08:00', target_date='2026-10-02',
        forecast_basis=dict(reference_close_date='2026-09-30',reference_close=10,
            reference_source='https://example.org/reference',horizon_type='next_session',
            bull_case='Demand improves',bear_case='Margins weaken',invalidation='Below reference'))
    data['collection']['verified_forecast_reference_count']=1
    return row


def test_compact_zero_and_partial_coverage_no_minimum_rated(compact_report):
    path,data=compact_report
    assert validator.validate_report(path,data,public=True,compact=True)[:2]==(10,0)
    row=add_public_point(data)
    data['collection'].update(observed_us=1,missing_us=9)
    assert validator.validate_report(path,data,public=True)[:2]==(10,0)
    assert row['direction']=='unknown' and row['estimated_mid_case_value'] is None


def test_compact_fifty_unrated_zero_history(compact_report):
    from copy import deepcopy
    path,data=compact_report
    template=data['forecasts'][0]
    data['watchlist_config']['groups']=[{'key':k,'label':k,'emoji':'S'} for k in
        ['semiconductors']+[f'group{i}' for i in range(9)]]
    data['forecasts']=[]
    for g in data['watchlist_config']['groups']:
        for i in range(5):
            row=deepcopy(template);row.update(ticker=g['key']+str(i),sector_category=g['key'])
            data['forecasts'].append(row)
    data['collection']['missing_us']=50
    data['collection']['session_direction_counts']['unavailable']=50
    assert validator.validate_report(path,data,compact=True)[0]==50


@pytest.mark.parametrize('profile',[None,'','other-v1',True])
def test_explicit_compact_requires_supported_profile(report,profile):
    path,data=report
    data['metadata']['presentation_profile']=profile
    with pytest.raises(ValueError):validator.validate_report(path,data,compact=True)
    if profile not in (None,''):
        with pytest.raises(ValueError):validator.validate_report(path,data)


@pytest.mark.parametrize('case',['summary-count','summary-words','prose','reason','scenario','open-table','label','long-label'])
def test_compact_budgets_enforced_automatically(compact_report,case):
    path,data=compact_report
    if case=='summary-count':data['summary']*=5
    elif case=='summary-words':data['summary'][0]['summary']='word '*51
    elif case=='prose':data['sections']['news']['items']=[{'title':'Fixture','paragraphs':[{'text':'word '*1001}]}]
    elif case=='reason':data['forecasts'][0]['confidence_reason']='word '*41
    elif case=='scenario':data['forecasts'][0]['scenario']='word '*56
    else:
        table={'columns':['Audit'],'rows':[[{'text':'Preserved evidence'}] for _ in range(120)]}
        if case!='open-table':table['collapsed']=True
        if case=='long-label':table['details_label']='word '*13
        data['sections']['score']['tables']=[table]
    with pytest.raises(ValueError):validator.validate_report(path,data)
    # Historical mode continues accepting presentation verbosity/display defaults.
    del data['metadata']['presentation_profile']
    assert validator.validate_report(path,data)[0]==10


def test_compact_limits_accept_boundary_and_preserve_audit(compact_report):
    path,data=compact_report
    data['summary']*=4
    data['summary'][0]['summary']='word '*50
    data['sections']['news']['notes']=[{'text':'word '*1000}]
    data['forecasts'][0].update(confidence_reason='word '*40,scenario='word '*55)
    rows=[[{'text':'Preserved evidence'}] for _ in range(120)]
    data['sections']['score']['tables']=[{'columns':['Audit'],'rows':rows,
        'collapsed':True,'details_label':'word '*12}]
    assert validator.validate_report(path,data)[0]==10
    assert len(rows)==120


@pytest.mark.parametrize('key,value',[
    ('observed_us',1),('observed_my',True),('missing_us',9),('missing_my',None),
    ('trend_available_count',1),('verified_forecast_reference_count',1),
    ('observed_us',False),('missing_us','10'),('missing_my',-1)])
def test_compact_coverage_mismatch_and_malformed_rejected(compact_report,key,value):
    path,data=compact_report;data['collection'][key]=value
    with pytest.raises(ValueError,match='collection'):validator.validate_report(path,data)


@pytest.mark.parametrize('counts',[{},dict(bullish=True,bearish=0,neutral=0,unavailable=9),
    dict(bullish=0,bearish=0,neutral=0,unavailable=9),None])
def test_compact_signal_counts_rejected(compact_report,counts):
    path,data=compact_report;data['collection']['session_direction_counts']=counts
    with pytest.raises(ValueError,match='session_direction_counts'):validator.validate_report(path,data)


def test_compact_rated_nonbenchmark_requires_support(compact_report):
    path,data=compact_report;rated_row(data)
    assert validator.validate_report(path,data,public=True)[0]==10


@pytest.mark.parametrize('case',['basis','model','observations','horizon-count','bool-count','asof-missing',
    'asof-naive','asof-future','reference-future','reference-source','reference-bool','horizon-type',
    'bear','bull','invalidation','target-past','target-missing','mid-outside','unrated-confidence','null-target'])
def test_every_compact_rated_row_rejects_missing_future_support(compact_report,case):
    path,data=compact_report;row=rated_row(data)
    if case=='basis':row.pop('forecast_basis')
    elif case=='model':row['forecast_model']='No supported predictive model'
    elif case=='observations':row['forecast_observations']=0
    elif case=='horizon-count':row['forecast_horizon_sessions']=0
    elif case=='bool-count':row['forecast_observations']=True
    elif case=='asof-missing':row.pop('forecast_as_of')
    elif case=='asof-naive':row['forecast_as_of']='2026-10-01T07:55:00'
    elif case=='asof-future':row['forecast_as_of']='2026-10-01T08:00:01+08:00'
    elif case=='reference-future':row['forecast_basis']['reference_close_date']='2026-10-02'
    elif case=='reference-source':row['forecast_basis']['reference_source']='https://user:secret@example.org'
    elif case=='reference-bool':row['forecast_basis']['reference_close']=True
    elif case=='horizon-type':row['forecast_basis']['horizon_type']='invented'
    elif case in ('bull','bear','invalidation'):row['forecast_basis'][{'bull':'bull_case','bear':'bear_case','invalidation':'invalidation'}[case]]=''
    elif case=='target-past':row['target_date']='2026-10-01'
    elif case=='target-missing':row['target_date']=None
    elif case=='mid-outside':row['estimated_mid_case_value']=20
    elif case=='unrated-confidence':row['confidence']='unavailable'
    else:row['range_low_value']=None
    with pytest.raises(ValueError):validator.validate_report(path,data)


def test_compact_existing_future_quote_guard_still_runs(compact_report):
    path,data=compact_report;row=add_public_point(data)
    data['collection'].update(observed_us=1,missing_us=9)
    row['public_snapshot']['known_at']='2026-10-01T00:00:01Z'
    with pytest.raises(ValueError,match='public_snapshot invalid'):validator.validate_report(path,data,public=True)


def test_compact_cli_routes_final_profile_check(report,monkeypatch):
    path,data=report;calls=[]
    monkeypatch.setattr(sys,'argv',['validate_report_json.py','--compact','--public','--date','2026-10-01',
        '--reports-dir',str(path.parent),'--universe',str(path.parent/'universe.json')])
    universe={'effective_from':'2026-10-01','taxonomy_id':'fixture','groups':[]}
    data['watchlist_config']['taxonomy_id']='fixture'
    monkeypatch.setattr(validator,'read_json',lambda p:universe if p.name=='universe.json' else {'reports':[]} if p.name=='reports.json' else data)
    monkeypatch.setattr(validator,'validate_universe',lambda *args:([],{}))
    def checked(path,report,context,*,public=False,compact=False):
        calls.append((public,compact));return 10,0,{}
    monkeypatch.setattr(validator,'validate_report',checked)
    monkeypatch.setattr(validator,'validate_index',lambda *args:None)
    validator.main();assert calls==[(True,True)]


def add_conflicting_indicators(data):
    from ingest.daily_report_projection import _unavailable_moomoo_trend
    row=add_public_point(data);cutoff=data['metadata']['as_of']
    row['moomoo_session_direction']=dict(provider='moomoo-rest',method='last_price-vs-prev_close_price',
        signal='bullish',label='Bullish',status='available',reason=None,market_date='2026-09-30',
        source_at='2026-09-30T23:59:00Z',retrieved_at='2026-10-01T00:00:00Z',cutoff=cutoff)
    trend=_unavailable_moomoo_trend('US.FIXTURE',cutoff)
    trend.update(status='available',signal='bearish',label='Bearish',reason=None,bar_count=20,
        bar_dates=[f'2026-09-{i:02d}' for i in range(1,21)],last_bar_date='2026-09-20',
        last_bar_timezone_offset_minutes=-240,sma5=9,sma20=10,
        observed_at='2026-09-30T23:59:00Z',ingested_at='2026-09-30T23:59:30Z',known_at='2026-09-30T23:59:40Z')
    row['moomoo_trend']=trend
    data['collection'].update(observed_us=1,missing_us=9,trend_available_count=1)
    data['collection']['session_direction_counts'].update(bullish=1,unavailable=9)
    return row


def test_compact_quote_sma_disagreement_keeps_unrated(compact_report):
    path,data=compact_report;row=add_conflicting_indicators(data)
    assert validator.validate_report(path,data,public=True)[0]==10
    assert row['direction']=='unknown' and row['confidence']=='unavailable' and row['estimated_mid_case_value'] is None


@pytest.mark.parametrize('case',['quote-date','quote-time','SMA-date','SMA-time','missing-coverage','precision'])
def test_compact_future_indicator_evidence_and_missing_coverage_reject(compact_report,case):
    path,data=compact_report;row=add_conflicting_indicators(data)
    if case=='quote-date':row['moomoo_session_direction']['market_date']='2026-10-02'
    elif case=='quote-time':row['moomoo_session_direction']['retrieved_at']='2026-10-01T00:00:01Z'
    elif case=='SMA-date':
        row['moomoo_trend']['bar_dates'][-1]='2026-10-02';row['moomoo_trend']['last_bar_date']='2026-10-02'
    elif case=='SMA-time':row['moomoo_trend']['known_at']='2026-10-01T00:00:01Z'
    elif case=='missing-coverage':data.pop('collection')
    else:
        rated_row(data);row['forecast_as_of']='2026-10-01T07:59:59.1234567+08:00'
    with pytest.raises(ValueError):validator.validate_report(path,data)
