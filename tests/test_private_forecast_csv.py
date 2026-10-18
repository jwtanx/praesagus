"""Fictional private exports only; never source admission, broker access or fitting."""
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from ingest import forecast_scenario as core

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('private_csv_cli',ROOT/'scripts/daily-market-brief/prepare_private_forecast.py')
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
spec=importlib.util.spec_from_file_location('private_csv_cases',ROOT/'tests/test_forecast_scenario.py')
cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
STAMP=datetime(2026,10,22,0,0,tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network not authorized'))


@pytest.fixture
def private(tmp_path):
    p=tmp_path.resolve()/'private';p.mkdir(mode=0o700);return p


def packet(kind='legacy-raw',fixture=True):
    e,a,issue,cutoff=cases.private_case(kind)
    if fixture:e['classification']='authored_fixture';cases.reseal(e,a)
    return e,a,issue,cutoff


def prepare(kind='legacy-raw',fixture=True):
    e,a,issue,cutoff=packet(kind,fixture)
    return export.prepare_export(dict(evidence=e,admission=a),batch_mode=False,issued_at=issue,report_cutoff=cutoff)


def rows(result):return list(csv.DictReader(io.StringIO(result['csv_bytes'].decode())))


def put(path,value):
    path.write_text(json.dumps(value,allow_nan=False));path.chmod(0o600);return str(path)


def arguments(private,kind='legacy-raw',batch=False):
    e,a,issue,cutoff=packet(kind)
    if batch:
        item={k:e['instrument'][k] for k in ('ticker','market','currency')}
        item.update(evidence=e,admission=a)
        argv=['--batch',put(private/'batch.json',dict(schema_version=1,items=[item]))]
    else:argv=['--evidence',put(private/'evidence.json',e),'--admission',put(private/'admission.json',a)]
    return argv+['--issued-at',issue,'--cutoff',cutoff,'--output-parent',str(private)]


@pytest.mark.parametrize('kind',['legacy-raw','legacy-cash','generic-us-raw','generic-us-cash','generic-my-raw','generic-my-cash'])
def test_private_api_numbers_raw_precision_unknown_public_rights_and_immutable_bundle(private,kind):
    e,a,issue,cutoff=packet(kind);before=deepcopy((e,a))
    expected=core.build_private_forecast_scenario(e,admission=a,issued_at=issue,report_cutoff=cutoff)
    result=export.prepare_export(dict(evidence=e,admission=a),batch_mode=False,issued_at=issue,report_cutoff=cutoff)
    assert (e,a)==before
    row=rows(result)[0];assert row['purpose']==core.PRIVATE_PURPOSE and row['is_demo']=='True'
    assert row['classification']=='fixture_only' and row['status']=='generated'
    assert float(row['point'])==expected['estimates']['display_point']
    assert float(row['low'])==expected['estimates']['display_low'] and float(row['high'])==expected['estimates']['display_high']
    audit=result['audit']['rows'][0];assert audit['result']==expected
    assert audit['result']['estimates']['point']==expected['estimates']['point']
    assert row['evidence_sha256']==cases.sha(e) and row['admission_sha256']==cases.sha(a)
    assert row['result_sha256']==cases.sha(expected) and row['public_derived_forecast']=='unknown'
    assert 'report_fields' not in audit['result']
    folder=export.write_export(str(private),result,generated_at=STAMP)
    assert folder.name=='2026-10-22_000000' and folder.stat().st_mode&0o777==0o700
    assert {p.name for p in folder.iterdir()}=={'forecasts.csv','private-audit.json','manifest.json'}
    manifest=json.loads((folder/'manifest.json').read_bytes())
    assert manifest['created_at']=='2026-10-22T00:00:00+00:00' and manifest['is_demo'] is True
    assert 'not whole-window' in manifest['notice'] and 'measured 95 percent' in manifest['notice']
    assert manifest['public_use']=='not_granted_by_export' and manifest['model_status']=='research_only_uncalibrated'
    for name,meta in manifest['artifacts'].items():
        raw=(folder/name).read_bytes();assert meta==dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    assert all(p.stat().st_mode&0o777==0o600 for p in folder.iterdir())
    before_files={p.name:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(FileExistsError):export.write_export(str(private),result,generated_at=STAMP)
    assert {p.name:p.read_bytes() for p in folder.iterdir()}==before_files


def batch_item(ticker='OTHER'):
    e,a,_,_=packet('generic-us-raw');e['instrument']['ticker']=ticker;cases.reseal(e,a)
    return dict(ticker=ticker,market='US',currency='USD',evidence=e,admission=a)


@pytest.mark.parametrize('missing',['evidence','admission','both'])
def test_batch_missing_pair_rows_are_withheld_and_numeric_cells_blank(missing):
    item=batch_item()
    if missing in ('evidence','both'):item['evidence']=None
    if missing in ('admission','both'):item['admission']=None
    result=export.prepare_export(dict(schema_version=1,items=[item]),batch_mode=True,
        issued_at=cases.ISSUE,report_cutoff=cases.CUTOFF)
    row=rows(result)[0]
    assert row['ticker']=='OTHER' and row['status']=='withheld'
    assert row['point']==row['low']==row['high']==row['reference_close']==''
    assert 'admission_missing' in row['reasons']
    assert result['audit']['rows'][0]['result']['estimates'] is None
    assert result['counts']['generated']==0


def test_singleton_missing_admission_withholds_without_inventing_identity():
    e,a,issue,cutoff=packet()
    result=export.prepare_export(dict(evidence=e,admission=None),batch_mode=False,issued_at=issue,report_cutoff=cutoff)
    assert rows(result)[0]['ticker']=='SPY' and rows(result)[0]['point']==''
    with pytest.raises(export.PrivateForecastExportError):
        export.prepare_export(dict(evidence=None,admission=a),batch_mode=False,issued_at=issue,report_cutoff=cutoff)


@pytest.mark.parametrize('bad',['duplicate','unknown-market','currency','cross-evidence','cross-admission','public-admission',
    'wrong-purpose','item-extra','item-missing','wrapper-extra','bool-version','too-many','public-result'])
def test_batch_shape_identity_purpose_bypass_errors_are_fatal_before_calculation(monkeypatch,bad):
    item=batch_item();payload=dict(schema_version=1,items=[item])
    if bad=='duplicate':payload['items'].append(deepcopy(item))
    elif bad=='unknown-market':item['market']='HK'
    elif bad=='currency':item['currency']='MYR'
    elif bad=='cross-evidence':item['evidence']['instrument']['ticker']='DIFFERENT';cases.reseal(item['evidence'],item['admission'])
    elif bad=='cross-admission':item['admission']=batch_item('DIFFERENT')['admission']
    elif bad=='public-admission':item['admission'].pop('purpose')
    elif bad=='wrong-purpose':item['admission']['purpose']='public_report'
    elif bad=='item-extra':item['result']=core._unavailable(['schema'])
    elif bad=='item-missing':item.pop('admission')
    elif bad=='wrapper-extra':payload['extra']=1
    elif bad=='bool-version':payload['schema_version']=True
    elif bad=='too-many':payload['items']=[item]*51
    elif bad=='public-result':item['evidence']=core._unavailable(['schema'])
    monkeypatch.setattr(export,'build_private_forecast_scenario',lambda *a,**k:pytest.fail('must preflight first'))
    with pytest.raises(export.PrivateForecastExportError,match='^private-forecast-export-invalid-input$'):
        export.prepare_export(payload,batch_mode=True,issued_at=cases.ISSUE,report_cutoff=cases.CUTOFF)


def test_fifty_independent_rows_bounded_and_empty_batch_explicit():
    result=export.prepare_export(dict(schema_version=1,items=[batch_item('FIX'+str(n)) for n in range(50)]),
        batch_mode=True,issued_at=cases.ISSUE,report_cutoff=cases.CUTOFF)
    assert len(rows(result))==50 and result['counts']==dict(total=50,generated=50,withheld=0,is_demo=50)
    empty=export.prepare_export(dict(schema_version=1,items=[]),batch_mode=True,issued_at=cases.ISSUE,report_cutoff=cases.CUTOFF)
    assert not rows(empty) and empty['counts']['total']==0


@pytest.mark.parametrize('value',['=1+2','+SUM(1)','-SOURCE','@DANGEROUS','  =1',"'=already"])
def test_formula_like_text_is_escaped_and_full_private_audit_preserved(value):
    e,a,issue,cutoff=packet();e['rights']['public_derived_forecast']=value;cases.reseal(e,a)
    result=export.prepare_export(dict(evidence=e,admission=a),batch_mode=False,issued_at=issue,report_cutoff=cutoff)
    assert export.csv_cell(value)=="'"+value
    if value.strip()==value:
        assert rows(result)[0]['public_derived_forecast']=="'"+value
        assert result['audit']['rows'][0]['result']['provenance']['rights']['public_derived_forecast']==value
    else:
        assert rows(result)[0]['status']=='withheld' and rows(result)[0]['point']==''
    assert export.csv_cell(-.0123)==-.0123


def test_denying_private_rights_produces_withheld_not_bypassed_numbers():
    e,a,issue,cutoff=packet();e['rights']['private_retention_research']='unknown';cases.reseal(e,a)
    result=export.prepare_export(dict(evidence=e,admission=a),batch_mode=False,issued_at=issue,report_cutoff=cutoff)
    assert rows(result)[0]['status']=='withheld' and 'rights' in rows(result)[0]['reasons']
    assert rows(result)[0]['point']==''


@pytest.mark.parametrize('batch',[False,True])
def test_cli_singleton_and_batch_real_subprocess_private_only(private,batch):
    argv=arguments(private,batch=batch)
    result=subprocess.run([sys.executable,str(ROOT/'scripts/daily-market-brief/prepare_private_forecast.py'),*argv],
        capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and result.stderr=='' and str(private) not in result.stdout
    assert json.loads(result.stdout)['counts']['generated']==1
    folders=[p for p in private.iterdir() if p.is_dir()]
    assert len(folders)==1 and (folders[0]/'forecasts.csv').exists()


@pytest.mark.parametrize('extra',[['--evidence','/PRIVATE-CANARY/x'],['--admission','/PRIVATE-CANARY/x']])
def test_batch_legacy_arguments_mutually_exclusive_before_any_read(private,capsys,monkeypatch,extra):
    argv=arguments(private,batch=True)+extra
    monkeypatch.setattr(export.private_io,'read_private_json',lambda *a,**k:pytest.fail('must not read'))
    assert export.main(argv)==1
    assert json.loads(capsys.readouterr().out)==dict(status='failed',reason='arguments-invalid')


@pytest.mark.parametrize('bad',['duplicate-json','nan','oversize','depth','symlink','mode'])
def test_input_guards_are_reused_no_canary_disclosure_or_outputs(private,capsys,bad):
    argv=arguments(private,batch=True);path=private/'batch.json'
    if bad=='duplicate-json':path.write_text('{"schema_version":1,"items":[],"items":[]}')
    elif bad=='nan':path.write_text('{"PRIVATE-CANARY":NaN}')
    elif bad=='oversize':path.write_bytes(b'x'*(export.MAX_BYTES+1))
    elif bad=='depth':path.write_text('['*13+'0'+']'*13)
    elif bad=='symlink':path.unlink();path.symlink_to(private/'unrelated')
    else:path.chmod(0o644)
    assert export.main(argv)==1
    output=capsys.readouterr().out;assert 'CANARY' not in output and str(private) not in output
    assert json.loads(output)['reason']=='private-input-invalid' and not [p for p in private.iterdir() if p.is_dir()]


@pytest.mark.parametrize('bad',['public','git','symlink','parent-mode','failed-audit','failed-manifest','failed-open'])
def test_private_destination_bounds_and_rollback(private,monkeypatch,bad):
    result=prepare();target=private
    if bad=='public':target=private/'public';target.mkdir(mode=0o700)
    elif bad=='git':(private/'.git').write_text('fictional checkout')
    elif bad=='symlink':target=private/'alias';target.symlink_to(private,target_is_directory=True)
    elif bad=='parent-mode':private.chmod(0o755)
    elif bad in ('failed-audit','failed-manifest'):
        original=export.private_io._write_file
        def fail(fd,name,value):
            if name==('private-audit.json' if bad=='failed-audit' else 'manifest.json'):raise OSError('PRIVATE-CANARY')
            return original(fd,name,value)
        monkeypatch.setattr(export.private_io,'_write_file',fail)
    else:
        original=export.os.open
        def fail(path,*a,**k):
            if path=='2026-10-22_000000':raise OSError('PRIVATE-CANARY')
            return original(path,*a,**k)
        monkeypatch.setattr(export.os,'open',fail)
    with pytest.raises((ValueError,OSError)):export.write_export(str(target),result,generated_at=STAMP)
    assert not (private/'2026-10-22_000000').exists()


def test_timestamps_utc_and_output_collision_does_not_change_existing_bytes(private):
    result=prepare();folder=export.write_export(str(private),result,generated_at=STAMP)
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(FileExistsError):export.write_export(str(private),result,generated_at=STAMP)
    assert {p.name:p.read_bytes() for p in folder.iterdir()}==before
    with pytest.raises(ValueError):export.write_export(str(private),result,generated_at=STAMP.replace(tzinfo=None))


def test_batch_byte_limit_and_no_public_api_called(monkeypatch):
    payload=dict(schema_version=1,items=[batch_item()]);monkeypatch.setattr(export,'MAX_BYTES',10)
    with pytest.raises(export.PrivateForecastExportError):
        export.prepare_export(payload,batch_mode=True,issued_at=cases.ISSUE,report_cutoff=cases.CUTOFF)
    monkeypatch.setattr(export,'MAX_BYTES',2*1024*1024)
    monkeypatch.setattr(core,'build_forecast_scenario',lambda *a,**k:pytest.fail('no public calculator'))
    monkeypatch.setattr(core,'apply_scenario_to_row',lambda *a,**k:pytest.fail('no public mapper'))
    assert prepare()['counts']['generated']==1
