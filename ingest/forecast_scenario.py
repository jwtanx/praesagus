"""Pure reviewed-evidence scenarios; no intake, training, approval or publication.

Legacy schema1/raw and schema2/cash remain SPY/USD. Generic schema3 uses the
same EVIDENCE keys plus narrative (exact NARRATIVE keys), GENERIC_METHOD or
GENERIC_CASH_METHOD, unchanged instrument/source/calendar/bar/action/rights
keysets, and schema3 ADMISSION. All seven reviewed gates remain mandatory.
Generic results preserve the outer result/FIELDS keys. Their private audit uses
GENERIC_AUDIT; public time basis uses GENERIC_TIME_BASIS schema2, binding the
instrument and declared display rounding. Prices are continuous research
estimates displayed to 2 decimals HALF_UP, not exchange-tick projections.
apply_scenario_to_row(..., identity={ticker,market,currency}) requires exact
ROW_IDENTITY for generic results and non-SPY withholding; no identity argument
retains legacy SPY semantics. Authored fixtures cannot map to public rows.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import math
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

METHOD = dict(method_id='spy_raw_close_drift_lognormal_h1_v1', version='1', observations=20,
              horizon_sessions=1, ddof=1, z=1.959964, direction_rule='sign_mu_exact_zero',
              point_semantics='model_median', range_semantics='uncalibrated_model_range', rounding='USD_2dp_HALF_UP')
CASH_METHOD = dict(METHOD, method_id='spy_cash_return_drift_lognormal_h1_v1')
DISPLAY_ROUNDING = 'currency_2dp_HALF_UP_display_only'
GENERIC_METHOD = dict(METHOD, method_id='instrument_raw_close_drift_lognormal_h1_v1', rounding=DISPLAY_ROUNDING)
GENERIC_CASH_METHOD = dict(GENERIC_METHOD, method_id='instrument_cash_return_drift_lognormal_h1_v1')
NARRATIVE = {'bull_case','bear_case','invalidation'}
ROW_IDENTITY = {'ticker','market','currency'}
CASH_EVENT = {'event_id','effective_date','kind','amount','currency','unit','source_url','source_sha256',
              'source_publication_at','retrieved_at','ingested_at','known_at'}
EVIDENCE = {'schema_version','classification','instrument','source','calendar','bars','corporate_actions','rights','method'}
INSTRUMENT = {'instrument_id','ticker','market','mic','currency','unit','effective_from','effective_to','mapping_version','source_url'}
SOURCE = {'provider','source_field','estimand','basis','scale_id','vintage','convention_id','convention','source_url'}
CALENDAR = {'version','mic','timezone','coverage_start','coverage_end','complete','source_url','known_at','sessions'}
BAR = {'instrument_id','session_date','close_at','close','currency','unit','basis','scale_id','vintage','source_url',
       'source_sha256','source_publication_at','retrieved_at','ingested_at','known_at','settled_at'}
ACTIONS = {'instrument_id','source_url','source_sha256','known_at','coverage_start','coverage_end','complete','events'}
RIGHTS = {'history_collection','private_retention_research','public_derived_forecast','evidence_reference','source_sha256','known_at'}
ADMISSION = {'schema_version','classification','evidence_sha256','method_sha256','reviewed_at','reviewers','decisions'}
GATES = ('identity_units','calendar_window','bar_provenance','close_convention','basis_actions','rights','method')
FIELDS = {'direction','direction_label','forecast_status','estimated_mid_case','estimated_range','estimated_mid_case_value',
          'range_low_value','range_high_value','forecast_as_of','target_date','forecast_model','forecast_observations',
          'forecast_horizon_sessions','confidence','confidence_reason','scenario','forecast_basis','forecast_time_basis'}
BASIS = {'reference_close_date','reference_close','reference_source','horizon_type','bull_case','bear_case','invalidation'}
AUDIT = {'classification','evidence_sha256','admission_sha256','method_sha256','issued_at','report_cutoff',
         'reference_session','reference_close_at','target_session','target_close_at','reference_close','observations',
         'horizon_sessions','mu','sample_sd','point','low','high','baseline_point','baseline_low','baseline_high','venue_timezone','calendar_version'}
REASONS = dict(schema='Forecast evidence is missing or malformed.', admission_missing='Reviewed admission is missing.',
 admission_binding='Reviewed evidence bindings do not match.', admission_time='Evidence review is outside the issuance boundary.',
 identity_units='Instrument identity or price units are unsupported.', calendar_window='Consecutive completed sessions are unavailable.',
 bar_provenance='Close evidence is missing, stale or known after issuance.', close_convention='Regular close settlement is unverified.',
 basis_actions='Raw-close corporate-action coverage is incomplete or contains an event.', rights='Required data-use permissions are missing.',
 method='The reviewed scenario method does not match.', arithmetic='Scenario arithmetic is not finite and ordered.',
 rounding_unrepresentable='Scenario values cannot be displayed safely.')
CONFIDENCE = 'Research only: unvalidated drift method and uncalibrated range; low confidence is not a probability.'
SCENARIO = 'Research-only raw-close model median and uncalibrated model range. No predictive-performance or executable-price claim.'
MODEL = 'Raw-close drift/lognormal median scenario v1 (uncalibrated)'
BULL = 'Positive raw-close drift may persist under unchanged price basis.'
BEAR = 'Recent drift may reverse; historical volatility does not capture all event risk.'
INVALIDATION = 'Withhold if close evidence, action coverage or input basis becomes invalid.'
CASH_MODEL = 'Cash-return drift/lognormal median scenario v1 (uncalibrated)'
CASH_SCENARIO = 'Research-only cash-return model median and uncalibrated range; historical cash uses an authored end-session reinvestment proxy, not vendor adjusted-series equivalence. Declared-event review retains source-index/revision risk; unexpected events remain possible. No predictive-performance or executable-price claim.'
CASH_BULL = 'Positive cash-inclusive historical drift may persist under unchanged target price basis.'
GENERIC_MODEL = 'Instrument raw-close drift/lognormal median scenario v1 (uncalibrated)'
GENERIC_CASH_MODEL = 'Instrument cash-return drift/lognormal median scenario v1 (uncalibrated)'
DISPLAY_NOTICE = ' Continuous research estimates displayed to 2 decimals HALF_UP; not executable quotes or exchange-tick-valid prices.'
GENERIC_SCENARIO = SCENARIO + DISPLAY_NOTICE
GENERIC_CASH_SCENARIO = 'Research-only cash-return median and uncalibrated range; historical cash uses an end-session reinvestment proxy, not vendor adjusted-series equivalence. Source revisions and unexpected events remain risks. Continuous estimates display 2 decimals HALF_UP; not executable quotes or exchange-tick-valid prices. No predictive-performance claim.'
MODELS = {MODEL: METHOD, CASH_MODEL: CASH_METHOD, GENERIC_MODEL: GENERIC_METHOD, GENERIC_CASH_MODEL: GENERIC_CASH_METHOD}
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', re.ASCII)
TIME_BASIS = {'schema_version','method_id','venue_timezone','calendar_version','reference_close_at','target_close_at'}
GENERIC_TIME_BASIS = TIME_BASIS | {'instrument_id','ticker','market','mic','currency','mapping_version','display_rounding'}
GENERIC_AUDIT = AUDIT | {'instrument','narrative','method_id','display_rounding'}


def _row_identity(value):
    return (_obj(value, ROW_IDENTITY) and _id(value['ticker'])
            and (value['market'],value['currency']) in (('US','USD'),('MY','MYR')))


def _generic_method(e):
    return GENERIC_CASH_METHOD if e['method'].get('method_id') == GENERIC_CASH_METHOD['method_id'] else GENERIC_METHOD

SHA = re.compile(r'[0-9a-f]{64}', re.ASCII)
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', re.ASCII)


class ScenarioValidationError(ValueError):
    """Fixed error only, never input/exception text."""
    def __init__(self):
        super().__init__('scenario-invalid-input')


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def _obj(value, keys):
    return type(value) is dict and set(value)==keys


def _text(value):
    return type(value) is str and 0<len(value)<=2048 and value.strip()==value and not any(ord(c)<32 for c in value)


def _id(value):
    return type(value) is str and ID.fullmatch(value) is not None


def _sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _url(value):
    if not _text(value) or any(c.isspace() for c in value):return False
    try:
        p=urlparse(value)
        return p.scheme=='https' and bool(p.hostname) and not (p.username or p.password or p.query or p.fragment) and p.port in (None,443)
    except ValueError:return False


def _time(value):
    if type(value) is not str or not STAMP.fullmatch(value):raise ValueError()
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)


def _day(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value,re.ASCII):raise ValueError()
    return date.fromisoformat(value)


def _positive(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value) and value>0
    except OverflowError:return False


def _bounded(value, *, max_depth=8):
    if type(max_depth) is not int or max_depth not in (8,12):return False
    stack=[(value,0)];count=0
    while stack:
        value,depth=stack.pop();count+=1
        if depth>max_depth or count>100000:return False
        kind=type(value)
        if kind not in (dict,list,str,int,float,bool,type(None)):return False
        if kind is str and (len(value)>2048 or any(ord(c)<32 for c in value)):return False
        if kind in (dict,list):
            size=len(value)*(2 if kind is dict else 1)
            if size+count+len(stack)>100000:return False
            if kind is dict:
                for k,v in value.items():
                    if type(k) is not str:return False
                    stack.extend(((k,depth+1),(v,depth+1)))
            else:stack.extend((v,depth+1) for v in value)
    return True


def _schema(e,a):
    if type(e) is not dict or not _obj(e,EVIDENCE | {'narrative'} if e.get('schema_version')==3 else EVIDENCE) or not _obj(a,ADMISSION):return False
    if e.get('schema_version')==3 and (not _obj(e['narrative'],NARRATIVE) or not all(_text(v) for v in e['narrative'].values())):return False
    for key,keys in (('instrument',INSTRUMENT),('source',SOURCE),('calendar',CALENDAR),('corporate_actions',ACTIONS),('rights',RIGHTS),('method',set(METHOD))):
        if not _obj(e[key],keys):return False
    if type(e['bars']) is not list or len(e['bars'])!=21 or any(not _obj(b,BAR) for b in e['bars']):return False
    c=e['calendar'];x=e['corporate_actions']
    if type(c['sessions']) is not list or not 1<=len(c['sessions'])<=366 or any(not _obj(s,{'session_date','regular_close_at'}) for s in c['sessions']):return False
    event_keys=CASH_EVENT if e.get('schema_version')==2 or e.get('schema_version')==3 and _generic_method(e)==GENERIC_CASH_METHOD else {'effective_date','kind','source_url','source_sha256'}
    if type(x['events']) is not list or any(not _obj(v,event_keys) for v in x['events']):return False
    if type(c['complete']) is not bool or type(x['complete']) is not bool:return False
    if not _obj(a['decisions'],set(GATES)) or any(not _obj(d,{'decision','evidence_reference','contract_sha256'}) for d in a['decisions'].values()):return False
    if type(a['reviewers']) is not list:return False
    return (type(e['schema_version']) is int and e['schema_version'] in (1,2,3)
            and type(a['schema_version']) is int and a['schema_version']==e['schema_version'])


def _unavailable(reasons):
    fields=dict.fromkeys(FIELDS)
    fields.update(direction='unknown',direction_label='Unrated',forecast_status='unavailable',
                  estimated_mid_case='Unavailable',estimated_range='Unavailable',forecast_model='Unavailable',
                  confidence='unavailable',confidence_reason='Research only: required input gates failed; see missing-input reasons.',scenario='Research only; no supported price scenario.')
    return dict(status='withheld',reasons=reasons,report_fields=fields,private_audit=None)


def _cents(value):
    return Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)


def build_forecast_scenario(evidence, *, admission, issued_at, report_cutoff):
    """Verify reviewed workflow bindings and seven gates, then calculate a scenario.

    Review/authenticity/rights are external responsibilities; caller declarations
    and digests do not independently authenticate the provider or reviewers.
    """
    if admission is None:return _unavailable(['admission_missing'])
    if not all(_bounded(v) for v in (evidence,admission,issued_at,report_cutoff)) or not _schema(evidence,admission):
        return _unavailable(['schema'])
    e,a=evidence,admission; reasons=set()
    generic=e['schema_version']==3
    cash=e['schema_version']==2 or generic and _generic_method(e)==GENERIC_CASH_METHOD
    method=_generic_method(e) if generic else CASH_METHOD if cash else METHOD
    model=CASH_MODEL if cash else MODEL
    scenario=CASH_SCENARIO if cash else SCENARIO
    bull=CASH_BULL if cash else BULL
    bear,invalidation=BEAR,INVALIDATION
    if generic:
        model=GENERIC_CASH_MODEL if cash else GENERIC_MODEL
        scenario=GENERIC_CASH_SCENARIO if cash else GENERIC_SCENARIO
        bull,bear,invalidation=(e['narrative'][k] for k in ('bull_case','bear_case','invalidation'))
    cash_by_day={}
    def check(gate,fn):
        try:
            if not fn():reasons.add(gate)
        except (ValueError,TypeError,KeyError,OverflowError,ZoneInfoNotFoundError):reasons.add(gate)
    try:issue,cutoff,review=_time(issued_at),_time(report_cutoff),_time(a['reviewed_at'])
    except (ValueError,TypeError):return _unavailable(['admission_time'])
    i,s,c,bars,x,r,m=e['instrument'],e['source'],e['calendar'],e['bars'],e['corporate_actions'],e['rights'],e['method']
    subsets=dict(identity_units={'instrument':i,'source':s},calendar_window=c,bar_provenance=bars,
                 close_convention=s,basis_actions={'source':s,'corporate_actions':x},rights=r,method=m)
    def bindings():
        if e['classification'] not in ('reviewed_real','authored_fixture') or a['classification']!=e['classification']:return False
        if a['reviewers']!=['Lead','Trader']:return False
        if not _sha(a['evidence_sha256']) or not _sha(a['method_sha256']):return False
        if a['evidence_sha256']!=_hash(e) or a['method_sha256']!=_hash(m):return False
        return all(d['decision']=='accepted' and _text(d['evidence_reference']) and _sha(d['contract_sha256'])
                   and d['contract_sha256']==_hash(subsets[key]) for key,d in a['decisions'].items())
    check('admission_binding',bindings)
    check('admission_time',lambda: max([_time(c['known_at']),_time(x['known_at']),_time(r['known_at'])]+
                                     [_time(b['known_at']) for b in bars]+
                                     ([_time(v['known_at']) for v in x['events']] if cash else []))<=review<=issue<=cutoff)
    check('identity_units',lambda: (_row_identity({k:i[k] for k in ROW_IDENTITY}) if generic else i['ticker']=='SPY' and i['market']=='US' and i['currency']=='USD') and i['unit']=='traded_price'
          and _id(i['instrument_id']) and _id(i['mapping_version']) and type(i['mic']) is str
          and bool(re.fullmatch(r'[A-Z0-9]{4}',i['mic'],re.ASCII)) and _url(i['source_url']))
    sessions=[];reference=target=None
    def calendar():
        nonlocal sessions,reference,target
        zone=ZoneInfo(c['timezone']);start,end=_day(c['coverage_start']),_day(c['coverage_end'])
        if not (_id(c['version']) and c['mic']==i['mic'] and c['complete'] is True and _url(c['source_url']) and _time(c['known_at'])<=issue):return False
        sessions=sorted([(_day(v['session_date']),_time(v['regular_close_at'])) for v in c['sessions']])
        if len({v[0] for v in sessions})!=len(sessions) or len({v[1] for v in sessions})!=len(sessions):return False
        if any(not start<=day<=end or close.astimezone(zone).date()!=day for day,close in sessions):return False
        if any(sessions[n][1]>=sessions[n+1][1] for n in range(len(sessions)-1)):return False
        completed=[v for v in sessions if v[1]<=issue]
        if len(completed)<21 or len(completed)==len(sessions):return False
        reference=completed[-1];target=sessions[len(completed)]
        if not _day(i['effective_from'])<=completed[-21][0] or not target[0]<_day(i['effective_to']):return False
        return issue<target[1]
    check('calendar_window',calendar)
    if reference is not None and target is not None and 'calendar_window' not in reasons:
        window=sessions[sessions.index(reference)-20:sessions.index(reference)+1]
        def provenance():
            if [_day(b['session_date']) for b in bars]!=[v[0] for v in window]:return False
            for bar,(_,close) in zip(bars,window):
                if not (_positive(bar['close']) and bar['instrument_id']==i['instrument_id'] and bar['currency']==i['currency']
                        and bar['unit']=='traded_price' and bar['basis']=='unadjusted' and bar['scale_id']==s['scale_id']
                        and bar['vintage']==s['vintage'] and _url(bar['source_url']) and _sha(bar['source_sha256'])
                        and _time(bar['close_at'])==close):return False
                retrieved,ingested,known=(_time(bar[k]) for k in ('retrieved_at','ingested_at','known_at'))
                if not close<=retrieved<=ingested<=known<=issue:return False
                if bar['source_publication_at'] is not None and not close<=_time(bar['source_publication_at'])<=retrieved:return False
            return True
        check('bar_provenance',provenance)
        check('close_convention',lambda: s['source_field']=='close' and s['estimand'] in ('vendor_regular_close','exchange_regular_close')
              and s['convention'] in ('provider_finalized','operational_revision_cutoff') and _url(s['source_url'])
              and all(_id(s[k]) for k in ('provider','scale_id','vintage','convention_id'))
              and all(_time(b['close_at'])<=_time(b['settled_at'])<=_time(b['retrieved_at'])<=issue for b in bars))
        def actions():
            if not (s['basis']=='unadjusted' and x['instrument_id']==i['instrument_id'] and x['complete'] is True
                    and _url(x['source_url']) and _sha(x['source_sha256']) and _time(x['known_at'])<=issue
                    and _day(x['coverage_start'])<=window[0][0]<=target[0]<=_day(x['coverage_end'])):return False
            event_ids=set();amounts={};session_days={day for day,_ in sessions}
            for event in x['events']:
                if not _url(event['source_url']) or not _sha(event['source_sha256']):return False
                day=_day(event['effective_date'])
                if not _day(x['coverage_start'])<=day<=_day(x['coverage_end']):return False
                if not cash:
                    if event['kind'] not in ('split','distribution','other_basis_change') or window[0][0]<=day<=target[0]:return False
                    continue
                if (not _id(event['event_id']) or event['event_id'] in event_ids or event['kind']!='cash_distribution'
                        or not _positive(event['amount']) or event['currency']!=i['currency'] or event['unit']!='gross_cash_per_share'
                        or day not in session_days or day==target[0]):return False
                event_ids.add(event['event_id'])
                retrieved,ingested,known=(_time(event[k]) for k in ('retrieved_at','ingested_at','known_at'))
                if not retrieved<=ingested<=known<=_time(x['known_at'])<=review<=issue:return False
                if event['source_publication_at'] is not None and not _time(event['source_publication_at'])<=retrieved:return False
                amounts.setdefault(day,[]).append(float(event['amount']))
            if cash:
                for day,values in amounts.items():
                    amount=math.fsum(sorted(values))
                    if not _positive(amount):return False
                    cash_by_day[day]=amount
            return True
        check('basis_actions',actions)
    check('rights',lambda: all(r[k]=='permitted' for k in ('history_collection','private_retention_research','public_derived_forecast'))
          and _text(r['evidence_reference']) and _sha(r['source_sha256']) and _time(r['known_at'])<=issue)
    check('method',lambda: m==method and all(type(m[k]) is type(v) for k,v in method.items()))
    if reasons:return _unavailable(sorted(reasons))
    try:
        prices=[float(b['close']) for b in bars]
        returns=[math.log(prices[n]+cash_by_day.get(_day(bars[n]['session_date']),0))-math.log(prices[n-1])
                 for n in range(1,21)] if cash else [math.log(prices[n])-math.log(prices[n-1]) for n in range(1,21)]
        mu=math.fsum(returns)/20;sd=math.sqrt(math.fsum((v-mu)**2 for v in returns)/19)
        ref=prices[-1];point=ref*math.exp(mu);low=ref*math.exp(mu-METHOD['z']*sd);high=ref*math.exp(mu+METHOD['z']*sd)
        baseline_low=ref*math.exp(-METHOD['z']*sd);baseline_high=ref*math.exp(METHOD['z']*sd)
        if not all(_positive(v) for v in (ref,point,low,high,baseline_low,baseline_high)) or not low<=point<=high or not all(math.isfinite(v) for v in (mu,sd)):
            return _unavailable(['arithmetic'])
    except (ValueError,OverflowError):return _unavailable(['arithmetic'])
    try:
        lo,mid,hi=(_cents(v) for v in (low,point,high))
        if not 0<lo<=mid<=hi or not all(_positive(float(v)) for v in (lo,mid,hi)):return _unavailable(['rounding_unrepresentable'])
    except (InvalidOperation,ValueError,OverflowError):return _unavailable(['rounding_unrepresentable'])
    direction='up' if mu>0 else 'down' if mu<0 else 'flat'
    basis=dict(reference_close_date=reference[0].isoformat(),reference_close=ref,reference_source=bars[-1]['source_url'],
               horizon_type='next_session',bull_case=bull,bear_case=bear,invalidation=invalidation)
    fields=dict(direction=direction,direction_label={'up':'Bullish','down':'Bearish','flat':'Sideways'}[direction],
                forecast_status='available',estimated_mid_case=f"{i['currency']} {mid:.2f}",estimated_range=f"{i['currency']} {lo:.2f}–{i['currency']} {hi:.2f}",
                estimated_mid_case_value=float(mid),range_low_value=float(lo),range_high_value=float(hi),
                forecast_as_of=issued_at,target_date=target[0].isoformat(),forecast_model=model,forecast_observations=20,
                forecast_horizon_sessions=1,confidence='low',confidence_reason=CONFIDENCE,scenario=scenario,forecast_basis=basis,
                forecast_time_basis=dict(schema_version=1,method_id=method['method_id'],venue_timezone=c['timezone'],
                    calendar_version=c['version'],reference_close_at=reference[1].isoformat(),target_close_at=target[1].isoformat()))
    audit=dict(classification='fixture_only' if e['classification']=='authored_fixture' else 'reviewed_real',
               evidence_sha256=a['evidence_sha256'],admission_sha256=_hash(a),method_sha256=a['method_sha256'],
               issued_at=issued_at,report_cutoff=report_cutoff,reference_session=reference[0].isoformat(),
               reference_close_at=reference[1].isoformat(),target_session=target[0].isoformat(),target_close_at=target[1].isoformat(),
               reference_close=ref,observations=20,horizon_sessions=1,mu=mu,sample_sd=sd,point=point,low=low,high=high,
               baseline_point=ref,baseline_low=baseline_low,baseline_high=baseline_high,venue_timezone=c['timezone'],calendar_version=c['version'])
    if cash:audit['method_id']=method['method_id']
    if generic:
        audit.update(instrument=deepcopy(i),narrative=deepcopy(e['narrative']),method_id=method['method_id'],display_rounding=DISPLAY_ROUNDING)
        fields['forecast_time_basis'].update(schema_version=2,display_rounding=DISPLAY_ROUNDING,
            **{k:i[k] for k in ('instrument_id','ticker','market','mic','currency','mapping_version')})
    return dict(status='generated',reasons=[],report_fields=fields,private_audit=audit)


def _valid_result(result):
    if not _obj(result,{'status','reasons','report_fields','private_audit'}) or not _bounded(result):return False
    f=result['report_fields'];reasons=result['reasons'];audit=result['private_audit']
    if not _obj(f,FIELDS) or type(reasons) is not list or any(type(r) is not str or r not in REASONS for r in reasons):return False
    if reasons!=sorted(set(reasons)):return False
    if result['status']=='withheld':return bool(reasons) and audit is None and f==_unavailable(reasons)['report_fields']
    generic=f.get('forecast_model') in (GENERIC_MODEL,GENERIC_CASH_MODEL)
    cash=f.get('forecast_model') in (CASH_MODEL,GENERIC_CASH_MODEL)
    model=(GENERIC_CASH_MODEL if cash else GENERIC_MODEL) if generic else CASH_MODEL if cash else MODEL
    method=MODELS.get(model)
    if result['status']!='generated' or reasons or not _obj(audit,GENERIC_AUDIT if generic else AUDIT|{'method_id'} if cash else AUDIT):return False
    if (cash or generic) and audit['method_id']!=method['method_id']:return False
    try:
        i=audit['instrument'] if generic else {'ticker':'SPY','market':'US','currency':'USD'}
        if generic and (not _obj(i,INSTRUMENT) or not _row_identity({k:i[k] for k in ROW_IDENTITY})
                or not _obj(audit['narrative'],NARRATIVE) or not all(_text(v) for v in audit['narrative'].values())
                or audit['display_rounding']!=DISPLAY_ROUNDING or i['unit']!='traded_price'
                or not _url(i['source_url']) or not _day(i['effective_from'])<=_day(audit['reference_session'])
                or not _day(audit['target_session'])<_day(i['effective_to'])):return False
        if audit['classification']!='reviewed_real' or f['direction'] not in ('up','down','flat'):return False
        if any(type(audit[k]) is not int or audit[k]!=v for k,v in (('observations',20),('horizon_sessions',1))):return False
        if not all(_positive(f[k]) for k in ('estimated_mid_case_value','range_low_value','range_high_value')):return False
        if not all(_sha(audit[k]) for k in ('evidence_sha256','admission_sha256','method_sha256')):return False
        if not (_obj(f['forecast_basis'],BASIS) and _url(f['forecast_basis']['reference_source'])):return False
        if not validate_forecast_time_basis(dict(f,**{k:i[k] for k in ROW_IDENTITY}),audit['report_cutoff']):return False
        time_basis=f['forecast_time_basis']
        if time_basis['method_id']!=method['method_id']:return False
        if generic and any(time_basis[k]!=i[k] for k in ('instrument_id','ticker','market','mic','currency','mapping_version')):return False
        if time_basis['venue_timezone']!=audit['venue_timezone'] or time_basis['calendar_version']!=audit['calendar_version']:return False
        if any(_time(time_basis[k])!=_time(audit[k]) for k in ('reference_close_at','target_close_at')):return False
        if not all(_positive(audit[k]) for k in ('reference_close','point','low','high','baseline_point','baseline_low','baseline_high')):return False
        if not all(type(audit[k]) is float and math.isfinite(audit[k]) for k in ('mu','sample_sd')) or audit['sample_sd']<0:return False
        if not audit['low']<=audit['point']<=audit['high'] or not audit['baseline_low']<=audit['baseline_point']<=audit['baseline_high']:return False
        if audit['baseline_point']!=audit['reference_close']:return False
        ref,mu,sd=audit['reference_close'],audit['mu'],audit['sample_sd']
        calculated=dict(point=ref*math.exp(mu),low=ref*math.exp(mu-METHOD['z']*sd),high=ref*math.exp(mu+METHOD['z']*sd),
                        baseline_low=ref*math.exp(-METHOD['z']*sd),baseline_high=ref*math.exp(METHOD['z']*sd))
        if any(audit[k]!=value for k,value in calculated.items()):return False
        if not (_time(audit['reference_close_at'])<=_time(audit['issued_at'])<=_time(audit['report_cutoff'])
                and _time(audit['issued_at'])<_time(audit['target_close_at'])
                and _day(audit['reference_session'])<_day(audit['target_session'])):return False
        lo,mid,hi=(_cents(audit[k]) for k in ('low','point','high'))
        expected=deepcopy(f)
        expected.update(direction='up' if audit['mu']>0 else 'down' if audit['mu']<0 else 'flat',
                        forecast_status='available',confidence='low',confidence_reason=CONFIDENCE,scenario=(GENERIC_CASH_SCENARIO if cash else GENERIC_SCENARIO) if generic else CASH_SCENARIO if cash else SCENARIO,
                        forecast_model=model,forecast_observations=20,forecast_horizon_sessions=1,
                        forecast_as_of=audit['issued_at'],target_date=audit['target_session'],
                        estimated_mid_case=f"{i['currency']} {mid:.2f}",estimated_range=f"{i['currency']} {lo:.2f}–{i['currency']} {hi:.2f}",
                        estimated_mid_case_value=float(mid),range_low_value=float(lo),range_high_value=float(hi))
        expected['direction_label']={'up':'Bullish','down':'Bearish','flat':'Sideways'}[expected['direction']]
        if f!=expected or type(f['forecast_observations']) is not int or type(f['forecast_horizon_sessions']) is not int:return False
        if not 0<lo<=mid<=hi:return False
        b=f['forecast_basis']
        return (b['reference_close_date']==audit['reference_session'] and b['reference_close']==audit['reference_close']
                and _positive(b['reference_close']) and b['horizon_type']=='next_session'
                and (b['bull_case'],b['bear_case'],b['invalidation'])== (tuple(audit['narrative'][k] for k in ('bull_case','bear_case','invalidation')) if generic else (CASH_BULL if cash else BULL,BEAR,INVALIDATION)))
    except (ValueError,TypeError,KeyError,OverflowError,InvalidOperation):return False



def validate_forecast_time_basis(row, report_cutoff):
    """Check internal method/session-time linkage; never source authenticity.

    Null/absent contracts retain legacy behavior on other methods. Nonnull
    contracts are reserved for registered exact models, including Unrated rows.
    """
    if type(row) is not dict:return False
    basis=row.get('forecast_time_basis')
    method=MODELS.get(row.get('forecast_model')) if type(row.get('forecast_model')) is str else None
    if method is None:return basis is None
    generic=method in (GENERIC_METHOD,GENERIC_CASH_METHOD)
    if not _obj(basis,GENERIC_TIME_BASIS if generic else TIME_BASIS):return False
    if generic:
        if not _row_identity({k:row.get(k) for k in ROW_IDENTITY}) or any(row.get(k)!=basis[k] for k in ROW_IDENTITY):return False
        if any(not _id(basis[k]) for k in ('instrument_id','mapping_version')) or type(basis['mic']) is not str or not re.fullmatch(r'[A-Z0-9]{4}',basis['mic'],re.ASCII):return False
        if basis['display_rounding']!=DISPLAY_ROUNDING:return False
    elif any(row.get(k)!=v for k,v in (('ticker','SPY'),('market','US'),('currency','USD'))):return False
    try:
        if type(basis['schema_version']) is not int or basis['schema_version']!=(2 if generic else 1):return False
        if basis['method_id']!=method['method_id'] or type(basis['method_id']) is not str:return False
        if not _id(basis['calendar_version']) or not _text(basis['venue_timezone']) or len(basis['venue_timezone'])>128:return False
        zone=ZoneInfo(basis['venue_timezone'])
        if any(type(row.get(k)) is not int or row[k]!=v for k,v in (('forecast_observations',20),('forecast_horizon_sessions',1))):return False
        frozen=row.get('forecast_basis')
        if not _obj(frozen,BASIS) or frozen['horizon_type']!='next_session':return False
        issue=_time(row['forecast_as_of'])
        cutoff=report_cutoff if type(report_cutoff) is datetime else _time(report_cutoff)
        if cutoff.utcoffset() is None:return False
        reference=_time(basis['reference_close_at']);target=_time(basis['target_close_at'])
        reference_day=_day(frozen['reference_close_date']);target_day=_day(row['target_date'])
        return (reference<=issue<=cutoff and issue<target and reference_day<target_day
                and reference.astimezone(zone).date()==reference_day and target.astimezone(zone).date()==target_day)
    except (ValueError,TypeError,KeyError,OverflowError,ZoneInfoNotFoundError):return False


def apply_scenario_to_row(row, result, *, identity=None):
    """Copy an exactly bound row; retain quotes/sources/gaps, no writer/publication.

    Refuses authored_fixture generated results. Reviewed-real-shaped test records
    still prove plumbing only, not provider/authentic review or issuance approval.
    """
    generic=result.get('report_fields',{}).get('forecast_model') in (GENERIC_MODEL,GENERIC_CASH_MODEL) if type(result) is dict and type(result.get('report_fields')) is dict else False
    target=identity if identity is not None else {'ticker':'SPY','market':'US','currency':'USD'}
    valid=(_row_identity(target) and (not generic or identity is not None)
           and type(row) is dict and all(row.get(k)==target[k] for k in ROW_IDENTITY)
           and type(row.get('data_gaps')) is list
           and all(_text(gap) for gap in row['data_gaps']) and _bounded(row))
    if not valid or not _valid_result(result):raise ScenarioValidationError()
    if result['status']=='generated':
        bound=result['private_audit']['instrument'] if generic else {'ticker':'SPY','market':'US','currency':'USD'}
        if any(target[k]!=bound[k] for k in ROW_IDENTITY):raise ScenarioValidationError()
        if generic and any(k in row and row[k]!=bound[k] for k in ('instrument_id','mic','mapping_version')):raise ScenarioValidationError()
    mapped=deepcopy(row);mapped.update(deepcopy(result['report_fields']))
    if result['status']=='withheld':
        for reason in result['reasons']:
            message=REASONS[reason]
            if message not in mapped['data_gaps']:mapped['data_gaps'].append(message)
    return mapped
