#!/usr/bin/env python3
"""Manual market discovery and immutable local collection. No orders or model work."""
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import argparse
import json
import os
import re
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

# Direct entrypoints work without installing or naming the hyphenated directory as a package.
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from config import CollectionConfig, load_collection_config
from contracts import RESTError, code, integer
from provider import build_live_provider, classify_discovered_etfs
from storage import (Generation, HISTORY_COLUMNS, MAX_HISTORY_ROWS, StorageError, canonical,
                     forecast_symbols, latest_state, merge_history, sha, output_parent, COMPONENT_REQUIRED)
from universe import build_candidate, reviewed, select_universe


def compatibility(settings):
    return sha(canonical({'state_schema':1,'history_schema':1,'calendar':settings.calendar,
                          'adjustment':settings.provider.autype,'universe_policy':1}))


def completed_sessions(cutoff_ms,years=3):
    import exchange_calendars as xc
    end=datetime.fromtimestamp(cutoff_ms/1000,timezone.utc).date()
    start=end.replace(year=end.year-years,day=min(end.day,28))
    calendar=xc.get_calendar('XNYS',start=(start-timedelta(days=400)).isoformat(),end=(end+timedelta(days=7)).isoformat())
    schedule=calendar.schedule.loc[start.isoformat():end.isoformat()]
    closes={stamp.date().isoformat():int(row['close'].value//1000000) for stamp,row in schedule.iterrows()
            if int(row['close'].value//1000000)<=cutoff_ms}
    return list(closes),closes


def load_metadata(path):
    if not path:return {'schema_version':1}
    file=Path(path).expanduser()
    if file.stat().st_size>16*1024*1024:raise ValueError('metadata-file-budget')
    value=json.loads(file.read_text())
    if not isinstance(value,dict) or value.get('schema_version')!=1:raise ValueError('metadata-schema')
    allowed={'schema_version','industry_evidence','sector_crosswalk','issuer_relations','currency_evidence','comparison_evidence','listing_records'}
    if not set(value)<=allowed:raise ValueError('unknown-metadata-section')
    for section,rows in value.items():
        if section=='schema_version':continue
        if section=='sector_crosswalk':
            if not isinstance(rows,list) or not all(isinstance(row,dict) for row in rows):raise ValueError('invalid-crosswalk')
        elif not isinstance(rows,dict) or not all(isinstance(row,dict) for row in rows.values()):raise ValueError('invalid-metadata-records')
        else:
            for key in rows:code(key)
    return value


def apply_field_currency(rows,record,cutoff,identity=None):
    # Listing currency alone is deliberately insufficient for REST OHLC/turnover fields.
    established=(isinstance(identity,dict) and record.get('code')==identity.get('code')
        and identity.get('stock_id') is not None and type(record.get('stock_id')) is type(identity['stock_id'])
        and record.get('stock_id')==identity['stock_id'] and reviewed(record,cutoff) and record.get('endpoint')=='history-kline' and record.get('currency')=='USD'
        and record.get('identity_binding_status')=='verified'
        and set(record.get('fields',[]))>={'open','high','low','close','turnover'}
        and isinstance(record.get('applicable_from_session'),str) and isinstance(record.get('applicable_to_session'),str))
    from universe import known_ms
    result=[]
    for source in rows:
        row=dict(source)
        row.setdefault('price_known_at_ms',row['known_at_ms'])
        applies=established and row.get('code')==identity['code'] and record['applicable_from_session']<=row['session_date']<=record['applicable_to_session']
        currency='USD' if applies else None
        evidence_hash=sha(canonical(record)) if applies else None
        changed=row.get('currency')!=currency or row.get('currency_evidence_hash')!=evidence_hash
        row.update(currency=currency,currency_source_url=record['source_url'] if applies else None,
                   currency_evidence_hash=evidence_hash,currency_known_at_ms=known_ms(record) if applies else None,
                   currency_status='reviewed-endpoint-fields' if applies else 'unverified')
        if changed:row['known_at_ms']=max(row['known_at_ms'],known_ms(record) if applies else cutoff,cutoff)
        result.append(row)

    return result


@dataclass
class CollectionResult:
    generation: Generation
    universe: dict
    state: dict
    history_rows: list
    receipt: dict
    manifest_metadata: dict


def run_collection(settings,*,provider=None,metadata=None,offline=False,generated_at=None,as_of_ms=None,
                   clock_ms=lambda:int(time.time()*1000),session_provider=completed_sessions):
    if not isinstance(settings,CollectionConfig):raise ValueError('invalid-collection-config')
    initial=as_of_ms if as_of_ms is not None else clock_ms()
    if not integer(initial,1):raise ValueError('invalid-cutoff')
    generation=Generation(settings.state_parent,generated_at=generated_at,compatibility_id=compatibility(settings),as_of_ms=initial)
    result=collect_into(settings,generation=generation,provider=provider,metadata=metadata,offline=offline,
        as_of_ms=as_of_ms,clock_ms=clock_ms,session_provider=session_provider,write_selection_csv=True)
    return generation.finish(**result.manifest_metadata)


def collect_into(settings,*,generation,provider=None,metadata=None,offline=False,generated_at=None,as_of_ms=None,
                 write_selection_csv=False,
                   clock_ms=lambda:int(time.time()*1000),session_provider=completed_sessions):
    if not isinstance(settings,CollectionConfig):raise ValueError('invalid-collection-config')
    if not isinstance(generation,Generation) or generation.closed:raise ValueError('open-generation-required')
    if type(write_selection_csv) is not bool:raise ValueError('selection-csv-flag')
    if generated_at is not None and generated_at.isoformat()!=generation.manifest['generated_at']:raise ValueError('generation-time-mismatch')
    initial=as_of_ms if as_of_ms is not None else generation.manifest.get('as_of_ms')
    if not integer(initial,1):raise ValueError('invalid-cutoff')
    policy=compatibility(settings)
    if generation.parent!=output_parent(settings.state_parent) or generation.manifest.get('compatibility_id')!=policy or generation.manifest.get('as_of_ms')!=initial:
        raise ValueError('generation-parent-policy-cutoff-mismatch')
    if generation.manifest.get('kind') not in {'stock-research-run','stock-research-collection'}:raise ValueError('collection-generation-kind')
    names=COMPONENT_REQUIRED['collection']|({'universe.csv','speculative.csv'} if write_selection_csv else set())
    if any(name in generation.manifest['artifacts'] or (generation.path/name).exists() or (generation.path/name).is_symlink() for name in names):raise ValueError('collection-artifact-occupied')
    previous=latest_state(settings.state_parent,policy)
    old=previous['state'] if previous else {}
    histories=previous['histories'] if previous else {}
    state={'schema_version':1,'pools':{},'identities':{},'quotes':{},'raw_metadata':{},'history_status':{},
           'discovery_records':{},'membership_first_seen_ms':{},'identity_current_status':{},'identity_quarantine':{},'basis_versions':{},'metadata_current_only':True,'historical_membership':'not-backfilled'}|old
    retained=forecast_symbols(settings.state_parent)
    if metadata is None:
        metadata=(previous.get('metadata_input') if offline and previous and not settings.metadata_file else None)
        if metadata is None:metadata=load_metadata(settings.metadata_file)
    revisions=[]
    for security,cached in list(histories.items()):
        enriched=apply_field_currency(cached,metadata.get('currency_evidence',{}).get(security,{}),initial,state['identities'].get(security))
        histories[security],changes=merge_history(cached,enriched)
        revisions.extend(changes)
    sessions,closes=session_provider(initial,settings.history_years)
    if len(sessions)<252:raise ValueError('calendar-history-too-short')
    issues=[];statuses={};fatal=False
    def invoke(method,*args,**kwargs):
        nonlocal fatal
        if fatal:return None
        try:return getattr(provider,method)(*args,**kwargs)
        except RESTError as error:
            # First upstream/budget failure ends network work; keep already collected observations.
            fatal=True;issues.append({'stage':method,'category':error.kind});return None
    if offline:
        statuses={key:'offline-cached' for key in state.get('pools',{})}
        if not previous:issues.append({'stage':'offline','category':'compatible-state-missing'})
    else:
        if provider is None:raise ValueError('explicit-provider-required')
        if provider.config!=settings.provider:raise ValueError('provider-config-mismatch')
        cumulative=lambda name:{'cumulative_property':{'name':name,'days':1,'period_average':False}}
        retrieve=[{'simple_property':{'name':2201}},cumulative(3104),cumulative(3105),cumulative(3102)]
        state['pools']={};state['discovery_records']={};state['screen_dispositions']={};state['snapshot_dispositions']={}
        for pool,factor,direction in [('winners',3102,2),('losers',3102,1),('volume',3105,2)]:
            result=invoke('screen',retrieve_queries=retrieve,sort={'direction':direction,**cumulative(factor)},page_limit=settings.discovery_pages)
            if result is None:statuses[pool]='request-failed';state['pools'][pool]=[];continue
            statuses[pool]=result.status
            state['screen_dispositions'][pool]=result.metadata
            state['pools'][pool]=[row['code'] for row in result.rows]
            for row in result.rows:
                stored={key:value for key,value in row.items() if key!='fields'}
                stored['fields']=[asdict(value) for value in row['fields']]
                state['discovery_records'][row['code']]=stored
                state['membership_first_seen_ms'].setdefault(row['code'],row.get('known_at_ms') or result.retrieved_at_ms or initial)
        discovered=set().union(*(set(rows) for rows in state['pools'].values())) if state['pools'] else set()
        ranks={security:min(i for rows in state['pools'].values() for i,item in enumerate(rows) if item==security) for security in discovered}
        current=sorted(discovered,key=lambda security:(ranks[security],security))[:settings.max_candidates]
        if len(current)<len(discovered):issues.append({'stage':'discovery','category':'candidate-budget-truncated'})
        # Old forecast names are retained for actuals only; they never seed discovery/selection.
        tracked=sorted(retained)+[security for security in current if security not in retained]
        for start in range(0,len(tracked),400):
            chunk=tracked[start:start+400]
            for method,key in [('basicinfo','identities'),('snapshots','quotes')]:
                result=invoke(method,chunk)
                if result is None:
                    if key=='identities':state['identity_current_status'].update({security:'request-failed' for security in chunk})
                    continue
                fresh={row['code']:row for row in result.rows}
                if key=='quotes':
                    state['snapshot_dispositions'][sha(canonical(chunk))]=result.metadata
                    rejected=result.metadata.get('rejected_rows',[])
                    for security in set(result.missing_codes)|{row['code'] for row in rejected}:
                        state['quotes'].pop(security,None)
                    if rejected:
                        issues.append({'stage':'snapshots','category':'snapshot-rows-rejected',
                                       'rejected_row_count':len(rejected)})
                if key=='identities':
                    for security,identity in fresh.items():
                        prior=state[key].get(security)
                        if prior and (type(prior.get('stock_id')) is not type(identity.get('stock_id')) or prior.get('stock_id')!=identity.get('stock_id')):
                            transition={'old_stock_id':prior.get('stock_id'),'new_stock_id':identity.get('stock_id'),
                                'known_at_ms':identity.get('known_at_ms') or result.retrieved_at_ms or initial,
                                'status':'history-binding-unverified'}
                            state['identity_quarantine'][security]=transition
                            histories[security]=[];state['basis_versions'].pop(security,None)
                            issues.append({'stage':'identity','code':security,'category':'security-id-changed-history-quarantined'})
                state[key].update(fresh)
                if key=='identities':state['identity_current_status'].update({security:'fresh' if security in fresh else 'missing' for security in chunk})
                if result.missing_codes:issues.append({'stage':method,'category':'requested-codes-missing','codes':list(result.missing_codes)})
        if settings.metadata_enabled:
            taxonomy=invoke('industry_catalog')
            if taxonomy is not None:state['taxonomy']={'rows':list(taxonomy.rows),'metadata':taxonomy.metadata}
        # Prefer missing/old histories so bounded repeated runs advance without forced ticker rotation.
        tracked.sort(key=lambda security:(security not in retained,len(histories.get(security,[])),security))
        for security in tracked:
            if fatal:break
            cached=histories.get(security,[])
            basis=metadata.get('comparison_evidence',{}).get(security,{})
            token=basis.get('adjustment_vintage_id') if reviewed(basis,initial) else None
            if token is not None and token!=state['basis_versions'].get(security):
                if cached:issues.append({'stage':'history','code':security,'category':'adjustment-vintage-requires-full-backfill'})
                cached=[];histories[security]=[];state['basis_versions'][security]=token
            start=sessions[0];end=sessions[-1]
            if cached:
                cached_dates={row['session_date'] for row in cached}
                missing=[day for day in sessions if day not in cached_dates]
                recent_start=sessions[max(0,len(sessions)-settings.revision_sessions)]
                start=missing[0] if missing else recent_start
                end=missing[-1] if missing else sessions[-1]
            result=invoke('history',security,start=start,end=end,session_closes=closes)
            if result is not None:
                incoming=apply_field_currency(result.rows,metadata.get('currency_evidence',{}).get(security,{}),as_of_ms or clock_ms(),state['identities'].get(security))
                merged,changed=merge_history(cached,incoming)
                total_rows=sum(len(rows) for key,rows in histories.items() if key!=security)+len(merged)
                if total_rows>MAX_HISTORY_ROWS:
                    fatal=True;issues.append({'stage':'history','category':'cached-history-row-budget'});break
                histories[security]=merged;revisions.extend(changed)
                state['history_status'][security]={'status':result.status,'reason':result.reason,'metadata':result.metadata}
                if result.metadata.get('stopped_on_failure'):
                    fatal=True;issues.append({'stage':'history','category':result.reason})
            if settings.metadata_enabled and not fatal:
                for kind in ['owner-plate','company/profile']:
                    result=invoke('source_metadata',security,kind)
                    if result is not None:state['raw_metadata'].setdefault(security,{})[kind]={'rows':list(result.rows),'metadata':result.metadata}
    cutoff=as_of_ms if as_of_ms is not None else clock_ms()
    if not integer(cutoff,initial):raise ValueError('collection-clock-order')
    # Re-evaluate completion at the decision cutoff, without asserting provider finality/offset units.
    sessions,closes=session_provider(cutoff,settings.history_years)
    for rows in histories.values():
        for row in rows:
            close=closes.get(row['session_date'])
            row['completed']=bool(close is not None and row['retrieved_at_ms']>=close)
            row['completion_status']='completed' if row['completed'] else 'calendar-unverified-or-incomplete'
    discovered=set().union(*(set(rows) for rows in state['pools'].values())) if state['pools'] else set()
    classified=classify_discovered_etfs(sorted(discovered))
    candidates=[]
    for security in sorted(discovered):
        identity=state['identities'].get(security)
        if identity is None:
            issues.append({'stage':'identity','category':'identity-unavailable','code':security});continue
        candidate=build_candidate(identity,histories.get(security,[]),required_sessions=sessions,cutoff_ms=cutoff,
                                  metadata=metadata,etf=classified.get(security))
        if not offline and state['identity_current_status'].get(security)!='fresh':
            candidate['listing_verified']=False;candidate['reasons'].append('current-identity-coverage-missing')
        transition=state['identity_quarantine'].get(security)
        if transition:
            listing=metadata.get('listing_records',{}).get(security,{})
            from universe import known_ms
            rebound=(reviewed(listing,cutoff) and listing.get('stock_id')==identity.get('stock_id')
                     and listing.get('history_identity_status')=='verified' and (known_ms(listing) or 0)>=transition['known_at_ms'])
            if not rebound:
                candidate['listing_verified']=False;candidate['reasons'].append('history-security-binding-quarantined')
            else:state['identity_quarantine'].pop(security)
        candidate['membership_first_seen_ms']=state['membership_first_seen_ms'].get(security)
        quote=state['quotes'].get(security,{})
        if identity.get('suspension') is True or quote.get('suspension') is True:
            candidate['listing_verified']=False;candidate['reasons'].append('source-suspension')
        candidates.append(candidate)
    selected=select_universe(candidates,state['pools'],discovery_status=statuses)
    selected['coverage']['collection_issues']=issues
    selected['coverage']['screen_dispositions']=state.get('screen_dispositions',{})
    selected['coverage']['snapshot_dispositions']=state.get('snapshot_dispositions',{})
    rows=[row for security in sorted(histories) for row in histories[security]]
    if len(rows)>MAX_HISTORY_ROWS:raise ValueError('cached-history-row-budget')
    generation.csv('history.csv',rows,HISTORY_COLUMNS)
    generation.csv('history_revisions.csv',revisions,('code','session_date','change_type','old_hash','new_hash','known_at_ms','revision_vintage'))
    generation.json('state.json',state)
    generation.json('metadata_input.json',metadata)
    bindings=[{'code':security,'stock_id':identity.get('stock_id'),'source':identity.get('source'),
        'source_payload_hash':identity.get('revision_vintage'),'source_at_ms':identity.get('source_at_ms'),
        'retrieved_at_ms':identity.get('retrieved_at_ms'),'known_at_ms':identity.get('known_at_ms'),
        'effective_from':None,'effective_to':None,'scope':'current-observed-binding/not-historical-alias'}
        for security,identity in sorted(state['identities'].items())]
    generation.json('identity_bindings.json',bindings)
    from importlib.metadata import version
    schedule=[{'session_date':day,'close_at_ms':closes[day]} for day in sessions]
    calendar_metadata={'name':settings.calendar,'dependency':'exchange_calendars',
        'dependency_version':version('exchange_calendars') if session_provider is completed_sessions else None,
        'source':'exchange_calendars' if session_provider is completed_sessions else 'injected-session-provider',
        'schedule_sha256':sha(canonical(schedule))}
    generation.json('calendar.json',{'schema_version':1,**calendar_metadata,'sessions':schedule})

    generation.json('universe.json',selected)
    generation.json('coverage.json',selected['coverage'])
    # Stable machine-readable current shortlist; numeric CSVs are not workbook forecasts.
    columns=('code','stock_id','name','asset_type','sector_id','issuer_group_id','signed_leverage','exposure_family','price','reference_session_date','median20_turnover','latest_turnover','latest_volume','latest_return','valid_sessions','selection_bucket','selection_reasons')
    if write_selection_csv:
        generation.csv('universe.csv',selected['main'],columns)
        generation.csv('speculative.csv',selected['speculative'],columns+('speculative_flags',))
    finish_metadata=dict(as_of_ms=cutoff,status='partial' if issues or any(selected['coverage']['shortfalls'].values()) else 'complete',
        offline=offline,history_interpretation='retrospective-backfill/current-vintages-not-historical-membership',
        retained_forecast_symbols=sorted(retained),identity_quarantined_symbols=sorted(state['identity_quarantine']),current_discovered_symbols=sorted(discovered),
        selected_symbols=[row['code'] for row in selected['main']],source_capabilities=provider.capabilities() if provider else {'live':'not-called'},
        financial_metadata='current-only/not-training-features',metadata_evidence_hash=sha(canonical(metadata)),calendar=calendar_metadata,
        adjustment_policy={'autype':settings.provider.autype,'vintage_consistency':'response-vintages-kept; reviewed adjustment_vintage_id change forces fresh backfill',
            'factor_evidence':'not-supplied-by-provider; unknown unless separately reviewed','price_volume_adjustment':'not-assumed-equivalent',
            'historical_point_in_time':'not-established'})
    receipt={'identity_bindings':bindings,'calendar':{'schema_version':1,**calendar_metadata,'sessions':schedule},
        'metadata_input':metadata,'adjustment_policy':finish_metadata['adjustment_policy'],'as_of_ms':cutoff,
        'historical_membership':finish_metadata['history_interpretation'],
        'open_generation_artifacts':dict(generation.manifest['artifacts'])}
    return CollectionResult(generation,selected,state,rows,receipt,finish_metadata)


def load_secure_locator(reference):
    if not reference:raise ValueError('configure PRSG_MOOMOO_CREDENTIAL_LOCATOR or credential_locator_file before online collection')
    import stat
    path=Path(reference).expanduser()
    if not path.is_absolute() or path.resolve().is_relative_to(ROOT):raise ValueError('locator-reference-must-be-private-outside-repository')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>4096:
            raise ValueError('invalid-private-locator-reference')
        value=json.loads(stream.read(4097))
    if not isinstance(value,dict) or set(value)!={'directory','app_key_name'} or not isinstance(value['directory'],str) or not Path(value['directory']).is_absolute():
        raise ValueError('invalid-locator-reference')
    if not isinstance(value['app_key_name'],str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',value['app_key_name']) is None:
        raise ValueError('invalid-locator-reference')
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--state-dir');parser.add_argument('--metadata-file')
    args=parser.parse_args()
    settings=load_collection_config(args.config)
    from dataclasses import replace
    if args.state_dir:settings=replace(settings,state_parent=args.state_dir)
    if args.metadata_file:settings=replace(settings,metadata_file=args.metadata_file)
    provider=None
    if not args.offline:
        # Manual invocation is explicit read-only use; implementation tests never execute this branch.
        locator=load_secure_locator(settings.credential_locator_file or os.environ.get('PRSG_MOOMOO_CREDENTIAL_LOCATOR',''))
        provider=build_live_provider(locator,allow_live=True,config=settings.provider,
            clock_ms=lambda:int(time.time()*1000),nonce_factory=lambda:os.urandom(16).hex())
    result=run_collection(settings,provider=provider,offline=args.offline)
    print(json.dumps({'generation':str(result),'kind':'stock-research-collection'}))
    return 0


if __name__=='__main__':
    failure=None
    try:code_result=main()
    except FileExistsError:failure=('generation-exists','Choose a new generation time; existing generations are never overwritten.')
    except StorageError as error:
        failure=('storage-validation-failed','Use an output parent outside the repository; an in-repository data parent must be fully Git-ignored and outside code paths.')
    except (RESTError,ValueError,OSError):
        failure=('collection-failed','Check local configuration and coverage. Online use requires an explicit private credential_locator_file or PRSG_MOOMOO_CREDENTIAL_LOCATOR reference.')
    if failure:
        print(json.dumps({'status':failure[0],'setup':failure[1]}));raise SystemExit(2)
    raise SystemExit(code_result)
