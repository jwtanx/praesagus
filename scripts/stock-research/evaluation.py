"""Append-only actual-OHLC reviews. Immutable issuances are never rewritten."""
import json
import math
import re
from pathlib import Path
from collections import defaultdict
import numpy as np
from data import require,validate_window
from inference import security_binding,FORECAST_SCHEMA,evidence_time,converted_quantiles
from model import TARGETS,QUANTILES,pinball
from storage import canonical,private_read,sha,manifests

EVALUATION_SCHEMA=1
MAX_SAVED_FORECASTS=100000


def check_forecast_id(row):
    require(isinstance(row,dict) and row.get('schema_version')==FORECAST_SCHEMA,'forecast-row-schema')
    require(row.get('forecast_id')==sha(canonical({k:v for k,v in row.items() if k!='forecast_id'})),'immutable-forecast-id-mismatch')


def basis_matches(forecast,actual,cutoff):
    expected=forecast.get('basis_evidence') or {}
    current=actual or {}
    required=('adjustment_vintage_id','currency','adjustment','source_hash')
    for receipt in (expected,current):
        if not all(receipt.get(key) for key in required):return False
        if re.fullmatch(r'[0-9a-f]{64}',str(receipt['source_hash'])) is None:return False
        if not isinstance(receipt['adjustment_vintage_id'],str) or re.fullmatch(r'[A-Za-z0-9._:+/-]{1,128}',receipt['adjustment_vintage_id']) is None:return False
        try:known=evidence_time(receipt)
        except (ValueError,TypeError):return False
        if known>(forecast['as_of_ms'] if receipt is expected else cutoff):return False
    return (all(expected[key]==current[key] for key in ('adjustment_vintage_id','currency','adjustment'))
        and expected['currency']==forecast['reference']['currency'] and expected['adjustment']==forecast['reference']['adjustment'])


def forecast_metrics(forecast,actual):
    result={};reference=forecast['reference']['close']
    for name in ('model','baseline'):
        converted=converted_quantiles(forecast[name]['relative_quantiles'],reference)
        require(canonical(converted)==canonical(forecast[name]),'saved-price-conversion-or-axes-mismatch')
        predicted=np.asarray(forecast[name]['relative_quantiles'],dtype=float);targets=np.asarray([actual[t] for t in TARGETS])
        require(predicted.shape==(3,3) and np.isfinite(predicted).all(),'invalid-saved-quantiles')
        metrics={}
        for t,target in enumerate(TARGETS):
            metrics[target]={'absolute_error':float(abs(targets[t]-predicted[t,1])),
                'pinball':[float(pinball(targets[t],predicted[t,j],q)) for j,q in enumerate(QUANTILES)],
                'coverage':bool(predicted[t,0]<=targets[t]<=predicted[t,2]),'width':float(predicted[t,2]-predicted[t,0])}
            if t<2:metrics[target]['price_absolute_error']=metrics[target]['absolute_error']*reference
        metrics['joint_envelope_containment']=bool(predicted[0,0]<=targets[0] and targets[1]<=predicted[1,2])
        result[name]=metrics
    return result


def review_forecasts(forecasts,history,*,calendar,review_at_ms,basis_evidence=None,previous=()):
    require(type(review_at_ms) is int and review_at_ms>0,'review-cutoff')
    require(len(forecasts)<=MAX_SAVED_FORECASTS,'saved-forecast-budget')
    basis_evidence=basis_evidence or {};outcomes={};latest={}
    for row in previous:
        require(type(row.get('review_at_ms')) is int,'prior-review-cutoff-type')
        if row['review_at_ms']>review_at_ms:continue  # Original later file remains unchanged.
        require(row.get('schema_version')==EVALUATION_SCHEMA,'prior-outcome-schema')
        require(row.get('outcome_id')==sha(canonical({k:v for k,v in row.items() if k not in ('outcome_id','review_at_ms','supersedes_outcome_id')})),'prior-outcome-id-mismatch')
        require(row['outcome_id'] not in outcomes or canonical(outcomes[row['outcome_id']])==canonical(row),'prior-outcome-conflict')
        outcomes[row['outcome_id']]=row
        if row['review_at_ms']<=review_at_ms:
            key=row['forecast_id'];old=latest.get(key)
            if old is None or old['review_at_ms']<row['review_at_ms']:latest[key]=row
    seen={}
    for forecast in forecasts:
        check_forecast_id(forecast);key=forecast['forecast_id']
        require(key not in seen or canonical(seen[key])==canonical(forecast),'forecast-conflict')
        if key in seen:continue
        seen[key]=forecast;outcome={'schema_version':EVALUATION_SCHEMA,'forecast_id':key,'code':forecast['code'],
            'origin':forecast['origin'],'horizon':forecast['horizon'],'review_at_ms':review_at_ms,'status':'unscored',
            'reason':None,'actual':None,'actual_vintage_sha256':None,'actual_provenance':[],'metrics':None}
        try:
            require(forecast['issued_at_ms']<=review_at_ms,'forecast-issued-after-review')
            require(forecast['status']=='available','original-forecast-unavailable')
            expected=calendar.windows(forecast['origin'])[forecast['horizon']]
            window=forecast['window']
            reference=forecast['reference']
            require(reference and reference['session_date']==forecast['origin']
                and type(reference.get('known_at_ms')) is int and reference['known_at_ms']<=forecast['as_of_ms']
                and type(reference.get('price_known_at_ms')) is int
                and calendar.close_ms(forecast['origin'])<=reference['price_known_at_ms']<=reference['retrieved_at_ms']
                and reference['source_at_ms']<=reference['price_known_at_ms']<=reference['known_at_ms']
                and (reference.get('currency_known_at_ms') is None or reference['currency_known_at_ms']<=reference['known_at_ms']),
                'saved-reference-cutoff-or-session-mismatch')
            require(expected==window['sessions'] and window['horizon']==forecast['horizon']
                and window['start']==expected[0] and window['end']==expected[-1]
                and window['first_open_ms']==calendar.open_ms(expected[0])
                and window['last_close_ms']==calendar.close_ms(expected[-1])
                and window['started']==(forecast['as_of_ms']>=calendar.open_ms(expected[0])),'saved-window-calendar-mismatch')
            if review_at_ms<window['last_close_ms']:
                outcome['status']='pending';raise ValueError('full-window-not-ended')
            security=security_binding(history,forecast['code'],review_at_ms)
            require(type(security) is type(forecast['stock_id']) and security==forecast['stock_id'],'actual-security-identity-mismatch')
            require(basis_matches(forecast,basis_evidence.get(forecast['code']),review_at_ms),'adjustment-vintage-or-units-unverified')
            ref=forecast['reference'];require(ref and ref['close']>0,'original-reference-unavailable')
            rows=history.as_of(forecast['code'],review_at_ms)
            bars=validate_window(rows,expected,calendar,cutoff_ms=review_at_ms,currency=ref['currency'],adjustment=ref['adjustment'])
            actual={'realized_low':min(r['low'] for r in bars),'realized_high':max(r['high'] for r in bars),
                'terminal_close':bars[-1]['close'],'label_available_at':max(r['known_at_ms'] for r in bars)}
            actual.update(low_return=actual['realized_low']/ref['close']-1,high_return=actual['realized_high']/ref['close']-1,
                terminal_logreturn=math.log(actual['terminal_close']/ref['close']))
            outcome.update(status='scored',actual=actual,metrics=forecast_metrics(forecast,actual),
                actual_vintage_sha256=sha(canonical({'bars':bars,'basis':basis_evidence[forecast['code']]})),
                actual_provenance=[{key:r.get(key) for key in ('session_date','source','source_at_ms','retrieved_at_ms','known_at_ms',
                    'price_known_at_ms','currency_known_at_ms','revision_vintage','currency','adjustment')} for r in bars])
        except (ValueError,KeyError,TypeError) as error:outcome['reason']=str(error)
        outcome['outcome_id']=sha(canonical({k:v for k,v in outcome.items() if k not in ('review_at_ms','outcome_id')}))
        prior=latest.get(key)
        if outcome['outcome_id'] not in outcomes:
            outcome['supersedes_outcome_id']=prior['outcome_id'] if prior else None
            outcomes[outcome['outcome_id']]=outcome
        # Preserve first actual review time for unchanged source evidence/status.
        latest[key]=outcomes[outcome['outcome_id']]
    all_rows=sorted(outcomes.values(),key=lambda r:(r['review_at_ms'],r['forecast_id'],r['outcome_id']))
    return {'schema_version':EVALUATION_SCHEMA,'kind':'stock-research-evaluation','review_at_ms':review_at_ms,
        'outcome_revisions':all_rows,'current_outcomes':sorted(latest.values(),key=lambda r:r['forecast_id']),
        'cumulative':cumulative_metrics(list(latest.values()),seen),'retraining':False,'promotion':False}


def cumulative_metrics(outcomes,forecasts):
    """Equal dates, instruments, horizons; intraday issuances share one origin weight."""
    groups=defaultdict(lambda:defaultdict(lambda:defaultdict(lambda:defaultdict(list))))
    scored=0
    def vector(metrics):
        values=[]
        for name in ('model','baseline'):
            for target in TARGETS:
                item=metrics[name][target];values.extend([item['absolute_error'],*item['pinball'],float(item['coverage']),item['width']])
            values.append(float(metrics[name]['joint_envelope_containment']))
        return np.asarray(values)
    for outcome in outcomes:
        if outcome['status']!='scored' or outcome['forecast_id'] not in forecasts:continue
        forecast=forecasts[outcome['forecast_id']];m=forecast['instrument'];scored+=1
        group=str((forecast['horizon'],m.get('instrument_class'),m.get('signed_leverage')))
        for key in ('all',group):groups[key][forecast['origin']][forecast['code']][forecast['horizon']].append(vector(outcome['metrics']))
    summary={}
    for group,dates in groups.items():
        per_date=[]
        for instruments in dates.values():
            per_date.append(np.mean([np.mean([np.mean(issues,axis=0) for issues in horizons.values()],axis=0) for horizons in instruments.values()],axis=0))
        average=np.mean(per_date,axis=0);models={}
        for j,name in enumerate(('model','baseline')):
            targets={}
            for t,target in enumerate(TARGETS):
                offset=j*19+t*6;values=average[offset:offset+6]
                targets[target]={'mae':float(values[0]),'mean_pinball_by_quantile':values[1:4].tolist(),
                    'coverage':float(values[4]),'width':float(values[5])}
            models[name]=targets|{'joint_envelope_containment':float(average[j*19+18])}
        summary[group]={'distinct_origin_dates':len(dates),'metrics':models}
    return {'scored_issuances':scored,'groups':summary,
        'weighting':'equal reference-session dates, instrument-origins, horizons, then intraday issuances; all original issuances retained',
        'units':{'endpoints':'reference-price fractions','terminal':'logreturn'},'accuracy_is_not_profitability':True}


def load_saved_predictions(parent):
    forecasts={};outcomes={}
    for _,folder,manifest in manifests(parent,kind='stock-research-prediction'):
        if 'predictions.json' in manifest['artifacts']:
            payload=json.loads(private_read(folder/'predictions.json'))
            require(payload.get('schema_version')==FORECAST_SCHEMA,'saved-forecast-schema')
            for row in payload['forecasts']:
                check_forecast_id(row);key=row['forecast_id']
                require(key not in forecasts or canonical(forecasts[key])==canonical(row),'saved-forecast-conflict')
                forecasts[key]=row;require(len(forecasts)<=MAX_SAVED_FORECASTS,'saved-forecast-budget')
        if 'outcomes.json' in manifest['artifacts']:
            payload=json.loads(private_read(folder/'outcomes.json'))
            for row in payload['outcome_revisions']:outcomes[row['outcome_id']]=row
    return list(forecasts.values()),list(outcomes.values())


def write_evaluation_payload(generation,payload):
    require(not generation.closed,'generation-already-finalized')
    require(payload.get('schema_version')==EVALUATION_SCHEMA,'evaluation-payload-schema')
    generation.json('outcomes.json',payload)
    return {'evaluation_schema_version':EVALUATION_SCHEMA,'review_at_ms':payload['review_at_ms']}
