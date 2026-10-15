"""Fictional offline implementation regressions, never forecast quality evidence."""
import csv
from datetime import datetime, timezone
import importlib.util
import math
from pathlib import Path
import sqlite3
import sys

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/stock-research'
# Existing repository tests also load standalone modules; isolate imports explicitly.
for name in ('storage','data','market_calendar','features'):
    spec=importlib.util.spec_from_file_location(name,SCRIPT/f'{name}.py')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
from data import GAPS, assemble, make_labels, normalize, origin_weights, purged_splits, read_csv, read_generations, read_sqlite
from features import causal_features, FEATURE_COLUMNS
from market_calendar import MarketCalendar
from storage import HISTORY_COLUMNS, Generation, canonical, sha

@pytest.fixture(scope='module')
def cal(): return MarketCalendar('2025-01-01','2028-01-01')

def bar(cal, day, *, code='US.DEMO', low=99, high=103, close=100, known=None):
    end=cal.close_ms(day);known=known or end+1000
    row={k:None for k in HISTORY_COLUMNS}
    row.update(code=code,session_date=day,open=100,high=high,low=low,close=close,volume=1000,turnover=100000,
        currency='USD',adjustment='forward-excluding-dividends',source='fictional',source_at_ms=end,
        raw_time_key=end,raw_date=int(day.replace('-','')),raw_time_zone=-300,
        time_zone_unit_status='runtime-unverified',time_zone_unit_source_url='https://example.com',
        provider_finality_status='unverified',retrieved_at_ms=known,known_at_ms=known,revision_vintage='a',
        completed=True,completion_status='completed',volume_precision=0,currency_source_url='https://example.com',
        price_known_at_ms=known,currency_known_at_ms=known,currency_evidence_hash='hash',currency_status='verified')
    return row

def receipt():return {'identity_bindings':[{'code':'US.DEMO','stock_id':1}]}

def history(rows):return assemble(rows,[receipt()])

def test_calendar_and_handcomputed_labels(cal):
    assert cal.close_ms('2026-11-27')==int(datetime(2026,11,27,18,tzinfo=timezone.utc).timestamp()*1000)
    assert cal.windows('2026-11-18')['next_week']==['2026-11-23','2026-11-24','2026-11-25','2026-11-27']
    rows=[bar(cal,'2026-11-18')]
    for day,lo,hi,cl in [('2026-11-19',80,120,110),('2026-11-20',90,115,100),('2026-11-23',99,103,102),('2026-11-24',98,105,104),('2026-11-25',100,106,103),('2026-11-27',100,107,106)]:
        rows.append(bar(cal,day,low=lo,high=hi,close=cl))
    labels=make_labels(history(rows),'US.DEMO','2026-11-18',calendar=cal,fit_cutoff_ms=cal.close_ms('2026-11-30'),origin_cutoff_ms=cal.close_ms('2026-11-18')+1000)
    for label,(lo,hi,terminal) in zip(labels,[(80,120,110),(80,120,102),(80,120,103),(98,107,106)]):
        assert (label['realized_low'],label['realized_high'])==(lo,hi)
        assert label['terminal_logreturn']==pytest.approx(math.log(terminal/100))
    assert sum(r['weight'] for r in labels)==1

@pytest.mark.parametrize('field,value',[('completed','yes'),('known_at_ms','1.1'),('open',float('nan')),('low',0),('price_known_at_ms',None),('currency_known_at_ms',-1)])
def test_invalid_types(cal,field,value):
    row=bar(cal,'2026-11-18');row[field]=value
    with pytest.raises((ValueError,TypeError)):normalize(row)

def test_revisions_dedup_conflict_identity(cal):
    old=bar(cal,'2026-11-18');new=dict(old,high=104,known_at_ms=old['known_at_ms']+5000,retrieved_at_ms=old['known_at_ms']+5000)
    data=history([new,old,old])
    assert len(data.rows)==2
    assert data.as_of('US.DEMO',old['known_at_ms'])[0]['high']==103
    assert data.as_of('US.DEMO',new['known_at_ms'])[0]['high']==104
    with pytest.raises(ValueError,match='conflicting-same'):history([old,dict(old,high=104)])
    with pytest.raises(ValueError,match='symbol-identity'):assemble([old],[receipt(),{'identity_bindings':[{'code':'US.DEMO','stock_id':2}]}])

def test_csv_sqlite_equivalent(cal,tmp_path):
    row=bar(cal,'2026-11-18');file=tmp_path/'history.csv'
    with file.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=HISTORY_COLUMNS);writer.writeheader();writer.writerow(row)
    db=tmp_path/'data.sqlite'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE ohlcv ('+','.join('"'+c+'"' for c in HISTORY_COLUMNS)+')')
        conn.execute('INSERT INTO ohlcv VALUES ('+','.join('?' for _ in HISTORY_COLUMNS)+')',[row[c] for c in HISTORY_COLUMNS])
    assert read_csv([file,file],receipt=receipt()).rows==read_sqlite(db,receipt=receipt()).rows
    with pytest.raises(ValueError):read_sqlite(db,receipt=receipt(),table='ohlcv; DROP TABLE ohlcv')

def test_missing_late_and_gap(cal):
    origin='2026-11-18';end=cal.close_ms('2026-11-30');rows=[bar(cal,origin),dict(bar(cal,'2026-11-19',low=102,high=104,close=103),open=102)]
    labels=make_labels(history(rows),'US.DEMO',origin,calendar=cal,fit_cutoff_ms=end,origin_cutoff_ms=cal.close_ms(origin)+1000)
    assert labels[0]['realized_low']==102
    assert labels[1]['status']=='pending'
    late=dict(rows[1],known_at_ms=end+1000,retrieved_at_ms=end+1000)
    labels=make_labels(history([rows[0],late]),'US.DEMO',origin,calendar=cal,fit_cutoff_ms=end,origin_cutoff_ms=cal.close_ms(origin)+1000)
    assert all(r['status']=='pending' for r in labels)

def test_split_purge_all_instruments_and_weights(cal):
    boundary=cal.close_ms('2026-11-23')
    row={'code':'US.DEMO','origin':'2026-11-18','horizon':'1d','status':'complete','end_at_ms':cal.close_ms('2026-11-19'),'label_available_at':boundary+1}
    rows=[row,dict(row,code='US.OTHER'),dict(row,horizon='3d')]
    result=purged_splits(rows,validation_start='2026-11-23',holdout_start='2026-11-30',fit_cutoff_ms=boundary+100,calendar=cal)
    assert len(result['purged'])==3 and result['status']['train']=='empty'
    assert len(origin_weights([row,row]))==1

def test_research_feature_masks_and_actual_label_gate(cal):
    days=cal.sessions('2026-07-01','2026-11-18')[-51:];present=cal.close_ms('2026-12-01')
    data=history([bar(cal,day,known=present) for day in days])
    with pytest.raises(ValueError):data.as_of('US.DEMO',present,policy='research-retrospective')
    result=causal_features(data,'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=cal.close_ms(days[-1])+1000,horizon='next_week',policy='research-retrospective',declared_gaps=GAPS)
    assert tuple(result['features'])==FEATURE_COLUMNS
    assert result['features']['benchmark_relative20'] is None
    assert result['features']['signed_leverage'] is None
    assert result['assumed_feature_vintage'] and result['feature_known_at_ms']==present
    with pytest.raises(ValueError):causal_features(data,'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=present,horizon='1d')

def test_hash_verified_generations(cal,tmp_path):
    row=bar(cal,'2026-11-18');schedule=[{'session_date':row['session_date'],'close_at_ms':cal.close_ms(row['session_date'])}]
    gen=Generation(tmp_path,generated_at=datetime(2026,11,19,tzinfo=timezone.utc),compatibility_id='demo',as_of_ms=row['known_at_ms'])
    gen.csv('history.csv',[row],HISTORY_COLUMNS);gen.json('identity_bindings.json',[{'code':'US.DEMO','stock_id':'123'}])
    gen.json('calendar.json',{'sessions':schedule,'schedule_sha256':sha(canonical(schedule))})
    gen.json('metadata_input.json',{});folder=gen.finish(adjustment_policy={'historical_point_in_time':'not-established'})
    assert read_generations(tmp_path,compatibility_id='demo').rows==history([row]).rows
    (folder/'history.csv').write_text('tampered')
    with pytest.raises(ValueError):read_generations(tmp_path,compatibility_id='demo')

def test_late_currency_and_reference(cal):
    row=bar(cal,'2026-11-18');old=row['retrieved_at_ms'];row.update(known_at_ms=old+10000,currency_known_at_ms=old+10000)
    assert normalize(row)['retrieved_at_ms']==old
    data=history([row,bar(cal,'2026-11-19')])
    assert not data.receipt('strict')['point_in_time']
    with pytest.raises(ValueError,match='reference-not-available'):
        make_labels(data,'US.DEMO','2026-11-18',calendar=cal,fit_cutoff_ms=old+5000,
            origin_cutoff_ms=old,policy='research-retrospective',declared_gaps=GAPS)

def test_budgets(cal,tmp_path,monkeypatch):
    import data
    monkeypatch.setattr(data,'MAX_ROWS',1)
    with pytest.raises(ValueError,match='row-budget'):
        history([bar(cal,'2026-11-18'),bar(cal,'2026-11-19')])
    monkeypatch.setattr(data,'MAX_BYTES',1)
    path=tmp_path/'big.csv';path.write_text('not a permitted size')
    with pytest.raises(ValueError,match='byte-budget'):read_csv([path],receipt=receipt())

def test_strict_features_dated_identity_and_benchmark(cal):
    days=cal.sessions('2026-07-01','2026-11-18')[-51:]
    data=history([bar(cal,day) for day in days]);cutoff=cal.close_ms(days[-1])+1000
    metadata={'code':'US.DEMO','stock_id':1,'known_at_ms':cal.close_ms(days[0]),
        'effective_from':days[0],'effective_to':days[-1],'membership':True,
        'source_url':'https://example.com/fiction','source_hash':'a'*64,'reviewer':'fixture','instrument_class':'stock','signed_leverage':1}
    result=causal_features(data,'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=cutoff,
        horizon='1d',dated_metadata=metadata,benchmark=(data,'US.DEMO'))
    assert result['features']['benchmark_relative20']==0
    assert result['features']['metadata_missing']==0
    with pytest.raises(ValueError,match='metadata-identity-conflict'):
        causal_features(data,'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=cutoff,
            horizon='1d',dated_metadata=dict(metadata,stock_id=2))

def test_reference_late_but_admitted_propagates_label_availability(cal):
    origin='2026-11-18';known=cal.close_ms('2026-11-23')
    rows=[bar(cal,origin,known=known),bar(cal,'2026-11-19')]
    labels=make_labels(history(rows),'US.DEMO',origin,calendar=cal,origin_cutoff_ms=cal.close_ms(origin)+1000,
        fit_cutoff_ms=known,policy='research-retrospective',declared_gaps=GAPS)
    assert labels[0]['label_available_at']==known
    splits=purged_splits(labels,validation_start='2026-11-23',holdout_start='2026-11-30',fit_cutoff_ms=known,calendar=cal)
    assert splits['status']['train']=='empty'

@pytest.mark.parametrize('bad', ['currency','adjustment','completed'])
def test_feature_units_and_completion_reject_even_research(cal,bad):
    days=cal.sessions('2026-07-01','2026-11-18')[-51:];rows=[bar(cal,d) for d in days]
    rows[-1][bad]={'currency':'UNKNOWN','adjustment':'unadjusted','completed':False}[bad]
    with pytest.raises(ValueError):
        causal_features(history(rows),'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=cal.close_ms(days[-1])+1000,
            horizon='1d',policy='research-retrospective',declared_gaps=GAPS)

@pytest.mark.parametrize('identity',[True,'x',0,-1,1.0])
def test_typed_identity_rejection(cal,identity):
    with pytest.raises(ValueError):assemble([bar(cal,'2026-11-18')],[{'identity_bindings':[{'code':'US.DEMO','stock_id':identity}]}])

def test_metadata_and_late_benchmark_availability(cal):
    days=cal.sessions('2026-07-01','2026-11-18')[-51:];cutoff=cal.close_ms(days[-1])+1000
    data=history([bar(cal,d) for d in days]);late=cutoff+100000
    benchmark=history([bar(cal,d,known=late) for d in days])
    kwargs=dict(calendar=cal,origin_cutoff_ms=cutoff,horizon='1d',policy='research-retrospective',declared_gaps=GAPS)
    result=causal_features(data,'US.DEMO',days[-1],benchmark=(benchmark,'US.DEMO'),**kwargs)
    assert result['feature_known_at_ms']==late
    metadata={'code':'US.DEMO','stock_id':1,'known_at_ms':1,'retrieved_at_ms':late,
        'effective_from':days[0],'effective_to':days[-1],'membership':True,'source_url':'https://example.com',
        'source_hash':'a'*64,'reviewer':'fixture','instrument_class':'stock','signed_leverage':1}
    assert causal_features(data,'US.DEMO',days[-1],dated_metadata=metadata,**kwargs)['features']['metadata_missing']==1
    metadata['retrieved_at_ms']=cutoff
    for change in ({'signed_leverage':3},{'effective_from':'invalid'},{'source_hash':None},{'reviewer':None}):
        assert causal_features(data,'US.DEMO',days[-1],dated_metadata=dict(metadata,**change),**kwargs)['features']['metadata_missing']==1
    with pytest.raises(ValueError,match='metadata-identity-conflict'):
        causal_features(data,'US.DEMO',days[-1],dated_metadata=dict(metadata,stock_id=2),**kwargs)

def test_late_units_cannot_finalize_partial_price(cal):
    from data import validate_window
    row=bar(cal,'2026-11-18');close=cal.close_ms(row['session_date'])
    row.update(source_at_ms=close-2000,price_known_at_ms=close-1000,retrieved_at_ms=close-1000,
        known_at_ms=close+2000,currency_known_at_ms=close+2000,completed=True)
    row=normalize(row)
    with pytest.raises(ValueError,match='incomplete-session'):
        validate_window([row],[row['session_date']],cal,cutoff_ms=close+5000)


def test_decimal_string_binding_preserves_wire_type(cal,tmp_path):
    row=bar(cal,'2026-11-18');binding={'identity_bindings':[{'code':'US.DEMO','stock_id':'123'}]}
    assert assemble([row],[binding]).receipts[0]['identity_bindings'][0]['stock_id']=='123'
    path=tmp_path/'history.csv'
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=HISTORY_COLUMNS);writer.writeheader();writer.writerow(row)
    assert read_csv([path],receipt=binding).rows==history([row]).rows
    with pytest.raises(ValueError,match='symbol-identity-conflict'):
        assemble([row],[binding,{'identity_bindings':[{'code':'US.DEMO','stock_id':123}]}])


def test_holiday_partition_rejected_explicitly(cal):
    row={'code':'US.DEMO','origin':'2026-11-18','horizon':'1d','status':'complete',
        'end_at_ms':cal.close_ms('2026-11-19'),'label_available_at':cal.close_ms('2026-11-19')+1000}
    with pytest.raises(ValueError):
        purged_splits([row],validation_start='2026-11-26',holdout_start='2026-11-30',fit_cutoff_ms=cal.close_ms('2026-11-30'),calendar=cal)

def test_index_calendar_cache_matches_reference(cal):
    rows=[bar(cal,'2026-11-18'),bar(cal,'2026-11-19')]
    rows.append(dict(rows[0],high=104,known_at_ms=rows[1]['known_at_ms'],retrieved_at_ms=rows[1]['retrieved_at_ms']))
    other=[bar(cal,'2026-11-18',code='US.OTHER')]
    data=assemble(rows+other,[{'identity_bindings':[{'code':'US.DEMO','stock_id':1},{'code':'US.OTHER','stock_id':2}]}])
    for cutoff in (rows[0]['known_at_ms']-1,rows[0]['known_at_ms'],rows[1]['known_at_ms']):
        expected={}
        for row in sorted(rows,key=lambda r:r['known_at_ms']):
            if row['known_at_ms']<=cutoff:expected[row['session_date']]=row
        assert data.as_of('US.DEMO',cutoff)==[expected[k] for k in sorted(expected)]
    reference=[s.date().isoformat() for s in cal.calendar.sessions_in_range('2026-10-01','2026-11-27')]
    assert cal.sessions('2026-10-01','2026-11-27')==reference
    assert cal.trailing_sessions('2026-11-27',5)==reference[-5:]

def test_unknown_future_metadata_time_not_ignored(cal):
    days=cal.sessions('2026-07-01','2026-11-18')[-51:];data=history([bar(cal,d) for d in days])
    with pytest.raises(ValueError,match='unsupported-metadata-availability'):
        causal_features(data,'US.DEMO',days[-1],calendar=cal,origin_cutoff_ms=cal.close_ms(days[-1])+1000,
            horizon='1d',policy='research-retrospective',declared_gaps=GAPS,
            dated_metadata={'known_at_ms':1,'first_seen_at':'2099-01-01T00:00:00Z'})

def test_aggregate_input_budget(cal,tmp_path,monkeypatch):
    import data
    path=tmp_path/'history.csv'
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=HISTORY_COLUMNS);writer.writeheader();writer.writerow(bar(cal,'2026-11-18'))
    monkeypatch.setattr(data,'MAX_TOTAL_BYTES',path.stat().st_size)
    with pytest.raises(ValueError,match='aggregate-input-byte-budget'):read_csv([path],receipt=receipt())
    folder=tmp_path/'2026-11-19_000000';folder.mkdir();(folder/'sidecar.json').write_text('x'*path.stat().st_size)
    (folder/'other.json').write_text('x')
    with pytest.raises(ValueError,match='aggregate-input-byte-budget'):read_generations(tmp_path,compatibility_id='fixture')
