"""Offline fictional selection, immutable storage and collection regressions."""
from collections import Counter
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/stock-research'))
universe=importlib.import_module('universe');storage=importlib.import_module('storage')
collect=importlib.import_module('collect');config=importlib.import_module('config')
from contracts import Batch,FieldValue,RESTError

NOW=int(datetime(2026,10,15,tzinfo=timezone.utc).timestamp()*1000)
SESSIONS,CLOSES=collect.completed_sessions(NOW)
STAMP=datetime(2026,10,15,10,tzinfo=timezone(timedelta(hours=8)))


def candidate(identity,*,asset='STOCK',sector='s0',issuer=None,leverage=1,family=None,turnover=30000000,change=.01):
    return {'code':'US.'+identity,'stock_id':identity,'name':'Fictional '+identity,'asset_type':asset,
        'price':25.,'median20_turnover':turnover,'latest_turnover':turnover,'latest_volume':1000000.,'latest_return':change,'atr_fraction':.02,'valid_sessions':252,
        'latest20_complete':True,'comparison_basis_verified':True,'listing_verified':True,'sector_id':sector,
        'sector_mapping_status':'verified','issuer_status':'verified','issuer_group_id':issuer or identity,
        'classification_verified':True,'signed_leverage':leverage,'exposure_family':family or identity,
        'reset':'not_applicable' if leverage==1 else 'daily','reasons':[]}


def evidence(**changes):
    return {'status':'verified','source_url':'https://example.org/fictional-evidence','source_hash':'a'*64,
            'reviewer':'Trader','known_at_ms':NOW-1000,**changes}


def test_full_stock_quotas_sector_caps_refill_and_determinism():
    rows=[candidate('STOCK'+str(i),sector='s'+str(i%5),change=.01 if i<40 else -.01) for i in range(80)]
    pools={'winners':[r['code'] for r in rows[:40]],'losers':[r['code'] for r in rows[40:]],'volume':[r['code'] for r in rows]}
    result=universe.select_universe(rows,pools)
    stocks=[row for row in result['main'] if row['asset_type']=='STOCK']
    assert len(stocks)==80 and Counter(row['selection_bucket'] for row in stocks)==universe.STOCK_QUOTAS
    assert max(Counter(row['sector_id'] for row in stocks).values())==16
    assert universe.select_universe(list(reversed(rows)),pools)['main']==result['main']
    assert all(row['selection_reasons'] for row in stocks)


def test_etf_allocation_reassigns_greedy_counterexample_without_false_shortfall():
    # Fictional witnesses mirror the reviewed family constraints, not actual eligible securities.
    families=['tech','bio','semi','finance','energy','health','industrial','materials','staples','utility','comm','disc']
    rows=[candidate('ORD'+str(i),asset='ETF',family=f,turnover=100000000-i) for i,f in enumerate(families)]
    for name,lev,family,rank in [('HOT2TECH',2,'tech',90),('HOT2BIO',2,'bio',89),('ALT2ENERGY',2,'energy',50),
      ('ALT2HEALTH',2,'health',49),('HOT3SEMI',3,'semi',88),('HOT3FIN',3,'finance',87),
      ('ALT3TECH',3,'tech',48),('ALT3IND',3,'industrial',47),('INV1BROAD',-1,'broad',46),
      ('INV1FIN',-1,'finance',45),('INV2MAT',-2,'materials',44),('INV3SEMI',-3,'semi',43)]:
        rows.append(candidate(name,asset='ETF',leverage=lev,family=family,turnover=rank*1000000))
    pools={'volume':[r['code'] for r in rows]}
    result=universe.select_universe(rows,pools)
    assert len(result['main'])==20 and Counter(row['selection_bucket'] for row in result['main'])==universe.ETF_QUOTAS
    assert max(Counter(row['exposure_family'] for row in result['main']).values())<=2
    assert all(result['coverage']['shortfalls'][key]==0 for key in universe.ETF_QUOTAS)


def test_unknown_sector_issuer_liquidity_missingness_and_speculative_disjoint():
    rows=[candidate('GOOD'),candidate('UNKNOWNSECTOR'),candidate('UNKNOWNISSUER'),candidate('LOW',turnover=6000000)]
    rows[1]['sector_mapping_status']='unmapped';rows[2]['issuer_status']='unresolved'
    rows[3].update(price=2.,valid_sessions=50)
    result=universe.select_universe(rows,{'volume':[r['code'] for r in rows]})
    assert [r['code'] for r in result['main']]==['US.GOOD']
    assert [r['code'] for r in result['speculative']]==['US.LOW']
    assert 'sector-unverified' in result['coverage']['rejections']['US.UNKNOWNSECTOR']
    assert 'issuer-unresolved' in result['coverage']['rejections']['US.UNKNOWNISSUER']
    assert result['coverage']['shortfall_status']=='coverage-or-identity-blocked'
    assert set(r['code'] for r in result['main']).isdisjoint(r['code'] for r in result['speculative'])


def test_reviewed_issuer_dedup_does_not_use_ticker_punctuation_or_force_rotation():
    rows=[candidate('CLASSA',issuer='issuer-one'),candidate('CLASSB',issuer='issuer-one',turnover=40000000),candidate('CLASSC')]
    pools={'volume':[r['code'] for r in rows]}
    result=universe.select_universe(rows,pools)
    assert {r['code'] for r in result['main']}=={'US.CLASSB','US.CLASSC'}
    assert result['coverage']['rejections']['US.CLASSA']==['duplicate-verified-issuer-class']
    assert universe.select_universe(rows,pools)==result
    assert universe.select_universe(rows,pools,discovery_status={'volume':'truncated'})['coverage']['shortfall_status']=='budget-or-discovery-incomplete'


def test_sector_crosswalk_exact_ids_all_memberships_profile_conflict_and_future_evidence():
    industry=evidence(market='US',taxonomy_id='vendor-v1',taxonomy_snapshot_hash='b'*64,
        industry_records=[{'plate_code':'US.I1','plate_type':'INDUSTRY','plate_name':'Exact industry'}])
    mapping=evidence(market='US',vendor_taxonomy_id='vendor-v1',vendor_taxonomy_snapshot_hash='b'*64,
        industry_code='US.I1',sector_id='sector1',target_sector_taxonomy_id='reviewed-research',target_taxonomy_version='1',mapping_version='1')
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='verified'
    industry['profile_industry_label']='Different label'
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='conflicting'
    mapping['reviewed_exact_profile_aliases']=['Different label']
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='verified'
    industry['industry_records'].append({'plate_code':'US.MISSING','plate_type':'INDUSTRY','plate_name':'Other'})
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='unmapped'
    industry['industry_records'].pop();mapping['known_at_ms']=NOW+1
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='stale'
    industry['industry_records'][0]['plate_type']='CONCEPT'
    assert universe.resolve_sector(industry,[mapping],NOW)['sector_mapping_status']=='unmapped'


def bars_for(security,*,known=NOW-100):
    rows=[]
    for i,day in enumerate(SESSIONS):
        close=25.25 if i==len(SESSIONS)-1 else 25.
        stamp=int(datetime.fromisoformat(day).replace(hour=4,tzinfo=timezone.utc).timestamp()*1000)
        rows.append({'code':security,'session_date':day,'open':25.,'high':max(close,25.)+.2,'low':24.8,'close':close,
            'volume':1000.,'turnover':30000000.,'currency':'USD','adjustment':'forward-excluding-dividends',
            'source':'fictional','source_at_ms':stamp,'raw_time_key':stamp,'raw_date':int(day.replace('-','')),'raw_time_zone':-240,
            'time_zone_unit_status':'documented-minutes/runtime-unverified','time_zone_unit_source_url':'https://example.org/time',
            'provider_finality_status':'unverified','retrieved_at_ms':known,'known_at_ms':known,'revision_vintage':'d'*64,
            'completed':True,'completion_status':'completed','volume_precision':0,'currency_source_url':'https://example.org/field-units'})
    return rows


def metadata_for(security='US.DEMO',stock_id=123):
    return {'schema_version':1,'listing_records':{security:evidence(code=security,stock_id=stock_id,suspended=False)},
      'comparison_evidence':{security:evidence(price_units='USD',turnover_units='USD',volume_units='shares',adjustment='forward-excluding-dividends')},
      'issuer_relations':{security:evidence(code=security,stock_id=stock_id,issuer_id_namespace='fictional',issuer_group_id='issuer-demo',relation_type='issuer-security-table')},
      'industry_evidence':{security:evidence(market='US',taxonomy_id='fixture',taxonomy_snapshot_hash='b'*64,
           industry_records=[{'plate_code':'US.I1','plate_name':'Exact','plate_type':'INDUSTRY'}])},
      'sector_crosswalk':[evidence(market='US',vendor_taxonomy_id='fixture',vendor_taxonomy_snapshot_hash='b'*64,industry_code='US.I1',
         sector_id='sector1',target_sector_taxonomy_id='fictional',target_taxonomy_version='1',mapping_version='1')],
      'currency_evidence':{security:evidence(code=security,stock_id=stock_id,endpoint='history-kline',identity_binding_status='verified',currency='USD',
         fields=['open','high','low','close','turnover'],applicable_from_session=SESSIONS[0],applicable_to_session=SESSIONS[-1])}}


def test_latest20_exact_session_median_does_not_compress_holes_or_use_screener_mean():
    identity={'code':'US.DEMO','stock_id':123,'stock_type':'STOCK','name':'Fictional'}
    rows=bars_for('US.DEMO');metadata=metadata_for()
    good=universe.build_candidate(identity,rows,required_sessions=SESSIONS,cutoff_ms=NOW,metadata=metadata)
    assert good['median20_turnover']==30000000 and good['latest20_complete']
    rows.pop(-5)
    bad=universe.build_candidate(identity,rows,required_sessions=SESSIONS,cutoff_ms=NOW,metadata=metadata)
    assert bad['median20_turnover'] is None and not bad['latest20_complete']
    assert 'latest-20-required-sessions-missing' in bad['reasons']


def test_currency_listing_evidence_never_fills_provider_history_fields():
    rows=bars_for('US.DEMO')
    for row in rows:row['currency']=None
    listing_only=evidence(currency='USD',endpoint='issuer-listing',identity_binding_status='verified')
    assert all(row['currency'] is None for row in collect.apply_field_currency(rows,listing_only,NOW,{'code':'US.DEMO','stock_id':123}))
    record=metadata_for()['currency_evidence']['US.DEMO']
    assert all(row['currency']=='USD' for row in collect.apply_field_currency(rows,record,NOW,{'code':'US.DEMO','stock_id':123}))
    record['known_at_ms']=NOW+1
    assert all(row['currency'] is None for row in collect.apply_field_currency(rows,record,NOW,{'code':'US.DEMO','stock_id':123}))


def test_generation_exclusive_private_timestamp_and_compatible_manifest_discovery(tmp_path):
    g=storage.Generation(tmp_path,generated_at=STAMP,compatibility_id='policy')
    g.json('state.json',{'schema_version':1});g.csv('history.csv',[],storage.HISTORY_COLUMNS);path=g.finish(status='partial')
    assert path.name=='2026-10-15_100000' and path.stat().st_mode&0o777==0o700
    assert all(p.stat().st_mode&0o777==0o600 for p in path.iterdir())
    with pytest.raises(FileExistsError):storage.Generation(tmp_path,generated_at=STAMP)
    pilot=storage.Generation(tmp_path,generated_at=STAMP+timedelta(seconds=1),kind='capability-pilot');pilot.finish()
    assert storage.latest_state(tmp_path,'policy')['folder']==str(path)
    assert storage.latest_state(tmp_path,'other-policy') is None
    (path/'state.json').write_text('tampered')
    with pytest.raises(storage.StorageError):storage.latest_state(tmp_path,'policy')


@pytest.mark.parametrize('path',[ROOT,ROOT/'scripts/data',ROOT/'frontend/node_modules/data',ROOT/'stock-research-data'])
def test_output_root_codepaths_and_unignored_parent_rejected(path):
    with pytest.raises(storage.StorageError):storage.output_parent(path)


def test_append_only_revision_merge_preserves_original_known_time_on_reobservation():
    old=bars_for('US.DEMO')[-1];again=dict(old,retrieved_at_ms=NOW,known_at_ms=NOW,revision_vintage='e'*64)
    merged,changes=storage.merge_history([old],[again])
    assert merged[0]['known_at_ms']==old['known_at_ms'] and changes[0]['change_type']=='reobserved'
    revised=dict(again,close=25.2,known_at_ms=NOW+1)
    merged,changes=storage.merge_history(merged,[revised])
    assert merged[0]['known_at_ms']==NOW+1 and changes[0]['change_type']=='revised'
    assert old['close']==25.25


class FakeProvider:
    def __init__(self,settings,*,fail=False):self.config=settings.provider;self.calls=[];self.fail=fail
    def screen(self,**kwargs):
        self.calls.append(('screen',kwargs))
        if self.fail:raise RESTError('rate-limited')
        return Batch(({'code':'US.DEMO','name':'Fictional','fields':(FieldValue(25.,25000,'price','available'),)},),'screen','success',None,1)
    def basicinfo(self,codes):
        self.calls.append(('basicinfo',list(codes)))
        return Batch(tuple({'code':c,'stock_id':123,'name':'Fictional','stock_type':'STOCK','suspension':False} for c in codes),'basic','success',None,1)
    def snapshots(self,codes):
        self.calls.append(('snapshots',list(codes)))
        return Batch(tuple({'code':c,'suspension':False,'source_at_ms':NOW-100} for c in codes),'snapshot','success',None,1)
    def history(self,security,**kwargs):
        self.calls.append(('history',security,kwargs))
        rows=[row for row in bars_for(security) if kwargs['start']<=row['session_date']<=kwargs['end']]
        for row in rows:row['currency']=None
        return Batch(tuple(rows),'history','success',None,1)
    def capabilities(self):return {'live':'fictional-not-tested'}


def test_incremental_collection_and_prior_forecast_actuals_are_retained_outside_discovery(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path));fake=FakeProvider(settings)
    first=collect.run_collection(settings,provider=fake,metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    old_bytes=(first/'history.csv').read_bytes()
    prediction=storage.Generation(tmp_path,generated_at=STAMP+timedelta(seconds=1),kind='stock-research-prediction')
    prediction.finish(forecast_symbols=['US.EXITED'])
    second_fake=FakeProvider(settings)
    second=collect.run_collection(settings,provider=second_fake,metadata=metadata_for(),generated_at=STAMP+timedelta(seconds=2),as_of_ms=NOW)
    assert (first/'history.csv').read_bytes()==old_bytes
    calls=[call for call in second_fake.calls if call[0]=='history']
    assert any(call[1]=='US.EXITED' for call in calls)
    assert next(call for call in calls if call[1]=='US.DEMO')[2]['start']==SESSIONS[-5]
    manifest=json.loads((second/'manifest.json').read_text())
    assert manifest['retained_forecast_symbols']==['US.EXITED'] and manifest['current_discovered_symbols']==['US.DEMO']
    assert 'US.EXITED' not in manifest['selected_symbols']
    state=storage.latest_state(tmp_path,collect.compatibility(settings))
    assert 'US.EXITED' in state['histories']


def test_first_provider_failure_stops_network_and_saves_honest_partial_generation(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path));fake=FakeProvider(settings,fail=True)
    path=collect.run_collection(settings,provider=fake,metadata={},generated_at=STAMP,as_of_ms=NOW)
    assert len(fake.calls)==1
    manifest=json.loads((path/'manifest.json').read_text())
    assert manifest['status']=='partial'
    coverage=json.loads((path/'coverage.json').read_text())
    assert coverage['collection_issues'][0]['category']=='rate-limited'


def test_offline_has_no_provider_and_no_compatible_state_is_explicit(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    path=collect.run_collection(settings,offline=True,generated_at=STAMP,as_of_ms=NOW)
    coverage=json.loads((path/'coverage.json').read_text())
    assert coverage['collection_issues'][0]['category']=='compatible-state-missing'
    assert json.loads((path/'universe.json').read_text())['main']==[]


def test_calendar_excludes_incomplete_session_and_accounts_for_holiday():
    before=int(datetime(2026,10,14,19,tzinfo=timezone.utc).timestamp()*1000)
    sessions,_=collect.completed_sessions(before)
    assert sessions[-1]=='2026-10-13'
    sessions,_=collect.completed_sessions(NOW)
    assert sessions[-1]=='2026-10-14' and '2026-01-01' not in sessions


def test_stock_allocation_can_change_issuer_class_to_fill_needed_bucket():
    rows=[]
    for i in range(79):
        name=('WIN' if i<19 else 'LOSE' if i<39 else 'VOL')+str(i)
        rows.append(candidate(name,sector='s'+str(i%5),change=.01 if i<19 else -.01 if i<39 else .001))
    a=candidate('FLEXA',issuer='flex',sector='s4',turnover=999000000)
    b=candidate('FLEXB',issuer='flex',sector='s4')
    rows += [a,b]
    pools={'winners':[r['code'] for r in rows[:19]]+[b['code']],
           'losers':[r['code'] for r in rows[19:39]],'volume':[a['code']]+[r['code'] for r in rows[39:79]]}
    result=universe.select_universe(rows,pools)
    assert len(result['main'])==80 and Counter(r['selection_bucket'] for r in result['main'])==universe.STOCK_QUOTAS
    assert b['code'] in {r['code'] for r in result['main']} and a['code'] not in {r['code'] for r in result['main']}
    assert max(Counter(r['sector_id'] for r in result['main']).values())==16
    a['sector_id']='other'
    result=universe.select_universe(rows,pools)
    assert all('issuer-sector-conflict' in result['coverage']['rejections'][r['code']] for r in (a,b))


def test_effective_intervals_and_etf_source_observation_cannot_be_future_or_expired():
    assert not universe.reviewed(evidence(effective_from='2026-10-16'),NOW)
    assert not universe.reviewed(evidence(effective_to='2026-10-13'),NOW)
    assert universe.reviewed(evidence(effective_from=None,effective_to=None),NOW)
    assert not universe.etf_available({'source_asof':'2026-10-16'},NOW)
    assert not universe.etf_available({'source_asof':'2026-10-14','observed_at':'2026-10-15T01:00:00Z'},NOW)
    assert universe.etf_available({'source_asof':'2026-10-14','effective_from':None,'effective_to':None},NOW)
    assert not universe.etf_available({'source_asof':'2026-10-14','effective_to':'2026-10-13'},NOW)


def test_currency_requires_exact_code_security_id_and_applicable_session():
    rows=bars_for('US.DEMO');record=metadata_for()['currency_evidence']['US.DEMO']
    assert all(r['currency'] is None for r in collect.apply_field_currency(rows,record,NOW,{'code':'US.OTHER','stock_id':123}))
    assert all(r['currency'] is None for r in collect.apply_field_currency(rows,record,NOW,{'code':'US.DEMO','stock_id':999}))
    record['applicable_from_session']=SESSIONS[-1]
    result=collect.apply_field_currency(rows,record,NOW,{'code':'US.DEMO','stock_id':123})
    assert result[-1]['currency']=='USD' and all(r['currency'] is None for r in result[:-1])


def test_late_currency_evidence_enriches_all_cached_rows_without_backdating_or_overwrite(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path));metadata=metadata_for()
    metadata['currency_evidence']={}
    first=collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata,generated_at=STAMP,as_of_ms=NOW)
    original=(first/'history.csv').read_bytes()
    old=storage.latest_state(tmp_path,collect.compatibility(settings))
    assert all(row['currency'] is None for row in old['histories']['US.DEMO'])
    metadata=metadata_for();metadata['currency_evidence']['US.DEMO']['known_at_ms']=NOW+2000
    second=collect.run_collection(settings,offline=True,metadata=metadata,generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW+2000)
    current=storage.latest_state(tmp_path,collect.compatibility(settings))
    assert all(row['currency']=='USD' and row['known_at_ms']==NOW+2000 for row in current['histories']['US.DEMO'])
    assert (first/'history.csv').read_bytes()==original and (second/'history_revisions.csv').stat().st_size>100
    metadata['currency_evidence']['US.DEMO']['effective_to']='2026-10-15T00:00:03Z'
    collect.run_collection(settings,offline=True,metadata=metadata,generated_at=STAMP+timedelta(seconds=2),as_of_ms=NOW+4000)
    latest=storage.latest_state(tmp_path,collect.compatibility(settings))
    assert all(row['currency'] is None for row in latest['histories']['US.DEMO'])


def test_same_known_timestamp_conflicting_revision_rejected():
    old=bars_for('US.DEMO')[-1]
    with pytest.raises(storage.StorageError,match='conflicting-same-known-at'):
        storage.merge_history([old],[dict(old,close=25.2)])


def test_manifest_has_reproducible_calendar_hash_and_current_identity_sidecar(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    folder=collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    manifest=json.loads((folder/'manifest.json').read_text());calendar=json.loads((folder/'calendar.json').read_text())
    assert manifest['calendar']['schedule_sha256']==storage.sha(storage.canonical(calendar['sessions']))
    assert manifest['calendar']['dependency_version']
    identities=json.loads((folder/'identity_bindings.json').read_text())
    assert identities[0]['code']=='US.DEMO' and identities[0]['stock_id']==123
    assert identities[0]['effective_from'] is None and identities[0]['scope']=='current-observed-binding/not-historical-alias'
    assert manifest['adjustment_policy']['historical_point_in_time']=='not-established'


def test_secure_locator_reference_is_explicit_private_and_not_in_repository(tmp_path):
    with pytest.raises(ValueError,match='configure'):collect.load_secure_locator('')
    path=tmp_path/'locator.json'
    path.write_text(json.dumps({'directory':str(tmp_path/'fictional-private-directory'),'app_key_name':'fictional-key-name'}))
    path.chmod(0o600)
    assert collect.load_secure_locator(str(path))['app_key_name']=='fictional-key-name'
    path.chmod(0o644)
    with pytest.raises(ValueError,match='private-locator'):collect.load_secure_locator(str(path))


def test_truncated_history_resumes_older_missing_range_instead_of_same_latest_page(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    class ShortHistory(FakeProvider):
        def history(self,security,**kwargs):
            result=super().history(security,**kwargs)
            return Batch(result.rows[-20:],'history','truncated','page-budget',1)
    first_fake=ShortHistory(settings)
    first=collect.run_collection(settings,provider=first_fake,metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    oldest=storage.latest_state(tmp_path,collect.compatibility(settings))['histories']['US.DEMO'][0]['session_date']
    second_fake=ShortHistory(settings)
    collect.run_collection(settings,provider=second_fake,metadata=metadata_for(),generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW)
    second_call=next(call for call in second_fake.calls if call[0]=='history')
    assert second_call[2]['end']<oldest
    assert len(storage.latest_state(tmp_path,collect.compatibility(settings))['histories']['US.DEMO'])==40
    assert (first/'manifest.json').is_file()


def test_adjustment_vintage_change_requests_fresh_full_backfill_keeps_previous_folder(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path));metadata=metadata_for()
    metadata['comparison_evidence']['US.DEMO']['adjustment_vintage_id']='fixture-v1'
    first=collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata,generated_at=STAMP,as_of_ms=NOW)
    old=(first/'history.csv').read_bytes()
    metadata['comparison_evidence']['US.DEMO']['adjustment_vintage_id']='fixture-v2'
    fake=FakeProvider(settings)
    collect.run_collection(settings,provider=fake,metadata=metadata,generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW)
    assert next(call for call in fake.calls if call[0]=='history')[2]['start']==SESSIONS[0]
    assert (first/'history.csv').read_bytes()==old


def test_fully_ignored_data_parent_allowed_but_extension_only_ignore_rejected(tmp_path,monkeypatch):
    repo=tmp_path/'repository';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True,timeout=3)
    monkeypatch.setattr(storage,'ROOT',repo)
    (repo/'.gitignore').write_text('data/\npartial/*.csv\n')
    assert storage.output_parent(repo/'data')==repo/'data'
    with pytest.raises(storage.StorageError):storage.output_parent(repo/'partial')


def test_partial_identity_does_not_treat_cached_listing_as_fresh(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    class MissingIdentity(FakeProvider):
        def basicinfo(self,codes):
            self.calls.append(('basicinfo',list(codes)))
            return Batch((),'basic','partial','requested-codes-missing',1,tuple(codes))
    folder=collect.run_collection(settings,provider=MissingIdentity(settings),metadata=metadata_for(),generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW)
    assert json.loads((folder/'universe.json').read_text())['main']==[]
    assert 'US.DEMO' in storage.latest_state(tmp_path,collect.compatibility(settings))['state']['identities']


def test_offline_entrypoint_from_other_working_directory_never_loads_locator(tmp_path):
    output=tmp_path/'state'
    import os
    env=dict(os.environ,PRSG_MOOMOO_CREDENTIAL_LOCATOR=str(tmp_path/'does-not-exist'),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/stock-research/collect.py'),'--offline','--state-dir',str(output)],
                          cwd=tmp_path,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and not result.stderr
    assert json.loads(result.stdout)['kind']=='stock-research-collection'
    folder=Path(json.loads(result.stdout)['generation'])
    assert json.loads((folder/'manifest.json').read_text())['offline'] is True


def test_unignored_in_repo_cli_error_explains_setup_without_private_values(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/stock-research/collect.py'),'--offline','--state-dir',str(ROOT/'stock-research-data')],
                          cwd=tmp_path,capture_output=True,text=True,timeout=10)
    assert result.returncode==2
    assert 'fully Git-ignored' in json.loads(result.stdout)['setup'] and not (ROOT/'stock-research-data').exists()


def test_default_offline_replay_reuses_hash_checked_metadata_but_explicit_empty_withdraws(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    first=collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    collect.run_collection(settings,offline=True,generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW+1000)
    assert all(r['currency']=='USD' for r in storage.latest_state(tmp_path,collect.compatibility(settings))['histories']['US.DEMO'])
    original=(first/'history.csv').read_bytes()
    collect.run_collection(settings,offline=True,metadata={},generated_at=STAMP+timedelta(seconds=2),as_of_ms=NOW+2000)
    assert all(r['currency'] is None for r in storage.latest_state(tmp_path,collect.compatibility(settings))['histories']['US.DEMO'])
    assert (first/'history.csv').read_bytes()==original


def test_changed_security_id_quarantines_old_ticker_history_and_requests_full_backfill(tmp_path):
    settings=config.CollectionConfig(state_parent=str(tmp_path))
    first=collect.run_collection(settings,provider=FakeProvider(settings),metadata=metadata_for(),generated_at=STAMP,as_of_ms=NOW)
    old=(first/'history.csv').read_bytes()
    class ReusedTicker(FakeProvider):
        def basicinfo(self,codes):
            self.calls.append(('basicinfo',list(codes)))
            return Batch(tuple({'code':c,'stock_id':999,'name':'Different fictional security','stock_type':'STOCK','suspension':False} for c in codes),'basic','success',None,1)
    fake=ReusedTicker(settings)
    folder=collect.run_collection(settings,provider=fake,metadata=metadata_for(),generated_at=STAMP+timedelta(seconds=1),as_of_ms=NOW+1000)
    assert next(call for call in fake.calls if call[0]=='history')[2]['start']==SESSIONS[0]
    assert json.loads((folder/'manifest.json').read_text())['identity_quarantined_symbols']==['US.DEMO']
    assert json.loads((folder/'universe.json').read_text())['main']==[]
    assert (first/'history.csv').read_bytes()==old
    assert all(row['currency'] is None for row in storage.latest_state(tmp_path,collect.compatibility(settings))['histories']['US.DEMO'])


def test_volume_rank_uses_current_completed_turnover_not_median_or_live_quote():
    a=candidate('MEDIANLEADER',turnover=90000000);a['latest_turnover']=30000000
    b=candidate('CURRENTLEADER',turnover=30000000);b['latest_turnover']=100000000
    result=universe.select_universe([a,b],{'volume':[a['code'],b['code']]})
    ranks={row['code']:row['discovery_ranks']['volume'] for row in result['main']}
    assert ranks[b['code']]==1 and ranks[a['code']]==2
    identity={'code':'US.DEMO','stock_id':123,'stock_type':'STOCK','name':'Fictional'}
    bars=bars_for('US.DEMO');bars[-1]['turnover']=100000000;bars[-1]['volume']=5000
    derived=universe.build_candidate(identity,bars,required_sessions=SESSIONS,cutoff_ms=NOW,metadata=metadata_for())
    assert derived['median20_turnover']==30000000 and derived['latest_turnover']==100000000 and derived['latest_volume']==5000


def test_same_provider_security_id_cannot_count_as_two_issuers_or_two_etfs():
    a=candidate('DUPA');b=candidate('DUPB');b['stock_id']=a['stock_id']
    result=universe.select_universe([a,b],{'volume':[a['code'],b['code']]})
    assert result['main']==[] and all('provider-security-identity-conflict' in values for values in result['coverage']['rejections'].values())
    a=candidate('FUNDALIASA',asset='ETF',family='shared');b=candidate('FUNDALIASB',asset='ETF',family='shared')
    b['stock_id']=a['stock_id']
    result=universe.select_universe([a,b],{'volume':[a['code'],b['code']]})
    assert len(result['main'])==1


def test_future_actual_availability_overrides_earlier_asserted_known_time():
    record=evidence(available_at='2026-10-15T01:00:00Z')
    assert not universe.reviewed(record,NOW)
    assert universe.known_ms(record)>NOW


def test_generation_joblib_bytes_roundtrip_manifest_hash_and_private_permissions(tmp_path):
    # Deliberately not a serialized model: storage must not interpret or load bytes.
    import hashlib
    payload=b'\x00\xfffictional-opaque-model-bytes\r\n'
    generation=storage.Generation(tmp_path,generated_at=STAMP,kind='stock-research-model')
    generation.write('quantiles_v1.joblib',payload)
    folder=generation.finish(status='research-only')
    artifact=folder/'quantiles_v1.joblib'
    assert artifact.read_bytes()==payload and artifact.stat().st_mode&0o777==0o600
    assert folder.stat().st_mode&0o777==0o700
    entry=json.loads((folder/'manifest.json').read_text())['artifacts']['quantiles_v1.joblib']
    assert entry=={'path':'quantiles_v1.joblib','sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
    with pytest.raises(storage.StorageError):generation.write('after_close.joblib',payload)
    assert not (folder/'after_close.joblib').exists()


def test_joblib_write_collision_keeps_existing_bytes_and_manifest(tmp_path):
    generation=storage.Generation(tmp_path,generated_at=STAMP)
    generation.write('model.joblib',b'first-opaque-bytes')
    original=copy.deepcopy(generation.manifest)
    with pytest.raises(FileExistsError):generation.write('model.joblib',b'replacement')
    assert (generation.path/'model.joblib').read_bytes()==b'first-opaque-bytes'
    assert generation.manifest==original
    with pytest.raises(storage.StorageError):generation.write('other.joblib','not-bytes')
    assert not (generation.path/'other.joblib').exists()


@pytest.mark.parametrize('name',['../model.joblib','/tmp/model.joblib','nested/model.joblib',
                                  'model.joblib.exe','model.pkl','model.xlsx','model..joblib'])
def test_joblib_unsafe_or_unapproved_names_rejected(tmp_path,name):
    generation=storage.Generation(tmp_path,generated_at=STAMP)
    with pytest.raises(storage.StorageError):generation.write(name,b'opaque')
    assert list(generation.path.iterdir())==[] and generation.manifest['artifacts']=={}
