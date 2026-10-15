"""Versioned offline forecast payloads from existing trusted models. Never fit."""
import json
import math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from data import History, GAPS, require, validate_window, valid_identity
from features import causal_features
from model import (TARGETS,QUANTILES,canonical_records_hash,load_artifact,validate_runtime_policy)
from storage import canonical,private_read,sha
from ranking import decide,select_top20

FORECAST_SCHEMA=1
MAX_INSTRUMENTS=110


def load_existing_model(folder,*,trusted_root,expected_contract):
    model,contract=load_artifact(folder,trusted_root=trusted_root,expected_contract=expected_contract)
    manifest=json.loads(private_read(Path(folder)/'manifest.json'))
    return model,contract,{'contract_sha256':sha(canonical(contract)),'model_sha256':manifest['artifacts']['model.joblib']['sha256'],
        'training_data_sha256':contract['data_sha256'],'quality_status':contract['quality_status'],
        'trusted_artifact_folder':str(Path(folder).resolve()),'artifact_manifest_sha256':sha(private_read(Path(folder)/'manifest.json')),
        'artifact_known_at_ms':int(datetime.fromisoformat(manifest['generated_at']).timestamp()*1000)}


def evidence_time(record):
    values=[]
    for key in ('known_at_ms','retrieved_at_ms','available_at_ms','first_seen_at_ms','observed_at_ms'):
        if record.get(key) is not None:
            require(type(record[key]) is int and record[key]>=0,'invalid-evidence-availability');values.append(record[key])
    for key in ('known_at','retrieved_at','available_at','first_seen_at','observed_at'):
        if record.get(key) is not None:
            stamp=datetime.fromisoformat(record[key].replace('Z','+00:00'))
            require(stamp.tzinfo is not None,'evidence-timezone-required');values.append(int(stamp.timestamp()*1000))
    require(bool(values),'evidence-availability-missing');return max(values)


def security_binding(history,code,at_ms):
    bindings=[b for receipt in history.receipts for b in receipt.get('identity_bindings',[]) if b.get('code')==code]
    require(bool(bindings),'identity-binding-missing')
    # The canonical reader may quarantine symbol reuse globally. This helper does
    # not add a FUTURE identity fact to the issue-time information set.
    dated=[b for b in bindings if evidence_time(b)<=at_ms]
    ids={(type(b.get('stock_id')).__name__,b.get('stock_id')) for b in dated}
    require(len(ids)<=1 and all(valid_identity(b.get('stock_id')) for b in dated),'identity-binding-conflict')
    require(bool(dated),'identity-binding-not-known-at-cutoff')
    return max(dated,key=evidence_time)['stock_id']


def converted_quantiles(values,reference):
    array=np.asarray(values,dtype=float)
    require(array.shape==(3,3) and np.isfinite(array).all(),'invalid-nine-quantiles')
    require((np.diff(array,axis=1)>=0).all() and array[0,1]<=array[1,1],'crossing-quantiles')
    require(math.isfinite(reference) and reference>0,'invalid-reference-price')
    prices=[]
    for target in (0,1):
        points=[reference*(1+float(v)) for v in array[target]]
        require(all(math.isfinite(v) and v>0 for v in points),'nonpositive-or-invalid-extrema-price');prices.append(points)
    returns=[];terminal_prices=[]
    for value in array[2]:
        try:result=math.expm1(float(value))
        except OverflowError:raise ValueError('terminal-overflow') from None
        require(math.isfinite(result) and result>-1,'terminal-underflow-or-invalid')
        terminal=reference*(1+result);require(math.isfinite(terminal) and terminal>0,'terminal-price-invalid')
        returns.append(result);terminal_prices.append(terminal)
    return {'relative_quantiles':array.tolist(),'price_quantiles':prices+[terminal_prices],
        'terminal_return_quantiles':returns,'predicted_low':prices[0][1],'predicted_high':prices[1][1],
        'targets':list(TARGETS),'quantiles':list(QUANTILES)}


def metadata_eligible(instrument,security,cutoff):
    if type(instrument.get('stock_id')) is not type(security) or instrument.get('stock_id')!=security:return False
    if type(instrument.get('metadata_known_at_ms')) is not int or instrument['metadata_known_at_ms']>cutoff:return False
    lever=instrument.get('signed_leverage');asset=instrument.get('asset_type')
    if asset=='STOCK':return bool(instrument.get('issuer_group_id')) and type(lever) is int and lever==1 and instrument.get('sector_id') is not None and instrument.get('instrument_class')=='stock'

    if asset!='ETF' or type(lever) is not int or lever not in (1,2,3,-1,-2,-3):return False
    expected='ordinary-etf' if lever==1 else 'inverse-etf' if lever<0 else 'leveraged-etf'
    return (bool(instrument.get('issuer')) and isinstance(instrument.get('etf_verification_url'),str)
        and instrument['etf_verification_url'].startswith('https://') and instrument.get('instrument_class')==expected
        and bool(instrument.get('exposure_family'))) and instrument.get('reset')==('not_applicable' if lever==1 else 'daily') and instrument.get('classification_verified') is True


def validation_for(contract,model_ref,instrument,horizon,as_of_ms,receipt=None):
    # Current PRSG-113 artifacts are always research-only. An external declaration
    # cannot override that frozen artifact disposition.
    reasons=[]
    if contract.get('quality_status')!='promoted-for-research':reasons.append('artifact-research-only; PRSG-113-D2-unmet')
    receipt=receipt or {}
    if receipt.get('human_reviewed') is not True or receipt.get('trader_reviewed') is not True:reasons.append('reviewed-promotion-unavailable')
    if receipt.get('model_sha256')!=model_ref.get('model_sha256'):reasons.append('promotion-model-mismatch')
    if type(receipt.get('known_at_ms')) is not int or receipt['known_at_ms']>as_of_ms:reasons.append('promotion-not-known-at-cutoff')
    group=[horizon,instrument.get('instrument_class'),instrument.get('signed_leverage')]
    if group not in receipt.get('qualified_groups',[]):reasons.append('horizon-class-terminal-not-qualified')
    if receipt.get('terminal_validated') is not True:reasons.append('terminal-validation-unavailable')
    return {'qualified':not reasons,'reasons':reasons,'classification':'research only','automatic_promotion':False}


def build_forecasts(history,instruments,*,model,contract,model_ref,calendar,issued_at_ms,as_of_ms,
                    costs=None,dated_metadata=None,basis_evidence=None,benchmark=None,validation_receipt=None):
    require(type(as_of_ms) is int and type(issued_at_ms) is int and 0<as_of_ms<=issued_at_ms,'issuance-cutoff-order')
    require(0<len(instruments)<=MAX_INSTRUMENTS,'instrument-budget-or-empty')
    require(len({m['code'] for m in instruments})==len(instruments),'duplicate-instrument')
    data_hash=canonical_records_hash(r for r in history.rows if r['known_at_ms']<=as_of_ms)
    costs=costs or {};dated_metadata=dated_metadata or {};basis_evidence=basis_evidence or {}
    closed=[day for day in calendar._sessions if calendar.close_ms(day)<=as_of_ms]
    require(bool(closed),'no-completed-calendar-session');origin=closed[-1]
    windows=calendar.windows(origin);rows=[]
    policy=contract.get('provenance',{}).get('policy','strict')
    gaps=contract.get('provenance',{}).get('declared_gaps',[])
    for raw_instrument in instruments:
        instrument=dict(raw_instrument);instrument.setdefault('panel','speculative' if instrument.get('speculative') else 'main')
        # Ordinary stock exposure is a definition of verified current STOCK type,
        # not a guessed ETF mandate or historical training classification.
        known=instrument.get('metadata_known_at_ms')
        if type(known) is int and known<=as_of_ms and instrument.get('listing_verified') is True:
            if instrument.get('asset_type')=='STOCK':
                instrument.setdefault('signed_leverage',1);instrument.setdefault('instrument_class','stock')
            elif instrument.get('asset_type')=='ETF' and instrument.get('classification_verified') is True:
                lever=instrument.get('signed_leverage')
                if type(lever) is int and lever in (1,2,3,-1,-2,-3):
                    instrument.setdefault('instrument_class','ordinary-etf' if lever==1 else 'inverse-etf' if lever<0 else 'leveraged-etf')
        instrument['classification_scope']='current observation at issue; not historical feature membership'
        code=instrument['code'];common_error=None;reference=None;local=None;security=None
        try:
            require(model is not None,'compatible-existing-model-unavailable')
            require(type(model_ref.get('artifact_known_at_ms')) is int and model_ref['artifact_known_at_ms']<=as_of_ms,'model-artifact-not-known-at-cutoff')
            training=contract.get('training_boundaries') or {}
            calibration=contract.get('calibration_boundaries') or {}
            require(type(training.get('cutoff_ms')) is int and training['cutoff_ms']<=as_of_ms
                and type(training.get('max_available_at')) is int and training['max_available_at']<=as_of_ms
                and all(type(v) is int and v<=as_of_ms for k,v in calibration.items() if k in ('cutoff_ms','max_available_at')),'future-model-fit-or-calibration')
            security=security_binding(history,code,as_of_ms)
            require(type(instrument.get('stock_id')) is type(security) and instrument.get('stock_id')==security,'instrument-security-mismatch')
            # Even researcher feature policy NEVER admits data actually known after issuance.
            local=History(history.as_of(code,as_of_ms),history.receipts)
            require(any(r['session_date']==origin and r['completed'] for r in local.rows),'latest-completed-session-unavailable-or-incomplete')
            reference=validate_window(local.rows,[origin],calendar,cutoff_ms=as_of_ms)[0]
            validate_runtime_policy(contract,feature_variant='with-benchmark' if benchmark else 'no-benchmark',
                calendar_name=calendar.name,calendar_version=calendar.version,adjustment=reference['adjustment'],currency=reference['currency'])
        except (ValueError,KeyError,TypeError) as error:common_error=str(error)
        for horizon,sessions in windows.items():
            window={'horizon':horizon,'sessions':sessions,'start':sessions[0],'end':sessions[-1],
                'first_open_ms':calendar.open_ms(sessions[0]),'last_close_ms':calendar.close_ms(sessions[-1]),
                'started':as_of_ms>=calendar.open_ms(sessions[0])}
            row={'schema_version':FORECAST_SCHEMA,'code':code,'horizon':horizon,'issued_at_ms':issued_at_ms,'as_of_ms':as_of_ms,
                'origin':origin,'input_data_sha256':data_hash,'instrument':dict(instrument),'stock_id':security,'window':window,'reference':None,
                'model_ref':model_ref,'status':'unavailable','reasons':[],'model':None,'baseline':None,
                'validation':validation_for(contract,model_ref,instrument,horizon,as_of_ms,validation_receipt),
                'features':{'policy':policy,'declared_gaps':gaps,'known_at_ms':None},'basis_evidence':basis_evidence.get(code)}
            volatility=None;terminal=None
            try:
                require(common_error is None,common_error or 'invalid-input')
                row['reference']={key:reference[key] for key in ('session_date','close','source','source_at_ms','retrieved_at_ms','known_at_ms',
                    'price_known_at_ms','currency_known_at_ms','revision_vintage','currency','adjustment','provider_finality_status','time_zone_unit_status')}
                feature_benchmark=None
                if benchmark is not None:
                    other,other_code=benchmark
                    feature_benchmark=(History(other.as_of(other_code,as_of_ms),other.receipts),other_code)
                item=causal_features(local,code,origin,calendar=calendar,origin_cutoff_ms=as_of_ms,horizon=horizon,
                    policy=policy,declared_gaps=gaps,dated_metadata=dated_metadata.get(code),benchmark=feature_benchmark)
                require(item['feature_known_at_ms']<=as_of_ms,'future-feature-availability')
                row['features'].update(known_at_ms=item['feature_known_at_ms'],variant=item['variant'],
                    instrument_class=item['features']['instrument_class'],signed_leverage=item['features']['signed_leverage'],
                    provider_finality_status=item['provider_finality_status'],time_zone_unit_status=item['time_zone_unit_status'])
                prediction=model.predict([{'features':item['features'],'horizon':horizon}])
                require(bool(prediction['valid'][0]),prediction.get('rejection_reason','invalid-prediction'))
                row['model']=converted_quantiles(prediction['model'][0],reference['close'])
                row['baseline']=converted_quantiles(prediction['baseline'][0],reference['close'])
                row['status']='available';terminal=row['model']['relative_quantiles'][2][1]
                volatility=item['features']['volatility20']*math.sqrt(len(calendar.sessions(origin,sessions[-1]))-1)
            except (ValueError,KeyError,TypeError,OverflowError) as error:
                row['reasons'].append(str(error));row['model']=row['baseline']=None
            row['decision']=decide(terminal_logreturn=terminal,cost=costs.get(code),leverage=instrument.get('signed_leverage'),
                volatility=volatility,validated=row['validation']['qualified'],data_ok=row['status']=='available',
                tradable=instrument.get('listing_verified') is True and instrument.get('comparison_basis_verified') is True,
                metadata_ok=metadata_eligible(instrument,security,as_of_ms),started=window['started'])
            row['decision']['risk_session_count']=len(calendar.sessions(origin,sessions[-1]))-1
            if row['status']=='available':
                row['numeric_evidence']={'bull':{'terminal_positive':row['decision']['gross_return']>0},
                    'bear':{'terminal_negative':row['decision']['gross_return']<0},
                    'disconfirming':'Unvalidated forecasts and intervals are not proof of market direction.',
                    'causal_claim':None}
            row['forecast_id']=sha(canonical(row));rows.append(row)
    payload={'schema_version':FORECAST_SCHEMA,'kind':'stock-research-forecast-bundle','issued_at_ms':issued_at_ms,
        'as_of_ms':as_of_ms,'data_sha256':data_hash,'model_ref':model_ref,'forecasts':rows,
        'forecast_symbols':sorted({row['code'] for row in rows}),
        'pending_forecast_symbols':sorted({row['code'] for row in rows if row['status']=='available'}),
        'quality_status':'research-only unless independently reviewed promoted artifact'}
    return payload|select_top20(rows)


def write_forecast_payload(generation,payload):
    require(not generation.closed,'generation-already-finalized')
    require(payload.get('schema_version')==FORECAST_SCHEMA,'forecast-payload-schema')
    generation.json('predictions.json',payload)
    return {'forecast_schema_version':FORECAST_SCHEMA,'forecast_symbols':payload['forecast_symbols'],
        'pending_forecast_symbols':payload['pending_forecast_symbols'],'validated_candidate_count':payload['validated_candidate_count']}
