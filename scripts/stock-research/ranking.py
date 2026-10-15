"""Frozen long-only research actions and diversity caps. Never execution approval."""
import math
from collections import Counter
from data import require, valid_identity


def finite(value):
    return type(value) in (float,int) and math.isfinite(value)


def decide(*, terminal_logreturn, cost, leverage, volatility, validated=False,
           data_ok=True, tradable=False, metadata_ok=False, started=False, baseline=False):
    reasons=[]
    if not data_ok:reasons.append('invalid-or-unavailable-forecast-inputs')
    if not tradable:reasons.append('tradability-unverified')
    if not metadata_ok:reasons.append('identity-or-mandate-unverified')
    if not finite(cost) or cost<0:reasons.append('roundtrip-cost-unavailable-or-invalid')
    if type(leverage) is not int or leverage not in (1,2,3,-1,-2,-3):reasons.append('signed-leverage-unavailable')
    if not finite(volatility) or volatility<=0:reasons.append('holding-period-risk-unavailable')
    gross=None
    try:
        if not finite(terminal_logreturn):raise ValueError()
        gross=math.expm1(terminal_logreturn)
        if not math.isfinite(gross) or gross<=-1:raise ValueError()
    except (OverflowError,ValueError):reasons.append('terminal-return-overflow-underflow-or-invalid')
    result={'action':'NO TRADE','classification':'research only','reasons':reasons,'gross_return':gross,
        'roundtrip_cost':cost if finite(cost) and cost>=0 else None,'threshold':None,'score':None,
        'fund_direction':'unknown' if gross is None else 'bullish' if gross>0 else 'bearish' if gross<0 else 'flat',
        'underlying_direction':'unknown','holding_period_volatility':volatility if finite(volatility) and volatility>0 else None,'execution_authorized':False}
    if gross is not None and type(leverage) is int:
        sign=1 if gross>0 else -1 if gross<0 else 0
        underlying=sign*(1 if leverage>0 else -1)
        result['underlying_direction']='bullish' if underlying>0 else 'bearish' if underlying<0 else 'flat'
    if reasons:return result
    threshold=max(.01 if abs(leverage)>1 else .005,2*cost);result['threshold']=threshold
    if started:result.update(action='WATCH',reasons=['window-already-started']);return result
    if not validated or baseline:result.update(action='WATCH',reasons=['model-or-horizon-class-terminal-unvalidated']);return result
    if gross>threshold:result.update(action='BUY',score=(gross-cost)/volatility,reasons=['validated-long-purchase-candidate'])
    elif gross<-threshold:result.update(action='SELL',score=(-gross)/volatility,reasons=['validated-avoid-new-long; exit-review-only-if-held'])
    else:result.update(action='WATCH',reasons=['strict-directional-threshold-not-exceeded'])
    if result['score'] is not None and not finite(result['score']):
        result.update(action='NO TRADE',score=None,reasons=['rank-score-overflow'])
    return result


def select_top20(forecasts):
    """Primary table uses the three-session decision, no WATCH/speculative fill."""
    candidates=[];diagnostics=[];excluded=[]
    for row in forecasts:
        decision=row['decision']
        if row.get('horizon')!='3d':continue
        m=row['instrument']
        if decision['action'] in ('WATCH','NO TRADE') and row['status']=='available' and not m.get('speculative') and m.get('panel','main')=='main':diagnostics.append(row)
        if decision['action'] not in ('BUY','SELL'):continue
        m=row['instrument'];reasons=[]
        if row.get('status')!='available':reasons.append('forecast-unavailable')
        if row.get('validation',{}).get('qualified') is not True:reasons.append('unvalidated')
        if row['window']['started']:reasons.append('started-window')
        if m.get('speculative') is True:reasons.append('speculative-excluded')
        if not valid_identity(m.get('stock_id')):reasons.append('security-identity-unverified')
        if m.get('asset_type')=='STOCK' and not m.get('issuer_group_id'):reasons.append('stock-issuer-unverified')
        if m.get('asset_type') not in ('STOCK','ETF'):reasons.append('asset-type-unverified')
        if m.get('asset_type')=='STOCK' and not m.get('sector_id'):reasons.append('sector-unverified')
        if m.get('asset_type')=='ETF' and (not m.get('issuer') or not isinstance(m.get('etf_verification_url'),str)
                or not m['etf_verification_url'].startswith('https://') or m.get('classification_verified') is not True
                or m.get('reset')!=('not_applicable' if m.get('signed_leverage')==1 else 'daily')
                or not m.get('exposure_family') or type(m.get('signed_leverage')) is not int
                or m['signed_leverage'] not in (1,2,3,-1,-2,-3)):reasons.append('ETF-exposure-or-mandate-unverified')
        if not finite(decision.get('score')):reasons.append('rank-score-unavailable')
        if reasons:excluded.append({'forecast_id':row['forecast_id'],'reasons':reasons})
        else:candidates.append(row)
    candidates.sort(key=lambda r:(-r['decision']['score'],r['code'],r['forecast_id']))
    sectors=Counter();families=Counter();seen_ids=set();issuers=set();seen_codes=set();etfs=geared=0;selected=[]
    for row in candidates:
        m=row['instrument'];etf=m['asset_type']=='ETF';lever=m.get('signed_leverage')
        union=etf and (lever<0 or abs(lever)>1);family=m.get('exposure_family');security=(type(m['stock_id']).__name__,m['stock_id'])
        reason=None
        if row['code'] in seen_codes or security in seen_ids or (not etf and m['issuer_group_id'] in issuers):reason='duplicate-code-security-or-stock-issuer'
        elif not etf and sectors[m['sector_id']]>=4:reason='stock-sector-cap4'
        elif etf and etfs>=5:reason='ETF-cap5'
        elif union and geared>=2:reason='geared-or-inverse-union-cap2'
        elif family and families[family]>=2:reason='common-exposure-family-cap2'
        elif len(selected)>=20:reason='top20-cap'
        if reason:excluded.append({'forecast_id':row['forecast_id'],'reasons':[reason]});continue
        selected.append(row);seen_codes.add(row['code']);seen_ids.add(security)
        if not etf:issuers.add(m['issuer_group_id'])
        if etf:etfs+=1
        else:sectors[m['sector_id']]+=1
        if union:geared+=1
        if family:families[family]+=1
    return {'top20':selected,'research_diagnostics':diagnostics,'rank_exclusions':excluded,
        'validated_candidate_count':len(selected),'meaning':'long-only research candidates; no execution approval'}
