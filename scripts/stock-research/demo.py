#!/usr/bin/env python3
"""Authored fictional output template. No model fitting, credentials or provider calls."""
import argparse
import math
from datetime import datetime,timezone
from pathlib import Path

from storage import Generation,canonical,sha
from export import export_bundle,HORIZONS


def fixtures():
    from market_calendar import MarketCalendar
    calendar=MarketCalendar('2026-10-01','2026-11-20')
    windows=calendar.windows('2026-10-14')
    main=[];spec=[];forecasts=[]
    for i,(symbol,action,asset,lever) in enumerate([('DEMOA','WATCH','STOCK',1),('DEMOB','NO TRADE','STOCK',1),
        ('DEMOC','WATCH','ETF',3),('DEMOD','WATCH','ETF',-2),('DEMOS','NO TRADE','STOCK',1)]):
        instrument={'code':'US.'+symbol,'stock_id':10001+i,'name':('=Literal name' if i==1 else 'Fictional '+symbol),
            'asset_type':asset,'signed_leverage':lever,'sector_id':'Fictional Technology' if i%2==0 else 'Fictional Consumer',
            'issuer_group_id':'fictional-'+str(i),'panel':'speculative' if i==4 else 'main','speculative':i==4,'is_demo':True}
        (spec if i==4 else main).append(instrument)
        reference={'session_date':'2026-10-14','close':100.0,'currency':'USD','adjustment':'forward-excluding-dividends',
            'source':'authored-fictional-example','known_at_ms':1792008000000,'is_demo':True}
        for h,horizon in enumerate(HORIZONS):
            relative=[[-.04,-.01,.01],[.01,.03,.06],[math.log1p(v) for v in (-.03,-.01,.04)]]
            price=[[96.,99.,101.],[101.,103.,106.],[97.,99.,104.]]
            values={'targets':['low_return','high_return','terminal_logreturn'],'quantiles':[.05,.5,.95],
                'relative_quantiles':relative,'price_quantiles':price,'terminal_return_quantiles':[-.03,-.01,.04],
                'predicted_low':99.,'predicted_high':103.}
            row={'schema_version':1,'code':instrument['code'],'stock_id':instrument['stock_id'],'instrument':instrument,
                'horizon':horizon,'issued_at_ms':1792022400000,'as_of_ms':1792022400000,'origin':'2026-10-14',
                'input_data_sha256':'fictional-authored-input','model_ref':{'quality_status':'fictional-authored-template/no-model'},
                'reference':reference,'window':{'horizon':horizon,'sessions':windows[horizon],
                    'start':windows[horizon][0],'end':windows[horizon][-1],
                    'first_open_ms':calendar.open_ms(windows[horizon][0]),'last_close_ms':calendar.close_ms(windows[horizon][-1]),'started':False},
                'status':'available','model':values,'baseline':dict(values),
                'validation':{'qualified':False,'reasons':['fictional-template-not-model-performance']},
                'decision':{'action':action,'reasons':['required-cost-unavailable'] if action=='NO TRADE' else ['illustrative-unvalidated-research'],
                    'roundtrip_cost':None if action=='NO TRADE' else 0.,'score':None,'fund_direction':'bearish',
                    'underlying_direction':'bullish' if lever<0 else 'bearish','execution_authorized':False},'is_demo':True}
            row['forecast_id']=sha(canonical(row));forecasts.append(row)
    universe={'main':main,'speculative':spec,'coverage':{'status':'fictional-template','is_demo':True}}
    state={'pools':{name:[row['code'] for row in main] for name in ('winners','losers','volume')},
        'identities':{r['code']:dict(r,source='authored-fictional-example') for r in main+spec},
        'quotes':{r['code']:{'code':r['code'],'stock_id':r['stock_id'],'low_price':99.,'high_price':101.,'source_at_ms':1792022400000,
            'financial_metrics':{'earning_per_share':{'value':-2.5,'period':'fictional','currency':'USD'}},'is_demo':True} for r in main+spec}}
    payload={'schema_version':1,'kind':'stock-research-forecast-bundle','issued_at_ms':1792022400000,'as_of_ms':1792022400000,
        'data_sha256':'fictional-authored-input','model_ref':{'quality_status':'fictional-authored-template/no-model'},
        'forecasts':forecasts,'top20':[],'validated_candidate_count':0,'quality_status':'Fictional prices only; no trained model or validated candidates.',
        'forecast_symbols':[r['code'] for r in main+spec],'pending_forecast_symbols':[],'is_demo':True}
    evaluation={'schema_version':1,'kind':'stock-research-evaluation','outcome_revisions':[],
        'cumulative':{'groups':{},'scored_issuances':0},'is_demo':True}
    return universe,state,payload,evaluation


def run_demo(parent=None,*,generated_at=None):
    generation=Generation(parent or Path.home()/'Documents/stock-research-data',kind='stock-research-exports',generated_at=generated_at)
    universe,state,payload,evaluation=fixtures()
    generation.json('predictions.json',payload);generation.json('outcomes.json',evaluation)
    result=export_bundle(generation,universe,state,payload,evaluation,is_demo=True)
    return generation.finish(status='fictional-template',is_demo=True,training=False,provider_called=False,coverage=result['coverage'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir')
    args=parser.parse_args();print(run_demo(args.output_dir))


if __name__=='__main__':main()
