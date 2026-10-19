"""Synthetic offline captures only; no broker credentials/network/portfolio."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import traceback

import pytest
from connectors.moomoo_rest import ReadRequest, ReadResponse, MoomooRESTConnector, RESTError
from ingest.private_market_store import PrivateMarketStore, MarketStoreError, CaptureTransport, APP_ID, MAX_RAW

OBS = '2026-10-02T00:00:00Z'
ING = '2026-10-02T00:01:00Z'
LATER = '2026-10-03T00:01:00Z'
STAMP = 1790899200000


def snap(**changes):
    return dict({'code':'US.SYN','name':'Synthetic','update_time':STAMP,'data_date':'2026-10-02',
                 'last_price':10.5,'volume':0,'equity_valid':True}, **changes)


def news(**changes):
    return dict({'news_id':'synthetic:1','title':'<em>Synthetic</em> story','url':'https://example.invalid/item',
                 'publish_time':STAMP//1000,'news_type':'POST'}, **changes)


def request(kind='snapshot', codes=None, query='symbol=synthetic&size=10', headers=None):
    if kind=='snapshot':return ReadRequest('POST','/api/v1.0/quote/snapshot','',json.dumps({'code_list':codes or ['US.SYN']}).encode(),headers or {},1)
    return ReadRequest('GET','/api/v1.0/quote/find-news',query,b'',headers or {},1)


def response(rows=None, kind='snapshot', **changes):
    data={'snapshot_list':rows if rows is not None else [snap()]} if kind=='snapshot' else rows if rows is not None else [news()]
    return ReadResponse(200,json.dumps(dict({'ret_code':0,'ret_msg':'success','data':data},**changes),indent=2).encode()+b'\n')


@pytest.fixture
def store(tmp_path):
    return PrivateMarketStore(tmp_path/'private-market',create=True)


def ingest(store, req=None, resp=None, run='run1', observed=OBS, ingested=ING):
    return store.ingest(req or request(),resp or response(),run_id=run,observed_at=observed,ingested_at=ingested,origin='synthetic')


def test_exact_raw_private_schema_and_replay(store):
    resp=response();first=ingest(store,resp=resp)
    assert first.status=='success' and first.added
    assert first.raw_hash==hashlib.sha256(resp.body).hexdigest()
    assert store.raw(first.raw_hash)==resp.body
    assert not ingest(store,resp=resp).added
    assert store.root.stat().st_mode&0o777==0o700
    assert store.database.stat().st_mode&0o777==0o600
    assert (store.raw_dir/(first.raw_hash+'.json')).stat().st_mode&0o777==0o400
    with sqlite3.connect(store.database) as db:
        assert db.execute('PRAGMA application_id').fetchone()[0]==APP_ID
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==1
    row=store.query('snapshot',ING)[0]
    assert row['record']['volume']==0 and row['record']['currency'] is None
    assert row['record']['session'] is row['record']['adjustment'] is None
    assert 'point_observation_not_bar' in row['quality'] and row['observation']['known_ms']==STAMP+60000
    assert repr(store)=='<PrivateMarketStore>' and repr(first)=='<StoredMarketAttempt>'


def test_partial_all_missing_empty_news_and_failed_coverage(store):
    assert ingest(store,req=request(codes=['US.SYN','US.MISSING'])).status=='partial'
    assert ingest(store,resp=response([]),run='empty-snapshot').status=='all-missing'
    assert ingest(store,request('news'),response([],kind='news'),run='empty-news').status=='successful-empty'
    assert ingest(store,resp=ReadResponse(429,b'private-provider-body'),run='failure').status=='failed'
    attempts={row['run_id']:row for row in store.attempts(ING)}
    assert attempts['run1']['missing_codes']==['US.MISSING']
    assert attempts['empty-snapshot']['missing_codes']==['US.SYN']
    assert attempts['failure']['raw_hash'] is None
    assert all(row['unsupported_markets']=={'MY':'unattempted-unsupported'} for row in attempts.values())
    assert len(list(store.raw_dir.iterdir()))==3


def test_semantic_replay_new_observation_and_news_revisions(store):
    ingest(store,request('news'),response(kind='news'))
    ingest(store,request('news',query='symbol=other&size=10'),response(kind='news'),run='other-query',observed=LATER,ingested=LATER)
    rows=store.query('news',LATER);assert len(rows)==2 and {r['revision'] for r in rows}=={1}
    ingest(store,request('news'),response([news(title='Synthetic revision')],kind='news'),run='revision',observed=LATER,ingested=LATER)
    assert {r['revision'] for r in store.query('news',LATER)}=={1,2}
    assert len(store.query('news',ING))==1
    ingest(store,request('news'),response([news(news_id='synthetic:2')],kind='news'),run='equal-headline',observed=LATER,ingested=LATER)
    assert len({r['record']['item_id'] for r in store.query('news',LATER)})==2
    assert store.query('news',ING)[0]['record']['title']=='<em>Synthetic</em> story'


def test_quote_revisions_point_identity_and_future_cutoff(store):
    ingest(store)
    ingest(store,resp=response([snap(last_price=11)]),run='revision',observed=LATER,ingested=LATER)
    assert [r['revision'] for r in store.query('snapshot',LATER)]==[1,2]
    assert [r['record']['price'] for r in store.query('snapshot',ING)]==[10.5]
    ingest(store,resp=response([snap(update_time=STAMP+86400000*2)]),run='future-source')
    assert len(store.query('snapshot',ING))==1
    ingest(store,request('news'),response([news(publish_time=STAMP//1000-86400*20)],kind='news'),run='backfill',observed=LATER,ingested=LATER)
    assert store.query('news',ING)==[]


def test_missing_source_times_modes_and_zero_price(store):
    ingest(store,resp=response([snap(update_time=None,last_price=0)]))
    assert store.query('snapshot',ING)==[]
    row=store.query('snapshot',ING,mode='observation-known')[0]
    assert 'source_time_unknown' in row['quality'] and 'price_unusable' in row['quality']
    assert row['eligible_for_temporal_evidence'] is False
    ingest(store,request('news'),response([news(publish_time=None)],kind='news'),run='unknown-news')
    assert store.query('news',ING)==[]
    assert store.query('news',ING,mode='observation-known')[0]['quality']==['availability_unknown','source_time_unknown']


@pytest.mark.parametrize('rows',[ [snap(last_price=True)], [snap(volume=-1)], [snap(last_price=-1)],
    [snap(last_price=float('nan'))], [snap(last_price=float('inf'))], [snap(volume=1.5)],
    [snap(equity_valid='true')], [snap(update_time=True)], [snap(data_date='2026-02-30')],
    [snap(),snap()], [snap(code='US.UNREQUESTED')], [snap(code='BMS.SYN')]])
def test_invalid_response_is_failed_no_raw_or_versions(store,rows):
    attempt=ingest(store,resp=response(rows))
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert store.query('snapshot',ING)==[] and list(store.raw_dir.iterdir())==[]


@pytest.mark.parametrize('raw',[b'not-json',b'{"ret_code":0,"ret_code":1,"data":[]}',b'\xff',b'x'*(MAX_RAW+1)])
def test_malformed_raw_never_archived(store,raw):
    assert ingest(store,resp=ReadResponse(200,raw)).status=='failed'
    assert list(store.raw_dir.iterdir())==[]


def test_provider_error_and_secret_exclusion(store):
    assert ingest(store,resp=response(ret_code=-1,ret_msg='private-provider-body')).raw_hash is None
    headers={'X-Api-Key':'synthetic-api-key','Authorization':'synthetic-signature','X-Nonce':'synthetic-nonce'}
    for row in [snap(api_key='private'),snap(name='synthetic-api-key'),snap(extra={'headers':{}})]:
        assert ingest(store,request(headers=headers),response([row]),run='secret-'+str(len(store.attempts(ING)))).status=='failed'
    assert list(store.raw_dir.iterdir())==[]
    with store.database.open('rb') as f:data=f.read()
    for secret in [b'private-provider-body',b'synthetic-api-key',b'synthetic-signature',b'synthetic-nonce']:assert secret not in data


def test_capture_before_core_decode_and_no_header_persistence(store):
    original=response(kind='news')
    wrapper=CaptureTransport(store,lambda _:original,run_id='captured',origin='synthetic',observed_clock=lambda:OBS,ingestion_clock=lambda:ING)
    core=MoomooRESTConnector(api_key='synthetic-api-key',signer=lambda _:b'synthetic-signature',transport=wrapper,
        clock_ms=lambda:STAMP,nonce_factory=lambda:'synthetic-nonce')
    result=core.search_news('synthetic');assert result.data[0]['title']==news()['title']
    attempt=store.attempts(ING)[0];assert store.raw(attempt['raw_hash'])==original.body
    assert repr(wrapper)=='<PrivateMarketCapture>'
    assert 'headers' not in json.dumps(attempt) and attempt['origin']=='synthetic'


def test_capture_failed_transport_no_private_context(store):
    def fail(_):raise RuntimeError('private-provider-body')
    wrapped=CaptureTransport(store,fail,run_id='fail',observed_clock=lambda:OBS,ingestion_clock=lambda:ING)
    with pytest.raises(RESTError) as caught:wrapped(request())
    assert caught.value.__context__ is None and 'private-provider-body' not in str(caught.value)
    assert store.attempts(ING)[0]['raw_hash'] is None


def test_integrity_query_verifies_raw_and_rejects_missing(store):
    attempt=ingest(store);path=store.raw_dir/(attempt.raw_hash+'.json')
    path.chmod(0o600);path.write_bytes(b'corrupted');path.chmod(0o400)
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    with pytest.raises(MarketStoreError):store.attempts(ING)
    path.unlink()
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)


def test_readonly_queries_and_immutable_schema(store):
    ingest(store);before=store.database.read_bytes();paths=set(store.root.rglob('*'))
    reopened=PrivateMarketStore(store.root)
    reopened.query('snapshot',ING);reopened.attempts(ING)
    assert store.database.read_bytes()==before and set(store.root.rglob('*'))==paths
    with reopened._connection(readonly=True) as db:
        assert db.execute('PRAGMA query_only').fetchone()[0]==1
    with sqlite3.connect(store.database) as db:
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM attempts')
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE versions SET payload='bad'")


def test_unknown_schema_not_repaired(store):
    with sqlite3.connect(store.database) as db:db.execute('PRAGMA user_version=99')
    before=store.database.read_bytes()
    with pytest.raises(MarketStoreError):PrivateMarketStore(store.root,create=True)
    assert store.database.read_bytes()==before


def test_no_create_on_queries_or_unsafe_storage(tmp_path,store):
    missing=tmp_path/'missing'
    with pytest.raises(MarketStoreError):PrivateMarketStore(missing)
    assert not missing.exists()
    store.root.chmod(0o755)
    with pytest.raises(MarketStoreError):store.query('news',ING)
    store.root.chmod(0o700)
    link=tmp_path/'linked';link.symlink_to(store.root,target_is_directory=True)
    with pytest.raises(MarketStoreError):PrivateMarketStore(link)
    with pytest.raises(MarketStoreError):PrivateMarketStore(tmp_path/'public'/'store',create=True)
    with pytest.raises(MarketStoreError):PrivateMarketStore(store.root,public_roots=[tmp_path])
    with pytest.raises(MarketStoreError):PrivateMarketStore(Path(__file__).resolve().parents[1]/'private-data',create=True)


def test_bounded_lock_orphan_raw_without_partial_database(store):
    ingest(store)
    with sqlite3.connect(store.database) as locked:
        locked.execute('BEGIN IMMEDIATE')
        short=PrivateMarketStore(store.root,lock_timeout=0.01)
        later=response([snap(last_price=11)])
        with pytest.raises(MarketStoreError):ingest(short,resp=later,run='locked')
    assert len(store.attempts(ING))==1 and len(store.query('snapshot',ING))==1
    assert len(list(store.raw_dir.iterdir()))==2 # Explicit orphan; no automatic deletion.


@pytest.mark.parametrize('cutoff',['2026-10-02','2026-10-02T00:00:00','bad',None])
def test_cutoff_requires_aware_time(store,cutoff):
    with pytest.raises(MarketStoreError):store.query('news',cutoff)


def test_invalid_query_and_inputs_fail_no_writes(store):
    for options in [dict(limit=0),dict(limit=1001),dict(limit=True),dict(mode='historical')]:
        with pytest.raises(MarketStoreError):store.query('news',ING,**options)
    with pytest.raises(MarketStoreError):store.query('portfolio',ING)
    with pytest.raises(MarketStoreError):ingest(store,request(codes=['BMS.SYN']))
    with pytest.raises(MarketStoreError):ingest(store,observed=LATER,ingested=ING)
    with pytest.raises(MarketStoreError):ingest(store,run='../secret')
    assert store.attempts(LATER)==[]


def test_fixture_cli_synthetic_only_readonly_and_safe_errors(tmp_path):
    root=tmp_path/'cli';script=Path(__file__).resolve().parents[1]/'scripts/market_ingest.py'
    def cli(*args):return subprocess.run([sys.executable,str(script),'--root',str(root),*args],capture_output=True,text=True)
    assert cli('init').returncode==0
    req=request();resp=response()
    fixture={'schema_version':1,'origin':'synthetic','run_id':'fixture','observed_at':OBS,'ingested_at':ING,
             'method':req.method,'path':req.path,'query':req.query,'request_body_base64':base64.b64encode(req.body).decode(),
             'http_status':200,'response_body_base64':base64.b64encode(resp.body).decode()}
    file=tmp_path/'fixture.json';file.write_text(json.dumps(fixture))
    assert cli('ingest-fixture','--fixture',str(file)).returncode==0
    assert json.loads(cli('query','--kind','snapshot','--cutoff',ING).stdout)[0]['record']['volume']==0
    fixture['origin']='live';file.write_text(json.dumps(fixture))
    result=cli('ingest-fixture','--fixture',str(file));assert result.returncode==1 and str(file) not in result.stderr


def test_exact_semantics_new_raw_observation_and_source_time_uncertainty(store):
    first=ingest(store)
    same=response();compact=ReadResponse(200,json.dumps(json.loads(same.body),separators=(',',':')).encode())
    second=ingest(store,resp=compact,run='other-encoding',observed=LATER,ingested=LATER)
    assert first.raw_hash!=second.raw_hash
    rows=store.query('snapshot',LATER);assert len(rows)==2 and {r['revision'] for r in rows}=={1}
    ingest(store,resp=response([snap(update_time=STAMP+86400000)]),run='future')
    future=[r for r in store.query('snapshot',LATER) if r['record']['quote_time_ms']>STAMP]
    assert future[0]['quality'][-1]=='source_time_after_observation'


def test_unknown_application_id_and_extra_schema_rejected(store):
    with sqlite3.connect(store.database) as db:db.execute('PRAGMA application_id=123')
    with pytest.raises(MarketStoreError):PrivateMarketStore(store.root)


def test_normalized_tampering_detected_against_raw(store):
    from ingest.private_market_store import DDL,canonical,digest
    ingest(store)
    with sqlite3.connect(store.database) as db:
        db.execute('DROP TRIGGER versions_update')
        payload=json.loads(db.execute('SELECT payload FROM versions').fetchone()[0]);payload['price']=999
        changed=canonical(payload)
        db.execute('UPDATE versions SET payload=?,semantic_hash=?',(changed,digest(changed.encode())))
        db.execute(DDL['versions_update'])
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)


def test_symlink_raw_database_and_permissions_rejected(store,tmp_path):
    attempt=ingest(store);p=store.raw_dir/(attempt.raw_hash+'.json');original=p.read_bytes();p.unlink()
    other=tmp_path/'other';other.write_bytes(original);other.chmod(0o400);p.symlink_to(other)
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    p.unlink();p.write_bytes(original);p.chmod(0o400)
    dbbytes=store.database.read_bytes();store.database.unlink();otherdb=tmp_path/'otherdb';otherdb.write_bytes(dbbytes);otherdb.chmod(0o600);store.database.symlink_to(otherdb)
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)


def test_capture_clock_failure_has_no_private_exception_context(store):
    def clock():raise RuntimeError('synthetic-private-clock-secret')
    wrapped=CaptureTransport(store,lambda _:response(),run_id='clock-fail',observed_clock=clock,ingestion_clock=lambda:ING)
    with pytest.raises(MarketStoreError) as caught:wrapped(request())
    assert caught.value.__context__ is None
    assert 'synthetic-private-clock-secret' not in str(caught.value)


def test_source_observation_ingestion_cutoff_and_limits(store):
    ingest(store)
    assert store.query('snapshot',OBS)==[] and store.attempts(OBS)==[]
    assert len(store.query('snapshot','2026-10-02T08:01:00+08:00'))==1
    assert len(store.query('snapshot',LATER,limit=1))==1
    with pytest.raises(MarketStoreError):store.attempts(ING,limit=True)


def test_failed_paths_do_not_log_or_leak_provider_content(store,capsys):
    attempt=ingest(store,resp=ReadResponse(503,b'synthetic-private-provider-body'))
    assert attempt.raw_hash is None
    result=capsys.readouterr();assert result.out==result.err==''


def test_wal_and_hot_journal_queries_reject_without_side_effects(store):
    ingest(store)
    with sqlite3.connect(store.database) as db:db.execute('PRAGMA journal_mode=WAL')
    before={p:p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    assert {p:p.read_bytes() for p in store.root.rglob('*') if p.is_file()}==before


def test_unsafe_storage_ingestion_cannot_archive_first(store):
    store.root.chmod(0o755)
    with pytest.raises(MarketStoreError):ingest(store)
    assert list(store.raw_dir.iterdir())==[]


@pytest.mark.parametrize('extra',[{'privateKey':'synthetic-private'}, {'AccountId':'synthetic-account'},
    {'img_url':'https://user:pass@example.invalid/image'}, {'img_url':'https://example.invalid/image?accessToken=private'}])
def test_secret_key_variants_and_private_urls_discarded(store,extra):
    assert ingest(store,resp=response([snap(**extra)])).raw_hash is None
    assert list(store.raw_dir.iterdir())==[]


def test_existing_journal_never_recovered_by_query(store):
    ingest(store)
    journal=Path(str(store.database)+'-journal');journal.write_bytes(b'synthetic-journal');journal.chmod(0o600)
    before=store.database.read_bytes()
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    assert store.database.read_bytes()==before and journal.read_bytes()==b'synthetic-journal'


def test_submillisecond_cutoff_cannot_leak_later_ingestion(store):
    ingest(store,observed='2026-10-02T00:00:00.000100Z',ingested='2026-10-02T00:01:00.000900Z')
    assert store.query('snapshot','2026-10-02T00:01:00.000100Z')==[]
    assert store.attempts('2026-10-02T00:01:00.000100Z')==[]
    assert len(store.query('snapshot','2026-10-02T00:01:00.001000Z'))==1


def test_submillisecond_ingestion_order_not_hidden_by_rounding(store):
    with pytest.raises(MarketStoreError):
        ingest(store,observed='2026-10-02T00:00:00.000900Z',ingested='2026-10-02T00:00:00.000100Z')
    assert store.attempts(ING)==[]


@pytest.mark.parametrize('timestamp',[
    '2026-10-02T00:01:00.000000100Z',
    '2026-10-02T00:01:00.000000900Z',
    '2026-10-02T00:01:00.0000001+00:00',
    '2026-10-02T00:01:00+00:00:00.5',
    '2026-10-02T00:01:00+01:30.5',
    '2026-10-02T00:01:00+01:99',
    '20261002T000100Z',
    '2026-10-02 00:01:00Z',
    '2026-10-02T00:01Z',
    '2026-10-02T00:01:00,123Z',
])
def test_explicit_timestamp_grammar_rejects_unsupported_cutoffs(store,timestamp):
    ingest(store)
    with pytest.raises(MarketStoreError):store.query('snapshot',timestamp)
    with pytest.raises(MarketStoreError):store.attempts(timestamp)


def test_nanosecond_capture_and_reversed_ingestion_rejected(store):
    with pytest.raises(MarketStoreError):
        ingest(store,observed=OBS,ingested='2026-10-02T00:01:00.000000900Z')
    with pytest.raises(MarketStoreError):
        ingest(store,observed='2026-10-02T00:00:00.000000900Z',ingested='2026-10-02T00:00:00.000000100Z')
    assert store.attempts(ING)==[] and list(store.raw_dir.iterdir())==[]


@pytest.mark.parametrize('timestamp',[
    '2026-10-02T00:00:00+00:00:00.5',
    '2026-10-02T00:00:00+08:00.5',
    '2026-10-02T00:00:00.1234567Z',
])
def test_unsupported_observation_offset_and_precision_no_archive(store,timestamp):
    with pytest.raises(MarketStoreError):ingest(store,observed=timestamp,ingested=LATER)
    assert store.attempts(LATER)==[] and list(store.raw_dir.iterdir())==[]


def test_six_digit_precision_and_conventional_offsets_supported(store):
    ingest(store,observed='2026-10-02T05:30:00.000100+05:30',ingested='2026-10-01T20:01:00.000900-04:00')
    assert store.query('snapshot','2026-10-02T00:01:00.000899Z')==[]
    assert len(store.query('snapshot','2026-10-02T08:01:00.001000+08:00'))==1
    attempt=store.attempts(LATER)[0]
    assert attempt['observed_at']=='2026-10-02T05:30:00.000100+05:30'
    assert attempt['ingested_at']=='2026-10-01T20:01:00.000900-04:00'


def test_nano_reversed_order_independently_rejected(store):
    with pytest.raises(MarketStoreError):
        ingest(store,observed='2026-10-02T00:00:00.000000900Z',ingested='2026-10-02T00:00:00.000000100Z')
    assert store.attempts(ING)==[]


def test_strict_rows_still_require_temporal_eligibility_filter(store):
    ingest(store,resp=response([snap(last_price=0)]))
    ingest(store,resp=response([snap(update_time=STAMP+1000)]),run='future-observed')
    rows=store.query('snapshot',ING)
    assert len(rows)==2 and all(row['eligible_for_temporal_evidence'] is False for row in rows)
    assert 'price_unusable' in rows[0]['quality']
    assert 'source_time_after_observation' in rows[1]['quality']


def test_bounded_limits_are_not_complete_coverage(store):
    ingest(store)
    ingest(store,run='second')
    assert len(store.query('snapshot',ING,limit=1))==1
    assert len(store.query('snapshot',ING))==2
    assert len(store.attempts(ING,limit=1))==1 and len(store.attempts(ING))==2


@pytest.mark.parametrize('count',[1,30])
def test_finite_auxiliary_history_preserves_complete_core_quotes(store,count):
    codes=[f'US.SYN{i}' for i in range(count)]
    rows=[snap(code=code,lowest_history_price=-0.5,highest_history_price=20.5) for code in codes]
    original=response(rows)
    attempt=ingest(store,req=request(codes=codes),resp=original)
    assert attempt.status=='success' and store.attempts(ING)[0]['missing_codes']==[]
    assert store.raw(attempt.raw_hash)==original.body
    records=store.query('snapshot',ING)
    assert len(records)==count and {r['record']['code'] for r in records}==set(codes)
    assert all(r['record']['price']==10.5 and r['record']['adjustment'] is None for r in records)


@pytest.mark.parametrize('field',['last_price','open_price','high_price','low_price',
                                 'prev_close_price','volume','turnover','turnover_rate'])
@pytest.mark.parametrize('bad',[-1,True,None,'invalid'])
def test_auxiliary_history_never_relaxes_core_field_validation(store,field,bad):
    original=response([snap(lowest_history_price=-0.5,**{field:bad})])
    if field=='prev_close_price' and bad is None:
        # V2 explicitly treats an optional null previous close as missing; V1 remains strict.
        from ingest.private_market_store import normalized
        with pytest.raises(MarketStoreError):normalized(original.body,'snapshot',{'codes':['US.SYN']},version=1)
        assert ingest(store,resp=original).status=='success'
        assert store.query('snapshot',ING)[0]['record']['provider_prev_close'] is None
        return
    attempt=ingest(store,resp=original)
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert store.query('snapshot',ING)==[] and list(store.raw_dir.iterdir())==[]


@pytest.mark.parametrize('extra',[{'lowest_history_price':float('nan')},
                                  {'lowest_history_price':float('inf')},
                                  {'extra':{'historical_price':float('-inf')}},
                                  {'extra':{'api_key':'synthetic-private'}},
                                  {'lowest_history_price':'synthetic-api-key'}])
def test_auxiliary_history_retains_recursive_finite_and_secret_screening(store,extra):
    headers={'X-Api-Key':'synthetic-api-key'}
    attempt=ingest(store,req=request(headers=headers),resp=response([snap(**extra)]))
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert store.query('snapshot',ING)==[] and list(store.raw_dir.iterdir())==[]


def append_frozen_v1_fixture(store,*,version=None):
    """Build an old append-only record fixture, never modify an existing row."""
    from ingest.private_market_store import canonical,digest,normalized,aware_ms
    raw=response([snap(prev_close_price=9.5)]).body
    raw_hash=digest(raw);store._archive(raw,raw_hash)
    expected={'provider':'moomoo-rest','code':'US.SYN','quote_time_ms':STAMP,'market_date':'2026-10-02',
              'price':10.5,'volume':0,'currency':None,'session':None,'adjustment':None,
              'source_timezone':'UTC','market_timezone':None,'validity':{'equity_valid':True}}
    identity=canonical(['moomoo-rest','US.SYN',STAMP]);payload=canonical(expected)
    assert normalized(raw,'snapshot',{'codes':['US.SYN']},version=1)==[(identity,payload,STAMP)]
    meta={'origin':'synthetic','capture_authenticity':'caller-supplied-unverified','provider':'moomoo-rest',
          'run_id':'legacy','kind':'snapshot','query':{'codes':['US.SYN']},'observed_at':OBS,'ingested_at':ING,
          'observed_ms':aware_ms(OBS,True),'ingested_ms':aware_ms(ING,True),'known_ms':aware_ms(ING,True),
          'raw_hash':raw_hash,'status':'success','reason':None,'missing_codes':[],
          'unsupported_markets':{'MY':'unattempted-unsupported'},'record_count':1,'rights_status':'unconfirmed',
          'connector':'moomoo-rest-capture','endpoint':'/api/v1.0/quote/snapshot'}
    if version is not None:meta['normalization_version']=version
    aid=digest(canonical(meta).encode());semantic=digest(payload.encode())
    with store._connection() as db:
        db.execute('INSERT INTO runs VALUES (?,?)',('legacy','moomoo-rest'))
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?)',(aid,'legacy','snapshot',aware_ms(ING,True),canonical(meta)))
        vid=db.execute('INSERT INTO versions(kind,identity,semantic_hash,revision,payload,source_ms) VALUES (?,?,?,?,?,?)',
                       ('snapshot',identity,semantic,1,payload,STAMP)).lastrowid
        db.execute('INSERT INTO observations VALUES (?,?,?)',(aid,vid,0))
    return aid,semantic,payload


def test_frozen_v1_hash_replay_and_v2_append_dedup_without_rewrite(store):
    from ingest.private_market_store import digest
    aid,semantic,payload=append_frozen_v1_fixture(store)
    with store._connection(readonly=True) as db:
        before=[tuple(row) for row in db.execute('SELECT * FROM versions')]
        old_attempt=tuple(db.execute('SELECT * FROM attempts WHERE id=?',(aid,)).fetchone())
    old=store.query('snapshot',ING)[0]
    assert old['semantic_hash']==semantic==digest(payload.encode())
    assert 'normalization_version' not in old['record'] and 'provider_prev_close' not in old['record']
    assert store.select_snapshots('legacy',ING,['US.SYN'])['quotes']['US.SYN']['quote']['prior_close'] is None
    original=response([snap(prev_close_price=9.5)])
    fresh=ingest(store,resp=original,run='legacy')
    assert fresh.added and fresh.attempt_id!=aid
    assert not ingest(store,resp=original,run='legacy').added
    with store._connection(readonly=True) as db:
        assert [tuple(row) for row in db.execute('SELECT * FROM versions WHERE revision=1')]==before
        assert tuple(db.execute('SELECT * FROM attempts WHERE id=?',(aid,)).fetchone())==old_attempt
        assert db.execute('PRAGMA user_version').fetchone()[0]==1
    records=store.query('snapshot',ING)
    assert len(records)==2 and records[1]['semantic_hash']!=semantic
    assert records[1]['record']['provider_prev_close']==9.5 and records[1]['record']['normalization_version']==2
    assert {m.get('normalization_version',1) for m in store.attempts(ING)}=={1,2}
    # Same source time across differing versions stays conservatively conflicting.
    assert store.select_snapshots('legacy',ING,['US.SYN'])['quotes']['US.SYN']['quote'] is None


@pytest.mark.parametrize('version',[True,False,0,3,'2',2.0])
def test_replay_rejects_unknown_or_boolean_version_even_with_valid_metadata_hash(store,version):
    append_frozen_v1_fixture(store,version=version)
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    with pytest.raises(MarketStoreError):store.select_snapshots('legacy',ING,['US.SYN'])


def test_metadata_version_cannot_reinterpret_v1_payload(store):
    append_frozen_v1_fixture(store,version=2)
    with pytest.raises(MarketStoreError):store.query('snapshot',ING)
    with pytest.raises(MarketStoreError):store.select_snapshots('legacy',ING,['US.SYN'])


@pytest.mark.parametrize('previous',[None,0,9.5])
def test_new_snapshot_optional_previous_close(store,previous):
    assert ingest(store,resp=response([snap(prev_close_price=previous)])).status=='success'
    row=store.query('snapshot',ING)[0]
    assert row['record']['provider_prev_close']==previous and row['observation']['normalization_version']==2


@pytest.mark.parametrize('previous',[-1,True,'9',float('nan'),float('inf')])
def test_new_snapshot_invalid_previous_close_rejected(store,previous):
    attempt=ingest(store,resp=response([snap(prev_close_price=previous)]))
    assert attempt.status=='failed' and attempt.raw_hash is None and list(store.raw_dir.iterdir())==[]


def test_v2_replay_does_not_backdate_new_known_time(store):
    ingest(store,resp=response([snap(prev_close_price=9)]),observed=OBS,ingested=LATER)
    assert store.query('snapshot',ING)==[]
    assert store.select_snapshots('run1',ING,['US.SYN'])['coverage']['selected']['count']==0
    assert store.query('snapshot',LATER)[0]['record']['provider_prev_close']==9


@pytest.mark.parametrize('stamp,zone,market_date', [
    (1779271199999,840,20260520),(1779271200000,840,20260521),
    (1779278399999,-720,20260519),(1779278400000,-720,20260520),
    (1779235199999,0,20260519),(1779235200000,0,20260520),
    (1779288300123,-240,20260520),(0,-720,19691231),
])
def test_history_store_preserves_consistent_millisecond_local_dates(store,stamp,zone,market_date):
    req=ReadRequest('GET','/api/v1.0/quote/US.SYN/history-kline',
                    'end=2026-05-23&ktype=2&autype=0&num=100',b'',{},1)
    row={'time_key':stamp,'date':market_date,'time_zone':zone,'close':12.5}
    resp=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}).encode())
    attempt=ingest(store,req=req,resp=resp)
    assert attempt.status=='success' and attempt.raw_hash==hashlib.sha256(resp.body).hexdigest()
    records=store.query('history',ING)
    assert len(records)==1 and records[0]['source_ms']==stamp
    assert records[0]['record']['date']==f'{market_date//10000:04d}-{market_date//100%100:02d}-{market_date%100:02d}'
    assert records[0]['record']['time_zone']==zone and records[0]['record']['close']==12.5
    assert store.raw(attempt.raw_hash)==resp.body


@pytest.mark.parametrize('stamp,zone,market_date', [
    (1779249600000,-240,20260521),
    (1779271199999,840,20260521),(1779271200000,840,20260520),
    (1779278399999,-720,20260520),(1779278400000,-720,20260519),
    (2**63-1,0,20260520),
])
def test_history_store_rejects_local_date_mismatch_and_overflow(store,stamp,zone,market_date):
    from ingest.private_market_store import normalized,request_meta
    req=ReadRequest('GET','/api/v1.0/quote/US.SYN/history-kline',
                    'end=2026-05-23&ktype=2&autype=0&num=100',b'',{},1)
    row={'time_key':stamp,'date':market_date,'time_zone':zone,'close':12.5}
    resp=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}).encode())
    kind,query,_=request_meta(req)
    with pytest.raises(MarketStoreError) as error:normalized(resp.body,kind,query,version=3)
    assert str(error.value)=='invalid-response'
    attempt=ingest(store,req=req,resp=resp)
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert store.query('history',ING)==[] and list(store.raw_dir.iterdir())==[]
    assert store.attempts(ING)[0]['record_count']==0


# PRSG-94 authored synthetic stage matrix; no provider captures.
def diagnostic_history_body(row=None, **outer):
    row = {'time_key': STAMP, 'date': 20261001, 'time_zone': -240, 'close': 10} if row is None else row
    return json.dumps({'ret_code': 0, 'ret_msg': 'SYNTHETIC-BODY-CANARY',
                       'data': {'kline_list': [row]}, **outer}).encode()


def diagnostic_history_request():
    return ReadRequest('GET', '/api/v1.0/quote/US.SYN/history-kline',
                       'end=2026-10-02&ktype=2&autype=0&num=100', b'', {}, 1)


def diagnostic_cases():
    row = {'time_key': STAMP, 'date': 20261001, 'time_zone': -240, 'close': 10}
    cases = [(b'\xff', 'decode-screen'), (b'{', 'decode-screen'),
             (b'{"x":1,"x":2}', 'decode-screen'), (b'{"x":NaN}', 'decode-screen'),
             (b'{"x":Infinity}', 'decode-screen')]
    for extra in ({'token': 'SYNTHETIC-CREDENTIAL-CANARY'},
                  {'x': {'account_id': 'SYNTHETIC-CREDENTIAL-CANARY'}},
                  {'x': 'https://user:password@example.invalid/'},
                  {'x': 'https://example.invalid/?token=canary'},
                  {'x': '-----BEGIN SYNTHETIC'}, {'x': 'SYNTHETIC-CREDENTIAL-CANARY'}):
        cases.append((diagnostic_history_body(**extra), 'decode-screen'))
    for outer,stage in (({'ret_code': True},'envelope-ret-code-type'),
                  ({'ret_msg': 3},'envelope-ret-msg-type'), ({'pagination': {}},'envelope-root-fields'),
                  ({'data': []},'envelope-data-type'),
                  ({'data': {'kline_list': [], 'extra': 1}},'envelope-data-fields'),
                  ({'data': {'kline_list': [], 'next_time': True}},'envelope-next-time'),
                  ({'data': {'kline_list': [], 'volume_precision': 19}},'envelope-volume-precision')):
        cases.append((diagnostic_history_body(**outer), stage))
    cases += [(b'[]', 'envelope-root-type'), (b'{"ret_code":0}', 'envelope-root-fields'),
              (diagnostic_history_body(ret_code=1234567, data=None), 'provider-rejection'),
              (diagnostic_history_body(ret_code=1234567, ret_msg=False), 'envelope-ret-msg-type')]
    for missing in ({'date'}, {'time_key'}, {'time_zone'}, {'date', 'time_key', 'time_zone'}):
        cases.append((diagnostic_history_body({k:v for k,v in row.items() if k not in missing}), 'metadata-missing'))
    for change in ({'date': None}, {'date': True}, {'date': '20261001'}, {'date': 20260230},
                   {'time_key': -1}, {'time_key': True}, {'time_key': 2**63-1},
                   {'time_zone': None}, {'time_zone': 'UTC'}, {'time_zone': -721}, {'time_zone': 841}):
        cases.append((diagnostic_history_body({**row, **change}), 'metadata-invalid'))
    cases.append((diagnostic_history_body({**row, 'date': 20261002}), 'date-relation'))
    for data in ({'kline_list': None}, {'kline_list': [0]}, {'kline_list': [row]*101},
                 {'kline_list': [row, row]}, {'kline_list': [{**row, 'close': None}]},
                 {'kline_list': [{**row, 'close': 0}]}, {'kline_list': [{**row, 'close': -1}]},
                 {'kline_list': [{k:v for k,v in row.items() if k!='close'}]},
                 {'kline_list': [{**row, 'date': 20261003, 'time_key': STAMP+2*86400000}]}):
        cases.append((diagnostic_history_body(data=data), 'history-rows'))
    return cases


@pytest.mark.parametrize('raw,stage', diagnostic_cases())
def test_history_trusted_stages_generic_errors_and_store_disposal(raw, stage, store):
    from ingest.private_market_store import normalized, request_meta
    req = diagnostic_history_request();kind, query, _ = request_meta(req)
    with pytest.raises(MarketStoreError) as caught:
        normalized(raw, kind, query, ('SYNTHETIC-CREDENTIAL-CANARY',), version=3)
    assert str(caught.value) == 'invalid-response' and caught.value.diagnostic_stage == stage
    assert 'CANARY' not in str(caught.value) and 'CANARY' not in repr(caught.value)
    # Direct store ingestion also rejects all non-known-secret failures without archiving.
    if b'SYNTHETIC-CREDENTIAL-CANARY' in raw and b'"x": "SYNTHETIC-CREDENTIAL-CANARY"' in raw:
        req = ReadRequest(req.method, req.path, req.query, req.body,
                          {'X-API-Key': 'SYNTHETIC-CREDENTIAL-CANARY'}, req.timeout)
    attempt = store.ingest(req, ReadResponse(200, raw), run_id='synthetic-stage',
                           observed_at=OBS, ingested_at=ING, origin='synthetic', normalization_version=3)
    assert attempt.status == 'failed' and attempt.raw_hash is None
    assert not list(store.raw_dir.iterdir()) and store.query('history', ING) == []
    meta = store.attempts(ING)[0]
    assert meta['reason']=='invalid-response' and meta['normalization_version']==3
    assert 'diagnostic_stage' not in meta


@pytest.mark.parametrize('zone', [-720, 0, 840])
@pytest.mark.parametrize('delta', [-1, 0, 1, 123456])
def test_history_diagnostic_local_boundaries_remain_accepted(zone, delta):
    from datetime import date, timedelta
    from ingest.private_market_store import normalized, request_meta
    stamp = STAMP-zone*60000+delta
    local = date(1970,1,1)+timedelta(days=(stamp+zone*60000)//86400000)
    row = {'time_key':stamp,'date':int(local.strftime('%Y%m%d')),'time_zone':zone,'close':10}
    kind, query, _ = request_meta(diagnostic_history_request())
    assert len(normalized(diagnostic_history_body(row), kind, query, version=3))==1


def test_nonhistory_generic_error_and_controlled_annotation_allowlist():
    from ingest.private_market_store import normalized, request_meta
    kind, query, _ = request_meta(request())
    with pytest.raises(MarketStoreError) as caught:normalized(b'{', kind, query)
    assert str(caught.value)=='invalid-response' and caught.value.diagnostic_stage is None
    for stage in ([], {}, 'SYNTHETIC-PRIVATE-PATH', 'x'*5000):
        assert MarketStoreError('invalid-response', diagnostic_stage=stage).diagnostic_stage is None


@pytest.mark.parametrize('row,stage', [
    ({'date':False,'close':0}, 'metadata-missing'),
    ({'time_key':STAMP,'date':20261002,'time_zone':-240,'close':0}, 'date-relation'),
    ({'time_key':STAMP,'date':20260230,'time_zone':-240,'close':0}, 'metadata-invalid')])
def test_history_stage_first_guard_and_single_decode(row,stage,monkeypatch):
    from ingest import private_market_store as module
    calls=[];original=module.decode
    def counted(*a,**k):calls.append(1);return original(*a,**k)
    monkeypatch.setattr(module,'decode',counted)
    kind, query, _ = module.request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:
        module.normalized(diagnostic_history_body(row),kind,query,version=3)
    assert caught.value.diagnostic_stage==stage and len(calls)==1


@pytest.mark.parametrize('outer,stage',[
 ({'pagination':{},'ret_code':True,'ret_msg':False,'data':None},'envelope-root-fields'),
 ({'ret_code':True,'ret_msg':False,'data':None},'envelope-ret-code-type'),
 ({'ret_code':1234567,'ret_msg':False,'data':None},'envelope-ret-msg-type'),
 ({'ret_code':1234567,'data':None},'provider-rejection'),
 ({'data':None},'envelope-data-type'),
 ({'data':{'next_time':True,'volume_precision':19}},'envelope-data-fields'),
 ({'data':{'kline_list':None,'extra':1,'next_time':True}},'envelope-data-fields'),
 ({'data':{'kline_list':None,'next_time':True,'volume_precision':19}},'envelope-next-time'),
 ({'data':{'kline_list':None,'next_time':0,'volume_precision':19}},'envelope-volume-precision'),
 ({'data':{'kline_list':None,'next_time':0,'volume_precision':18}},'history-rows'),
])
def test_envelope_first_failure_and_single_decode(outer,stage,monkeypatch):
    from ingest import private_market_store as module
    original=module.decode;calls=[]
    def counted(*a,**k):calls.append(1);return original(*a,**k)
    monkeypatch.setattr(module,'decode',counted)
    kind,query,_=module.request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:module.normalized(diagnostic_history_body(**outer),kind,query,version=3)
    assert caught.value.diagnostic_stage==stage and len(calls)==1
    assert str(caught.value)=='invalid-response' and 'CANARY' not in repr(caught.value)


@pytest.mark.parametrize('field,value,stage',[
 ('next_time',-1,'envelope-next-time'),('next_time',2**63,'envelope-next-time'),
 ('next_time',1.0,'envelope-next-time'),('next_time',None,'envelope-next-time'),
 ('next_time','0','envelope-next-time'),('volume_precision',-1,'envelope-volume-precision'),
 ('volume_precision',True,'envelope-volume-precision'),('volume_precision',18.0,'envelope-volume-precision'),
 ('volume_precision',None,'envelope-volume-precision'),('volume_precision','0','envelope-volume-precision'),
])
def test_envelope_scalars_keep_exact_original_bounds(field,value,stage):
    from ingest.private_market_store import normalized,request_meta
    kind,query,_=request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:
        normalized(diagnostic_history_body(data={'kline_list':[],field:value}),kind,query,version=3)
    assert caught.value.diagnostic_stage==stage


@pytest.mark.parametrize('next_time',[0,2**63-1])
@pytest.mark.parametrize('precision',[0,18])
def test_envelope_valid_scalar_boundaries_still_accept(next_time,precision):
    from ingest.private_market_store import normalized,request_meta
    kind,query,_=request_meta(diagnostic_history_request())
    assert normalized(diagnostic_history_body(data={'kline_list':[],'next_time':next_time,'volume_precision':precision}),
                      kind,query,version=3)==[]


@pytest.mark.parametrize('raw',[b'x'*(MAX_RAW+1),b'{"ret_code":0,"ret_code":1}',
    b'{"ret_code":0,"ret_msg":"SYNTHETIC-CREDENTIAL-CANARY","data":null}',
    b'{"ret_code":0,"ret_msg":false,"data":{"kline_list":[NaN]}}'])
def test_envelope_detail_never_bypasses_decode_or_secret_screen(raw):
    from ingest.private_market_store import normalized,request_meta
    kind,query,_=request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:normalized(raw,kind,query,('SYNTHETIC-CREDENTIAL-CANARY',),version=3)
    assert caught.value.diagnostic_stage=='decode-screen' and 'CANARY' not in repr(caught.value)


@pytest.mark.parametrize('kind',['snapshot','news'])
def test_nonhistory_envelope_errors_still_have_no_stage(kind):
    from ingest.private_market_store import normalized,request_meta
    actual,query,_=request_meta(request(kind))
    with pytest.raises(MarketStoreError) as caught:normalized(b'{"ret_code":true,"ret_msg":false,"data":null}',actual,query)
    assert str(caught.value)=='invalid-response' and caught.value.diagnostic_stage is None


# PRSG-106 documented-shape fixtures only; no real provider capture.
def documented_history(**root):
    return diagnostic_history_body(pagination={'has_more':False,'total':1},extra={'next_time':0},**root)


@pytest.mark.parametrize('optional',[{}, {'pagination':{'has_more':True}}, {'extra':{'next_time':2**63-1}},
    {'pagination':{'has_more':False,'total':0},'extra':{'next_time':0}}])
def test_v4_documented_shape_and_unchanged_old_versions(optional):
    from ingest.private_market_store import normalized,request_meta
    kind,query,_=request_meta(diagnostic_history_request());raw=diagnostic_history_body(**optional)
    actual=normalized(raw,kind,query,version=4)
    baseline=normalized(diagnostic_history_body(),kind,query,version=3)
    assert actual==baseline
    for version in (1,2,3):
        if optional:
            with pytest.raises(MarketStoreError) as caught:normalized(raw,kind,query,version=version)
            assert caught.value.diagnostic_stage=='envelope-root-fields'
            assert caught.value.diagnostic_structure is None
        else:assert normalized(raw,kind,query,version=version)==baseline


@pytest.mark.parametrize('outer,stage',[
 ({'pagination':None},'envelope-pagination'),({'pagination':[]},'envelope-pagination'),
 ({'pagination':{}},'envelope-pagination'),({'pagination':{'has_more':1}},'envelope-pagination'),
 ({'pagination':{'has_more':True,'next_key':'CANARY'}},'envelope-pagination'),
 ({'pagination':{'has_more':False,'total':True}},'envelope-pagination'),
 ({'pagination':{'has_more':False,'total':-1}},'envelope-pagination'),
 ({'pagination':{'has_more':False,'total':2**63}},'envelope-pagination'),
 ({'pagination':{'has_more':False,'total':1.0}},'envelope-pagination'),
 ({'extra':None},'envelope-extra'),({'extra':{}},'envelope-extra'),
 ({'extra':{'next_time':True}},'envelope-extra'),({'extra':{'next_time':-1}},'envelope-extra'),
 ({'extra':{'next_time':2**63}},'envelope-extra'),({'extra':{'next_time':'0'}},'envelope-extra'),
 ({'extra':{'next_time':0,'other':0}},'envelope-extra'),
 ({'data':{'kline_list':[],'next_time':0},'extra':{'next_time':1}},'envelope-cursor-conflict'),
 ({'code':0},'envelope-root-fields'),({'error':{'code':1234567}},'envelope-root-fields'),
 ({'s':'ok','d':[]},'envelope-root-fields'),
 ({'ret_code':1234567,'pagination':None},'provider-rejection'),
 ({'data':{'kline_list':[],'next_time':True},'pagination':None},'envelope-next-time'),
])
def test_v4_malformed_documented_metadata_and_no_aliases(outer,stage,store):
    from ingest.private_market_store import normalized,request_meta,valid_structure
    req=diagnostic_history_request();kind,query,_=request_meta(req);raw=diagnostic_history_body(**outer)
    with pytest.raises(MarketStoreError) as caught:normalized(raw,kind,query,version=4)
    assert caught.value.diagnostic_stage==stage and valid_structure(caught.value.diagnostic_structure)
    assert caught.value.diagnostic_structure['status']=='available'
    failed=store.ingest(req,ReadResponse(200,raw),run_id='synthetic-v4',observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert failed.status=='failed' and failed.raw_hash is None and not list(store.raw_dir.iterdir())
    assert store.attempts(ING)[0]['normalization_version']==4
    assert 'diagnostic_structure' not in store.attempts(ING)[0]


def test_v4_equal_cursors_and_empty_rows_do_not_claim_window(store):
    from ingest.private_market_store import normalized,request_meta
    req=diagnostic_history_request();kind,query,_=request_meta(req)
    raw=diagnostic_history_body(data={'kline_list':[],'next_time':0,'volume_precision':18},
                              pagination={'has_more':True,'total':999999},extra={'next_time':0})
    assert normalized(raw,kind,query,version=4)==[]
    result=store.ingest(req,ReadResponse(200,raw),run_id='synthetic-empty',observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert result.status=='all-missing' and store.attempts(ING)[0]['record_count']==0
    assert store.raw(result.raw_hash)==raw


def test_v3_and_v4_store_metadata_replay_preserves_raw_shape(store):
    req=diagnostic_history_request();old=diagnostic_history_body();new=documented_history()
    first=store.ingest(req,ReadResponse(200,old),run_id='synthetic-old',observed_at=OBS,ingested_at=ING,
                       origin='synthetic',normalization_version=3)
    frozen=store.attempts(ING)[0]
    second=store.ingest(req,ReadResponse(200,new),run_id='synthetic-new',observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert first.status==second.status=='success'
    assert store.raw(first.raw_hash)==old and store.raw(second.raw_hash)==new
    assert frozen in store.attempts(ING)
    assert {v['normalization_version'] for v in store.attempts(ING)}=={3,4}
    assert store.query('history',ING)[0]['record']['close']==10


@pytest.mark.parametrize('missing',['date','time_key','time_zone'])
def test_v4_never_infers_row_metadata(missing):
    from ingest.private_market_store import normalized,request_meta
    body=json.loads(documented_history());del body['data']['kline_list'][0][missing]
    kind,query,_=request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:normalized(json.dumps(body).encode(),kind,query,version=4)
    assert caught.value.diagnostic_stage=='metadata-missing'
    assert caught.value.diagnostic_structure['first_row']['fields'][missing]=='absent'


@pytest.mark.parametrize('raw',[b'{',b'x'*(MAX_RAW+1),b'{"a":1,"a":2}',b'{"a":NaN}',
    b'{"ret_code":0,"ret_msg":"SYNTHETIC-CREDENTIAL-CANARY","data":{}}'])
def test_v4_screen_failure_structure_unavailable(raw):
    from ingest.private_market_store import normalized,request_meta
    kind,query,_=request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:normalized(raw,kind,query,('SYNTHETIC-CREDENTIAL-CANARY',),version=4)
    assert caught.value.diagnostic_stage=='decode-screen'
    assert caught.value.diagnostic_structure=={'schema_version':1,'status':'unavailable'}


@pytest.mark.parametrize('unknown',['private_uuid_1234','MixedCaseName','x'*65,'路径','field-PRIVATE-CANARY'])
def test_structure_fixed_labels_no_arbitrary_key_names_or_values(unknown):
    from ingest.private_market_store import normalized,request_meta
    raw=diagnostic_history_body(**{unknown:'BODY-VALUE-CANARY','code':1234567,'error':{'code':-1234567}})
    kind,query,_=request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:normalized(raw,kind,query,version=4)
    structure=caught.value.diagnostic_structure;encoded=json.dumps(structure)
    assert unknown not in encoded and 'CANARY' not in encoded and '1234567' not in encoded
    assert structure['root']['fields']['code']=='int' and structure['root']['fields']['error']=='object'
    assert structure['root']['unexpected_fields']=='present'
    assert sum(len(part['fields']) for key,part in structure.items() if key not in ('schema_version','status'))==17


@pytest.mark.parametrize('kind',['snapshot','news'])
def test_v4_history_only(kind):
    from ingest.private_market_store import normalized,request_meta
    actual,query,_=request_meta(request(kind))
    with pytest.raises(MarketStoreError):normalized(response(kind=kind).body,actual,query,version=4)


def my_history_request(query='end=2026-10-02&ktype=2&autype=0&num=100',code='BMS.1155'):
    return ReadRequest('GET',f'/api/v1.0/quote/{code}/history-kline',query,b'',{},1)


@pytest.mark.parametrize('stamp,market_date',[(STAMP-8*3600000-1,20261001),(STAMP-8*3600000,20261002)])
def test_exact_malaysia_candidate_keeps_raw_identity_offset_and_unconfirmed_admission(store,stamp,market_date):
    row={'time_key':stamp,'date':market_date,'time_zone':480,'close':12.5}
    resp=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}).encode())
    attempt=ingest(store,req=my_history_request(),resp=resp)
    assert attempt.status=='success'
    record=store.query('history',ING)[0];meta=record['observation']
    assert record['record']['code']=='BMS.1155' and record['record']['time_zone']==480
    assert record['record']['adjustment']==0 and record['source_ms']==stamp
    assert not {'currency','market_timezone','settled_at'}&record['record'].keys()
    assert meta['rights_status']=='unconfirmed'
    assert meta['unsupported_markets']=={'MY':'other-instruments-unattempted-unsupported'}
    assert store.raw(attempt.raw_hash)==resp.body


@pytest.mark.parametrize('code,query',[
    ('BMS.1156','end=2026-10-02&ktype=2&autype=0&num=100'),
    ('MY.1155','end=2026-10-02&ktype=2&autype=0&num=100'),
    ('BMS.1155','end=2026-10-02&ktype=2&autype=1&num=100'),
    ('BMS.1155','start=2026-10-01&end=2026-10-02&ktype=2&autype=0&num=100'),
    ('BMS.1155','end=2026-10-02&ktype=2&autype=0&num=99'),
    ('BMS.1155','%65nd=2026-10-02&ktype=2&autype=0&num=100'),
    ('BMS.1155','end=2026-10-02&ktype=2&autype=0&num=100&num=100'),
])
def test_store_malaysia_route_is_literal_raw_end_only(code,query):
    from ingest.private_market_store import request_meta
    with pytest.raises(MarketStoreError):request_meta(my_history_request(query,code))


@pytest.mark.parametrize('case',['date-mismatch','future-end','duplicate','nonfinite','secret','wrong-type'])
def test_malaysia_history_invalid_response_has_no_raw_or_records(store,case):
    row={'time_key':STAMP-8*3600000,'date':20261002,'time_zone':480,'close':12.5}
    rows=[row]
    if case=='date-mismatch':row['date']=20261001
    elif case=='future-end':row.update(time_key=STAMP+2*86400000,date=20261004)
    elif case=='duplicate':rows=[row,row]
    elif case=='nonfinite':row['close']=float('inf')
    elif case=='secret':row['account_id']='SYNTHETIC-CANARY'
    else:row['close']=True
    resp=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':rows}}).encode())
    attempt=ingest(store,req=my_history_request(),resp=resp)
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert not store.query('history',ING) and not list(store.raw_dir.iterdir())


def test_malaysia_raw_offset_is_not_reinterpreted_from_the_prefix(store):
    # This date happens to agree with either literal offset. Date agreement is
    # not evidence that a vendor meant hours rather than documented minutes.
    row={'time_key':STAMP,'date':20261002,'time_zone':8,'close':12.5}
    resp=ReadResponse(200,json.dumps({'ret_code':0,'ret_msg':'ok','data':{'kline_list':[row]}}).encode())
    attempt=ingest(store,req=my_history_request(),resp=resp)
    assert attempt.status=='success'
    record=store.query('history',ING)[0]['record']
    assert record['time_zone']==8 and 'currency' not in record and 'market_timezone' not in record


# PRSG-128: fictional metadata only; the hours hypothesis never repairs a row.
def date_summary_rows():
    base=dict(time_key=STAMP-4*3600000,date=20261002,time_zone=8,close=10)
    return [base,  # minutes = Oct 1, hours = Oct 2
        {**base,'time_zone':0,'date':20261001},  # both match: count once as minutes
        {**base,'time_zone':480},  # minutes match, hours differ
        {**base,'date':20261003},  # neither interpretation
        {**base,'time_key':True}, {**base,'time_zone':841},
        {**base,'date':20260230}, {**base,'time_key':2**63-1},
        {**base,'time_zone':'PRIVATE-METADATA-CANARY'}, False,
        {**base,'time_key':-1}, {**base,'date':True}, {**base,'time_zone':True},
        {**base,'date':18991231}, {**base,'time_zone':-721},
        {**base,'time_key':1.0}, {**base,'date':21010101},
        {'date':20261002,'time_zone':8}]


def test_date_summary_counts_all_rows_without_values_or_acceptance(store):
    from ingest import private_market_store as m
    rows=date_summary_rows();raw=diagnostic_history_body(data={'kline_list':rows})
    kind,query,_=m.request_meta(diagnostic_history_request())
    with pytest.raises(MarketStoreError) as caught:m.normalized(raw,kind,query,version=4)
    error=caught.value;structure=error.diagnostic_structure
    assert str(error)=='invalid-response' and error.diagnostic_stage=='date-relation'
    assert structure['schema_version']==2 and m.valid_structure(structure,stage='date-relation')
    assert structure['date_relation_summary']==dict(rows_examined=len(rows),minutes_match=2,
        hours_only_match=1,neither_match=1,uncheckable=len(rows)-4)
    encoded=json.dumps(structure)
    for literal in ('20261002',str(STAMP-4*3600000),'480','841','PRIVATE-METADATA-CANARY','SYNTHETIC-BODY-CANARY'):
        assert literal not in encoded
    # All historical normalization versions still reject exactly the same row.
    for version in (1,2,3):
        with pytest.raises(MarketStoreError) as old:m.normalized(raw,kind,query,version=version)
        assert old.value.diagnostic_stage=='date-relation' and old.value.diagnostic_structure is None
    attempt=ingest(store,req=diagnostic_history_request(),resp=ReadResponse(200,raw))
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert not store.query('history',ING) and not list(store.raw_dir.iterdir())


def test_date_summary_maximum_and_secret_screen():
    from ingest import private_market_store as m
    kind,query,_=m.request_meta(diagnostic_history_request());query={**query,'num':'370'}
    rows=[date_summary_rows()[0]]*370
    with pytest.raises(MarketStoreError) as caught:
        m.normalized(diagnostic_history_body(data={'kline_list':rows}),kind,query,version=4)
    assert caught.value.diagnostic_structure['date_relation_summary']==dict(rows_examined=370,
        minutes_match=0,hours_only_match=370,neither_match=0,uncheckable=0)
    with pytest.raises(MarketStoreError) as caught:
        m.normalized(diagnostic_history_body(data={'kline_list':rows+[rows[0]]}),kind,query,version=4)
    assert caught.value.diagnostic_stage=='history-rows' and caught.value.diagnostic_structure['schema_version']==1
    for extra,secrets in (({'token':'PRIVATE-SECRET'},()),({'note':'PRIVATE-SECRET'},('PRIVATE-SECRET',))):
        raw=diagnostic_history_body(data={'kline_list':[rows[0],extra]})
        with pytest.raises(MarketStoreError) as caught:m.normalized(raw,kind,query,secrets,version=4)
        assert caught.value.diagnostic_stage=='decode-screen'
        assert caught.value.diagnostic_structure==m.unavailable_structure()


def test_date_summary_closed_schema_and_controlled_error_binding():
    from copy import deepcopy
    from ingest import private_market_store as m
    value=json.loads(diagnostic_history_body(date_summary_rows()[0]))
    structure=m.history_structure(value,stage='date-relation')
    assert not m.valid_structure(structure)  # schema2 always needs its stage
    assert m.MarketStoreError('invalid-response',diagnostic_stage='date-relation',
        diagnostic_structure=structure).diagnostic_structure==structure
    for stage in m.HISTORY_STAGES-{'date-relation'}:
        assert not m.valid_structure(structure,stage=stage)
        assert m.MarketStoreError('invalid-response',diagnostic_stage=stage,
            diagnostic_structure=structure).diagnostic_structure is None
    assert m.MarketStoreError('other',diagnostic_stage='date-relation',diagnostic_structure=structure).diagnostic_structure is None
    for change in ({'schema_version':True},{'status':'unavailable'},{'extra':'PRIVATE-CANARY'},
                   {'date_relation_summary':None},{'schema_version':1}):
        bad={**structure,**change};assert not m.valid_structure(bad,stage='date-relation')
    for key in structure['date_relation_summary']:
        for value in (True,-1,371,1.0,'PRIVATE-CANARY',None,[],{}):
            bad=deepcopy(structure);bad['date_relation_summary'][key]=value
            assert not m.valid_structure(bad,stage='date-relation')
        bad=deepcopy(structure);bad['date_relation_summary'].pop(key)
        assert not m.valid_structure(bad,stage='date-relation')
    bad=deepcopy(structure);bad['date_relation_summary']['rows_examined']=2
    assert not m.valid_structure(bad,stage='date-relation')
    bad=deepcopy(structure);bad['date_relation_summary']['PRIVATE-CANARY']=0
    assert not m.valid_structure(bad,stage='date-relation')
    # Historical schema1 remains valid even at date-relation stage.
    legacy=m.history_structure(json.loads(diagnostic_history_body(date_summary_rows()[0])))
    assert m.valid_structure(legacy,stage='date-relation') and legacy['schema_version']==1


# PRSG-129: explicit local research dialect, fictional data only.
def hours_row(zone=8):
    from datetime import date,timedelta
    stamp=STAMP-4*3600000
    day=date(1970,1,1)+timedelta(days=(stamp+zone*3600000)//86400000)
    return dict(time_key=stamp,date=int(day.strftime('%Y%m%d')),time_zone=zone,close=12.5)


@pytest.mark.parametrize('zone',[-12,-1,0,1,8,14])
def test_explicit_hours_store_preserves_raw_metadata_and_integrity_replay(store,zone):
    from ingest import private_market_store as m
    row=hours_row(zone);resp=ReadResponse(200,diagnostic_history_body(row))
    req=my_history_request();kind,query,_=m.request_meta(req)
    records=m.normalized(resp.body,kind,query,version=5,normalization_dialect=m.HOURS_DIALECT)
    attempt=store.ingest(req,resp,run_id='synthetic-hours',observed_at=OBS,ingested_at=ING,
        origin='synthetic',normalization_version=5,normalization_dialect=m.HOURS_DIALECT)
    assert attempt.status=='success' and store.raw(attempt.raw_hash)==resp.body
    entry=store.query('history',ING)[0];record=entry['record'];meta=entry['observation']
    assert (record['time_key'],record['raw_date'],record['time_zone'])==(row['time_key'],row['date'],zone)
    assert record['effective_offset_minutes']==zone*60 and record['raw_time_zone_unit']=='hours_hypothesis'
    assert record['normalization_dialect']==meta['normalization_dialect']==m.HOURS_DIALECT
    assert record['unit_basis']==meta['unit_basis']==m.HOURS_BASIS
    assert record['inference_quality']==meta['inference_quality']==m.HOURS_QUALITY
    assert m.HOURS_QUALITY in entry['quality'] and meta['normalization_version']==5
    assert 'currency' not in record and 'market_timezone' not in record and meta['rights_status']=='unconfirmed'
    assert records[0][1]==m.canonical(record)
    # A missing token never selects hours, including the ambiguous both-match case.
    if zone==8:
        for version in (3,4):
            with pytest.raises(MarketStoreError) as caught:m.normalized(resp.body,kind,query,version=version)
            assert caught.value.diagnostic_stage=='date-relation'
    elif zone==0:
        legacy=json.loads(m.normalized(resp.body,kind,query,version=4)[0][1])
        assert 'normalization_dialect' not in legacy and 'effective_offset_minutes' not in legacy


@pytest.mark.parametrize('bad',['bool','fraction','low','high','overflow','invalid-date','future','duplicate',
    'negative-price','bool-price','nonfinite','secret','minute-only'])
def test_hours_rejection_never_falls_back_or_archives(store,bad):
    from ingest import private_market_store as m
    row=hours_row();rows=[row]
    if bad=='bool':row['time_zone']=True
    elif bad=='fraction':row['time_zone']=8.0
    elif bad=='low':row['time_zone']=-13
    elif bad=='high':row['time_zone']=15
    elif bad=='overflow':row['time_key']=2**63-1
    elif bad=='invalid-date':row['date']=20260230
    elif bad=='future':row.update(time_key=STAMP+3*86400000,date=20261005)
    elif bad=='duplicate':rows.append(dict(row))
    elif bad=='negative-price':row['close']=-1
    elif bad=='bool-price':row['close']=True
    elif bad=='nonfinite':row['close']=float('inf')
    elif bad=='secret':row['token']='PRIVATE-CANARY'
    elif bad=='minute-only':row['date']=20261001
    resp=ReadResponse(200,diagnostic_history_body(data={'kline_list':rows}))
    attempt=store.ingest(my_history_request(),resp,run_id='synthetic-bad-hours',observed_at=OBS,ingested_at=ING,
        origin='synthetic',normalization_version=5,normalization_dialect=m.HOURS_DIALECT)
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert not store.query('history',ING) and not list(store.raw_dir.iterdir())
    if bad=='minute-only':
        kind,query,_=m.request_meta(my_history_request())
        assert m.normalized(resp.body,kind,query,version=4)
        with pytest.raises(MarketStoreError) as caught:
            m.normalized(resp.body,kind,query,version=5,normalization_dialect=m.HOURS_DIALECT)
        assert caught.value.diagnostic_stage=='date-relation'
        assert caught.value.diagnostic_structure['date_relation_summary']['minutes_match']==1


@pytest.mark.parametrize('version,dialect,us',[(5,None,False),(4,'bms1155_hours_hypothesis_v1',False),
    (3,'bms1155_hours_hypothesis_v1',False),(5,'unknown',False),(5,True,False),
    (5,'bms1155_hours_hypothesis_v1',True)])
def test_hours_store_and_normalizer_require_exact_context(store,version,dialect,us):
    from ingest import private_market_store as m
    req=diagnostic_history_request() if us else my_history_request();kind,query,_=m.request_meta(req)
    resp=ReadResponse(200,diagnostic_history_body(hours_row()))
    with pytest.raises(MarketStoreError):m.normalized(resp.body,kind,query,version=version,normalization_dialect=dialect)
    with pytest.raises(MarketStoreError):store.ingest(req,resp,run_id='synthetic-context',observed_at=OBS,ingested_at=ING,
        normalization_version=version,normalization_dialect=dialect)
    assert not store.attempts(ING) and not list(store.raw_dir.iterdir())


def test_hours_store_rehashed_context_substitution_still_fails_replay(store):
    from ingest import private_market_store as m
    raw=diagnostic_history_body(hours_row())
    attempt=store.ingest(my_history_request(),ReadResponse(200,raw),run_id='synthetic-hash',observed_at=OBS,ingested_at=ING,
        normalization_version=5,normalization_dialect=m.HOURS_DIALECT)
    meta=store.attempts(ING)[0]
    for key,value in [('normalization_dialect','unknown'),('unit_basis','verified'),
                      ('raw_time_zone_unit','minutes'),('effective_offset_rule','identity'),
                      ('inference_quality','confirmed'),('normalization_version',4)]:
        changed={**meta,key:value};fake=dict(id=m.digest(m.canonical(changed).encode()),metadata=json.dumps(changed),
            known_ms=changed['known_ms'],run_id=changed['run_id'],kind=changed['kind'])
        with pytest.raises(MarketStoreError):store._meta(fake)
    assert store.query('history',ING)[0]['record']['time_zone']==8 and attempt.raw_hash


FIXED_MY20 = ('0820EA','0800EA','1155','1023','0277','0259','0166','0097','5225','5878',
              '4707','3689','5296','4715','6033','5681','5246','3816','1961','5285')
FIXED_MY_TOKEN = 'bms_fixed20_hours_hypothesis_v1'


@pytest.mark.parametrize('symbol',FIXED_MY20)
def test_fixed20_request_context_pure_normalization_and_store_replay(store,symbol):
    from ingest import private_market_store as m
    req=my_history_request(code='BMS.'+symbol)
    kind,query,_=m.request_meta(req,normalization_dialect=FIXED_MY_TOKEN)
    raw=diagnostic_history_body(hours_row())
    expected=m.normalized(raw,kind,query,version=6,normalization_dialect=FIXED_MY_TOKEN)
    attempt=store.ingest(req,ReadResponse(200,raw),run_id='fictional-fixed20',observed_at=OBS,ingested_at=ING,
        origin='synthetic',normalization_version=6,normalization_dialect=FIXED_MY_TOKEN)
    assert attempt.status=='success' and store.raw(attempt.raw_hash)==raw
    entry=store.query('history',ING)[0];record=entry['record']
    assert expected[0][1]==m.canonical(record) and record['code']=='BMS.'+symbol
    assert record['raw_date']==20261002 and record['time_zone']==8 and record['effective_offset_minutes']==480
    assert record['normalization_dialect']==entry['observation']['normalization_dialect']==FIXED_MY_TOKEN
    assert m.HOURS_QUALITY in entry['quality'] and entry['observation']['normalization_version']==6
    assert not {'currency','market_timezone'}&set(record)
    if symbol!='1155':
        with pytest.raises(MarketStoreError):m.request_meta(req)
        with pytest.raises(MarketStoreError):m.normalized(raw,kind,query,version=4)


@pytest.mark.parametrize('version,token',[(6,None),(6,'bms1155_hours_hypothesis_v1'),(5,FIXED_MY_TOKEN),
    (4,FIXED_MY_TOKEN),(6,'unknown'),(6,True)])
def test_fixed20_missing_old_or_cross_version_context_rejects_without_retention(store,version,token):
    from ingest import private_market_store as m
    req=my_history_request(code='BMS.1023');raw=diagnostic_history_body(hours_row())
    with pytest.raises(MarketStoreError):store.ingest(req,ReadResponse(200,raw),run_id='fictional-context',
        observed_at=OBS,ingested_at=ING,normalization_version=version,normalization_dialect=token)
    assert not store.attempts(ING) and not list(store.raw_dir.iterdir())


@pytest.mark.parametrize('bad',['date','future','duplicate','secret','price','overflow','zone','minute-only','too-many'])
def test_fixed20_invalid_rows_keep_bounded_rejection_and_count_diagnostics(store,bad):
    from ingest import private_market_store as m
    row=hours_row();rows=[row]
    if bad=='date':row['date']=20260230
    elif bad=='future':row.update(time_key=STAMP+3*86400000,date=20261005)
    elif bad=='duplicate':rows.append(dict(row))
    elif bad=='secret':row['token']='FICTIONAL-SECRET'
    elif bad=='price':row['close']=float('nan')
    elif bad=='overflow':row['time_key']=2**63-1
    elif bad=='zone':row['time_zone']=15
    elif bad=='minute-only':row['date']=20261001
    else:rows=[dict(row) for _ in range(101)]
    raw=diagnostic_history_body(data={'kline_list':rows});req=my_history_request(code='BMS.1023')
    attempt=store.ingest(req,ReadResponse(200,raw),run_id='fictional-invalid',observed_at=OBS,ingested_at=ING,
        normalization_version=6,normalization_dialect=FIXED_MY_TOKEN)
    assert attempt.status=='failed' and attempt.raw_hash is None
    assert not store.query('history',ING) and not list(store.raw_dir.iterdir())
    if bad=='minute-only':
        kind,query,_=m.request_meta(req,normalization_dialect=FIXED_MY_TOKEN)
        with pytest.raises(MarketStoreError) as caught:m.normalized(raw,kind,query,version=6,normalization_dialect=FIXED_MY_TOKEN)
        assert caught.value.diagnostic_stage=='date-relation'
        assert caught.value.diagnostic_structure['date_relation_summary']['minutes_match']==1


def test_fixed20_metadata_query_code_substitution_fails_raw_replay(store):
    from ingest import private_market_store as m
    raw=diagnostic_history_body(hours_row())
    attempt=store.ingest(my_history_request(code='BMS.1023'),ReadResponse(200,raw),run_id='fictional-tamper',
        observed_at=OBS,ingested_at=ING,normalization_version=6,normalization_dialect=FIXED_MY_TOKEN)
    meta=store.attempts(ING)[0];meta['query']['code']='BMS.0277'
    meta['endpoint']='/api/v1.0/quote/BMS.0277/history-kline'
    encoded=m.canonical(meta);newid=m.digest(encoded.encode())
    # Adversarial fixture deliberately bypasses SQLite immutable triggers to test
    # read-time replay, rather than relying only on a mismatching metadata hash.
    with sqlite3.connect(store.database) as db:
        db.execute('DROP TRIGGER attempts_update');db.execute('DROP TRIGGER observations_update')
        db.execute('UPDATE attempts SET id=?,metadata=? WHERE id=?',(newid,encoded,attempt.attempt_id))
        db.execute('UPDATE observations SET attempt_id=? WHERE attempt_id=?',(newid,attempt.attempt_id))
    with pytest.raises(MarketStoreError):store.query('history',ING)
