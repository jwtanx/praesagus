#!/usr/bin/env python3
"""One immutable collection/prediction/export run. Training is always separate."""
import argparse
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from config import load_collection_config
from collect import collect_into,compatibility,completed_sessions,load_secure_locator
from storage import Generation,COMPONENT_REQUIRED,canonical,sha,manifests,private_read
from data import assemble,History
from market_calendar import MarketCalendar
from predict import run_prediction,read_json
from inference import load_existing_model,write_forecast_payload
from evaluation import load_saved_predictions,review_forecasts,write_evaluation_payload
from export import export_bundle


def component(status,names,compatibility_id):
    return {'schema_version':1,'status':status,'artifacts':sorted(names),'compatibility_id':compatibility_id}


def existing_model(parent,*,model_dir=None,model_folder=None,model_contract=None):
    root=Path(model_dir or Path(parent)/'models').expanduser()
    if model_folder:folder=Path(model_folder).expanduser()
    else:
        matches=manifests(root,kind='stock-research-model')
        if not matches:return None,{'quality_status':'existing-trusted-model-missing'},{'quality_status':'unavailable'}
        folder=matches[-1][1]
    expected=read_json(model_contract,None) if model_contract else json.loads(private_read(folder/'model_contract.json'))
    return load_existing_model(folder,trusted_root=root,expected_contract=expected)


def run_bundle(settings,*,provider=None,provider_factory=None,offline=False,generated_at=None,as_of_ms=None,
               model=None,contract=None,model_ref=None,model_loader=None,costs=None,dated_metadata=None,basis_evidence=None,
               metadata=None,sentiment='auto',clock_ms=lambda:int(time.time()*1000),session_provider=completed_sessions):
    """Single collection and finalization; no fitting, no LLMs. Provider is explicit/injected."""
    if sentiment not in ('auto','off'):raise ValueError('sentiment-mode')
    initial=as_of_ms if as_of_ms is not None else clock_ms()
    if type(initial) is not int or initial<=0:raise ValueError('invalid-cutoff')
    policy=compatibility(settings)
    generation=Generation(settings.state_parent,generated_at=generated_at,kind='stock-research-run',compatibility_id=policy,as_of_ms=initial)
    prior,previous=load_saved_predictions(settings.state_parent)
    if offline:
        if provider is not None or provider_factory is not None:raise ValueError('offline-provider-forbidden')
    elif provider is None:
        if provider_factory is None:raise ValueError('explicit-provider-required')
        provider=provider_factory()
    collection=collect_into(settings,generation=generation,provider=provider,metadata=metadata,offline=offline,
        as_of_ms=as_of_ms,clock_ms=clock_ms,session_provider=session_provider,write_selection_csv=False)
    cutoff=collection.manifest_metadata['as_of_ms'];issued=max(clock_ms(),cutoff)
    issues=[]
    try:history=assemble(collection.history_rows,[collection.receipt])
    except (ValueError,KeyError,TypeError):
        # Do not coerce invalid rows or invent identity/currency receipts for model input.
        history=History([],[]);issues.append('canonical-history-or-identity-invalid; forecasts-unavailable')
    if model_loader is not None:model,contract,model_ref=model_loader()
    contract=contract or {'quality_status':'existing-trusted-model-missing'}
    model_ref=model_ref or {'quality_status':'unavailable'}
    stamp=datetime.fromtimestamp(cutoff/1000,timezone.utc)
    calendar=MarketCalendar((stamp.date()-timedelta(days=6*366)).isoformat(),(stamp.date()+timedelta(days=40)).isoformat(),settings.calendar)
    instruments=[dict(row,panel=panel,speculative=panel=='speculative',metadata_known_at_ms=cutoff)
        for panel in ('main','speculative') for row in collection.universe[panel]]
    if instruments:
        result=run_prediction(history,instruments,model=model,contract=contract,model_ref=model_ref,calendar=calendar,
            issued_at_ms=issued,as_of_ms=cutoff,generation=generation,costs=costs or {},dated_metadata=dated_metadata or {},
            basis_evidence=basis_evidence or {},prior_forecasts=prior,prior_outcomes=previous)
    else:
        # Empty discovery is a visible report, not a fabricated instrument/forecast or model fit.
        payload={'schema_version':1,'kind':'stock-research-forecast-bundle','issued_at_ms':issued,'as_of_ms':cutoff,
            'data_sha256':sha(canonical([])),'model_ref':model_ref,'forecasts':[],'forecast_symbols':[],
            'pending_forecast_symbols':[],'top20':[],'validated_candidate_count':0,'research_diagnostics':[],
            'quality_status':'no-admitted-instruments; bootstrap history and review coverage'}
        outcomes=review_forecasts(prior,history,calendar=calendar,review_at_ms=cutoff,basis_evidence=basis_evidence or {},previous=previous)
        prediction_metadata=write_forecast_payload(generation,payload)|write_evaluation_payload(generation,outcomes)
        prediction_metadata['pending_forecast_symbols']=sorted({r['code'] for r in outcomes['current_outcomes'] if r['status']!='scored'})
        result={'forecast_payload':payload,'evaluation_payload':outcomes,'manifest_metadata':prediction_metadata}
        issues.append('no-admitted-instruments')
    collection.universe['coverage']['run_issues']=issues
    sentiment_status='off' if sentiment=='off' else 'unavailable/not-configured-until-PRSG-116'
    collection.universe['coverage']['sentiment_status']=sentiment_status
    exported=export_bundle(generation,collection.universe,collection.state,result['forecast_payload'],result['evaluation_payload'])
    prediction_id=sha(canonical({'model_ref':model_ref,'data_sha256':result['forecast_payload']['data_sha256']}))
    cstatus=collection.manifest_metadata['status']
    components={'collection':component(cstatus,COMPONENT_REQUIRED['collection'],policy),
        'prediction':component('research-only',COMPONENT_REQUIRED['prediction'],prediction_id),
        'exports':component('complete',exported['artifacts'],prediction_id)}
    final=dict(collection.manifest_metadata)|result['manifest_metadata']
    final.update(status='partial' if cstatus=='partial' or model is None or issues else 'research-only',
        model_ref=model_ref,components_schema_version=1,components=components,is_demo=False,training=False,
        sentiment_status=sentiment_status,run_issues=issues)
    return generation.finish(**final)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--offline',action='store_true');parser.add_argument('--state-dir')
    parser.add_argument('--metadata-file');parser.add_argument('--model-dir');parser.add_argument('--model-folder')
    parser.add_argument('--model-contract');parser.add_argument('--costs');parser.add_argument('--dated-metadata')
    parser.add_argument('--basis-evidence');parser.add_argument('--sentiment',choices=('auto','off'),default='auto')
    args=parser.parse_args(argv);settings=load_collection_config(args.config)
    from dataclasses import replace
    if args.state_dir:settings=replace(settings,state_parent=args.state_dir)
    if args.metadata_file:settings=replace(settings,metadata_file=args.metadata_file)
    factory=None
    if not args.offline:
        def factory():
            from provider import build_live_provider
            locator=load_secure_locator(settings.credential_locator_file or os.environ.get('PRSG_MOOMOO_CREDENTIAL_LOCATOR',''))
            return build_live_provider(locator,allow_live=True,config=settings.provider,clock_ms=lambda:int(time.time()*1000),nonce_factory=lambda:os.urandom(16).hex())
    path=run_bundle(settings,provider_factory=factory,offline=args.offline,sentiment=args.sentiment,
        model_loader=lambda:existing_model(settings.state_parent,model_dir=args.model_dir,model_folder=args.model_folder,model_contract=args.model_contract),
        costs=read_json(args.costs,{}),dated_metadata=read_json(args.dated_metadata,{}),basis_evidence=read_json(args.basis_evidence,{}))
    print(json.dumps({'generation':str(path),'training':False,'sentiment':'off' if args.sentiment=='off' else 'unavailable/not-configured-until-PRSG-116'}))
    return 0


if __name__=='__main__':
    try:status=main()
    except (ValueError,OSError,KeyError,TypeError):
        print('{"status":"run-unavailable","reason":"check coverage, private setup and trusted model; existing folders unchanged; no training attempted"}');status=2
    raise SystemExit(status)
