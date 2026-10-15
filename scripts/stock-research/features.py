"""Small fixed causal schema; missing benchmark/class is explicit, never zero-filled."""
from datetime import date
import math
import re
from statistics import mean, pstdev

from data import GAPS, require, validate_window, valid_identity

FEATURE_COLUMNS = ('return1','return5','return20','gap','daily_range','close_position',
    'atr14_fraction','volatility20','sma20_distance','sma50_distance','high20_distance',
    'low20_distance','relative_volume','dollar_turnover20','benchmark_relative20',
    'benchmark_volatility20','benchmark_missing','instrument_class','signed_leverage',
    'metadata_missing','weekday','window_lead','window_count')


def causal_features(history, code, origin, *, calendar, origin_cutoff_ms, horizon,
                    policy='strict', declared_gaps=(), benchmark=None, dated_metadata=None):
    require(calendar.close_ms(origin)<=origin_cutoff_ms,'origin-incomplete')
    windows=calendar.windows(origin)
    require(horizon in windows,'unknown-horizon')
    rows=history.as_of(code,origin_cutoff_ms,policy=policy,declared_gaps=declared_gaps)
    prior=calendar.trailing_sessions(origin,51)
    require(len(prior)==51,'insufficient-feature-history')
    bars=validate_window(rows,prior,calendar,cutoff_ms=origin_cutoff_ms)
    # Currency/basis checks apply even in retrospective mode. Measured knowledge
    # remains in receipt while assumed feature vintages are separately disclosed.
    metadata=dated_metadata or {}
    bindings=[b for r in history.receipts for b in r.get('identity_bindings',[]) if b.get('code')==code]
    supported_times={'known_at_ms','retrieved_at_ms','available_at_ms'}
    # Reject unknown time spellings rather than silently ignoring late evidence.
    require(not any((key.endswith('_at') or key.endswith('_at_ms')) and key not in supported_times
                    for key in metadata),'unsupported-metadata-availability-field')
    availability=[]
    for key in ('known_at_ms','retrieved_at_ms','available_at_ms'):
        if metadata.get(key) is not None:
            require(type(metadata[key]) is int and metadata[key]>=0,'metadata-availability-invalid')
            availability.append(metadata[key])
    metadata_known=max(availability) if availability else None
    effective=False
    try:
        first=date.fromisoformat(metadata.get('effective_from',''))
        last_date=date.fromisoformat(metadata.get('effective_to',''))
        effective=first<=date.fromisoformat(origin)<=last_date
    except (TypeError,ValueError):
        pass
    classes={'stock':{1},'ordinary-etf':{1},'leveraged-etf':{2,3},'inverse-etf':{-1,-2,-3}}
    identity=metadata.get('stock_id')
    verified=(metadata.get('code')==code and valid_identity(identity)
        and metadata_known is not None and metadata_known<=origin_cutoff_ms and effective
        and metadata.get('membership') is True
        and isinstance(metadata.get('source_url'),str) and metadata['source_url'].startswith('https://')
        and re.fullmatch(r'[0-9a-f]{64}',str(metadata.get('source_hash',''))) is not None
        and isinstance(metadata.get('reviewer'),str) and bool(metadata['reviewer'].strip())
        and type(metadata.get('signed_leverage')) is int
        and metadata['signed_leverage'] in classes.get(metadata.get('instrument_class'),set()))
    if verified:
        require(bindings and all(type(b['stock_id']) is type(identity) and b['stock_id']==identity for b in bindings),'metadata-identity-conflict')
    if policy=='strict':
        require(verified,'origin-membership-mandate-unavailable')
    close=bars[-1]['close'];previous=bars[-2]['close'];last=bars[-1]
    returns=[math.log(b['close']/a['close']) for a,b in zip(bars[-21:],bars[-20:])]
    tr=[max(b['high']-b['low'],abs(b['high']-a['close']),abs(b['low']-a['close'])) for a,b in zip(bars[-15:],bars[-14:])]
    width=last['high']-last['low'];volume=mean(b['volume'] for b in bars[-21:-1])
    require(volume>0,'zero-volume-reference')
    benchmark_return=benchmark_vol=None
    benchmark_known=0
    if benchmark is not None:
        other,benchmark_code=benchmark
        other_rows=other.as_of(benchmark_code,origin_cutoff_ms,policy=policy,declared_gaps=declared_gaps)
        other_bars=validate_window(other_rows,prior[-21:],calendar,cutoff_ms=origin_cutoff_ms)
        benchmark_known=max(b['known_at_ms'] for b in other_bars)
        benchmark_return=close/bars[-21]['close']-other_bars[-1]['close']/other_bars[0]['close']
        benchmark_vol=pstdev(math.log(b['close']/a['close']) for a,b in zip(other_bars,other_bars[1:]))
    sessions=windows[horizon]
    features=dict(zip(FEATURE_COLUMNS,(
        close/previous-1,close/bars[-6]['close']-1,close/bars[-21]['close']-1,
        last['open']/previous-1,width/close,(close-last['low'])/width if width else .5,
        mean(tr)/close,pstdev(returns),close/mean(b['close'] for b in bars[-20:])-1,
        close/mean(b['close'] for b in bars[-50:])-1,close/max(b['high'] for b in bars[-20:])-1,
        close/min(b['low'] for b in bars[-20:])-1,last['volume']/volume,
        mean(b['turnover'] for b in bars[-20:]),benchmark_return,benchmark_vol,int(benchmark is None),
        metadata['instrument_class'] if verified else None,metadata['signed_leverage'] if verified else None,
        int(not verified),date.fromisoformat(origin).weekday(),
        len(calendar.sessions(origin,sessions[0]))-1,len(sessions))))
    return {'features':features,'feature_columns':FEATURE_COLUMNS,'policy':policy,
        'assumed_feature_vintage':policy=='research-retrospective',
        'declared_gaps':sorted(declared_gaps),'origin':origin,'code':code,'horizon':horizon,
        'feature_known_at_ms':max(max(b['known_at_ms'] for b in bars),benchmark_known,metadata_known if verified else 0),
        'provider_finality_status':sorted({b['provider_finality_status'] for b in bars}),
        'time_zone_unit_status':sorted({b['time_zone_unit_status'] for b in bars}),
        'variant':'no-benchmark' if benchmark is None else 'with-benchmark'}
