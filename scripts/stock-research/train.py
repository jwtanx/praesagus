#!/usr/bin/env python3
"""Explicit offline stock-research training. No provider, LLM or silent inference fit.

Default source is the configured collection generation parent. Standalone CSV or
SQLite requires --receipt JSON. Date folds are frozen before fitting and saved
alongside each immutable artifact. Missing data exits with setup guidance.
"""
import argparse
from datetime import datetime, timezone, timedelta
import glob
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from config import load_collection_config
from data import GAPS, make_labels, read_csv, read_generations, read_sqlite, require
from features import causal_features
from market_calendar import MarketCalendar
from model import (ModelConfig, clean_records, freeze, research_fit, save_artifact,
                   evaluate_scopes, train_frozen)
from storage import Generation, canonical, sha


def prepare_records(history,*,calendar,start,end,fit_cutoff_ms,policy,declared_gaps=(),metadata=(),benchmark=None):
    """Build only observed labels; rejected origins are counted with bounded reasons."""
    records=[];rejected={}
    sessions=calendar.sessions(start,end)
    session_indices={day:i for i,day in enumerate(calendar._sessions)}
    by_code={}
    for item in metadata:by_code.setdefault(item['code'],[]).append(item)
    for code in sorted(history._index):
        for origin in sessions:
            origin_at=calendar.close_ms(origin)+1_000
            dated=[m for m in by_code.get(code,[]) if m.get('effective_from','9999')<=origin<=m.get('effective_to','0000')]
            require(len(dated)<=1,'ambiguous-dated-metadata')
            try:
                labels=make_labels(history,code,origin,calendar=calendar,fit_cutoff_ms=fit_cutoff_ms,
                    origin_cutoff_ms=origin_at,policy=policy,declared_gaps=declared_gaps)
                for label in labels:
                    if label['status']!='complete':
                        reason='pending:'+label.get('reason','unknown');rejected[reason]=rejected.get(reason,0)+1;continue
                    item=causal_features(history,code,origin,calendar=calendar,origin_cutoff_ms=origin_at,
                        horizon=label['horizon'],policy=policy,declared_gaps=declared_gaps,
                        dated_metadata=dated[0] if dated else None,benchmark=benchmark)
                    records.append(label|item|{'origin_at_ms':origin_at,'origin_session_index':session_indices[origin],
                        'window_distance':session_indices[label['end']]-session_indices[origin]})
            except ValueError as error:
                reason=str(error);rejected[reason]=rejected.get(reason,0)+1
    require(records,'no-eligible-records: provide completed canonical OHLC and attributable identity/receipt; fresh backfill cannot create historical availability')
    return clean_records(records),rejected


def run_training(history,*,calendar,start,end,fit_cutoff_ms,folds,model_dir,
                 policy='strict',declared_gaps=(),metadata=(),benchmark=None,present_research_fit=False,generated_at=None):
    config=ModelConfig(feature_variant='with-benchmark' if benchmark else 'no-benchmark')
    records,rejected=prepare_records(history,calendar=calendar,start=start,end=end,fit_cutoff_ms=fit_cutoff_ms,
        policy=policy,declared_gaps=declared_gaps,metadata=metadata,benchmark=benchmark)
    provenance=history.receipt(policy,declared_gaps)|{'calendar':{'name':calendar.name,'version':calendar.version,
        'schedule_sha256':sha(canonical([{'session_date':day,'close_at_ms':calendar.close_ms(day)} for day in calendar._sessions]))},
        'adjustment_policy':{'required_basis':'forward-excluding-dividends','currency':'USD',
            'source_receipts':[r.get('adjustment_policy') for r in history.receipts],
            'historical_point_in_time':'not-established-without-independent-reviewed-evidence'},
        'metadata_sha256':sha(canonical(metadata)),'benchmark_sha256':None if benchmark is None else sha(canonical(benchmark[0].rows)),
        'rejected_origins':rejected,'target_source':'observed OHLC only'}
    receipt=freeze(records,folds=folds,config=config,provenance=provenance,fit_cutoff_ms=fit_cutoff_ms)
    generation=Generation(model_dir,kind='stock-research-model',generated_at=generated_at,
        compatibility_id=sha(canonical({'config':receipt['config'],'provenance':provenance})),as_of_ms=fit_cutoff_ms)
    generation.json('freeze.json',receipt)  # Durable freeze precedes every estimator fit.
    model,evaluation=train_frozen(records,receipt,calendar=calendar)
    evaluation['assessment']=evaluate_scopes(evaluation['predictions'],evidence={},resources=evaluation['resources'])
    if present_research_fit:
        require(policy=='research-retrospective','present-fit-requires-explicit-research-policy')
        model,present=research_fit(records,receipt);evaluation['present_research_fit']=present
    if model is not None:save_artifact(generation,model,receipt,evaluation)
    else:generation.json('evaluation.json',evaluation)
    return generation.finish(status='research-only' if model else 'insufficient-empty-purged-folds',
        model_available=model is not None,freeze_sha256=sha(canonical(receipt)),strong_model_accepted=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--csv-dir');parser.add_argument('--csv-glob')
    parser.add_argument('--sqlite');parser.add_argument('--table',default='ohlcv');parser.add_argument('--receipt')
    parser.add_argument('--model-dir');parser.add_argument('--state-dir');parser.add_argument('--metadata')
    parser.add_argument('--policy',choices=('strict','research-retrospective'),default='strict')
    parser.add_argument('--declare-gap',action='append',default=[])
    parser.add_argument('--present-research-fit',action='store_true')
    parser.add_argument('--start');parser.add_argument('--end');parser.add_argument('--calibration-start')
    parser.add_argument('--holdout-start');parser.add_argument('--fit-cutoff')
    args=parser.parse_args(argv)
    require(sum(bool(v) for v in (args.csv_dir,args.csv_glob,args.sqlite))<=1,'choose-one-history-input')
    settings=load_collection_config(args.config)
    if args.sqlite or args.csv_dir or args.csv_glob:
        require(args.receipt,'standalone-data-requires-attributable-receipt')
        path=Path(args.receipt);require(path.stat().st_size<=16*1024**2,'receipt-budget')
        receipt=json.loads(path.read_text())
        history=read_sqlite(args.sqlite,receipt=receipt,table=args.table) if args.sqlite else read_csv(
            glob.glob(args.csv_glob or str(Path(args.csv_dir)/'*.csv')),receipt=receipt)
    else:
        # Collection compatibility is the established ingestion policy, not a new screener.
        from collect import compatibility
        history=read_generations(args.state_dir or settings.state_parent,compatibility_id=compatibility(settings))
    require(history.rows,'no-local-history: run reviewed collection or supply canonical CSV/SQLite plus receipt')
    cutoff=datetime.fromisoformat(args.fit_cutoff.replace('Z','+00:00')) if args.fit_cutoff else datetime.now(timezone.utc)
    require(cutoff.tzinfo is not None,'fit-cutoff-timezone-required')
    end=args.end or (cutoff.date()-timedelta(days=1)).isoformat()
    start=args.start or (cutoff.date()-timedelta(days=3*365)).isoformat()
    calendar=MarketCalendar((datetime.fromisoformat(start).date()-timedelta(days=400)).isoformat(),
        (datetime.fromisoformat(end).date()+timedelta(days=40)).isoformat(),settings.calendar)
    dates=calendar.sessions(start,end)
    require(len(dates)>=100,'history-date-range-too-short')
    calibration=args.calibration_start or dates[int(len(dates)*.6)]
    holdout=args.holdout_start or dates[int(len(dates)*.8)]
    # One earlier walk-forward evaluation and one reserved final holdout.
    eval_index=dates.index(holdout);cal_index=dates.index(calibration)
    middle=dates[(cal_index+eval_index)//2]
    folds=[{'calibration_start':calibration,'evaluation_start':middle,'evaluation_end':dates[eval_index-1],'kind':'walk-forward'},
        {'calibration_start':calibration,'evaluation_start':holdout,'evaluation_end':dates[-1],'kind':'holdout'}]
    metadata=json.loads(Path(args.metadata).read_text()) if args.metadata else []
    result=run_training(history,calendar=calendar,start=start,end=end,fit_cutoff_ms=int(cutoff.timestamp()*1000),
        folds=folds,model_dir=args.model_dir or str(Path(settings.state_parent).expanduser()/'models'),
        policy=args.policy,declared_gaps=args.declare_gap,metadata=metadata,present_research_fit=args.present_research_fit)
    print(json.dumps({'generation':str(result),'quality':'research-only','strong_model_accepted':False}))
    return 0


if __name__=='__main__':
    try:exit_code=main()
    except (ValueError,OSError,KeyError,TypeError):
        print('{"status":"training-unavailable","reason":"check canonical history, identity/receipt, dates and availability; no provider or model promotion attempted"}')
        exit_code=2
    raise SystemExit(exit_code)
