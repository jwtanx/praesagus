"""Deterministic private quote overlay; no collection, publication or forecasts."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from importlib import import_module
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, urlparse
from zoneinfo import ZoneInfo

from ingest.private_market_store import REPO, canonical, check_secrets, need, parse_aware, private, safe

GAPS = ['currency_unknown', 'session_unknown', 'adjustment_unknown', 'prior_close_unknown']
QUOTE_KEYS = {'price','volume','source_at','observed_at','ingested_at','known_at','cutoff',
              'origin','currency','session','adjustment','prior_close','gaps','provenance'}
EXCLUSIONS = {'source_time_unknown','source_time_after_cutoff','source_time_after_observation','price_unusable'}
REASONS = set(GAPS) | {'no_eligible_quote','no_returned_quote','no_available_attempts','same_time_conflict'}
PROVENANCE_KEYS = {'provider','connector','capture_authenticity','rights_status'}


def epoch_time(milliseconds):
    return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(milliseconds=milliseconds)).isoformat(timespec='milliseconds')


def validate_observed_quote(quote, cutoff):
    """Strict optional schema3 point contract, shared by projection and validator."""
    need(isinstance(quote,dict) and set(quote)==QUOTE_KEYS)
    for key in ('price','volume'):
        value=quote[key]
        need(type(value) in (int,float) and math.isfinite(value) and value>=0
             and (key!='price' or value>0))
    need(all(quote[k] is None for k in ('currency','session','adjustment','prior_close')))
    need(quote['origin'] in ('synthetic','trusted-capture'))
    gaps=quote['gaps']
    need(isinstance(gaps,list) and 1<=len(gaps)<=16 and set(GAPS)<=set(gaps)
         and all(isinstance(g,str) and 0<len(g)<=256 for g in gaps))
    times={k:parse_aware(quote[k]) for k in ('source_at','observed_at','ingested_at','known_at','cutoff')}
    need(times['cutoff']==parse_aware(cutoff)
         and times['source_at']<=times['observed_at']<=times['ingested_at']<=times['known_at']<=times['cutoff'])
    provenance=quote['provenance']
    need(isinstance(provenance,dict) and set(provenance)==PROVENANCE_KEYS
         and provenance['provider']=='moomoo-rest' and provenance['connector']=='moomoo-rest-capture'
         and provenance['capture_authenticity']=='caller-supplied-unverified'
         and provenance['rights_status']=='unconfirmed')
    check_secrets(quote)


PUBLIC_REFERENCE_URL = 'https://open.moomoo.com/mcp-docs/available-tools'
PUBLIC_TIMES = ('source_at','observed_at','ingested_at','known_at','cutoff')
PUBLIC_GAPS = ['provider_currency_unknown','session_unknown','adjustment_unknown','prior_close_unknown','rights_unconfirmed']
PUBLIC_KEYS = {'price',*PUBLIC_TIMES,'provider','reference_url','listing_currency',
               'provider_currency','session','adjustment','prior_close','rights_status',
               'capture_authenticity','gaps'}
PRIVATE_PUBLIC_KEYS = {'private_draft','observed_quote','quote_provenance','attempt_id',
                       'raw_hash','semantic_hash','run_id','raw_body','raw_response',
                       'credential_directory','credential_path','account_id','account',
                       'private_path','private_store','provenance'}


def validate_public_report_boundary(value):
    """Reject private structures anywhere in a clean public report, not just rows."""
    check_secrets(value)
    def walk(item):
        if isinstance(item,dict):
            need(all(isinstance(key,str) and key.lower() not in PRIVATE_PUBLIC_KEYS for key in item))
            for child in item.values():walk(child)
        elif isinstance(item,list):
            for child in item:walk(child)
    walk(value)


def validate_public_snapshot(snapshot, cutoff, *, listing_currency):
    need(isinstance(snapshot,dict) and set(snapshot)==PUBLIC_KEYS)
    price=snapshot['price']
    need(type(price) in (int,float) and math.isfinite(price) and price>0)
    need(listing_currency=='USD' and snapshot['listing_currency']==listing_currency)
    need(all(snapshot[k] is None for k in ('provider_currency','session','adjustment','prior_close')))
    need(snapshot['provider']=='moomoo-rest' and snapshot['reference_url']==PUBLIC_REFERENCE_URL
         and snapshot['rights_status']=='unconfirmed'
         and snapshot['capture_authenticity']=='caller-supplied-unverified'
         and snapshot['gaps']==PUBLIC_GAPS)
    times={key:parse_aware(snapshot[key]) for key in PUBLIC_TIMES}
    need(times['cutoff']==parse_aware(cutoff)
         and times['source_at']<=times['observed_at']<=times['ingested_at']<=times['known_at']<=times['cutoff'])
    check_secrets(snapshot)


def map_public_snapshot(quote, cutoff, *, listing_currency):
    """Price-only allowlist; input IDs/volume never copied, no report or writer I/O."""
    def project():
        validate_observed_quote(quote,cutoff)
        need(quote['origin']=='trusted-capture')
        result={key:quote[key] for key in ('price',*PUBLIC_TIMES)}
        result.update(provider='moomoo-rest',reference_url=PUBLIC_REFERENCE_URL,
                      listing_currency=listing_currency,provider_currency=None,session=None,
                      adjustment=None,prior_close=None,rights_status='unconfirmed',
                      capture_authenticity='caller-supplied-unverified',gaps=list(PUBLIC_GAPS))
        validate_public_snapshot(result,cutoff,listing_currency=listing_currency)
        return result
    return safe(project,category='public-snapshot-failed')


MARKET_SNAPSHOT_FIELDS = {
    'schema_version','report_date','cutoff','provider','rights','coverage','quotes','news_queries'
}
MARKET_QUOTE_FIELDS = {
    'market','country','ticker','name','listing_currency','status','gaps','public_snapshot','metrics'
}
MARKET_QUOTE_STATUSES = {'selected','missing','conflicted','failed','unsupported'}
MARKET_METRIC_FIELDS = {'provider_volume','volume_unit'}
MARKET_NEWS_QUERY_FIELDS = {'keyword','status','records'}
MARKET_NEWS_FIELDS = {
    'provider','endpoint','title','url','news_type','published_at','source_at',
    'observed_at','ingested_at','known_at','cutoff'
}
RIGHTS_FIELDS = {
    'quote.price','quote.provider_volume','news.title','news.url','news.news_type',
    'news.publication_time','source.timestamps'
}
RIGHTS_INPUT_FIELDS = {
    'schema_version','provider','authority','markets','fields','uses','evidence_url',
    'verified_by','verified_at','expires_at'
}
RIGHTS_OUTPUT_FIELDS = {
    'status','provider','markets','fields','uses','evidence_url','verified_at','expires_at','published_at'
}
RIGHTS_USES = {'public-website-display','redistribution'}
RIGHTS_URL = re.compile(r'^https://[^\s<>"\']+$')
NEWS_KEYWORDS = ('SPY','QQQ')


def _timestamp(value, field):
    try:
        return parse_aware(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f'invalid {field}') from None


def _safe_https_url(value):
    if not isinstance(value,str) or RIGHTS_URL.fullmatch(value) is None:
        return False
    parsed=urlparse(value)
    query_keys={key.lower() for key,_ in parse_qsl(parsed.query,keep_blank_values=True)}
    return bool(parsed.hostname and not parsed.username and not parsed.password
                and not query_keys.intersection({'token','key','secret','auth','authorization','account','session'})
                and not parsed.fragment)


def validate_market_rights(evidence, published_at, *, markets=('US',), fields=RIGHTS_FIELDS):
    """Require explicit current permission for every field and requested market."""
    need(isinstance(evidence,dict) and set(evidence)==RIGHTS_INPUT_FIELDS)
    need(type(evidence['schema_version']) is int and evidence['schema_version']==1
         and evidence['provider']=='moomoo-rest')
    for key in ('authority','verified_by'):
        need(isinstance(evidence[key],str) and 1<=len(evidence[key].strip())<=512)
    requested_markets=set(markets)
    allowed_markets=evidence['markets']
    need(isinstance(allowed_markets,list) and len(allowed_markets)==len(set(allowed_markets))
         and requested_markets<=set(allowed_markets) and set(allowed_markets)<={'US','HK','SG','JP','CN'})
    allowed_fields=evidence['fields']
    need(isinstance(allowed_fields,list) and len(allowed_fields)==len(set(allowed_fields))
         and all(isinstance(field,str) and field for field in allowed_fields)
         and set(fields)<=set(allowed_fields))
    uses=evidence['uses']
    need(isinstance(uses,list) and len(uses)==len(set(uses)) and RIGHTS_USES<=set(uses))
    source=evidence['evidence_url']
    need(_safe_https_url(source))
    verified=_timestamp(evidence['verified_at'],'rights verified_at')
    expires=_timestamp(evidence['expires_at'],'rights expires_at')
    now=_timestamp(published_at,'publication time')
    need(verified<=now<expires)
    return {
        'status':'verified', 'provider':'moomoo-rest', 'markets':sorted(requested_markets),
        'fields':sorted(fields), 'uses':sorted(RIGHTS_USES), 'evidence_url':source,
        'verified_at':evidence['verified_at'], 'expires_at':evidence['expires_at'],
        'published_at':published_at,
    }


def _market_quote_point(entry, cutoff, ticker, run_id):
    record=entry.get('quote')
    provenance=entry.get('provenance')
    if record is None or provenance is None:
        return None
    need(record.get('code')=='US.'+ticker and record.get('price',0)>0)
    quote={
        'price':record['price'], 'volume':record['volume'],
        'source_at':epoch_time(provenance['source_ms']), 'observed_at':provenance['observed_at'],
        'ingested_at':provenance['ingested_at'], 'known_at':epoch_time(provenance['known_ms']),
        'cutoff':cutoff, 'origin':provenance['origin'], 'currency':None, 'session':None,
        'adjustment':None, 'prior_close':None, 'gaps':list(GAPS),
        'provenance':{key:provenance[key] for key in PROVENANCE_KEYS},
    }
    return map_public_snapshot(quote,cutoff,listing_currency='USD')


def project_public_market_snapshot(store, universe, *, run_id, cutoff, rights_evidence=None,
                                   publication_time=None):
    """Project a same-run REST selection to a rights-gated, public-safe data shape.

    With no permission evidence this creates only a private analysis artifact. The
    public writer separately refuses to write such an artifact into Pages.
    """
    validator=import_module('scripts.daily-market-brief.validate_report_json')
    keys,instruments=validator.validate_universe(Path('watchlist-universe-five.json'),universe)
    need(len(instruments)==50 and universe.get('count_per_group')==5)
    expected=['US.'+ticker for (market,ticker) in instruments if market=='US']
    need(len(expected)==30 and len(set(expected))==30)
    cutoff_time=_timestamp(cutoff,'report cutoff')
    published=publication_time or datetime.now(timezone.utc).isoformat()
    rights=(validate_market_rights(rights_evidence,published) if rights_evidence is not None else None)
    selection=store.select_snapshots(run_id,cutoff,expected)
    rows=[]
    for group in universe['groups']:
        for instrument in group['instruments']:
            market,ticker=instrument['market'],instrument['ticker']
            code=market+'.'+ticker
            gaps=[];point=None;metrics={'provider_volume':None,'volume_unit':'unknown'}
            if market=='MY':
                status='unsupported';gaps=['market_not_supported_by_moomoo_rest_snapshot']
            else:
                selected=selection['quotes'][code]
                reasons=selected['gap_reasons']+list(selected.get('excluded_counts',{}))
                if selected['quote'] is not None:
                    status='selected'
                    point=_market_quote_point(selected,cutoff,ticker,run_id)
                    metrics={'provider_volume':selected['quote']['volume'],
                             'volume_unit':'provider unit/session not verified'}
                    gaps=['provider_currency_unknown','session_unknown','adjustment_unknown','prior_close_unknown',
                          'volume_unit_unknown','point_observation_not_bar']
                elif 'same_time_conflict' in reasons:
                    status='conflicted';gaps=list(dict.fromkeys(reasons))
                elif selection['attempt_status_counts'].get('failed',0) and not selection['coverage']['returned']['count']:
                    status='failed';gaps=list(dict.fromkeys(reasons+['collection_failed_attempt']))
                else:
                    status='missing';gaps=list(dict.fromkeys(reasons or ['no_eligible_quote']))
            rows.append({
                'market':market,'country':instrument['country'].upper(),'ticker':ticker,
                'name':instrument['name'],'listing_currency':instrument['currency'],
                'status':status,'gaps':gaps,'public_snapshot':point,'metrics':metrics,
            })
    attempts=store.attempts(cutoff,limit=1000)
    news_rows=store.query('news',cutoff,limit=1000)
    queries=[]
    for keyword in NEWS_KEYWORDS:
        matching=[item for item in attempts if item.get('run_id')==run_id and item.get('kind')=='news'
                  and item.get('query',{}).get('symbol')==keyword]
        if len(matching)>1:
            status='unavailable';records=[]
        elif not matching:
            status='unavailable';records=[]
        else:
            attempt=matching[0]
            status=('success' if attempt['status']=='success' else
                    'empty' if attempt['status']=='successful-empty' else 'unavailable')
            records=[]
            if status=='success':
                for item in news_rows:
                    meta=item['observation'];record=item['record']
                    if meta['run_id']!=run_id or meta['query'].get('symbol')!=keyword:
                        continue
                    if not item['eligible_for_temporal_evidence'] or item['source_ms'] is None:
                        continue
                    records.append({
                        'provider':'moomoo-rest','endpoint':'/api/v1.0/quote/find-news',
                        'title':record['title'],'url':record['url'],'news_type':record['news_type'],
                        'published_at':epoch_time(item['source_ms']),
                        'source_at':epoch_time(item['source_ms']),
                        'observed_at':meta['observed_at'],'ingested_at':meta['ingested_at'],
                        'known_at':epoch_time(meta['known_ms']),'cutoff':cutoff,
                    })
        deduped=[];seen=set()
        for record in records:
            identity=(record['title'],record['url'],record['published_at'])
            if identity not in seen:seen.add(identity);deduped.append(record)
        if status=='success' and not deduped:status='empty'
        queries.append({'keyword':keyword,'status':status,'records':deduped})
    report_date=cutoff_time.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    snapshot={
        'schema_version':1,'report_date':report_date,'cutoff':cutoff,'provider':'moomoo-rest',
        'rights':rights or {'status':'unverified','provider':'moomoo-rest'},
        'coverage':{'expected_us':30,'selected_us':selection['coverage']['selected']['count'],
                    'unsupported_my':20,'quote_attempt_statuses':selection['attempt_status_counts']},
        'quotes':rows,'news_queries':queries,
    }
    validate_market_snapshot(snapshot,require_rights=rights is not None)
    return snapshot


MOOMOO_TREND_FIELDS={
    'provider','endpoint','method','signal','label','status','reason','adjustment',
    'bar_count','bar_dates','last_bar_date','last_bar_timezone_offset_minutes',
    'sma5','sma20','observed_at','ingested_at','known_at','cutoff','source_url',
    'rights_status','capture_authenticity'
}
MOOMOO_TREND_URL='https://open.moomoo.com/api/quote/basic-data/history-kline'


def _unavailable_moomoo_trend(code,cutoff,reason='history-unavailable'):
    return {'provider':'moomoo-rest' if code.startswith('US.') else 'unsupported',
        'endpoint':'/api/v1.0/quote/{symbol}/history-kline' if code.startswith('US.') else None,
        'method':'SMA-5-vs-SMA-20','signal':'unavailable','label':'Unavailable',
        'status':'unavailable','reason':reason,'adjustment':'none' if code.startswith('US.') else None,
        'bar_count':0,'bar_dates':[],'last_bar_date':None,'last_bar_timezone_offset_minutes':None,
        'sma5':None,'sma20':None,'observed_at':None,'ingested_at':None,'known_at':None,
        'cutoff':cutoff,'source_url':MOOMOO_TREND_URL if code.startswith('US.') else None,
        'rights_status':'unconfirmed' if code.startswith('US.') else 'not-applicable',
        'capture_authenticity':'caller-supplied-unverified' if code.startswith('US.') else 'not-collected'}


def project_moomoo_trend(store,*,run_id,cutoff,code,history_entries=None,history_attempts=None):
    """Derive a descriptive SMA trend from same-run completed Moomoo daily bars."""
    def project():
        need(isinstance(code,str) and re.fullmatch(r'(?:US\.[A-Z][A-Z0-9.-]{0,59}|MY\.[A-Z0-9]{1,14})',code))
        frozen=parse_aware(cutoff)
        result=_unavailable_moomoo_trend(code,cutoff,'unsupported-market' if code.startswith('MY.') else 'history-unavailable')
        if code.startswith('MY.'):
            validate_moomoo_trend(result,cutoff)
            return result
        attempts=[a for a in (history_attempts if history_attempts is not None else store.attempts(cutoff,limit=1000))
                  if a.get('run_id')==run_id and a.get('kind')=='history'
                  and a.get('query',{}).get('code')==code]
        if len(attempts)>1:
            result['reason']='ambiguous-history-attempts'
            validate_moomoo_trend(result,cutoff);return result
        if attempts and attempts[0]['status']=='failed':
            result['reason']='history-request-failed'
            validate_moomoo_trend(result,cutoff);return result
        try:
            entries=(history_entries if history_entries is not None else
                     store.query('history',cutoff,mode='strict',limit=5000,run_id=run_id))
        except Exception:
            result['reason']='history-selection-failed'
            validate_moomoo_trend(result,cutoff);return result
        now_et=frozen.astimezone(ZoneInfo('America/New_York'))
        latest_complete=now_et.date() if now_et.time()>=time(16,15) else now_et.date()-timedelta(days=1)
        by_date={}
        for item in entries:
            meta=item['observation'];record=item['record']
            if meta['run_id']!=run_id or meta.get('query',{}).get('code')!=code:continue
            if (not item['eligible_for_temporal_evidence'] or item['source_ms'] is None
                    or parse_aware(meta['observed_at'])>frozen or parse_aware(meta['ingested_at'])>frozen):continue
            try:bar_date=date.fromisoformat(record['date'])
            except (TypeError,ValueError):continue
            if bar_date>latest_complete:continue
            prior=by_date.get(bar_date)
            candidate={'record':record,'meta':meta,'source_ms':item['source_ms'],
                       'semantic_hash':item['semantic_hash']}
            if prior is None or meta['known_ms']>prior['meta']['known_ms']:
                by_date[bar_date]=candidate
            elif meta['known_ms']==prior['meta']['known_ms'] and item['semantic_hash']!=prior['semantic_hash']:
                result['reason']='same-time-bar-conflict'
                validate_moomoo_trend(result,cutoff);return result
        bars=sorted(by_date.items())
        valid=[]
        for bar_day,candidate in bars:
            close=candidate['record']['close']
            if type(close) in (int,float) and math.isfinite(close) and close>0:
                valid.append((bar_day,candidate))
        if len(valid)<20:
            result['reason']='insufficient-completed-history' if attempts and attempts[0]['status']!='failed' else 'history-unavailable'
            validate_moomoo_trend(result,cutoff);return result
        latest=valid[-20:]
        closes=[entry['record']['close'] for _,entry in latest]
        sma5=math.fsum(closes[-5:])/5
        sma20=math.fsum(closes)/20
        signal='bullish' if sma5>sma20 else 'bearish' if sma5<sma20 else 'neutral'
        last_record,last_meta=latest[-1][1]['record'],latest[-1][1]['meta']
        result.update(signal=signal,label=signal.capitalize(),status='available',reason=None,
            bar_count=20,bar_dates=[day.isoformat() for day,_ in latest],
            last_bar_date=latest[-1][0].isoformat(),
            last_bar_timezone_offset_minutes=last_record['time_zone'],
            sma5=round(sma5,8),sma20=round(sma20,8),
            observed_at=last_meta['observed_at'],ingested_at=last_meta['ingested_at'],
            known_at=epoch_time(last_meta['known_ms']))
        validate_moomoo_trend(result,cutoff)
        return result
    return safe(project,category='moomoo-trend-projection-failed')


def validate_moomoo_trend(value,cutoff):
    need(isinstance(value,dict) and set(value)==MOOMOO_TREND_FIELDS
         and value['signal'] in {'bullish','bearish','neutral','unavailable'}
         and value['status'] in {'available','unavailable'}
         and value['method']=='SMA-5-vs-SMA-20' and value['cutoff']==cutoff
         and value['adjustment'] in {'none',None})
    need((value['provider']=='moomoo-rest' and value['endpoint']=='/api/v1.0/quote/{symbol}/history-kline'
          and value['source_url']==MOOMOO_TREND_URL and value['rights_status']=='unconfirmed'
          and value['capture_authenticity']=='caller-supplied-unverified')
         or (value['provider']=='unsupported' and value['endpoint'] is None and value['source_url'] is None
          and value['rights_status']=='not-applicable' and value['capture_authenticity']=='not-collected'))
    need(value['source_url'] is None or value['source_url']==MOOMOO_TREND_URL)
    if value['status']=='unavailable':
        need(value['signal']=='unavailable' and value['label']=='Unavailable'
             and value['bar_count']==0 and value['bar_dates']==[]
             and all(value[k] is None for k in ('last_bar_date','last_bar_timezone_offset_minutes','sma5','sma20','observed_at','ingested_at','known_at')))
        return True
    need(value['signal'] in {'bullish','bearish','neutral'} and value['reason'] is None
         and value['bar_count']==20 and isinstance(value['bar_dates'],list) and len(value['bar_dates'])==20
         and all(isinstance(d,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',d) for d in value['bar_dates'])
         and value['bar_dates']==sorted(set(value['bar_dates']))
         and value['last_bar_date']==value['bar_dates'][-1]
         and type(value['last_bar_timezone_offset_minutes']) is int
         and -720<=value['last_bar_timezone_offset_minutes']<=840
         and all(type(value[k]) in (int,float) and math.isfinite(value[k]) and value[k]>0 for k in ('sma5','sma20')))
    times={k:parse_aware(value[k]) for k in ('observed_at','ingested_at','known_at','cutoff')}
    need(times['observed_at']<=times['ingested_at']<=times['known_at']<=times['cutoff']
         and times['cutoff']==parse_aware(cutoff))
    need((value['signal']=='bullish' and value['sma5']>value['sma20'])
         or (value['signal']=='bearish' and value['sma5']<value['sma20'])
         or (value['signal']=='neutral' and value['sma5']==value['sma20']))
    return True


def forecast_basis_error(forecast, report_as_of):
    """Return a validation error when a rated SPY/QQQ forecast lacks frozen support."""
    if forecast.get('ticker') not in {'SPY','QQQ'} or forecast.get('direction')=='unknown':
        return None
    basis=forecast.get('forecast_basis')
    required={'reference_close_date','reference_close','reference_source','horizon_type',
              'bull_case','bear_case','invalidation'}
    if not isinstance(basis,dict) or set(basis)!=required:
        return 'rated SPY/QQQ forecast requires complete forecast_basis'
    try:
        reference_date=datetime.fromisoformat(basis['reference_close_date']).date()
        as_of=_timestamp(forecast.get('forecast_as_of'),'forecast_as_of')
        report_cutoff=_timestamp(report_as_of,'report as_of')
        price=basis['reference_close']
        if (reference_date>as_of.date() or reference_date>=datetime.fromisoformat(forecast['target_date']).date()
                or as_of>report_cutoff or type(price) not in (int,float) or not math.isfinite(price) or price<=0
                or basis['horizon_type'] not in {'next_session','week_end'}):
            return 'invalid forecast reference/horizon/time'
        source=basis['reference_source']
        parsed=urlparse(source)
        if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password:
            return 'forecast reference_source must be HTTPS'
        if any(not isinstance(basis[key],str) or not basis[key].strip() for key in ('bull_case','bear_case','invalidation')):
            return 'forecast basis needs bull_case, bear_case and invalidation'
    except (ValueError,TypeError,KeyError,OverflowError):
        return 'invalid forecast reference/horizon/time'
    return None


def validate_market_snapshot(snapshot, *, require_rights=True):
    """Validate both private analysis snapshots and public publication snapshots."""
    need(isinstance(snapshot,dict) and set(snapshot)==MARKET_SNAPSHOT_FIELDS
         and type(snapshot['schema_version']) is int and snapshot['schema_version']==1
         and snapshot['provider']=='moomoo-rest')
    cutoff=_timestamp(snapshot['cutoff'],'snapshot cutoff')
    report_date=cutoff.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    need(snapshot['report_date']==report_date)
    rights=snapshot['rights']
    if require_rights:
        need(isinstance(rights,dict) and set(rights)==RIGHTS_OUTPUT_FIELDS
             and rights.get('status')=='verified' and rights.get('provider')=='moomoo-rest'
             and rights.get('markets')==['US'] and set(RIGHTS_FIELDS)<=set(rights.get('fields',[]))
             and set(RIGHTS_USES)<=set(rights.get('uses',[])))
        need(RIGHTS_URL.fullmatch(rights.get('evidence_url','')) is not None)
        need(_timestamp(rights['verified_at'],'rights verified_at')
             <=_timestamp(rights['published_at'],'rights published_at')
             <_timestamp(rights['expires_at'],'rights expires_at'))
    else:
        need(isinstance(rights,dict) and rights=={'status':'unverified','provider':'moomoo-rest'})
    coverage=snapshot['coverage']
    need(isinstance(coverage,dict) and set(coverage)=={'expected_us','selected_us','unsupported_my','quote_attempt_statuses'}
         and coverage['expected_us']==30 and coverage['unsupported_my']==20
         and type(coverage['selected_us']) is int and 0<=coverage['selected_us']<=30
         and isinstance(coverage['quote_attempt_statuses'],dict))
    quotes=snapshot['quotes'];need(isinstance(quotes,list) and len(quotes)==50)
    symbols=set();selected=0
    for row in quotes:
        need(isinstance(row,dict) and set(row)==MARKET_QUOTE_FIELDS)
        need(row['market'] in {'US','MY'} and row['country']==row['market']
             and isinstance(row['ticker'],str) and row['ticker'] and isinstance(row['name'],str) and row['name'])
        symbol=(row['market'],row['ticker']);need(symbol not in symbols);symbols.add(symbol)
        need(row['status'] in MARKET_QUOTE_STATUSES and isinstance(row['gaps'],list))
        need(row['listing_currency']==('USD' if row['market']=='US' else 'MYR'))
        need(isinstance(row['metrics'],dict) and set(row['metrics'])==MARKET_METRIC_FIELDS)
        point=row['public_snapshot']
        if row['market']=='MY':
            need(row['status']=='unsupported' and point is None and row['metrics']['provider_volume'] is None)
        elif row['status']=='selected':
            selected+=1
            need(point is not None and row['metrics']['provider_volume'] is not None
                 and type(row['metrics']['provider_volume']) is int and row['metrics']['provider_volume']>=0)
            validate_public_snapshot(point,snapshot['cutoff'],listing_currency='USD')
        else:
            need(point is None and row['metrics']['provider_volume'] is None)
    need(selected==coverage['selected_us'] and sum(r['market']=='US' for r in quotes)==30
         and sum(r['market']=='MY' for r in quotes)==20)
    queries=snapshot['news_queries'];need(isinstance(queries,list) and len(queries)==2)
    seen_queries=set()
    for query in queries:
        need(isinstance(query,dict) and set(query)==MARKET_NEWS_QUERY_FIELDS
             and query['keyword'] in NEWS_KEYWORDS and query['keyword'] not in seen_queries)
        seen_queries.add(query['keyword'])
        need(query['status'] in {'success','empty','unavailable'} and isinstance(query['records'],list))
        if query['status'] in {'empty','unavailable'}:need(not query['records'])
        seen_news=set()
        for item in query['records']:
            need(isinstance(item,dict) and set(item)==MARKET_NEWS_FIELDS
                 and item['provider']=='moomoo-rest' and item['endpoint']=='/api/v1.0/quote/find-news')
            need(isinstance(item['title'],str) and item['title'] and len(item['title'])<=8192)
            need(_safe_https_url(item['url']))
            need(item['news_type'] in {'POST','NOTICE','REPORT'})
            times={key:_timestamp(item[key],key) for key in ('published_at','source_at','observed_at','ingested_at','known_at','cutoff')}
            need(times['published_at']==times['source_at']<=times['observed_at']<=times['ingested_at']<=times['known_at']<=times['cutoff']<=cutoff)
            identity=(item['title'],item['url'],item['published_at']);need(identity not in seen_news);seen_news.add(identity)
    need(seen_queries==set(NEWS_KEYWORDS))
    validate_public_report_boundary(snapshot)
    def has_markup(value):
        if isinstance(value,dict):return any(has_markup(v) for v in value.values())
        if isinstance(value,list):return any(has_markup(v) for v in value)
        return isinstance(value,str) and bool(re.search(r'<\s*/?\s*[a-z][^>]*>',value,re.I))
    need(not has_markup(snapshot),'html-rejected')
    return True


def project_report(store,template,universe,*,run_id,cutoff,expected_codes):
    """Pure mapping of an accepted template and explicit store selection."""
    def project():
        need(isinstance(template,dict) and template.get('schema_version')==3)
        check_secrets(template)
        validator=import_module('scripts.daily-market-brief.validate_report_json')
        keys,instruments=validator.validate_universe(Path('universe.json'),universe)
        need(universe['count_per_group']==5 and len(instruments)==50)
        config=template['watchlist_config']
        need(config['taxonomy_id']==universe['taxonomy_id'] and config['count_per_group']==5
             and [{k:g[k] for k in ('key','label','emoji')} for g in config['groups']]==
                 [{k:g[k] for k in ('key','label','emoji')} for g in universe['groups']])
        frozen=parse_aware(cutoff)
        need(parse_aware(template['metadata']['as_of'])==frozen
             and template['metadata']['date']==frozen.astimezone(timezone(timedelta(hours=8))).date().isoformat())
        expected=['US.'+ticker for (market,ticker) in instruments if market=='US']
        need(isinstance(expected_codes,list) and len(expected_codes)==len(set(expected_codes))
             and set(expected_codes)==set(expected))
        rows=template['forecasts']
        need(isinstance(rows,list) and len(rows)==50)
        symbols=[(r['market'],r['ticker']) for r in rows]
        need(len(set(symbols))==50 and set(symbols)==set(instruments))
        for row in rows:
            instrument=instruments[(row['market'],row['ticker'])]
            need(row['sector_category']==instrument['group'] and row['asset_type']==instrument['asset_type']
                 and row['country']==instrument['country'] and row['currency']==instrument['currency'])
            need(row.get('direction')=='unknown' and row.get('forecast_status')=='unavailable'
                 and row.get('confidence')=='unavailable'
                 and all(row.get(k) is None for k in ('estimated_mid_case_value','range_low_value','range_high_value')))
        selection=store.select_snapshots(run_id,cutoff,expected_codes)
        try:
            history_entries=store.query('history',cutoff,mode='strict',limit=5000,run_id=run_id)
            history_attempts=store.attempts(cutoff,limit=1000)
        except Exception:
            history_entries=[];history_attempts=[]
        output=deepcopy(template)
        output['metadata']['private_draft']=True
        output['metadata']['quote_cutoff']=cutoff
        for row in output['forecasts']:
            row.pop('quote_provenance',None)
            row.update(current_price='Unavailable',current_price_value=None,quote_status='missing',
                       price_as_of='No verified reference quote at report cutoff',observed_quote=None)
            point=selection['quotes'].get('US.'+row['ticker']) if row['market']=='US' else None
            reasons=['MY_unattempted_unsupported']
            if point:
                need(isinstance(point['gap_reasons'],list) and set(point['gap_reasons'])<=REASONS
                     and set(point['excluded_counts'])<=EXCLUSIONS)
                reasons=[*point['gap_reasons'],*point['excluded_counts']]
                if point['quote'] is None:
                    if selection['attempt_status_counts']['failed']:reasons.append('collection_failed_attempt')
                    if selection['attempt_status_counts']['all-missing']:reasons.append('all_missing_attempt')
            row['data_gaps']=list(dict.fromkeys([*row.get('data_gaps',[]),*reasons]))
            row['moomoo_trend']=project_moomoo_trend(store,run_id=run_id,cutoff=cutoff,
                code=('US.'+row['ticker'] if row['market']=='US' else 'MY.'+row['ticker']),
                history_entries=history_entries,history_attempts=history_attempts)
            if point and point['quote'] is not None:
                record=point['quote'];p=point['provenance']
                need(record['code']=='US.'+row['ticker'])
                quote=dict(price=record['price'],volume=record['volume'],source_at=epoch_time(p['source_ms']),
                    observed_at=p['observed_at'],ingested_at=p['ingested_at'],known_at=epoch_time(p['known_ms']),
                    cutoff=cutoff,origin=p['origin'],currency=None,session=None,adjustment=None,prior_close=None,
                    gaps=list(GAPS),provenance={k:p[k] for k in PROVENANCE_KEYS})
                validate_observed_quote(quote,cutoff)
                row['observed_quote']=quote
        return output
    return safe(project,category='projection-failed')


def write_private_draft(destination,report):
    """Atomic link publication inside an existing owned0700 private directory."""
    def write():
        path=Path(destination)
        need(path.is_absolute() and path==path.resolve() and not path.is_relative_to(REPO)
             and path.suffix=='.json'
             and not any(p.lower() in {'public','www','htdocs','artifacts','dist'} for p in path.parts))
        private(path.parent,directory=True)
        need(not path.exists() and not path.is_symlink())
        raw=(canonical(report)+'\n').encode()
        temporary=None
        try:
            fd,name=tempfile.mkstemp(prefix='.private-draft-',dir=path.parent);temporary=Path(name)
            with os.fdopen(fd,'wb') as stream:
                stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o400);os.fsync(stream.fileno())
            os.link(temporary,path,follow_symlinks=False)
            fd=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        finally:
            if temporary is not None:temporary.unlink()
    return safe(write,category='private-draft-failed')
