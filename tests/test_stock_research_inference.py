"""Offline fictional inference/review regressions; never fit or use provider data."""
from datetime import datetime,timezone
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/stock-research'
sys.path.insert(0,str(SCRIPT))
for name in ('storage','data','market_calendar','features','model','ranking','inference','evaluation','predict'):
    existing=sys.modules.get(name)
    if existing is not None and Path(getattr(existing,'__file__','')).resolve()==(SCRIPT/f'{name}.py').resolve():continue
    spec=importlib.util.spec_from_file_location(name,SCRIPT/f'{name}.py');module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module)
from data import GAPS,assemble
from market_calendar import MarketCalendar
from model import WINDOW_POLICY
from storage import HISTORY_COLUMNS,Generation,canonical,sha
from inference import build_forecasts,converted_quantiles,write_forecast_payload
from evaluation import review_forecasts,load_saved_predictions
from ranking import decide,select_top20
from predict import run_prediction


class ExistingModel:
    def __init__(self,values=None):
        self.values=values if values is not None else [[-.03,-.02,-.01],[.01,.02,.03],[-.01,.013,.03]]
        self.calls=[]
    def predict(self,rows):
        self.calls.extend(rows);array=np.asarray([self.values for _ in rows],dtype=float)
        return {'model':array,'baseline':array.copy(),'valid':np.ones(len(rows),dtype=bool)}
    def fit(self,*args,**kwargs):raise AssertionError('INFERENCE MUST NEVER TRAIN')
    def calibrate(self,*args,**kwargs):raise AssertionError('INFERENCE MUST NEVER CALIBRATE')


@pytest.fixture(scope='module')
def calendar():return MarketCalendar('2026-01-01','2027-04-01')


def make_bar(calendar,day,index=0,known=None):
    end=calendar.close_ms(day);price=100+(index%7)*.1;known=known or end+1000
    row={k:None for k in HISTORY_COLUMNS};row.update(code='US.DEMO',session_date=day,open=price,low=price-1,high=price+2,
        close=price+.5,volume=1000+index,turnover=(1000+index)*price,currency='USD',adjustment='forward-excluding-dividends',
        source='fiction',source_at_ms=end,raw_time_key=end,raw_date=int(day.replace('-','')),raw_time_zone=-300,
        time_zone_unit_status='runtime-unverified',time_zone_unit_source_url='https://example.com',provider_finality_status='unverified',
        retrieved_at_ms=known,known_at_ms=known,price_known_at_ms=known,currency_known_at_ms=known,
        revision_vintage='fiction-v1',completed=True,completion_status='completed',volume_precision=0,
        currency_source_url='https://example.com',currency_evidence_hash='a'*64,currency_status='verified')
    return row


def fixture_inputs(calendar):
    days=calendar.sessions('2026-07-01','2026-12-10');rows=[make_bar(calendar,day,i) for i,day in enumerate(days)]
    receipts=[{'identity_bindings':[{'code':'US.DEMO','stock_id':123,'known_at_ms':calendar.close_ms(days[0])}]}]
    history=assemble(rows,receipts)
    instrument={'code':'US.DEMO','stock_id':123,'issuer_group_id':'demo-issuer','asset_type':'STOCK','sector_id':'tech',
        'signed_leverage':1,'instrument_class':'stock','metadata_known_at_ms':calendar.close_ms(days[0]),'listing_verified':True,'comparison_basis_verified':True}
    contract={'feature_variant':'no-benchmark','window_policy':WINDOW_POLICY,
        'calendar_policy':{'name':'XNYS','version':calendar.version},
        'adjustment_policy':{'required_basis':'forward-excluding-dividends','currency':'USD'},
        'training_boundaries':{'cutoff_ms':calendar.close_ms(days[0]),'max_available_at':calendar.close_ms(days[0])},
        'calibration_boundaries':None,'quality_status':'research-only','provenance':{'policy':'research-retrospective','declared_gaps':sorted(GAPS)}}
    model_ref={'model_sha256':'a'*64,'contract_sha256':'b'*64,'training_data_sha256':'c'*64,'quality_status':'research-only',
        'trusted_artifact_folder':'/fictional/trusted/model','artifact_manifest_sha256':'d'*64,'artifact_known_at_ms':calendar.close_ms(days[0])}
    cutoff=calendar.close_ms('2026-11-18')+10000
    basis={'US.DEMO':{'adjustment_vintage_id':'split-basis-v1','currency':'USD','adjustment':'forward-excluding-dividends',
        'source_hash':'e'*64,'known_at_ms':calendar.close_ms(days[0])}}
    return history,instrument,contract,model_ref,cutoff,basis


def payload(calendar,model=None,as_of=None):
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    if as_of is not None:cutoff=as_of
    return build_forecasts(history,[instrument],model=model or ExistingModel(),contract=contract,model_ref=ref,
        calendar=calendar,issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001},basis_evidence=basis)


def test_four_windows_actual_issue_cutoff_and_research_visibility(calendar):
    model=ExistingModel();bundle=payload(calendar,model)
    assert len(bundle['forecasts'])==4 and bundle['validated_candidate_count']==0 and bundle['top20']==[]
    assert len(bundle['research_diagnostics'])==1
    refs={row['reference']['close'] for row in bundle['forecasts']};assert len(refs)==1
    for row in bundle['forecasts']:
        assert row['status']=='available' and row['decision']['action']=='WATCH'
        assert row['features']['known_at_ms']<=row['as_of_ms']
        assert row['reference']['known_at_ms']>calendar.close_ms(row['origin'])
        assert row['forecast_id']==sha(canonical({k:v for k,v in row.items() if k!='forecast_id'}))
    assert bundle['forecasts'][-1]['window']['sessions']==['2026-11-23','2026-11-24','2026-11-25','2026-11-27']
    assert all(r['features']['instrument_class'] is None for r in bundle['forecasts'])
    assert len(model.calls)==4


@pytest.mark.parametrize('gross,cost,lever,action',[(.013,.006,1,'BUY'),(.012,.006,1,'WATCH'),(-.013,.006,1,'SELL'),
    (-.012,.006,1,'WATCH'),(.012,.001,-2,'BUY'),(.006,.001,-1,'BUY'),(.011,.006,3,'WATCH')])
def test_frozen_thresholds_and_inverse(gross,cost,lever,action):
    result=decide(terminal_logreturn=math.log1p(gross),cost=cost,leverage=lever,volatility=.02,
        validated=True,data_ok=True,tradable=True,metadata_ok=True)
    assert result['action']==action
    if action=='BUY':assert result['score']==pytest.approx((gross-cost)/.02)
    if action=='SELL':assert result['score']==pytest.approx(-gross/.02)
    if action=='BUY' and lever<0:assert result['fund_direction']=='bullish' and result['underlying_direction']=='bearish'


@pytest.mark.parametrize('change,expected',[({'cost':None},'NO TRADE'),({'cost':-1},'NO TRADE'),({'volatility':0},'NO TRADE'),
    ({'validated':False},'WATCH'),({'baseline':True},'WATCH'),({'tradable':False,'validated':False},'NO TRADE'),({'started':True},'WATCH')])
def test_required_failures_precede_research_fallback(change,expected):
    args=dict(terminal_logreturn=.02,cost=.001,leverage=1,volatility=.02,validated=True,data_ok=True,tradable=True,metadata_ok=True)
    assert decide(**(args|change))['action']==expected


@pytest.mark.parametrize('values',[[[-.01,-.02,.03],[.01,.02,.03],[-.01,.01,.02]],
    [[-.03,.05,.06],[.01,.02,.03],[-.01,.01,.02]],[[-1,-.9,-.8],[0,.1,.2],[-.01,.01,.02]],
    [[-.03,-.02,-.01],[.01,.02,.03],[-1000,-900,-800]],[[0,.1,.2],[.3,.4,.5],[900,1000,1100]]])
def test_invalid_quantiles_never_clipped(values):
    with pytest.raises(ValueError):converted_quantiles(values,100)


def test_gap_above_below_and_started_boundary(calendar):
    above=ExistingModel([[.01,.02,.03],[.03,.04,.05],[-.01,.01,.02]])
    rows=payload(calendar,above)['forecasts'];assert rows[0]['model']['predicted_low']>rows[0]['reference']['close']
    below=converted_quantiles([[-.05,-.04,-.03],[-.03,-.02,-.01],[-.03,-.02,-.01]],100)
    assert below['predicted_high']<100
    issued=calendar.open_ms('2026-11-19')
    rows=payload(calendar,as_of=issued)['forecasts']
    assert rows[0]['window']['started'] and rows[0]['decision']['action']=='WATCH'
    assert rows[0]['origin']=='2026-11-18'


def test_future_revision_or_missing_model_explicit_unavailable(calendar):
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    # All retained future history must not leak into this issue's features.
    model=ExistingModel();a=build_forecasts(history,[instrument],model=model,contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    stripped=assemble([r for r in history.rows if r['known_at_ms']<=cutoff],history.receipts)
    b=build_forecasts(stripped,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert [r['model'] for r in a['forecasts']]==[r['model'] for r in b['forecasts']]
    missing=build_forecasts(history,[instrument],model=None,contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert len(missing['forecasts'])==4 and all(r['status']=='unavailable' for r in missing['forecasts'])


def test_actuals_pending_missing_revision_exited_and_immutable_action(calendar):
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);forecasts=payload(calendar)['forecasts']
    before=canonical(forecasts)
    pending=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=cutoff,basis_evidence=basis)
    assert all(r['status']=='pending' and r['metrics'] is None for r in pending['current_outcomes'])
    reviewed_at=calendar.close_ms('2026-12-01')
    review=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=reviewed_at,basis_evidence=basis,previous=pending['outcome_revisions'])
    assert len(review['current_outcomes'])==4 and all(r['status']=='scored' for r in review['current_outcomes'])
    assert review['cumulative']['groups']['all']['distinct_origin_dates']==1
    assert canonical(forecasts)==before  # No current universe argument: exited name still scored.
    missing=assemble([r for r in history.rows if r['session_date']!='2026-11-24'],history.receipts)
    result=review_forecasts(forecasts,missing,calendar=calendar,review_at_ms=reviewed_at,basis_evidence=basis)
    assert next(r for r in result['current_outcomes'] if r['horizon']=='next_week')['status']=='unscored'
    old=next(r for r in history.rows if r['session_date']=='2026-11-19')
    revised=dict(old,high=old['high']+10,known_at_ms=reviewed_at+1000,price_known_at_ms=reviewed_at+1000,
        retrieved_at_ms=reviewed_at+1000,revision_vintage='corrected')
    revised_history=assemble(history.rows+[revised],history.receipts)
    later=review_forecasts(forecasts,revised_history,calendar=calendar,review_at_ms=reviewed_at+2000,
        basis_evidence=basis,previous=review['outcome_revisions'])
    assert len(later['outcome_revisions'])>len(review['outcome_revisions'])
    assert canonical(forecasts)==before and later['retraining'] is False and later['promotion'] is False


def test_identity_basis_mismatch_and_forecast_mutation_rejected(calendar):
    history,_,_,_,_,basis=fixture_inputs(calendar);forecasts=payload(calendar)['forecasts'];review_at=calendar.close_ms('2026-12-01')
    mismatched={'US.DEMO':basis['US.DEMO']|{'adjustment_vintage_id':'unknown-new-split'}}
    result=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=review_at,basis_evidence=mismatched)
    assert all(r['status']=='unscored' for r in result['current_outcomes'])
    damaged=forecasts[0]|{'model':forecasts[0]['baseline']|{'predicted_low':1}}
    with pytest.raises(ValueError,match='immutable-forecast'):review_forecasts([damaged],history,calendar=calendar,review_at_ms=review_at,basis_evidence=basis)


def candidate(index,asset='STOCK',lever=1,sector='tech',family=None,issuer=None):
    return {'code':f'US.DEMO{index}','forecast_id':str(index),'horizon':'3d','status':'available',
        'instrument':{'stock_id':index+1,'issuer_group_id':issuer or f'issuer{index}','asset_type':asset,
            'sector_id':sector,'signed_leverage':lever,'exposure_family':family,'speculative':False,
            'classification_verified':True,'issuer':'fictional-manager','etf_verification_url':'https://example.com/issuer',
            'reset':'not_applicable' if lever==1 else 'daily'},
        'validation':{'qualified':True},'window':{'started':False},'decision':{'action':'BUY','score':100-index}}


def test_diversity_caps_no_speculative_or_issuer_fill():
    rows=[candidate(i) for i in range(6)]
    rows += [candidate(i,'ETF',-2 if i<9 else 1,family='family' if i<11 else f'f{i}') for i in range(6,14)]
    rows += [candidate(20,sector='other',issuer='issuer0'),candidate(21,sector='other')]
    rows[-1]['instrument']['speculative']=True
    result=select_top20(rows);chosen=result['top20']
    assert sum(r['instrument']['asset_type']=='STOCK' for r in chosen)==4
    assert sum(r['instrument']['asset_type']=='ETF' for r in chosen)<=5
    assert sum(r['instrument']['signed_leverage']<0 or abs(r['instrument']['signed_leverage'])>1 for r in chosen)<=2
    assert sum(r['instrument'].get('exposure_family')=='family' for r in chosen)<=2
    assert len({r['instrument']['issuer_group_id'] for r in chosen})==len(chosen)


def test_shared_open_generation_and_offline_cli_no_training(calendar,tmp_path):
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    gen=Generation(tmp_path,kind='stock-research-prediction',generated_at=datetime(2026,11,18,23,tzinfo=timezone.utc))
    result=run_prediction(history,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,generation=gen,costs={'US.DEMO':.001},basis_evidence=basis)
    assert not gen.closed
    folder=gen.finish(**result['manifest_metadata'])
    saved,_=load_saved_predictions(tmp_path);assert len(saved)==4
    assert json.loads((folder/'manifest.json').read_text())['pending_forecast_symbols']==['US.DEMO']
    with pytest.raises(ValueError):write_forecast_payload(gen,result['forecast_payload'])
    for args in (['--help'],['--offline','--state-dir',str(tmp_path/'missing')]):
        cli=subprocess.run([sys.executable,str(SCRIPT/'predict.py'),*args],capture_output=True,text=True,timeout=30)
        assert cli.returncode==(0 if args==['--help'] else 2)
        assert not cli.stderr


def rehash(row):
    row=dict(row);row['forecast_id']=sha(canonical({k:v for k,v in row.items() if k!='forecast_id'}));return row


@pytest.mark.parametrize('field,value',[('currency','CAD'),('adjustment','unadjusted'),('source_hash','bad'),('adjustment_vintage_id','x'*129)])
def test_basis_reference_provenance_and_cutoff_guards(calendar,field,value):
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);row=payload(calendar)['forecasts'][0]
    wrong=basis['US.DEMO']|{field:value};row=rehash(row|{'basis_evidence':wrong})
    result=review_forecasts([row],history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence={'US.DEMO':wrong})
    assert result['current_outcomes'][0]['status']=='unscored'
    late=basis['US.DEMO']|{'known_at_ms':cutoff+1000};row=rehash(row|{'basis_evidence':late})
    assert review_forecasts([row],history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),
        basis_evidence={'US.DEMO':late})['current_outcomes'][0]['status']=='unscored'


def test_saved_shape_conversion_and_calendar_cannot_be_rehashed_into_validity(calendar):
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);original=payload(calendar)['forecasts'][0]
    changed=original['model']|{'relative_quantiles':[[.03,.02,.01],[.01,.02,.03],[-.01,.01,.02]]}
    row=rehash(original|{'model':changed})
    result=review_forecasts([row],history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence=basis)
    assert result['current_outcomes'][0]['status']=='unscored'
    early=rehash(original|{'window':original['window']|{'last_close_ms':cutoff-1}})
    result=review_forecasts([early],history,calendar=calendar,review_at_ms=cutoff,basis_evidence=basis)
    assert result['current_outcomes'][0]['status']=='unscored'
    assert result['current_outcomes'][0]['reason']=='saved-window-calendar-mismatch'


def test_past_review_excludes_future_outcomes_and_binding_facts(calendar):
    from data import History
    from inference import security_binding
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);forecasts=payload(calendar)['forecasts']
    future=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence=basis)
    old=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=cutoff,basis_evidence=basis,previous=future['outcome_revisions'])
    assert all(r['review_at_ms']<=cutoff for r in old['outcome_revisions'])
    known=history.receipts[0]['identity_bindings'][0]
    scoped=History(history.rows,[{'identity_bindings':[known,known|{'stock_id':999,'known_at_ms':cutoff+100000}]}])
    assert security_binding(scoped,'US.DEMO',cutoff)==123
    with pytest.raises(ValueError):security_binding(scoped,'US.DEMO',cutoff+200000)


def test_intraday_issuances_share_origin_weight(calendar):
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);first=payload(calendar)['forecasts']
    extra=[rehash(row|{'issued_at_ms':cutoff+i,'as_of_ms':cutoff+i}) for i in range(1,4) for row in first]
    review=review_forecasts(first+extra,history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence=basis)
    assert review['cumulative']['scored_issuances']==16
    assert review['cumulative']['groups']['all']['distinct_origin_dates']==1
    original=review_forecasts(first,history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence=basis)
    assert canonical(review['cumulative']['groups'])==canonical(original['cumulative']['groups'])


def test_latest_completed_bar_and_late_identity_metadata_are_not_guessed(calendar):
    from data import History
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    missing=assemble([r for r in history.rows if r['session_date']!='2026-11-18'],history.receipts)
    result=build_forecasts(missing,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert len(result['forecasts'])==4
    assert all(r['status']=='unavailable' and any('latest-completed-session' in reason for reason in r['reasons']) for r in result['forecasts'])
    late_binding=history.receipts[0]['identity_bindings'][0]|{'observed_at_ms':cutoff+1000}
    late=History(history.rows,[{'identity_bindings':[late_binding]}])
    result=build_forecasts(late,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert all(r['status']=='unavailable' for r in result['forecasts'])
    late_metadata=instrument|{'metadata_known_at_ms':cutoff+1000}
    result=build_forecasts(history,[late_metadata],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert all(r['status']=='available' and r['decision']['action']=='NO TRADE' for r in result['forecasts'])


def test_pending_manifest_does_not_retain_unavailable_originals(calendar,tmp_path):
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    original=payload(calendar)['forecasts']
    invalid=[rehash(r|{'status':'unavailable','model':None,'baseline':None,'code':'US.EXITED'}) for r in original]
    gen=Generation(tmp_path,kind='stock-research-prediction',generated_at=datetime(2026,11,18,23,tzinfo=timezone.utc))
    result=run_prediction(history,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,generation=gen,costs={'US.DEMO':.001},prior_forecasts=invalid)
    assert 'US.EXITED' not in result['manifest_metadata']['pending_forecast_symbols']


def test_same_actual_review_deduplicates_without_overwriting_first_cutoff(calendar):
    history,_,_,_,_,basis=fixture_inputs(calendar);forecasts=payload(calendar)['forecasts']
    cutoff=calendar.close_ms('2026-12-01')
    first=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=cutoff,basis_evidence=basis)
    second=review_forecasts(forecasts,history,calendar=calendar,review_at_ms=cutoff+1000,
        basis_evidence=basis,previous=first['outcome_revisions'])
    assert canonical(second['outcome_revisions'])==canonical(first['outcome_revisions'])


def test_unvalidated_artifact_cannot_be_promoted_by_declaration(calendar):
    history,instrument,contract,ref,cutoff,basis=fixture_inputs(calendar)
    declaration={'human_reviewed':True,'trader_reviewed':True,'known_at_ms':cutoff-1,'terminal_validated':True,
        'model_sha256':ref['model_sha256'],'qualified_groups':[[h,'stock',1] for h in ('1d','3d','5d','next_week')]}
    result=build_forecasts(history,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001},validation_receipt=declaration)
    assert result['top20']==[] and all(not row['validation']['qualified'] for row in result['forecasts'])



def test_future_model_or_calibration_cannot_enter_earlier_issue(calendar):
    history,instrument,contract,ref,cutoff,_=fixture_inputs(calendar)
    for bad_contract,bad_ref in ((contract,ref|{'artifact_known_at_ms':cutoff+1}),
            (contract|{'training_boundaries':{'cutoff_ms':cutoff+1,'max_available_at':cutoff}},ref),
            (contract|{'calibration_boundaries':{'cutoff_ms':cutoff+1,'max_available_at':cutoff}},ref)):
        model=ExistingModel()
        result=build_forecasts(history,[instrument],model=model,contract=bad_contract,model_ref=bad_ref,calendar=calendar,
            issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
        assert len(result['forecasts'])==4 and all(r['status']=='unavailable' for r in result['forecasts'])
        assert not model.calls


def test_shared_ETF_manager_is_not_an_extra_cap_but_stock_shareclasses_dedup():
    rows=[candidate(1,'ETF',1,family='broad-market',issuer='same-manager'),
        candidate(2,'ETF',1,family='bonds',issuer='same-manager'),
        candidate(3,sector='tech',issuer='company-A'),candidate(4,sector='other',issuer='company-A')]
    result=select_top20(rows)
    assert len([r for r in result['top20'] if r['instrument']['asset_type']=='ETF'])==2
    assert len([r for r in result['top20'] if r['instrument']['asset_type']=='STOCK'])==1


def test_reference_cannot_use_later_data_or_a_different_session(calendar):
    history,_,_,_,cutoff,basis=fixture_inputs(calendar);original=payload(calendar)['forecasts'][0]
    for reference in (original['reference']|{'known_at_ms':cutoff+1},original['reference']|{'session_date':'2026-11-17'}):
        row=rehash(original|{'reference':reference})
        result=review_forecasts([row],history,calendar=calendar,review_at_ms=calendar.close_ms('2026-12-01'),basis_evidence=basis)
        assert result['current_outcomes'][0]['status']=='unscored'
        assert result['current_outcomes'][0]['reason']=='saved-reference-cutoff-or-session-mismatch'


def test_collection_stock_type_maps_current_exposure_without_historical_features(calendar):
    history,instrument,contract,ref,cutoff,_=fixture_inputs(calendar)
    instrument={key:value for key,value in instrument.items() if key not in ('signed_leverage','instrument_class')}
    result=build_forecasts(history,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={'US.DEMO':.001})
    assert all(row['instrument']['signed_leverage']==1 and row['instrument']['instrument_class']=='stock' for row in result['forecasts'])
    assert all(row['features']['instrument_class'] is None and row['decision']['action']=='WATCH' for row in result['forecasts'])



def test_main_no_trade_numeric_prices_visible_without_relabel_or_speculative_fill(calendar):
    history,instrument,contract,ref,cutoff,_=fixture_inputs(calendar)
    result=build_forecasts(history,[instrument],model=ExistingModel(),contract=contract,model_ref=ref,calendar=calendar,
        issued_at_ms=cutoff,as_of_ms=cutoff,costs={})
    assert result['top20']==[] and len(result['research_diagnostics'])==1
    diagnostic=result['research_diagnostics'][0]
    assert diagnostic['decision']['action']=='NO TRADE' and diagnostic['status']=='available' and diagnostic['model']['predicted_low']>0
    speculative=build_forecasts(history,[instrument|{'speculative':True,'panel':'speculative'}],model=ExistingModel(),
        contract=contract,model_ref=ref,calendar=calendar,issued_at_ms=cutoff,as_of_ms=cutoff,costs={})
    assert speculative['research_diagnostics']==[] and len(speculative['forecasts'])==4


def test_verified_ETF_does_not_need_a_stock_shareclass_issuer_group(calendar):
    from inference import metadata_eligible
    row=candidate(1,'ETF',1,family='bonds');row['instrument'].pop('issuer_group_id')
    row['instrument'].update(instrument_class='ordinary-etf',metadata_known_at_ms=calendar.close_ms('2026-07-01'))
    assert metadata_eligible(row['instrument'],2,calendar.close_ms('2026-11-18'))
    assert select_top20([row])['validated_candidate_count']==1
    row['instrument'].pop('etf_verification_url')
    assert not metadata_eligible(row['instrument'],2,calendar.close_ms('2026-11-18'))
    assert select_top20([row])['top20']==[]


def test_next_week_terminal_risk_includes_lead_sessions(calendar):
    from data import History
    from features import causal_features
    history,_,_,_,cutoff,_=fixture_inputs(calendar);result=payload(calendar)
    week=next(row for row in result['forecasts'] if row['horizon']=='next_week')
    assert len(week['window']['sessions'])==4 and week['decision']['risk_session_count']==6
    local=History(history.as_of('US.DEMO',cutoff),history.receipts)
    features=causal_features(local,'US.DEMO','2026-11-18',calendar=calendar,origin_cutoff_ms=cutoff,
        horizon='next_week',policy='research-retrospective',declared_gaps=GAPS)
    assert week['decision']['holding_period_volatility']==pytest.approx(features['features']['volatility20']*math.sqrt(6))
