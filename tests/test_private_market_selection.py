"""Synthetic read-only selection; no credentials, provider calls or public output."""
import json
import sqlite3

import pytest
from connectors.moomoo_rest import ReadRequest, ReadResponse
from ingest.private_market_store import PrivateMarketStore, MarketStoreError, canonical, digest

OBS = '2026-10-02T00:00:00Z'
ING = '2026-10-02T00:01:00Z'
LATER = '2026-10-03T00:01:00Z'
STAMP = 1790899200000
CODES = ['US.SYN']


def record(**changes):
    return dict({'code':'US.SYN','name':'Synthetic','update_time':STAMP,
                 'data_date':'2026-10-02','last_price':10,'volume':0,'equity_valid':True},**changes)


@pytest.fixture
def store(tmp_path):
    return PrivateMarketStore(tmp_path/'private-selection',create=True)


def ingest(store,rows=None,*,run='synthetic',codes=None,observed=OBS,ingested=ING,http=200):
    request=ReadRequest('POST','/api/v1.0/quote/snapshot','',canonical({'code_list':codes or CODES}).encode(),{},1)
    response=ReadResponse(http,canonical({'ret_code':0,'ret_msg':'ok','data':{'snapshot_list':[record()] if rows is None else rows}}).encode())
    return store.ingest(request,response,run_id=run,observed_at=observed,ingested_at=ingested,origin='synthetic')


def select(store,cutoff=ING,codes=None,run='synthetic'):
    return store.select_snapshots(run,cutoff,codes or CODES)


def test_exact_selection_provenance_unknowns_and_read_only(store):
    stored=ingest(store)
    before={str(p):p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    result=select(store)
    after={str(p):p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    assert before==after and result['view_complete'] is True
    assert result['coverage']['selected']=={'codes':CODES,'count':1}
    assert result['attempt_status_counts']==dict(success=1,partial=0,**{'all-missing':0},failed=0)
    q=result['quotes']['US.SYN']
    assert q['quote']['price']==10 and q['quote']['volume']==0
    assert all(q['quote'][k] is None for k in ('currency','session','adjustment','prior_close'))
    assert all(k in q['gap_reasons'] for k in ('currency_unknown','session_unknown','adjustment_unknown','prior_close_unknown'))
    assert q['provenance']['attempt_id']==stored.attempt_id and q['provenance']['raw_hash']==stored.raw_hash
    assert q['provenance']['origin']=='synthetic' and q['provenance']['capture_authenticity']=='caller-supplied-unverified'
    assert q['replay_count']==0 and q['latest_observation_count']==1
    assert 'forecast' not in q and 'change' not in q and 'rvol' not in q


def test_missing_future_only_indistinguishable_no_other_run_fallback(store):
    ingest(store,run='other')
    absent=select(store)
    ingest(store,observed=LATER,ingested=LATER)
    assert select(store)==absent and absent['status']=='no_available_attempts'
    assert absent['coverage']['requested']['count']==0 and absent['coverage']['missing']['codes']==CODES
    assert absent['quotes']['US.SYN']['gap_reasons'][-1]=='no_available_attempts'


@pytest.mark.parametrize('codes',[[],['MY.SYN'],['US.SYN','US.SYN'],['US.S'+str(i) for i in range(401)],None,'US.SYN'])
def test_invalid_explicit_universe(store,codes):
    with pytest.raises(MarketStoreError):store.select_snapshots('synthetic',ING,codes)


@pytest.mark.parametrize('run',['',None,'../unsafe','x'*129])
def test_invalid_run(store,run):
    with pytest.raises(MarketStoreError):store.select_snapshots(run,ING,CODES)


@pytest.mark.parametrize('cutoff',['2026-10-02T00:01:00','2026-10-02T00:01:00.1234567Z','invalid'])
def test_invalid_cutoff(store,cutoff):
    with pytest.raises(MarketStoreError):select(store,cutoff)


def test_universe_mismatch_fails_closed(store):
    ingest(store,codes=['US.SYN','US.MISSING'])
    with pytest.raises(MarketStoreError):select(store)


def test_universe_order_is_not_mismatch(store):
    ingest(store,codes=['US.OTHER','US.SYN'])
    result=select(store,codes=['US.SYN','US.OTHER'])
    assert result['coverage']['requested']['codes']==['US.SYN','US.OTHER']
    assert result['coverage']['missing']['codes']==['US.OTHER']
    assert result['attempt_status_counts']['partial']==1


def test_failed_all_missing_and_partial_are_distinct(store):
    codes=['US.SYN','US.MISSING']
    ingest(store,codes=codes,http=503)
    ingest(store,[],codes=codes,ingested='2026-10-02T00:00:30Z')
    ingest(store,codes=codes,ingested='2026-10-02T00:00:40Z')
    result=select(store,codes=codes)
    assert result['attempt_status_counts']==dict(success=0,partial=1,**{'all-missing':1},failed=1)
    assert result['coverage']['requested']['count']==2 and result['coverage']['returned']['count']==1
    assert result['coverage']['selected']['codes']==['US.SYN']
    assert result['quotes']['US.MISSING']['quote'] is None
    assert result['quotes']['US.MISSING']['gap_reasons'][-1]=='no_returned_quote'


@pytest.mark.parametrize('changes,reason', [({'update_time':None},'source_time_unknown'),
    ({'update_time':STAMP+1},'source_time_after_observation'),
    ({'update_time':STAMP+120000},'source_time_after_cutoff'),({'last_price':0},'price_unusable')])
def test_ineligible_records_keep_returned_diagnostics(store,changes,reason):
    ingest(store,[record(**changes)])
    result=select(store);q=result['quotes']['US.SYN']
    assert result['coverage']['returned']['count']==1 and result['coverage']['eligible']['count']==0
    assert q['quote'] is None and q['excluded_counts'][reason]==1
    assert q['gap_reasons'][-1]=='no_eligible_quote'


def test_same_time_conflict_withheld_no_old_fallback(store):
    ingest(store,[record(update_time=STAMP-1000,last_price=9)])
    ingest(store,[record(last_price=10)],ingested='2026-10-02T00:00:30Z')
    ingest(store,[record(last_price=11)],ingested='2026-10-02T00:00:40Z')
    result=select(store);q=result['quotes']['US.SYN']
    assert result['coverage']['conflicted']['codes']==CODES and result['coverage']['eligible']['count']==1
    assert result['coverage']['selected']['count']==0 and q['quote'] is None and q['provenance'] is None
    assert q['gap_reasons'][-1]=='same_time_conflict' and len(q['conflict_provenance'])==2
    assert q['replay_count'] is None and q['latest_observation_count']==2


def test_greatest_provider_time_not_revision_or_ingestion_order(store):
    ingest(store,[record(update_time=STAMP,last_price=10)])
    ingest(store,[record(update_time=STAMP-1000,last_price=11)],ingested='2026-10-02T00:00:30Z')
    assert select(store)['quotes']['US.SYN']['quote']['price']==10


def test_replay_bounded_provenance_and_future_conflict_not_used(store):
    first=ingest(store)
    ingest(store,ingested='2026-10-02T00:00:30Z')
    ingest(store,[record(last_price=11)],observed=LATER,ingested=LATER)
    q=select(store)['quotes']['US.SYN']
    assert q['quote']['price']==10 and q['replay_count']==1 and q['latest_observation_count']==2
    assert q['conflict_provenance']==[] and q['provenance']['attempt_id']!=first.attempt_id
    assert select(store,LATER)['quotes']['US.SYN']['quote'] is None


def test_newer_eligible_point_supersedes_older_conflict(store):
    ingest(store);ingest(store,[record(last_price=11)],ingested='2026-10-02T00:00:30Z')
    ingest(store,[record(update_time=STAMP+1000,last_price=12)],observed=ING,ingested=ING)
    result=select(store)
    assert result['quotes']['US.SYN']['quote']['price']==12 and result['coverage']['conflicted']['count']==0


def test_submillisecond_ingestion_never_leaks(store):
    ingest(store,observed='2026-10-02T00:00:00.000500Z',ingested='2026-10-02T00:00:00.000500Z')
    assert select(store,'2026-10-02T00:00:00.000999Z')['status']=='no_available_attempts'
    assert select(store,'2026-10-02T00:00:00.001000Z')['coverage']['selected']['count']==1


@pytest.mark.parametrize('scope',['own','other'])
def test_more_than_1000_rows_cannot_hide_latest_or_target(store,scope):
    # Actual immutable ingestions, not handcrafted database rows bypassing integrity.
    for i in range(1001):
        ingest(store,run='synthetic' if scope=='own' else 'other',
               observed=OBS,ingested=f'2026-10-02T00:00:{i//100:02d}.{i%100:02d}0000Z')
    ingest(store,[record(update_time=STAMP+1000,last_price=12)],observed=ING,ingested=ING)
    result=select(store)
    assert result['quotes']['US.SYN']['quote']['price']==12
    assert result['attempt_status_counts']['success']==(1002 if scope=='own' else 1)
    assert result['view_complete'] and result['quotes']['US.SYN']['latest_observation_count']==1


def corrupt(store,table,sql,args=()):
    # Deliberately tamper without changing the stored schema, as existing regressions do.
    with sqlite3.connect(store.database) as db:
        trigger=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(table+'_update',)).fetchone()[0]
        db.execute('DROP TRIGGER '+table+'_update');db.execute(sql,args);db.execute(trigger)


@pytest.mark.parametrize('damage',['missing-raw','raw-hash','payload','ordinal','source','count','missing-observation'])
def test_integrity_corruption_fails_closed(store,damage):
    saved=ingest(store)
    if damage=='missing-raw':(store.raw_dir/(saved.raw_hash+'.json')).unlink()
    elif damage=='raw-hash':
        path=store.raw_dir/(saved.raw_hash+'.json');path.chmod(0o600);path.write_bytes(b'corrupt');path.chmod(0o400)
    elif damage=='payload':corrupt(store,'versions','UPDATE versions SET payload=?',(canonical({'price':999}),))
    elif damage=='ordinal':corrupt(store,'observations','UPDATE observations SET ordinal=1')
    elif damage=='source':corrupt(store,'versions','UPDATE versions SET source_ms=source_ms+1')
    elif damage=='count':
        # Hash-consistent metadata tampering must still disagree with raw/observations.
        with sqlite3.connect(store.database) as db:meta=json.loads(db.execute('SELECT metadata FROM attempts').fetchone()[0])
        meta['record_count']=2;raw=canonical(meta)
        corrupt(store,'attempts','UPDATE attempts SET id=?,metadata=?',(digest(raw.encode()),raw))
    else:
        with sqlite3.connect(store.database) as db:
            trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='observations_delete'").fetchone()[0]
            db.execute('DROP TRIGGER observations_delete');db.execute('DELETE FROM observations');db.execute(trigger)
    with pytest.raises(MarketStoreError) as caught:select(store)
    assert caught.value.__context__ is None and str(store.root) not in str(caught.value)


def test_failure_with_forged_observation_is_rejected(store):
    good=ingest(store);failed=ingest(store,http=503)
    with sqlite3.connect(store.database) as db:
        version=db.execute('SELECT id FROM versions').fetchone()[0]
        db.execute('INSERT INTO observations VALUES (?,?,0)',(failed.attempt_id,version))
    with pytest.raises(MarketStoreError):select(store)


def test_news_only_run_is_no_snapshot_attempt(store):
    request=ReadRequest('GET','/api/v1.0/quote/find-news','symbol=synthetic&size=10',b'',{},1)
    store.ingest(request,ReadResponse(200,b'{"ret_code":0,"ret_msg":"ok","data":[]}'),run_id='synthetic',observed_at=OBS,ingested_at=ING,origin='synthetic')
    assert select(store)['status']=='no_available_attempts'


def test_all_400_codes_bounded_complete_output(store):
    codes=['US.S'+str(i) for i in range(400)]
    ingest(store,[record(code=code) for code in codes],codes=codes)
    result=select(store,codes=codes)
    assert len(result['quotes'])==400 and result['coverage']['selected']['count']==400
    assert result['coverage']['missing']['count']==0
    assert all(len(q['conflict_provenance'])<=2 for q in result['quotes'].values())


def test_conflict_by_volume_not_only_price(store):
    ingest(store);ingest(store,[record(volume=1)],ingested='2026-10-02T00:00:30Z')
    assert select(store)['coverage']['conflicted']['codes']==CODES


def test_excluded_future_point_does_not_hide_diagnostics(store):
    ingest(store)
    ingest(store,[record(update_time=STAMP+1,last_price=11)],ingested='2026-10-02T00:00:30Z')
    q=select(store)['quotes']['US.SYN']
    assert q['quote']['price']==10 and q['excluded_counts']=={'source_time_after_observation':1}


@pytest.mark.parametrize('change',[{'record_count':2},{'missing_codes':['US.SYN']},
    {'status':'partial'},{'reason':'invented'},{'connector':'other'}, {'query':{'codes':CODES,'extra':1}}])
def test_hash_consistent_metadata_still_checked_against_raw(store,change):
    old=ingest(store)
    with sqlite3.connect(store.database) as db:
        meta=json.loads(db.execute('SELECT metadata FROM attempts').fetchone()[0])
    meta.update(change);raw=canonical(meta);new_id=digest(raw.encode())
    corrupt(store,'attempts','UPDATE attempts SET id=?,metadata=?',(new_id,raw))
    corrupt(store,'observations','UPDATE observations SET attempt_id=? WHERE attempt_id=?',(new_id,old.attempt_id))
    with pytest.raises(MarketStoreError):select(store)


def test_corrupt_run_provider_rejected(store):
    ingest(store)
    corrupt(store,'runs','UPDATE runs SET provider=?',('other-provider',))
    with pytest.raises(MarketStoreError):select(store)


@pytest.mark.parametrize('count',[1,30])
def test_v2_selection_retains_provider_previous_close_without_comparability(count,store):
    codes=[f'US.SYN{i}' for i in range(count)]
    ingest(store,[record(code=code,prev_close_price=9) for code in codes],codes=codes)
    chosen=select(store,codes=codes)
    assert chosen['coverage']['selected']['count']==count
    for entry in chosen['quotes'].values():
        assert entry['quote']['provider_prev_close']==9 and entry['quote']['normalization_version']==2
        assert entry['quote']['prior_close'] is None and 'prior_close_unknown' in entry['gap_reasons']
        assert all(entry['quote'][key] is None for key in ('currency','session','adjustment'))
        assert 'change' not in entry['quote'] and 'direction' not in entry['quote']


def test_missing_previous_close_is_explicit_null_and_changed_previous_close_conflicts(store):
    ingest(store);assert select(store)['quotes']['US.SYN']['quote']['provider_prev_close'] is None
    ingest(store,[record(prev_close_price=9)],observed=ING,ingested=ING)
    result=select(store)
    assert result['quotes']['US.SYN']['quote'] is None and result['coverage']['conflicted']['count']==1
