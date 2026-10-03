"""Synthetic deterministic private report drafts; no real quotes or network."""
from copy import deepcopy
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from connectors.moomoo_rest import ReadRequest, ReadResponse
from ingest.daily_report_projection import project_report, validate_observed_quote, write_private_draft
from ingest.private_market_store import PrivateMarketStore, MarketStoreError, canonical

REPO=Path(__file__).resolve().parents[1]
CUTOFF='2026-10-02T00:00:00Z'
OBS='2026-10-01T23:59:00Z'
STAMP=1790899200000-60000


@pytest.fixture
def inputs(tmp_path):
    universe=json.loads((REPO/'artifacts/daily-market-brief/watchlist-universe-five.json').read_text())
    validator=import_module('scripts.daily-market-brief.validate_report_json')
    rows=[]
    for group in universe['groups']:
        for item in group['instruments']:
            rows.append(dict(market=item['market'],country=item['country'],asset_type=item['asset_type'],
                ticker=item['ticker'],name='Synthetic',sector=group['label'],sector_category=group['key'],
                sector_emoji=group['emoji'],currency=item['currency'],current_price='Unavailable',
                current_price_value=None,price_as_of='Unknown',quote_status='missing',
                direction='unknown',direction_label='Unrated',forecast_status='unavailable',
                confidence='unavailable',confidence_reason='Synthetic no forecast',
                estimated_mid_case='Unavailable',estimated_range='Unavailable',
                estimated_mid_case_value=None,range_low_value=None,range_high_value=None,
                scenario='Synthetic research only',data_gaps=['No forecast'],sources=[]))
    report=dict(schema_version=3,metadata={'as_of':CUTOFF,'date':'2026-10-02','title':'Synthetic','subtitle':'Synthetic'},
        forecasts=rows,watchlist_config={'taxonomy_id':universe['taxonomy_id'],'count_per_group':5,
            'groups':[{k:g[k] for k in ('key','label','emoji')} for g in universe['groups']]},
        summary=[{'label':'Synthetic','title':'Synthetic','summary':'Synthetic'}],
        sections={key:{'title':key,'kicker':key,'description':[],'tables':[],'items':[],'notes':[]}
            for key in validator.REQUIRED_SECTIONS-{'calendar'}},calendar_ref='../financial-calendar/2026-10.json',footer='Synthetic')
    codes=['US.'+i['ticker'] for g in universe['groups'] for i in g['instruments'] if i['market']=='US']
    store=PrivateMarketStore(tmp_path/'private-store',create=True)
    request=ReadRequest('POST','/api/v1.0/quote/snapshot','',canonical({'code_list':codes}).encode(),{},1)
    row={'code':codes[0],'name':'Synthetic','update_time':STAMP,'data_date':'2026-10-01','last_price':10,'volume':0}
    response=ReadResponse(200,canonical({'ret_code':0,'ret_msg':'ok','data':{'snapshot_list':[row]}}).encode())
    store.ingest(request,response,run_id='synthetic',observed_at=OBS,ingested_at=CUTOFF,origin='synthetic')
    return store,report,universe,codes


def project(inputs,**kwargs):
    store,report,universe,codes=inputs
    return project_report(store,report,universe,run_id=kwargs.get('run','synthetic'),
                          cutoff=kwargs.get('cutoff',CUTOFF),expected_codes=kwargs.get('codes',codes))


def test_deterministic_50_rows_input_unchanged_allowlist(inputs):
    before=deepcopy(inputs[1]);first=project(inputs);assert first==project(inputs) and inputs[1]==before
    assert len(first['forecasts'])==50 and first['metadata']['private_draft'] is True
    points=[r for r in first['forecasts'] if r['observed_quote'] is not None];assert len(points)==1
    q=points[0]['observed_quote'];validate_observed_quote(q,CUTOFF)
    assert q['price']==10 and q['volume']==0 and q['origin']=='synthetic'
    assert all(q[k] is None for k in ('currency','session','adjustment','prior_close'))
    assert q['source_at']==q['observed_at'].replace('Z','.000+00:00')
    assert 'raw_hash' in q['provenance'] and 'raw' not in q['provenance']
    for row in first['forecasts']:
        assert row['current_price_value'] is None and row['quote_status']=='missing'
        assert row['direction']=='unknown' and row['confidence']=='unavailable'
        assert row['estimated_mid_case_value'] is None and row['scenario']==before['forecasts'][first['forecasts'].index(row)]['scenario']
    assert all('MY_unattempted_unsupported' in r['data_gaps'] for r in first['forecasts'] if r['market']=='MY')


@pytest.mark.parametrize('change',['cutoff','codes','taxonomy','symbols','forecast','target','secret'])
def test_reject_inconsistent_input(inputs,change):
    if change=='cutoff':kwargs={'cutoff':'2026-10-02T00:00:01Z'}
    elif change=='codes':kwargs={'codes':inputs[3][:-1]}
    else:
        kwargs={}
        if change=='taxonomy':inputs[1]['watchlist_config']['taxonomy_id']='other'
        elif change=='symbols':inputs[1]['forecasts'][0]['ticker']='WRONG'
        elif change=='forecast':inputs[1]['forecasts'][0]['direction']='up'
        elif change=='target':inputs[1]['forecasts'][0]['estimated_mid_case_value']=12
        else:inputs[1]['forecasts'][0]['account_id']='synthetic-private'
    with pytest.raises(MarketStoreError):project(inputs,**kwargs)


def test_missing_run_no_previous_quote_fallback(inputs):
    result=project(inputs,run='missing')
    assert all(r['observed_quote'] is None and r['current_price_value'] is None for r in result['forecasts'])
    assert all('no_available_attempts' in r['data_gaps'] for r in result['forecasts'] if r['market']=='US')


@pytest.mark.parametrize('kind',['conflict','zero','unknown-source','after-observation','late-ingest','failed','empty'])
def test_gaps_no_invented_quote(inputs,kind):
    store,template,universe,codes=inputs
    request=ReadRequest('POST','/api/v1.0/quote/snapshot','',canonical({'code_list':codes}).encode(),{},1)
    row={'code':codes[0],'name':'Synthetic','update_time':STAMP,'data_date':'2026-10-01','last_price':11,'volume':0}
    run='synthetic' if kind=='conflict' else kind
    if kind=='zero':row['last_price']=0
    if kind=='unknown-source':row['update_time']=None
    if kind=='after-observation':row['update_time']=STAMP+1
    rows=[] if kind=='empty' else [row]
    response=ReadResponse(503 if kind=='failed' else 200,canonical({'ret_code':0,'ret_msg':'ok','data':{'snapshot_list':rows}}).encode())
    store.ingest(request,response,run_id=run,observed_at=OBS,
                 ingested_at='2026-10-02T00:00:00.000001Z' if kind=='late-ingest' else CUTOFF,origin='synthetic')
    result=project(inputs,run=run)
    assert all(r['observed_quote'] is None for r in result['forecasts'])
    assert all(r['direction']=='unknown' for r in result['forecasts'])


@pytest.mark.parametrize('change',[{'price':True},{'price':float('nan')},{'volume':-1},
    {'currency':'USD'},{'source_at':'2026-10-02T00:00:01Z'},
    {'ingested_at':'2026-10-02T00:00:00.000001Z'}, {'source_at':'2026-10-01T23:59:00.0000001Z'},
    {'cutoff':'2026-10-03T00:00:00Z'}, {'gaps':[]},{'raw_body':'private'}, {'origin':'authenticated'}])
def test_strict_observed_contract(inputs,change):
    q=next(r['observed_quote'] for r in project(inputs)['forecasts'] if r['observed_quote'])
    q.update(change)
    with pytest.raises((ValueError,TypeError,OverflowError)):validate_observed_quote(q,CUTOFF)


def test_private_atomic_no_clobber_and_permission(inputs,tmp_path):
    root=tmp_path/'private-drafts';root.mkdir(mode=0o700);dest=root/'2026-10-02.json'
    result=project(inputs);write_private_draft(dest,result)
    assert dest.stat().st_mode&0o777==0o400 and json.loads(dest.read_text())==result
    before=dest.read_bytes()
    with pytest.raises(MarketStoreError):write_private_draft(dest,result)
    assert dest.read_bytes()==before and list(root.iterdir())==[dest]


@pytest.mark.parametrize('kind',['public','symlink','unsafe-mode','repo'])
def test_unsafe_destination_rejected(inputs,tmp_path,kind):
    root=tmp_path/('public' if kind=='public' else 'private-drafts');root.mkdir(mode=0o700)
    dest=root/'draft.json'
    if kind=='symlink':dest.symlink_to(tmp_path/'missing')
    elif kind=='unsafe-mode':root.chmod(0o755)
    elif kind=='repo':dest=REPO/'draft.json'
    with pytest.raises(MarketStoreError):write_private_draft(dest,project(inputs))
    assert not (REPO/'draft.json').exists()


def test_cli_private_output_roundtrip_and_reject_existing(inputs,tmp_path):
    store,template,universe,codes=inputs
    base=tmp_path/'input';base.mkdir();reports=base/'daily-market-brief';reports.mkdir()
    calendar=base/'financial-calendar';calendar.mkdir()
    (calendar/'2026-10.json').write_text(canonical({'schema_version':1,'month':'2026-10','timezone':'Asia/Kuala_Lumpur','notes':[],'entries':[]}))
    source=reports/'2026-10-02.json';source.write_text(canonical(template))
    upath=base/'universe.json';upath.write_text(canonical(universe));cpath=base/'codes.json';cpath.write_text(canonical(codes))
    private=tmp_path/'private-drafts';private.mkdir(mode=0o700);dest=private/'draft.json'
    argv=[sys.executable,str(REPO/'scripts/daily-market-brief/project_private_quotes.py'),
          '--root',str(store.root),'--template',str(source),'--universe',str(upath),
          '--run-id','synthetic','--cutoff',CUTOFF,'--expected-codes',str(cpath),'--output',str(dest)]
    result=subprocess.run(argv,capture_output=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)=={'private_draft_written':True} and json.loads(dest.read_text())==project(inputs)
    again=subprocess.run(argv,capture_output=True,timeout=5)
    assert again.returncode==1 and str(dest).encode() not in again.stderr and not again.stdout


def test_selection_extra_dictionary_never_copied(inputs):
    store,template,universe,codes=inputs
    selection=store.select_snapshots('synthetic',CUTOFF,codes)
    for point in selection['quotes'].values():
        if point['quote']:
            point['quote']['raw_body']='private-body';point['provenance']['private_path']='/private/synthetic-secret'
    class FakeStore:
        def select_snapshots(self,*args):return selection
    output=project_report(FakeStore(),template,universe,run_id='synthetic',cutoff=CUTOFF,expected_codes=codes)
    serialized=canonical(output)
    assert 'private-body' not in serialized and '/private/synthetic-secret' not in serialized


def test_no_clobber_race_and_temp_cleanup(inputs,tmp_path,monkeypatch):
    from ingest import daily_report_projection as module
    root=tmp_path/'private-drafts';root.mkdir(mode=0o700);dest=root/'draft.json'
    real_link=module.os.link
    def raced_link(source,target,**kwargs):
        Path(target).write_bytes(b'sentinel');return real_link(source,target,**kwargs)
    monkeypatch.setattr(module.os,'link',raced_link)
    with pytest.raises(MarketStoreError):write_private_draft(dest,project(inputs))
    assert dest.read_bytes()==b'sentinel' and list(root.iterdir())==[dest]


def test_cli_bad_arguments_no_private_path_output():
    result=subprocess.run([sys.executable,str(REPO/'scripts/daily-market-brief/project_private_quotes.py'),
                           '--unknown','/private/synthetic-secret'],capture_output=True,timeout=3)
    assert result.returncode==2 and b'/private/synthetic-secret' not in result.stderr


def test_private_path_in_selection_gaps_rejected(inputs):
    store,template,universe,codes=inputs
    selection=store.select_snapshots('synthetic',CUTOFF,codes)
    selection['quotes'][codes[0]]['gap_reasons'].append('/private/synthetic-secret')
    class FakeStore:
        def select_snapshots(self,*args):return selection
    with pytest.raises(MarketStoreError):project_report(FakeStore(),template,universe,run_id='synthetic',cutoff=CUTOFF,expected_codes=codes)


def public_input(inputs):
    quote=deepcopy(next(r['observed_quote'] for r in project(inputs)['forecasts'] if r['observed_quote']))
    quote['origin']='trusted-capture'  # Synthetic fixture of the caller-declared capture contract.
    return quote


def test_public_mapper_price_only_input_unchanged(inputs):
    from ingest.daily_report_projection import map_public_snapshot,validate_public_snapshot,PUBLIC_KEYS
    quote=public_input(inputs);before=deepcopy(quote)
    point=map_public_snapshot(quote,CUTOFF,listing_currency='USD')
    assert quote==before and set(point)==PUBLIC_KEYS and point['price']==10
    assert point['listing_currency']=='USD' and point['provider_currency'] is None
    assert point['rights_status']=='unconfirmed' and point['capture_authenticity']=='caller-supplied-unverified'
    assert all(point[k]==quote[k] for k in ('source_at','observed_at','ingested_at','known_at','cutoff'))
    raw=json.dumps(point)
    assert all(key not in raw for key in ('volume','attempt_id','raw_hash','semantic_hash','run_id','private_draft'))
    assert all(value not in raw for value in quote['provenance'].values() if isinstance(value,str) and len(value)==64)
    validate_public_snapshot(point,CUTOFF,listing_currency='USD')
    point['gaps'].append('mutated');assert quote==before


@pytest.mark.parametrize('change',['synthetic','zero','negative','bool','nan','future','precision','known-order','extra','private-path','secret','MYR'])
def test_public_mapper_rejects_invalid_or_private_input(inputs,change):
    from ingest.daily_report_projection import map_public_snapshot
    quote=public_input(inputs);currency='USD'
    if change=='synthetic':quote['origin']='synthetic'
    elif change in ('zero','negative','bool','nan'):quote['price']={'zero':0,'negative':-1,'bool':True,'nan':float('nan')}[change]
    elif change=='future':quote['source_at']='2026-10-03T00:00:00Z'
    elif change=='precision':quote['source_at']='2026-10-01T23:59:00.1234567Z'
    elif change=='known-order':quote['known_at']='2026-10-01T23:00:00Z'
    elif change=='extra':quote['extra']='private'
    elif change=='private-path':quote['provenance']['credential_path']='/private/fixture'
    elif change=='secret':quote['provenance']['api_key']='synthetic-secret'
    else:currency='MYR'
    with pytest.raises(ValueError):map_public_snapshot(quote,CUTOFF,listing_currency=currency)


def test_clean_public_overlay_preserves_independent_template(inputs):
    from ingest.daily_report_projection import map_public_snapshot
    template=deepcopy(inputs[1]);before=deepcopy(template)
    template['forecasts'][0]['public_snapshot']=map_public_snapshot(public_input(inputs),CUTOFF,listing_currency='USD')
    assert inputs[1]==before and len(template['forecasts'])==50
    assert 'private_draft' not in template['metadata']
    for original,row in zip(before['forecasts'],template['forecasts']):
        assert {k:v for k,v in row.items() if k!='public_snapshot'}==original
    assert all('public_snapshot' not in row for row in template['forecasts'] if row['market']=='MY')
