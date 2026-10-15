"""Offline bounded quantile research models. No automatic promotion or retraining.

Prepared records carry observed labels, origin-time features, availability and
window identity. Freeze receipts precede fits. Synthetic evidence never qualifies
for the actual-data gate, regardless of numerical results.
"""
from dataclasses import dataclass, asdict
from datetime import date
from importlib.metadata import version
import io
import json
import math
import platform
from pathlib import Path
import resource
import re
import stat
import time

import numpy as np
from threadpoolctl import threadpool_limits

from data import require, origin_weights
from features import FEATURE_COLUMNS
from storage import Generation, canonical, private_read, sha

TARGETS=('low_return','high_return','terminal_logreturn')
QUANTILES=(.05,.5,.95)
CLASSES={'stock':1,'ordinary-etf':2,'leveraged-etf':3,'inverse-etf':4}
BASELINE_VERSION='volatility-excursion-v1'
MAX_RECORDS=250000
GATES={'relative_improvement':.05,'near_zero':1e-8,'ci_level':.95,'bootstrap_replicates':1000,
       'minimum_block_sessions':10,'overall_dates':252,'subgroup_dates':100,'subgroup_blocks':10,
       'coverage_low':.85,'coverage_high':.95,'peak_bytes':2*1024**3,'train_seconds':600,
       'inference_seconds':10,'inference_names':110,'matched_coverage_abs_tolerance':1e-12}
WINDOW_POLICY={'calendar':'exchange-regular-sessions','horizons':['1d','3d','5d','next_week'],
    'next_week':'following-New-York-calendar-week-exchange-sessions-only',
    'reference':'latest-usable-completed-session-close','low_return':'min(low)/reference_close-1',
    'high_return':'max(high)/reference_close-1','terminal_logreturn':'log(last_close/reference_close)',
    'live_quotes':'excluded','crossings':'reject-no-repair'}


@dataclass(frozen=True)
class ModelConfig:
    """Fixed, sequential CPU fits; changing these invalidates the freeze receipt."""
    seed: int = 109
    bootstrap_seed: int = 113
    max_iter: int = 40
    max_leaf_nodes: int = 7
    max_depth: int = 3
    min_samples_leaf: int = 20
    learning_rate: float = .05
    l2_regularization: float = 1.
    threads: int = 1
    feature_variant: str = 'no-benchmark'
    calibration: str = 'prior-fold-additive-weighted-residual-quantiles-v1'

    def validate(self):
        require(self==ModelConfig(feature_variant=self.feature_variant),'configuration-not-frozen-default')
        require(self.feature_variant in ('no-benchmark','with-benchmark'),'unsupported-feature-variant')


def dependencies():
    return {name:version(name) for name in ('numpy','scikit-learn','joblib','threadpoolctl','exchange_calendars')} | {'python':platform.python_version()}


def record_key(row):
    return row['code'],row['origin'],row['horizon']


def clean_records(records):
    require(0<len(records)<=MAX_RECORDS,'training-record-budget-or-empty')
    unique={}
    for row in records:
        require(row.get('status')=='complete','uncompleted-label')
        require(not any(k.startswith('predicted') for k in row),'predicted-columns-not-labels')
        date.fromisoformat(row['origin'])
        require(set(row['features'])==set(FEATURE_COLUMNS),'feature-schema')
        require(all(type(row[k]) in (float,int) and math.isfinite(row[k]) for k in TARGETS),'observed-targets-required')
        require(row['low_return']<=row['high_return'],'observed-extrema-order')
        require(type(row['label_available_at']) is int and type(row['feature_known_at_ms']) is int,'availability-required')
        require(type(row['origin_at_ms']) is int and row['end_at_ms']>row['origin_at_ms'],'window-time-order')
        require(type(row['window_distance']) is int and row['window_distance']>0,'window-distance-required')
        require(row.get('policy') in ('strict','research-retrospective'),'evidence-policy-required')
        if row['policy']=='strict':require(row['feature_known_at_ms']<=row['origin_at_ms'],'future-feature')
        key=record_key(row)
        require(key not in unique or canonical(unique[key])==canonical(row),'duplicate-training-conflict')
        unique[key]=dict(row)
    return sorted(origin_weights(list(unique.values())),key=lambda r:(r['origin'],r['code'],r['horizon']))


def matrix(records, config):
    output=[]
    for row in records:
        features=row['features']
        require((features['benchmark_missing']==1)==(config.feature_variant=='no-benchmark'),'feature-variant-mismatch')
        values=[]
        for key in FEATURE_COLUMNS:
            value=features[key]
            if key=='instrument_class':
                require(value is None or value in CLASSES,'unsupported-instrument-class')
                value=CLASSES.get(value)
            require(value is None or type(value) in (int,float) and math.isfinite(value),'invalid-feature-value')
            values.append(np.nan if value is None else value)
        output.append(values)
    return np.asarray(output,dtype=float)


def weights(records):
    """Equal date weight, then equal instrument-origin, then available horizon."""
    counts={}
    for row in records:counts.setdefault(row['origin'],set()).add(row['code'])
    raw=np.asarray([row['weight']/len(counts[row['origin']]) for row in records])
    return raw/raw.sum()


def weighted_quantile(values, q, sample_weights):
    values=np.asarray(values,dtype=float);sample_weights=np.asarray(sample_weights,dtype=float)
    require(len(values)>0 and np.isfinite(values).all() and (sample_weights>0).all(),'invalid-quantile-input')
    order=np.argsort(values,kind='stable');cdf=np.cumsum(sample_weights[order]);cdf/=cdf[-1]
    return float(values[order[min(np.searchsorted(cdf,q),len(order)-1)]])


def condition(row):
    f=row['features']
    return (row['horizon'],f['window_lead'],f['window_count'],f['instrument_class'],f['signed_leverage'])


def volatility(row):
    f=row['features'];value=f['volatility20']
    require(type(value) in (int,float) and math.isfinite(value) and value>0,'volatility-unavailable')
    return value*math.sqrt(f['window_count'])


class QuantileModel:
    def __init__(self,config=ModelConfig()):
        config.validate();self.config=config;self.estimators={};self.baseline={}
        self.offsets={'model':np.zeros((3,3)),'baseline':np.zeros((3,3))};self.fitted=False;self.calibrated=False

    def fit(self, records, *, cutoff_ms):
        from sklearn.ensemble import HistGradientBoostingRegressor
        require(not self.fitted,'already-fitted-no-silent-retraining')
        records=clean_records(records)
        require(type(cutoff_ms) is int and all(eligible(r,cutoff_ms+1) for r in records),'fit-cutoff-availability')
        self.fit_cutoff_ms=cutoff_ms
        self.training_data_sha256=sha(canonical(records))
        x=matrix(records,self.config);w=weights(records)
        self.active_columns=tuple(i for i in range(x.shape[1]) if np.isfinite(x[:,i]).any())
        require(bool(self.active_columns),'no-observed-features')
        x=x[:,self.active_columns]
        self.training_keys=[record_key(r) for r in records]
        self.training_origin_start=min(r['origin'] for r in records)
        self.training_origin_end=max(r['origin'] for r in records)
        self.training_available_at=max(max(r['label_available_at'],r['feature_known_at_ms'],r['end_at_ms']) for r in records)
        groups={}
        for i,row in enumerate(records):groups.setdefault(condition(row),[]).append(i)
        for group,indices in groups.items():
            self.baseline[group]=np.asarray([[weighted_quantile([records[i][target]/volatility(records[i]) for i in indices],q,w[indices])
                for q in QUANTILES] for target in TARGETS])
        with threadpool_limits(limits=self.config.threads):
            for target in TARGETS:
                y=np.asarray([row[target] for row in records])
                for q in QUANTILES:
                    estimator=HistGradientBoostingRegressor(loss='quantile',quantile=q,early_stopping=False,
                        max_iter=self.config.max_iter,max_leaf_nodes=self.config.max_leaf_nodes,max_depth=self.config.max_depth,
                        min_samples_leaf=self.config.min_samples_leaf,learning_rate=self.config.learning_rate,
                        l2_regularization=self.config.l2_regularization,random_state=self.config.seed)
                    estimator.fit(x,y,sample_weight=w);self.estimators[target,q]=estimator
        self.fitted=True
        return self

    def raw_predictions(self,records):
        require(self.fitted,'model-not-fitted')
        x=matrix(records,self.config)
        require(all(np.isnan(x[:,i]).all() for i in range(x.shape[1]) if i not in self.active_columns),'missing-feature-variant-changed')
        x=x[:,self.active_columns]
        with threadpool_limits(limits=self.config.threads):
            prediction=np.stack([np.column_stack([self.estimators[target,q].predict(x) for q in QUANTILES]) for target in TARGETS],axis=1)
        baseline=[]
        for row in records:
            require(condition(row) in self.baseline,'matched-baseline-condition-unavailable')
            baseline.append(self.baseline[condition(row)]*volatility(row))
        return {'model':prediction,'baseline':np.asarray(baseline)}

    def calibrate(self, records, *, cutoff_ms):
        records=clean_records(records)
        require(self.fitted,'model-not-fitted')
        require(not self.calibrated,'already-calibrated')
        require(type(cutoff_ms) is int and all(eligible(r,cutoff_ms+1) for r in records),'calibration-cutoff-availability')
        require(self.fit_cutoff_ms<min(r['origin_at_ms'] for r in records),'calibration-origin-before-fit-cutoff')
        require(not set(self.training_keys)&{record_key(r) for r in records},'calibration-overlap')
        require(self.training_available_at<min(r['origin_at_ms'] for r in records),'calibration-temporal-overlap')
        predictions=self.raw_predictions(records);w=weights(records)
        for name,array in predictions.items():
            for t,target in enumerate(TARGETS):
                actual=np.asarray([row[target] for row in records])
                for j,q in enumerate(QUANTILES):
                    self.offsets[name][t,j]=weighted_quantile(actual-array[:,t,j],q,w)
        self.calibrated=True
        self.calibration_boundaries={'origin_start':min(r['origin'] for r in records),'origin_end':max(r['origin'] for r in records),
            'max_available_at':max(max(r['label_available_at'],r['feature_known_at_ms'],r['end_at_ms']) for r in records),
            'cutoff_ms':cutoff_ms,'data_sha256':sha(canonical(records))}
        return self

    def predict(self,records):
        predictions=self.raw_predictions(records)
        for name,array in predictions.items():predictions[name]=array+self.offsets[name]
        valid=np.ones(len(records),dtype=bool)
        for array in predictions.values():
            valid &= np.isfinite(array).all(axis=(1,2)) & (np.diff(array,axis=2)>=0).all(axis=(1,2)) & (array[:,0,1]<=array[:,1,1])
        return predictions | {'valid':valid,'rejection_reason':'crossing-or-nonfinite-forecast'}


def freeze(records, *, folds, config=ModelConfig(), provenance, fit_cutoff_ms):
    config.validate();records=clean_records(records)
    require(bool(folds),'folds-required')
    prior_end=None
    for fold in folds:
        require(set(fold)=={'calibration_start','evaluation_start','evaluation_end','kind'},'fold-schema')
        require(fold['calibration_start']<fold['evaluation_start']<=fold['evaluation_end'],'chronological-fold-order')
        for key in ('calibration_start','evaluation_start','evaluation_end'):date.fromisoformat(fold[key])
        require(fold['kind'] in ('walk-forward','holdout'),'fold-kind')
        require(prior_end is None or prior_end<fold['evaluation_start'],'overlapping-evaluations')
        prior_end=fold['evaluation_end']
    require(folds[-1]['kind']=='holdout' and sum(f['kind']=='holdout' for f in folds)==1,'one-final-holdout-required')
    receipt={'schema_version':1,'config':asdict(config),'folds':folds,'gates':GATES,'baseline_version':BASELINE_VERSION,
        'targets':TARGETS,'quantiles':QUANTILES,'feature_columns':FEATURE_COLUMNS,'window_policy':WINDOW_POLICY,'data_sha256':sha(canonical(records)),
        'fit_cutoff_ms':fit_cutoff_ms,'provenance':provenance,'dependencies':dependencies(),
        'calibration_policy':config.calibration,'status':'frozen-before-fit','promotion':'human-review-required'}
    return json.loads(canonical(receipt))


def eligible(row,cutoff_ms):
    return max(row['label_available_at'],row['feature_known_at_ms'],row['end_at_ms'])<cutoff_ms


def profile(start,records):
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'wall_seconds':time.perf_counter()-start,'peak_process_bytes':int(raw if platform.system()=='Darwin' else raw*1024),
        'peak_method':'process-lifetime ru_maxrss; not incremental fit allocation','platform':platform.platform(),
        'machine':platform.machine(),'records':len(records),'threads':1,'hardware_acceptance':'not-established-by-fixtures'}


def train_frozen(records,receipt,*,calendar):
    records=clean_records(records)
    require(sha(canonical(records))==receipt['data_sha256'],'frozen-data-mismatch')
    config=ModelConfig(**receipt['config']);config.validate()
    require(receipt['gates']==GATES and receipt['dependencies']==dependencies(),'frozen-policy-mismatch')
    output=[];fold_receipts=[];last_model=None;start=time.perf_counter()
    for fold in receipt['folds']:
        cal_cut=calendar.open_ms(fold['calibration_start']);eval_cut=calendar.open_ms(fold['evaluation_start'])
        train=[r for r in records if r['origin']<fold['calibration_start'] and eligible(r,min(cal_cut,receipt['fit_cutoff_ms']+1))]
        calibration=[r for r in records if fold['calibration_start']<=r['origin']<fold['evaluation_start'] and eligible(r,min(eval_cut,receipt['fit_cutoff_ms']+1))]
        evaluation=[r for r in records if fold['evaluation_start']<=r['origin']<=fold['evaluation_end'] and eligible(r,receipt['fit_cutoff_ms']+1)]
        summary={'fold':fold,'train':len(train),'calibration':len(calibration),'evaluation':len(evaluation)}
        if not train or not calibration or not evaluation:
            summary['status']='insufficient-empty-purged-fold';fold_receipts.append(summary);continue
        train=origin_weights(train);calibration=origin_weights(calibration)
        model=QuantileModel(config).fit(train,cutoff_ms=min(cal_cut-1,receipt['fit_cutoff_ms'])).calibrate(
            calibration,cutoff_ms=min(eval_cut-1,receipt['fit_cutoff_ms']))
        model.training_mode='purged-chronological-fold'
        predictions=model.predict(evaluation)
        for i,row in enumerate(evaluation):
            output.append({'record':row,'model':predictions['model'][i].tolist(),'baseline':predictions['baseline'][i].tolist(),
                'valid':bool(predictions['valid'][i]),'fold_kind':fold['kind'],
                'forecast_provenance':'offline-replay-not-immutable-origin-time-forecast'})
        summary['status']='evaluated';fold_receipts.append(summary);last_model=model
    return last_model,{'freeze_sha256':sha(canonical(receipt)),'folds':fold_receipts,'predictions':output,
                       'resources':profile(start,records),'quality_status':'research-only/not-promoted'}


def research_fit(records,receipt):
    """Explicit present-cutoff fit; never substitutes for historical evaluation."""
    records=clean_records(records)
    require(sha(canonical(records))==receipt['data_sha256'],'frozen-data-mismatch')
    available=[r for r in records if eligible(r,receipt['fit_cutoff_ms']+1)]
    require(bool(available),'no-present-available-training-labels')
    start=time.perf_counter();model=QuantileModel(ModelConfig(**receipt['config'])).fit(origin_weights(available),cutoff_ms=receipt['fit_cutoff_ms'])
    model.training_mode='unvalidated-present-cutoff-research-fit'
    return model,{'status':'unvalidated-present-cutoff-research-fit','calibration':'unavailable-not-fabricated','resources':profile(start,available)}


def pinball(actual,prediction,q):
    difference=actual-prediction
    return np.maximum(q*difference,(q-1)*difference)


def score_predictions(predictions, *, subgroups=True, evaluation_kind=None, _bootstrap_context=None):
    """Retain invalids. Losses average horizons/instruments within date, then dates."""
    if not predictions:return {'status':'insufficient-no-predictions','dates':0}
    unique={}
    for prediction in predictions:
        key=record_key(prediction['record'])
        require(key not in unique or canonical(unique[key])==canonical(prediction),'conflicting-evaluation-forecast')
        unique[key]=prediction
    predictions=list(unique.values())
    def valid_prediction(p):
        if not p['valid']:return False
        for name in ('model','baseline'):
            array=np.asarray(p[name],dtype=float)
            if array.shape!=(3,3) or not np.isfinite(array).all() or not (np.diff(array,axis=1)>=0).all() or array[0,1]>array[1,1]:return False
        return True
    valid=[p for p in predictions if valid_prediction(p)]
    if not valid:return {'status':'failed-invalid-forecasts','dates':0,'invalid':len(predictions)}
    dates=sorted({p['record']['origin'] for p in valid});daily={};groups={}
    for day in dates:
        subset=[p for p in valid if p['record']['origin']==day];daily[day]={}
        for name in ('model','baseline'):
            errors=[];pins=[]
            for p in subset:
                actual=np.asarray([p['record'][t] for t in TARGETS]);pred=np.asarray(p[name])
                errors.append(np.abs(actual-pred[:,1]));pins.append(np.asarray([pinball(actual,pred[:,j],q) for j,q in enumerate(QUANTILES)]).T)
            daily_weights=weights(origin_weights([p['record'] for p in subset]))
            daily[day][name]={'mae':np.average(errors,axis=0,weights=daily_weights),'pinball':np.average(pins,axis=0,weights=daily_weights)}
    for p in valid:
        row=p['record'];key=str((row['horizon'],row['features']['instrument_class'],row['features']['signed_leverage']))
        groups.setdefault(key,[]).append(p)
    diagnostics={}
    for key,subset in groups.items():
        diagnostics[key]={'dates':len({p['record']['origin'] for p in subset}),'endpoints':{}}
        for target_index,target in enumerate(TARGETS[:2]):
            item={}
            for name in ('model','baseline'):
                covered=[];width=[]
                for p in subset:
                    lo,_,hi=p[name][target_index];actual=p['record'][target]
                    covered.append(lo<=actual<=hi);width.append(hi-lo)
                group_weights=weights(origin_weights([p['record'] for p in subset]))
                item[name]={'coverage':float(np.average(covered,weights=group_weights)),'width':float(np.average(width,weights=group_weights))}
            diagnostics[key]['endpoints'][target]=item
        diagnostics[key]['joint_envelope_containment']=float(np.average(
            [p['model'][0][0]<=p['record']['low_return'] and p['record']['high_return']<=p['model'][1][2] for p in subset],
            weights=weights(origin_weights([p['record'] for p in subset]))))
    means={name:{'mae':np.mean([daily[d][name]['mae'] for d in dates],axis=0).tolist(),
        'pinball':np.mean([daily[d][name]['pinball'] for d in dates],axis=0).tolist()} for name in ('model','baseline')}
    # Common consecutive origin-date blocks span at least the maximum label lead.
    # Session ordinals come from the frozen dataset calendar, not ticker row counts.
    block_length=max(10,max(p['record']['window_distance'] for p in valid))
    ordinals={d:next(p['record']['origin_session_index'] for p in valid if p['record']['origin']==d) for d in dates}
    blocks={}
    for d in dates:blocks.setdefault((ordinals[d]-min(ordinals.values()))//block_length,[]).append(d)
    if _bootstrap_context is None:
        block_items=sorted(blocks.items())
        blocks=[item[1] for item in block_items]
        rng=np.random.default_rng(113)
        context={'blocks':blocks,'block_ids':[item[0] for item in block_items],
            'anchor_session_index':min(ordinals.values()),'block_sessions':block_length,
            'draws':rng.integers(0,len(blocks),(1000,len(blocks)))}
    else:
        context=_bootstrap_context;blocks=context['blocks'];block_length=context['block_sessions']
    improvements=[];missing_draws=0
    def losses(name,days):
        mae=np.mean([daily[d][name]['mae'] for d in days],axis=0)
        pb=np.mean([daily[d][name]['pinball'] for d in days],axis=0)
        return np.asarray([mae[0],mae[1],np.mean(pb),mae[2],np.mean(pb[2])])
    model_loss=losses('model',dates);baseline_loss=losses('baseline',dates)
    for draw in context['draws']:
        sampled=[d for i in draw for d in blocks[i] if d in daily]
        if not sampled:
            missing_draws+=1;continue
        improvements.append(losses('baseline',sampled)-losses('model',sampled))
    # Missing group dates/draws never become fabricated zero improvements.
    ci=np.quantile(improvements,[.025,.975],axis=0).tolist() if not missing_draws and improvements else [[None]*5,[None]*5]
    relative=[None if b<=1e-8 else float((b-m)/b) for b,m in zip(baseline_loss,model_loss)]
    for key,subset in groups.items():
        if subgroups:
            own=score_predictions(subset,subgroups=False,_bootstrap_context=context)
            diagnostics[key]['relative_improvement']=own['relative_improvement']
            diagnostics[key]['paired_ci']=own['paired_ci']
            diagnostics[key]['bootstrap_missing_draws']=own['bootstrap_missing_draws']
            diagnostics[key]['block_anchor_session_index']=own['block_anchor_session_index']
            diagnostics[key]['block_ids']=own['block_ids']
        group_days={p['record']['origin'] for p in subset}
        diagnostics[key]['blocks']=sum(bool(group_days.intersection(block)) for block in blocks)
    return {'status':'scored','evaluation_kind':evaluation_kind,'dates':len(dates),'invalid':len(predictions)-len(valid),'metrics':means,
        'gate_metrics':['low_mae','high_mae','all_pinball','terminal_mae','terminal_pinball'],
        'relative_improvement':relative,'paired_ci':ci,'block_sessions':block_length,
        'block_anchor_session_index':context['anchor_session_index'],
        'block_ids':[context['block_ids'][i] for i,block in enumerate(blocks) if set(dates).intersection(block)],
        'bootstrap_missing_draws':missing_draws,
        'blocks':len(blocks),'bootstrap_replicates':1000,'bootstrap_seed':113,'groups':diagnostics}


def _gate_input_error(score, resources):
    """Public review checker fails closed on malformed/nonfinite evidence."""
    finite=lambda value:type(value) in (int,float) and math.isfinite(value)
    integer=lambda value:type(value) is int and value>=0
    metrics=['low_mae','high_mae','all_pinball','terminal_mae','terminal_pinball']
    def improvements(value):
        return isinstance(value,list) and len(value)==5 and all(v is None or finite(v) for v in value)
    def interval(value):
        return (isinstance(value,list) and len(value)==2 and all(improvements(row) for row in value)
                and all(a is None or b is None or a<=b for a,b in zip(value[0],value[1])))
    try:
        require(score['gate_metrics']==metrics,'metric-schema')
        require(integer(score['dates']) and integer(score.get('overall_oos_dates',score['dates']))
                and score.get('overall_oos_dates',score['dates'])>=score['dates'] and integer(score['invalid']),'count-schema')
        require(improvements(score['relative_improvement']) and interval(score['paired_ci']),'improvement-schema')
        require(isinstance(score['groups'],dict) and bool(score['groups']),'empty-or-invalid-groups')
        for group in score['groups'].values():
            require(integer(group['dates']) and integer(group['blocks']),'group-count-schema')
            require(improvements(group['relative_improvement']) and interval(group['paired_ci']),'group-improvement-schema')
            require(set(group['endpoints'])==set(TARGETS[:2]),'endpoint-schema')
            for pair in group['endpoints'].values():
                require(set(pair)=={'model','baseline'},'baseline-schema')
                for values in pair.values():
                    require(finite(values['coverage']) and 0<=values['coverage']<=1
                            and finite(values['width']) and values['width']>=0,'nonfinite-coverage-width')
        require(isinstance(resources,dict),'resource-schema')
        for key in ('peak_process_bytes','wall_seconds','inference_names','inference_seconds'):
            if key in resources:require(finite(resources[key]) and resources[key]>=0,'nonfinite-resource')
    except (ValueError,TypeError,KeyError,IndexError):
        return 'malformed-or-nonfinite-gate-input'
    return None


def strong_gates(score,*,evidence,resources):
    reasons=[]
    if not isinstance(evidence,dict):return {'status':'insufficient','reasons':['malformed-evidence'],'groups':{}}
    if not isinstance(score,dict):return {'status':'insufficient','reasons':['malformed-score'],'groups':{}}
    if score.get('status')!='scored':return {'status':'insufficient','reasons':['no-assessable-score'],'groups':{}}
    error=_gate_input_error(score,resources)
    if error:return {'status':'insufficient','reasons':[error],'groups':{}}
    for key in ('actual_data','contemporary_membership','delistings','origin_vintages','untouched_holdout','walk_forward','immutable_origin_baselines'):
        if evidence.get(key) is not True:reasons.append('missing-evidence:'+key)
    if score.get('evaluation_kind') not in ('walk-forward','holdout'):reasons.append('unsegregated-evaluation-scope')
    if score.get('overall_oos_dates',score['dates'])<252:reasons.append('insufficient-oos-dates')
    if score['invalid']:reasons.append('invalid-crossing-forecasts')
    for metric,relative,lower in zip(score['gate_metrics'],score['relative_improvement'],score['paired_ci'][0]):
        if relative is None:reasons.append('unassessable-baseline:'+metric)
        elif lower is None or relative<.05 or lower<=0:reasons.append('failed-improvement:'+metric)
    if resources.get('actual_target_machine') is not True or resources.get('peak_process_bytes',math.inf)>2*1024**3 or resources.get('wall_seconds',math.inf)>600:
        reasons.append('unverified-or-failed-training-resources')
    if resources.get('inference_names',0)<110 or resources.get('inference_seconds',math.inf)>10:reasons.append('unverified-or-failed-inference-resources')
    groups={}
    for key,group in score['groups'].items():
        failures=[]
        if 'relative_improvement' not in group:failures.append('missing-subgroup-improvement-evidence')
        else:
            for metric,relative,lower in zip(score['gate_metrics'],group['relative_improvement'],group['paired_ci'][0]):
                if relative is None or lower is None or relative<.05 or lower<=0:failures.append('subgroup-improvement:'+metric)
        if group['dates']<100 or group['blocks']<10:failures.append('insufficient-subgroup')
        for target,pair in group['endpoints'].items():
            if not .85<=pair['model']['coverage']<=.95:failures.append('coverage:'+target)
            if not .85<=pair['baseline']['coverage']<=.95:failures.append('matched-baseline-coverage-unassessable:'+target)
            if not math.isclose(pair['model']['coverage'],pair['baseline']['coverage'],rel_tol=0,abs_tol=GATES['matched_coverage_abs_tolerance']):failures.append('matched-coverage-width-unassessable:'+target)
            if pair['model']['width']>pair['baseline']['width']:failures.append('width:'+target)
        groups[key]={'status':'qualified-for-review' if not failures and not reasons else 'failed-or-insufficient', 'reasons':failures+reasons}
    return {'status':'qualified-for-human-review' if not reasons and all(g['status']=='qualified-for-review' for g in groups.values()) else 'failed-or-insufficient',
            'reasons':reasons,'groups':groups,'promotion':'not-authorized-by-checker'}


def evaluate_scopes(predictions, *, evidence, resources):
    scopes={}
    overall_dates=len({p['record']['origin'] for p in predictions if p.get('valid')})
    for kind in ('walk-forward','holdout'):
        subset=[p for p in predictions if p.get('fold_kind')==kind]
        score=score_predictions(subset,evaluation_kind=kind)
        score['overall_oos_dates']=overall_dates
        scopes[kind]={'score':score,'gates':strong_gates(score,evidence=evidence,resources=resources)}
    return {'scopes':scopes,'pooled_diagnostic':score_predictions(predictions),
        'status':'qualified-for-human-review' if all(s['gates']['status']=='qualified-for-human-review' for s in scopes.values()) else 'failed-or-insufficient',
        'promotion':'not-authorized-by-checker'}


def save_artifact(generation,model,receipt,evaluation):
    import joblib
    require(isinstance(model,QuantileModel) and model.fitted,'no-fitted-artifact')
    stream=io.BytesIO();joblib.dump(model,stream,compress=3)
    generation.write('model.joblib',stream.getvalue())
    generation.json('model_contract.json',{'schema_version':1,'dependencies':dependencies(),
        'feature_columns':FEATURE_COLUMNS,'targets':TARGETS,'quantiles':QUANTILES,
        'config':asdict(model.config),'freeze_sha256':sha(canonical(receipt)),
        'data_sha256':receipt['data_sha256'],'provenance':receipt['provenance'],
        'fit_review_cutoff_ms':receipt['fit_cutoff_ms'],
        'training_mode':getattr(model,'training_mode','explicit-cutoff-research-unit-fit'),
        'training_data_sha256':model.training_data_sha256,
        'training_boundaries':{'cutoff_ms':model.fit_cutoff_ms,'origin_start':model.training_origin_start,'origin_end':model.training_origin_end,'max_available_at':model.training_available_at},
        'calibration_boundaries':getattr(model,'calibration_boundaries',None),
        'active_feature_columns':[FEATURE_COLUMNS[i] for i in model.active_columns],
        'window_policy':WINDOW_POLICY,'feature_variant':model.config.feature_variant,
        'calendar_policy':receipt['provenance'].get('calendar'),
        'adjustment_policy':receipt['provenance'].get('adjustment_policy'),
        'evidence_policy':receipt['provenance'].get('policy'),
        'baseline_version':BASELINE_VERSION,
        'calibrated':model.calibrated,'quality_status':'research-only'})
    generation.json('evaluation.json',evaluation)


def validate_runtime_policy(contract, *, feature_variant, calendar_name, calendar_version,
                            adjustment, currency):
    """Check new inference inputs against frozen policies, NOT old training data hash."""
    require(contract['feature_variant']==feature_variant,'runtime-feature-variant-mismatch')
    require(contract['calendar_policy']['name']==calendar_name
            and contract['calendar_policy']['version']==calendar_version,'runtime-calendar-mismatch')
    require(contract['adjustment_policy']['required_basis']==adjustment
            and contract['adjustment_policy']['currency']==currency,'runtime-adjustment-currency-mismatch')
    require(contract['window_policy']==WINDOW_POLICY,'runtime-window-policy-mismatch')
    return True


def load_artifact(folder,*,trusted_root,expected_contract):
    """Only explicitly trusted local artifacts; hashing is integrity, not pickle safety."""
    import joblib
    folder=Path(folder);root=Path(trusted_root).resolve()
    require(not folder.is_symlink() and folder.resolve().parent==root,'outside-trusted-model-root')
    require(stat.S_IMODE(folder.stat().st_mode)==0o700,'model-directory-permissions')
    manifest=json.loads(private_read(folder/'manifest.json'))
    require(manifest.get('kind')=='stock-research-model' and manifest.get('schema_version')==1,'model-manifest-schema')
    verified={}
    for key,entry in manifest['artifacts'].items():
        name=entry['path'];require(key==name and Path(name).name==name,'unsafe-model-artifact-path')
        raw=private_read(folder/name);require(sha(raw)==entry['sha256'] and len(raw)==entry['bytes'],'model-artifact-integrity')
        verified[name]=raw
    require({'model.joblib','model_contract.json','freeze.json'}<=manifest['artifacts'].keys(),'model-artifacts-missing')
    contract=json.loads(verified['model_contract.json'])
    require(contract['schema_version']==1 and contract['dependencies']==dependencies(),'model-dependency-schema-mismatch')
    require(contract['feature_columns']==list(FEATURE_COLUMNS) and contract['targets']==list(TARGETS) and contract['quantiles']==list(QUANTILES),'model-feature-target-schema-mismatch')
    require(contract==expected_contract,'model-compatibility-mismatch')
    require(contract['window_policy']==WINDOW_POLICY and contract['feature_variant']==contract['config']['feature_variant']
            and contract['baseline_version']==BASELINE_VERSION,'model-policy-mismatch')
    require(isinstance(contract.get('calendar_policy'),dict) and isinstance(contract.get('adjustment_policy'),dict),'model-calendar-adjustment-policy-missing')
    require(contract['calendar_policy'].get('version')==version('exchange_calendars')
            and bool(contract['calendar_policy'].get('name'))
            and re.fullmatch(r'[0-9a-f]{64}',str(contract['calendar_policy'].get('schedule_sha256',''))) is not None,'model-calendar-incompatible')
    require(contract['adjustment_policy'].get('required_basis')=='forward-excluding-dividends'
            and contract['adjustment_policy'].get('currency')=='USD','model-adjustment-incompatible')
    active=contract['active_feature_columns']
    require(bool(active) and len(active)==len(set(active)) and all(c in FEATURE_COLUMNS for c in active),'model-active-feature-schema')
    receipt=json.loads(verified['freeze.json'])
    require(sha(canonical(receipt))==contract['freeze_sha256'],'freeze-integrity-mismatch')
    require(receipt['gates']==GATES and receipt['window_policy']==WINDOW_POLICY and receipt['config']==contract['config']
            and receipt['provenance'].get('calendar')==contract['calendar_policy']
            and receipt['provenance'].get('adjustment_policy')==contract['adjustment_policy'],'freeze-contract-policy-mismatch')
    ModelConfig(**contract['config']).validate()
    model=joblib.load(io.BytesIO(verified['model.joblib']))
    require(isinstance(model,QuantileModel) and asdict(model.config)==contract['config'] and model.fitted,'incompatible-model-payload')
    require([FEATURE_COLUMNS[i] for i in model.active_columns]==contract['active_feature_columns']
            and model.training_data_sha256==contract['training_data_sha256']
            and model.fit_cutoff_ms==contract['training_boundaries']['cutoff_ms']
            and model.calibrated==contract['calibrated']
            and getattr(model,'calibration_boundaries',None)==contract['calibration_boundaries'],'model-payload-boundary-mismatch')
    return model,contract
