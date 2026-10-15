#!/usr/bin/env python3
"""Explicit saved-model inference. --offline uses cached data; never trains or calls LLMs."""
import argparse
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from config import load_collection_config
from collect import compatibility
from data import read_generations,require
from inference import build_forecasts,load_existing_model,write_forecast_payload
from evaluation import load_saved_predictions,review_forecasts,write_evaluation_payload
from market_calendar import MarketCalendar
from storage import Generation,manifests,private_read,canonical,sha


def read_json(path,default):
    if not path:return default
    file=Path(path).expanduser();require(file.stat().st_size<=16*1024**2,'input-json-budget')
    return json.loads(file.read_text())


def run_prediction(history,instruments,*,model,contract,model_ref,calendar,issued_at_ms,as_of_ms,
                   generation,costs=None,dated_metadata=None,basis_evidence=None,
                   prior_forecasts=(),prior_outcomes=()):
    """Accept an OPEN shared generation. No collection, fitting or finalization."""
    payload=build_forecasts(history,instruments,model=model,contract=contract,model_ref=model_ref,calendar=calendar,
        issued_at_ms=issued_at_ms,as_of_ms=as_of_ms,costs=costs,dated_metadata=dated_metadata,basis_evidence=basis_evidence)
    outcome=review_forecasts(list(prior_forecasts),history,calendar=calendar,review_at_ms=as_of_ms,
        basis_evidence=basis_evidence,previous=prior_outcomes)
    metadata=write_forecast_payload(generation,payload)|write_evaluation_payload(generation,outcome)
    valid_issued={r['forecast_id'] for r in prior_forecasts if r['status']=='available'}
    pending={r['code'] for r in outcome['current_outcomes'] if r['status']!='scored' and r['forecast_id'] in valid_issued}
    metadata['pending_forecast_symbols']=sorted(pending|set(metadata['pending_forecast_symbols']))
    return {'forecast_payload':payload,'evaluation_payload':outcome,'manifest_metadata':metadata}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true');parser.add_argument('--config');parser.add_argument('--state-dir')
    parser.add_argument('--model-dir');parser.add_argument('--model-folder');parser.add_argument('--model-contract')
    parser.add_argument('--output-dir');parser.add_argument('--costs');parser.add_argument('--dated-metadata')
    parser.add_argument('--basis-evidence');parser.add_argument('--as-of')
    args=parser.parse_args(argv);settings=load_collection_config(args.config)
    parent=Path(args.state_dir or settings.state_parent).expanduser()
    if not args.offline:
        # Reuse exactly one reviewed collector invocation; shared run.py calls the
        # pure run_prediction function after its own collection, never this branch.
        command=[sys.executable,str(Path(__file__).with_name('collect.py')),'--state-dir',str(parent)]
        if args.config:command+=['--config',args.config]
        result=subprocess.run(command,capture_output=True,text=True,timeout=180)
        require(result.returncode==0,'reviewed-collection-failed')
    issued=int(datetime.now(timezone.utc).timestamp()*1000)
    stamp=datetime.fromisoformat(args.as_of.replace('Z','+00:00')) if args.as_of else datetime.fromtimestamp(issued/1000,timezone.utc)
    require(stamp.tzinfo is not None,'as-of-timezone-required');as_of=int(stamp.timestamp()*1000)
    require(0<as_of<=issued,'issuance-cutoff-order')
    generations=manifests(parent,kind='stock-research-collection',compatibility_id=compatibility(settings))
    generations=[g for g in generations if type(g[2].get('as_of_ms')) is int and g[2]['as_of_ms']<=as_of]
    require(generations,'compatible-cached-collection-missing')
    _,folder,collection_manifest=generations[-1];universe=json.loads(private_read(folder/'universe.json'))
    instruments=[dict(row,panel='main',speculative=False,metadata_known_at_ms=collection_manifest['as_of_ms']) for row in universe['main']]+[
        dict(row,panel='speculative',speculative=True,metadata_known_at_ms=collection_manifest['as_of_ms']) for row in universe['speculative']]
    history=read_generations(parent,compatibility_id=compatibility(settings))
    root=Path(args.model_dir or parent/'models').expanduser()
    if args.model_folder:model_folder=Path(args.model_folder).expanduser()
    else:
        matches=manifests(root,kind='stock-research-model');require(matches,'existing-trusted-model-missing')
        model_folder=matches[-1][1]
    expected=read_json(args.model_contract,None) if args.model_contract else json.loads(private_read(model_folder/'model_contract.json'))
    model,contract,model_ref=load_existing_model(model_folder,trusted_root=root,expected_contract=expected)
    issued=int(datetime.now(timezone.utc).timestamp()*1000)  # Actual issue; frozen as_of remains the earlier input cutoff.
    start=(stamp.date()-timedelta(days=6*366)).isoformat();end=(stamp.date()+timedelta(days=40)).isoformat()
    calendar=MarketCalendar(start,end,settings.calendar)
    output=Path(args.output_dir or parent).expanduser();prior,outcomes=load_saved_predictions(output)
    generation=Generation(output,kind='stock-research-prediction',as_of_ms=as_of)
    result=run_prediction(history,instruments,model=model,contract=contract,model_ref=model_ref,calendar=calendar,
        issued_at_ms=issued,as_of_ms=as_of,generation=generation,costs=read_json(args.costs,{}),
        dated_metadata=read_json(args.dated_metadata,{}),basis_evidence=read_json(args.basis_evidence,{}),
        prior_forecasts=prior,prior_outcomes=outcomes)
    path=generation.finish(**result['manifest_metadata'],offline=args.offline,model_ref=model_ref)
    print(json.dumps({'generation':str(path),'validated_candidates':result['forecast_payload']['validated_candidate_count'],
        'model_status':contract['quality_status'],'training':False}))
    return 0


if __name__=='__main__':
    try:status=main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired):
        print('{"status":"prediction-unavailable","reason":"check cached canonical data, trusted existing model and explicit input policies; no training attempted"}')
        status=2
    raise SystemExit(status)
