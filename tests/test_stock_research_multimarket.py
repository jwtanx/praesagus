"""Fictional venue-bound model checks; no real-data quality or source admission."""
import csv
from datetime import datetime,timezone
import importlib.util
import json
import math
from pathlib import Path
import sys

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/stock-research'
sys.path.insert(0,str(SCRIPT))
from data import GAPS,assemble,validate_window,make_labels
from market_calendar import MarketCalendar
from train import run_training
from model import load_artifact,WINDOW_POLICY,venue_window_policy,validate_runtime_policy
from inference import build_forecasts
from storage import HISTORY_COLUMNS


def history(calendar,code='MY.0166',currency='MYR'):
    rows=[]
    for n,day in enumerate(calendar.sessions('2025-01-02','2026-09-30')):
        close=100+3*math.sin(n/10)+n*.01;stamp=calendar.close_ms(day)
        rows.append(dict(code=code,session_date=day,open=close,high=close+2,low=close-2,close=close,
            volume=100000,turnover=close*100000,currency=currency,adjustment='forward-excluding-dividends',
            source='fictional',source_at_ms=stamp,raw_time_key=stamp,raw_date=int(day.replace('-','')),
            raw_time_zone=8,time_zone_unit_status='verified',time_zone_unit_source_url='https://example.com',
            provider_finality_status='unverified',retrieved_at_ms=stamp+100,known_at_ms=stamp+100,
            revision_vintage='fictional-v1',completed=True,completion_status='completed',volume_precision=0,
            currency_source_url='https://example.com',price_known_at_ms=stamp+100,currency_known_at_ms=stamp+100,
            currency_evidence_hash='fictional',currency_status='verified'))
    return assemble(rows,[{'identity_bindings':[{'code':code,'stock_id':123,'known_at_ms':0}]}])


@pytest.fixture(scope='module')
def my_calendar():return MarketCalendar('2024-01-01','2027-12-31','XKLS')


@pytest.mark.parametrize('code',['MY.0166','MY.0820EA','MY.0800EA'])
def test_numeric_malaysian_identity_is_preserved(my_calendar,code):
    data=history(my_calendar,code)
    assert set(data._index)=={code}
    origin=data.rows[-1]['session_date']
    assert validate_window(data.rows,[origin],my_calendar,cutoff_ms=my_calendar.close_ms(origin)+100)[0]['currency']=='MYR'


@pytest.mark.parametrize('code,currency,reason',[('US.DEMO','MYR','instrument-venue'),('MY.0166','USD','incompatible-units')])
def test_venue_and_currency_cannot_be_silently_transferred(my_calendar,code,currency,reason):
    data=history(my_calendar,code,currency);origin=data.rows[-1]['session_date']
    with pytest.raises(ValueError,match=reason):validate_window(data.rows,[origin],my_calendar,cutoff_ms=my_calendar.close_ms(origin)+100)


def test_week_window_uses_kuala_lumpur_dates(my_calendar):
    # At this Friday's Malaysian close it is still Friday in both venues; the
    # policy explicitly binds local week dates and actual holiday sessions.
    policy=venue_window_policy('XKLS')
    assert policy['next_week']=='following-Kuala-Lumpur-calendar-week-exchange-sessions-only'
    assert venue_window_policy('XNYS')==WINDOW_POLICY
    assert my_calendar.windows('2026-09-25')['next_week']==my_calendar.sessions('2026-09-28','2026-10-02')
    with pytest.raises(ValueError,match='unsupported-model-venue'):venue_window_policy('UNKNOWN')


def test_my_training_reload_and_four_window_inference_are_venue_bound(my_calendar,tmp_path,monkeypatch):
    data=history(my_calendar)
    folder=run_training(data,calendar=my_calendar,start='2025-01-02',end='2026-08-28',
        fit_cutoff_ms=my_calendar.close_ms('2026-08-28')+1000,
        folds=[{'calibration_start':'2026-01-02','evaluation_start':'2026-05-04','evaluation_end':'2026-08-28','kind':'holdout'}],
        model_dir=tmp_path/'models',policy='research-retrospective',declared_gaps=GAPS,
        generated_at=datetime(2026,9,1,tzinfo=timezone.utc))
    contract=json.loads((folder/'model_contract.json').read_text())
    assert contract['adjustment_policy']['currency']=='MYR'
    assert contract['calendar_policy']['name']=='XKLS'
    assert contract['window_policy']==venue_window_policy('XKLS')
    model,_=load_artifact(folder,trusted_root=folder.parent,expected_contract=contract)
    cutoff=my_calendar.close_ms('2026-09-30')+1000
    payload=build_forecasts(data,[{'code':'MY.0166','stock_id':123}],model=model,contract=contract,
        model_ref={'artifact_known_at_ms':int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)},
        calendar=my_calendar,issued_at_ms=cutoff,as_of_ms=cutoff)
    assert len(payload['forecasts'])==4
    assert any(r['status']=='available' for r in payload['forecasts'])
    assert all(r['reference']['currency']=='MYR' for r in payload['forecasts'])
    # Any crossing quantile is still rejected; available rows retain MYR without
    # pretending a fictional fit is a promoted candidate.
    assert payload['validated_candidate_count']==0
    for r in payload['forecasts']:
        assert r['status']=='available' or 'crossing' in ';'.join(r['reasons']) or 'invalid' in ';'.join(r['reasons'])
    with pytest.raises(ValueError,match='calendar-mismatch'):
        validate_runtime_policy(contract,feature_variant='no-benchmark',calendar_name='XNYS',calendar_version=my_calendar.version,adjustment='forward-excluding-dividends',currency='USD')
    # Exercise the actual offline command with real trusted fictional artifacts;
    # neither collection nor another fit may be hidden behind the new input mode.
    csv_path=tmp_path/'history.csv'
    with csv_path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=HISTORY_COLUMNS);writer.writeheader();writer.writerows(data.rows)
    receipt_path=tmp_path/'receipt.json';receipt_path.write_text(json.dumps(data.receipts[0]))
    instruments_path=tmp_path/'instruments.json';instruments_path.write_text(json.dumps([{'code':'MY.0166','stock_id':123}]))
    spec=importlib.util.spec_from_file_location('my_predict',SCRIPT/'predict.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(type(model),'fit',lambda *a,**k:pytest.fail('offline inference must not fit'))
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('offline inference must not collect'))
    output=tmp_path/'predictions'
    assert module.main(['--offline','--calendar','XKLS','--csv-glob',str(csv_path),'--receipt',str(receipt_path),
        '--instruments',str(instruments_path),'--model-folder',str(folder),'--model-dir',str(folder.parent),
        '--output-dir',str(output),'--as-of',datetime.fromtimestamp(cutoff/1000,timezone.utc).isoformat()])==0
    forecasts=json.loads(next(output.glob('*/predictions.json')).read_text())['forecasts']
    assert len(forecasts)==4 and all(r['code']=='MY.0166' and r['reference']['currency']=='MYR' for r in forecasts)


def test_my_labels_keep_actual_availability_and_pending_missing_sessions(my_calendar):
    data=history(my_calendar);origin='2026-09-23';late=my_calendar.close_ms('2026-09-30')+100
    revised=assemble([dict(r,known_at_ms=late) for r in data.rows],data.receipts)
    cutoff=my_calendar.close_ms(origin)+1000
    labels=make_labels(revised,'MY.0166',origin,calendar=my_calendar,fit_cutoff_ms=late,
        origin_cutoff_ms=cutoff,policy='research-retrospective',declared_gaps=GAPS)
    assert all(r.get('label_available_at',late)>=late for r in labels)
    assert any(r['status']=='complete' for r in labels)
    earlier=make_labels(data,'MY.0166',origin,calendar=my_calendar,fit_cutoff_ms=cutoff,
        origin_cutoff_ms=cutoff,policy='research-retrospective',declared_gaps=GAPS)
    assert all(r['status']=='pending' for r in earlier)


def test_explicit_predict_cli_rejects_online_or_partial_inputs(monkeypatch):
    spec=importlib.util.spec_from_file_location('multi_predict',SCRIPT/'predict.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('provider subprocess must never run'))
    with pytest.raises(ValueError,match='requires-offline'):
        module.main(['--csv-glob','fictional.csv','--receipt','r.json','--instruments','i.json'])
    with pytest.raises(ValueError,match='requires-offline'):
        module.main(['--offline','--csv-glob','fictional.csv'])
    with pytest.raises(ValueError,match='malaysian-inference'):
        module.main(['--offline','--calendar','XKLS'])
