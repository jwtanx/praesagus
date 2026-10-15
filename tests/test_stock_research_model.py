"""Fictional offline model implementation checks; no actual accuracy evidence."""
from datetime import datetime, timezone
import importlib.util
import json
import math
import subprocess
import csv
from pathlib import Path
import sys

import numpy as np
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/stock-research'
sys.path.insert(0,str(SCRIPT))
for name in ('storage','data','market_calendar','features','model','train'):
    existing=sys.modules.get(name)
    if existing is not None and Path(getattr(existing,'__file__','')).resolve()==(SCRIPT/f'{name}.py').resolve():
        continue
    spec=importlib.util.spec_from_file_location(name,SCRIPT/f'{name}.py')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
from data import GAPS, assemble
from features import FEATURE_COLUMNS
from market_calendar import MarketCalendar
from model import (GATES, ModelConfig, QuantileModel, clean_records, freeze, load_artifact,
    matrix, research_fit, save_artifact, score_predictions, strong_gates, train_frozen)
from storage import Generation, canonical, sha

@pytest.fixture(scope='module')
def calendar():return MarketCalendar('2025-01-01','2027-12-31')


def records(calendar,start='2026-01-02',end='2026-09-30'):
    days=calendar.sessions(start,end);result=[]
    for i,day in enumerate(days):
        features={key:0. for key in FEATURE_COLUMNS}
        features.update(volatility20=.01,benchmark_missing=1,benchmark_relative20=None,
            benchmark_volatility20=None,instrument_class='stock',signed_leverage=1,
            window_lead=1,window_count=1,metadata_missing=0)
        features['return1']=math.sin(i/7)*.01
        next_day=calendar.windows(day)['1d'][0]
        result.append({'code':'US.DEMO','origin':day,'horizon':'1d','features':features,
            'low_return':-.02+math.sin(i/7)*.005,'high_return':.02+math.sin(i/7)*.005,
            'terminal_logreturn':math.sin(i/7)*.005,'status':'complete',
            'origin_at_ms':calendar.close_ms(day)+1000,'feature_known_at_ms':calendar.close_ms(day),
            'label_available_at':calendar.close_ms(next_day)+1000,'end_at_ms':calendar.close_ms(next_day),
            'origin_session_index':i,'window_distance':1,'policy':'strict'})
    return result


def frozen(rows,calendar):
    return freeze(rows,folds=[{'calibration_start':'2026-05-01','evaluation_start':'2026-07-01','evaluation_end':'2026-09-30','kind':'holdout'}],
        provenance={'fixture':True,'point_in_time':False,'calendar':{'name':'XNYS','version':calendar.version,'schedule_sha256':sha(canonical([{'session_date':d,'close_at_ms':calendar.close_ms(d)} for d in calendar._sessions]))},'adjustment_policy':{'required_basis':'forward-excluding-dividends','currency':'USD','fixture':True}},fit_cutoff_ms=calendar.close_ms('2026-10-02'))


def test_nine_models_baseline_calibration_reproducible(calendar):
    rows=records(calendar);a=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1);b=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    assert len(a.estimators)==9
    assert all(e.early_stopping is False for e in a.estimators.values())
    p=a.raw_predictions(rows[70:80]);other=b.raw_predictions(rows[70:80])
    np.testing.assert_array_equal(p['model'],other['model'])
    a.calibrate(rows[65:95],cutoff_ms=rows[96]['origin_at_ms']-1);assert a.calibrated
    prediction=a.predict(rows[100:110]);assert prediction['model'].shape==(10,3,3)
    with pytest.raises(ValueError,match='already-calibrated'):a.calibrate(rows[100:110],cutoff_ms=rows[111]['origin_at_ms']-1)
    with pytest.raises(ValueError,match='calibration-origin-before-fit-cutoff'):b.calibrate(rows[:10],cutoff_ms=rows[11]['origin_at_ms']-1)
    # An entirely unseen window/class has no silently substituted baseline.
    altered=dict(rows[110],horizon='next_week')
    with pytest.raises(ValueError,match='matched-baseline'):a.predict([altered])


def test_freeze_purge_empty_and_no_future_labels(calendar):
    rows=records(calendar);receipt=frozen(rows,calendar)
    model,evaluation=train_frozen(rows,receipt,calendar=calendar)
    assert model is not None and evaluation['folds'][0]['status']=='evaluated'
    late=[dict(r,label_available_at=calendar.close_ms('2026-10-02')) for r in rows]
    model,evaluation=train_frozen(late,frozen(late,calendar),calendar=calendar)
    assert model is None and evaluation['folds'][0]['status']=='insufficient-empty-purged-fold'
    fitted,report=research_fit(late,frozen(late,calendar))
    assert fitted.fitted and not fitted.calibrated
    assert report['status']=='unvalidated-present-cutoff-research-fit'
    with pytest.raises(ValueError,match='frozen-data'):train_frozen(rows[:-1],receipt,calendar=calendar)


def test_invalid_features_targets_and_schema(calendar):
    row=records(calendar)[0]
    with pytest.raises(ValueError,match='predicted-columns'):clean_records([row|{'predicted_low':1}])
    with pytest.raises(ValueError,match='future-feature'):clean_records([row|{'feature_known_at_ms':row['origin_at_ms']+1}])
    with pytest.raises(ValueError,match='observed-targets'):clean_records([row|{'terminal_logreturn':float('nan')}])
    with pytest.raises(ValueError,match='variant'):matrix([row],ModelConfig(feature_variant='with-benchmark'))
    with pytest.raises(ValueError,match='frozen-default'):QuantileModel(ModelConfig(max_iter=2))


def test_crossings_rejected_not_repaired(calendar):
    rows=records(calendar);model=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    model.offsets['model'][0,0]=100
    result=model.predict(rows[70:75])
    assert not result['valid'].any()
    assert (result['model'][:,0,0]>result['model'][:,0,1]).all()


def test_trusted_artifacts_roundtrip_and_rejections(calendar,tmp_path):
    rows=records(calendar);receipt=frozen(rows,calendar);model=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    gen=Generation(tmp_path,kind='stock-research-model',generated_at=datetime(2026,10,3,tzinfo=timezone.utc))
    gen.json('freeze.json',receipt);save_artifact(gen,model,receipt,{'fixture':True})
    folder=gen.finish(strong_model_accepted=False)
    contract=json.loads((folder/'model_contract.json').read_text())
    loaded,_=load_artifact(folder,trusted_root=tmp_path,expected_contract=contract)
    np.testing.assert_array_equal(model.predict(rows[70:75])['model'],loaded.predict(rows[70:75])['model'])
    with pytest.raises(ValueError,match='compatibility'):load_artifact(folder,trusted_root=tmp_path,expected_contract=contract|{'data_sha256':'wrong'})
    with pytest.raises(ValueError,match='outside-trusted'):load_artifact(folder,trusted_root=tmp_path/'other',expected_contract=contract)
    (folder/'model.joblib').write_bytes(b'not trusted')
    with pytest.raises(ValueError,match='integrity'):load_artifact(folder,trusted_root=tmp_path,expected_contract=contract)


def test_gates_never_promote_synthetic_and_retain_invalid(calendar):
    rows=records(calendar)[:25];pred=[]
    for row in rows:
        actual=np.asarray([row[t] for t in ('low_return','high_return','terminal_logreturn')])
        p=np.column_stack([actual-.03,actual+.001,actual+.03])
        pred.append({'record':row,'model':p.tolist(),'baseline':(p+.01).tolist(),'valid':True})
    score=score_predictions(pred)
    assert score['dates']==25 and score['bootstrap_replicates']==1000
    result=strong_gates(score,evidence={'synthetic':True},resources={})
    assert result['status']=='failed-or-insufficient'
    assert 'missing-evidence:actual_data' in result['reasons']
    assert 'insufficient-oos-dates' in result['reasons']
    assert score_predictions([])['status']=='insufficient-no-predictions'
    assert score_predictions([pred[0]|{'valid':False}])['status']=='failed-invalid-forecasts'


def test_offline_reader_to_frozen_empty_fold_generation(calendar,tmp_path):
    from train import run_training
    from storage import HISTORY_COLUMNS
    days=calendar.sessions('2026-01-02','2026-09-30');known=calendar.close_ms('2026-10-02')
    rows=[]
    for day in days:
        close=calendar.close_ms(day);row={key:None for key in HISTORY_COLUMNS}
        row.update(code='US.DEMO',session_date=day,open=100,low=99,high=101,close=100,
            volume=1000,turnover=100000,currency='USD',adjustment='forward-excluding-dividends',
            source='fixture',source_at_ms=close,raw_time_key=close,raw_date=int(day.replace('-','')),raw_time_zone=-300,
            time_zone_unit_status='unverified',time_zone_unit_source_url='https://example.com',provider_finality_status='unverified',
            retrieved_at_ms=known,known_at_ms=known,price_known_at_ms=known,currency_known_at_ms=known,
            revision_vintage='fixture',completed=True,completion_status='completed',volume_precision=0,
            currency_source_url='https://example.com',currency_evidence_hash='a'*64,currency_status='verified')
        rows.append(row)
    history=assemble(rows,[{'identity_bindings':[{'code':'US.DEMO','stock_id':1}]}])
    folder=run_training(history,calendar=calendar,start='2026-04-01',end='2026-09-15',fit_cutoff_ms=known,
        folds=[{'calibration_start':'2026-05-01','evaluation_start':'2026-07-01','evaluation_end':'2026-09-15','kind':'holdout'}],
        model_dir=tmp_path,policy='research-retrospective',declared_gaps=GAPS,
        generated_at=datetime(2026,10,3,tzinfo=timezone.utc))
    assert (folder/'freeze.json').exists()
    manifest=json.loads((folder/'manifest.json').read_text())
    evaluation=json.loads((folder/'evaluation.json').read_text())
    assert manifest['strong_model_accepted'] is False and not manifest['model_available']
    assert evaluation['folds'][0]['status']=='insufficient-empty-purged-fold'
    help_result=subprocess.run([sys.executable,str(SCRIPT/'train.py'),'--help'],capture_output=True,text=True,timeout=30)
    assert help_result.returncode==0 and '--csv-glob' in help_result.stdout
    missing=subprocess.run([sys.executable,str(SCRIPT/'train.py'),'--state-dir',str(tmp_path/'absent')],capture_output=True,text=True,timeout=30)
    assert missing.returncode==2 and 'training-unavailable' in missing.stdout and not missing.stderr
    csv_dir=tmp_path/'csv';csv_dir.mkdir()
    with (csv_dir/'history.csv').open('w') as file:
        writer=csv.DictWriter(file,fieldnames=HISTORY_COLUMNS);writer.writeheader();writer.writerows(rows)
    receipt_path=tmp_path/'receipt.json';receipt_path.write_text(json.dumps(history.receipts[0]))
    command=[sys.executable,str(SCRIPT/'train.py'),'--csv-dir',str(csv_dir),'--receipt',str(receipt_path),
        '--model-dir',str(tmp_path/'cli-models'),'--policy','research-retrospective',
        '--start','2026-01-02','--end','2026-09-30','--calibration-start','2026-05-01',
        '--holdout-start','2026-07-01','--fit-cutoff','2026-10-03T00:00:00Z']
    for gap in sorted(GAPS):command+=['--declare-gap',gap]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    assert result.returncode==0, result.stdout+result.stderr
    manifest=json.loads((Path(json.loads(result.stdout)['generation'])/'manifest.json').read_text())
    assert manifest['strong_model_accepted'] is False and not manifest['model_available']


def test_all_missing_feature_variant_is_explicit_and_immutable(calendar):
    rows=records(calendar);model=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    assert FEATURE_COLUMNS.index('benchmark_relative20') not in model.active_columns
    with pytest.raises(ValueError,match='missing-feature-variant-changed'):
        model.predict([rows[70]|{'features':rows[70]['features']|{'benchmark_relative20':.01}}])


def artificial_predictions(rows, *, fold_kind='holdout', class_name=None, start_index=0):
    result=[]
    for i,row in enumerate(rows):
        row=dict(row)
        if class_name is not None:row['features']=row['features']|{'instrument_class':class_name}
        actual=np.asarray([row[t] for t in ('low_return','high_return','terminal_logreturn')])
        model=np.column_stack([actual-.03,actual+.001,actual+.03])
        baseline=np.column_stack([actual-.04,actual+.01,actual+.04])
        result.append({'record':row,'model':model.tolist(),'baseline':baseline.tolist(),'valid':True,'fold_kind':fold_kind})
    return result


def test_common_date_blocks_do_not_reanchor_late_group(calendar):
    rows=records(calendar)[:35]
    all_rows=artificial_predictions(rows)
    late_rows=artificial_predictions([r|{'code':'US.OTHER'} for r in rows[5:]],class_name='ordinary-etf')
    score=score_predictions(all_rows+late_rows)
    late=next(group for key,group in score['groups'].items() if 'ordinary-etf' in key)
    assert late['block_anchor_session_index']==score['block_anchor_session_index']==0
    assert late['block_ids']==[0,1,2,3]  # Starts in the MIDDLE of shared first block.
    assert late['bootstrap_missing_draws']==0


def test_disjoint_scopes_and_overall_date_minimum(calendar):
    from model import evaluate_scopes
    rows=records(calendar)
    report=evaluate_scopes(artificial_predictions(rows[:70],fold_kind='walk-forward')+
        artificial_predictions(rows[70:],fold_kind='holdout'),evidence={},resources={})
    assert report['scopes']['walk-forward']['score']['dates']==70
    assert report['scopes']['holdout']['score']['dates']==len(rows)-70
    assert report['scopes']['holdout']['score']['overall_oos_dates']==len(rows)
    assert report['status']=='failed-or-insufficient'
    # Overall252 is not a new252 EACH-cohort requirement.
    score=report['scopes']['holdout']['score']|{'overall_oos_dates':252}
    gates=strong_gates(score,evidence={},resources={})
    assert 'insufficient-oos-dates' not in gates['reasons']


def test_coverage_mismatch_blocks_width_claim(calendar):
    score=score_predictions(artificial_predictions(records(calendar)[:25]),evaluation_kind='holdout')
    key=next(iter(score['groups']))
    score['groups'][key]['endpoints']['low_return']['model']['coverage']=.9
    score['groups'][key]['endpoints']['low_return']['baseline']['coverage']=.91
    report=strong_gates(score,evidence={},resources={})
    assert 'matched-coverage-width-unassessable:low_return' in report['groups'][key]['reasons']


def test_explicit_fit_and_calibration_cutoffs(calendar):
    rows=records(calendar)
    with pytest.raises(TypeError):QuantileModel().fit(rows[:60])
    with pytest.raises(ValueError,match='fit-cutoff-availability'):
        QuantileModel().fit(rows[:60],cutoff_ms=rows[20]['origin_at_ms'])
    model=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    with pytest.raises(ValueError,match='calibration-cutoff-availability'):
        model.calibrate(rows[65:95],cutoff_ms=rows[80]['origin_at_ms'])
    with pytest.raises(ValueError,match='already-fitted'):
        model.fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)


def test_joint_envelope_date_weighting(calendar):
    rows=records(calendar)[:2]
    predictions=artificial_predictions([rows[0]]+[rows[1]|{'code':f'US.DEMO{i}'} for i in range(9)])
    predictions[0]['model'][0][0]=rows[0]['low_return']+.0001  # Date1 misses, date2 nine names contained.
    score=score_predictions(predictions)
    group=next(iter(score['groups'].values()))
    assert group['joint_envelope_containment']==pytest.approx(.5)


def qualifying_gate_inputs():
    group={'dates':100,'blocks':10,'relative_improvement':[.06]*5,'paired_ci':[[.001]*5,[.01]*5],
        'endpoints':{target:{name:{'coverage':.9,'width':1.} for name in ('model','baseline')} for target in ('low_return','high_return')}}
    score={'status':'scored','dates':120,'overall_oos_dates':252,'evaluation_kind':'holdout','invalid':0,
        'gate_metrics':['low_mae','high_mae','all_pinball','terminal_mae','terminal_pinball'],
        'relative_improvement':[.06]*5,'paired_ci':[[.001]*5,[.01]*5],'groups':{'stock-1d':group}}
    evidence={key:True for key in ('actual_data','contemporary_membership','delistings','origin_vintages','untouched_holdout','walk_forward','immutable_origin_baselines')}
    resources={'actual_target_machine':True,'peak_process_bytes':1000000,'wall_seconds':1,'inference_names':110,'inference_seconds':1}
    return score,evidence,resources


@pytest.mark.parametrize('failure,reason',[
    ('improvement','failed-improvement:low_mae'),('nearzero','unassessable-baseline:low_mae'),
    ('ci','failed-improvement:low_mae'),('dates','insufficient-oos-dates')])
def test_independent_frozen_gate_rejections(failure,reason):
    score,evidence,resources=qualifying_gate_inputs()
    if failure=='improvement':score['relative_improvement'][0]=.049
    if failure=='nearzero':score['relative_improvement'][0]=None
    if failure=='ci':score['paired_ci'][0][0]=0
    if failure=='dates':score['overall_oos_dates']=251
    assert reason in strong_gates(score,evidence=evidence,resources=resources)['reasons']


@pytest.mark.parametrize('coverage',[.849,.951])
def test_independent_endpoint_coverage_rejections(coverage):
    score,evidence,resources=qualifying_gate_inputs()
    score['groups']['stock-1d']['endpoints']['low_return']['model']['coverage']=coverage
    report=strong_gates(score,evidence=evidence,resources=resources)
    assert 'coverage:low_return' in report['groups']['stock-1d']['reasons']


def test_gate_qualification_never_auto_promotes_and_subgroups_remain_separate():
    score,evidence,resources=qualifying_gate_inputs()
    report=strong_gates(score,evidence=evidence,resources=resources)
    assert report['status']=='qualified-for-human-review'
    assert report['promotion']=='not-authorized-by-checker'
    evidence['origin_vintages']=False
    assert strong_gates(score,evidence=evidence,resources=resources)['status']=='failed-or-insufficient'
    evidence['origin_vintages']=True
    score['groups']['stock-1d']['dates']=99
    assert 'insufficient-subgroup' in strong_gates(score,evidence=evidence,resources=resources)['groups']['stock-1d']['reasons']
    score['groups']['stock-1d']['endpoints']['high_return']['model']['width']=1.01
    assert 'width:high_return' in strong_gates(score,evidence=evidence,resources=resources)['groups']['stock-1d']['reasons']


def test_sparse_group_missing_bootstrap_draws_are_unassessable(calendar):
    rows=records(calendar)[:35]
    predictions=artificial_predictions(rows)+artificial_predictions([rows[-1]|{'code':'US.OTHER'}],class_name='ordinary-etf')
    score=score_predictions(predictions)
    group=next(value for key,value in score['groups'].items() if 'ordinary-etf' in key)
    assert group['bootstrap_missing_draws']>0
    assert group['paired_ci'][0]==[None]*5


def test_contract_policies_rejected_before_deserialization(calendar,tmp_path,monkeypatch):
    import joblib
    rows=records(calendar);receipt=frozen(rows,calendar)
    model=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    generation=Generation(tmp_path,kind='stock-research-model',generated_at=datetime(2026,10,3,tzinfo=timezone.utc))
    generation.json('freeze.json',receipt);save_artifact(generation,model,receipt,{})
    folder=generation.finish()
    contract=json.loads((folder/'model_contract.json').read_text())
    contract['calendar_policy']['version']='incompatible'
    data=canonical(contract);(folder/'model_contract.json').write_bytes(data)
    manifest=json.loads((folder/'manifest.json').read_text())
    manifest['artifacts']['model_contract.json'].update(sha256=sha(data),bytes=len(data))
    (folder/'manifest.json').write_bytes(canonical(manifest))
    def forbidden(*args,**kwargs):pytest.fail('deserialization reached before compatibility rejection')
    monkeypatch.setattr(joblib,'load',forbidden)
    with pytest.raises(ValueError,match='model-calendar-incompatible'):
        load_artifact(folder,trusted_root=tmp_path,expected_contract=contract)


@pytest.mark.parametrize('bad',['relative-nan','ci-infinite','width-nan','resource-nan','empty-groups','truncated-metrics'])
def test_gate_malformed_inputs_fail_closed(bad):
    score,evidence,resources=qualifying_gate_inputs()
    if bad=='relative-nan':score['relative_improvement'][0]=float('nan')
    if bad=='ci-infinite':score['paired_ci'][0][0]=float('-inf')
    if bad=='width-nan':score['groups']['stock-1d']['endpoints']['low_return']['model']['width']=float('nan')
    if bad=='resource-nan':resources['wall_seconds']=float('nan')
    if bad=='empty-groups':score['groups']={}
    if bad=='truncated-metrics':score['paired_ci'][0]=[]
    result=strong_gates(score,evidence=evidence,resources=resources)
    assert result['status']=='insufficient'
    assert 'malformed-or-nonfinite-gate-input' in result['reasons']


def test_load_uses_same_verified_bytes_not_second_read(calendar,tmp_path,monkeypatch):
    import model as module
    rows=records(calendar);receipt=frozen(rows,calendar)
    estimator=QuantileModel().fit(rows[:60],cutoff_ms=rows[61]['origin_at_ms']-1)
    generation=Generation(tmp_path,kind='stock-research-model',generated_at=datetime(2026,10,3,tzinfo=timezone.utc))
    generation.json('freeze.json',receipt);save_artifact(generation,estimator,receipt,{})
    folder=generation.finish();contract=json.loads((folder/'model_contract.json').read_text())
    original=module.private_read;counts={}
    def replaced(path):
        name=Path(path).name;counts[name]=counts.get(name,0)+1
        if counts[name]>1:return b'mutated-on-second-read'
        return original(path)
    monkeypatch.setattr(module,'private_read',replaced)
    loaded,_=load_artifact(folder,trusted_root=tmp_path,expected_contract=contract)
    assert loaded.fitted
    assert all(count==1 for count in counts.values())


def test_new_inference_data_checks_policy_not_training_data_hash(calendar):
    from model import validate_runtime_policy, WINDOW_POLICY
    contract={'data_sha256':'old-training-hash','feature_variant':'no-benchmark',
        'calendar_policy':{'name':'XNYS','version':calendar.version},
        'adjustment_policy':{'required_basis':'forward-excluding-dividends','currency':'USD'},'window_policy':WINDOW_POLICY}
    kwargs={'feature_variant':'no-benchmark','calendar_name':'XNYS','calendar_version':calendar.version,
        'adjustment':'forward-excluding-dividends','currency':'USD'}
    assert validate_runtime_policy(contract,**kwargs)
    for field,value in [('feature_variant','with-benchmark'),('calendar_version','other'),('adjustment','unadjusted'),('currency','UNKNOWN')]:
        with pytest.raises(ValueError):validate_runtime_policy(contract,**(kwargs|{field:value}))
