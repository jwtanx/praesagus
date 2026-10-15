"""Causal current-universe eligibility and bounded deterministic quota allocation."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import math
import re
from statistics import median

from contracts import code, history_coverage, integer, text

STOCK_QUOTAS = {'winners':20,'losers':20,'volume':40}
ETF_QUOTAS = {'ordinary':12,'long2':2,'long3':2,'inverse1':2,'inverse2':1,'inverse3':1}
ETF_BUCKET = {1:'ordinary',2:'long2',3:'long3',-1:'inverse1',-2:'inverse2',-3:'inverse3'}


def known_ms(record):
    times=[]
    for key in ('known_at_ms','known_at','available_at','first_seen_at','retrieved_at','observed_at'):
        value=record.get(key)
        if value in (None,''):continue
        if key.endswith('_ms'):
            if not integer(value):return None
            times.append(value);continue
        if not isinstance(value,str):return None
        try:
            stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
            if stamp.tzinfo is None:return None
            times.append(int(stamp.timestamp()*1000))
        except ValueError:return None
    return max(times) if times else None


def effective_now(record,cutoff):
    """Date-only bounds use UTC days (end inclusive); explicit timestamp end is exclusive."""
    for key in ('effective_from','effective_to'):
        raw=record.get(key)
        if raw in (None,''):continue
        if not isinstance(raw,str):return False
        try:
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):
                boundary=datetime.combine(date.fromisoformat(raw),datetime.min.time(),timezone.utc)
                if key=='effective_to':boundary+=timedelta(days=1)
            else:
                boundary=datetime.fromisoformat(raw.replace('Z','+00:00'))
                if boundary.tzinfo is None:return False
        except ValueError:return False
        value=int(boundary.timestamp()*1000)
        if key=='effective_from' and cutoff<value or key=='effective_to' and cutoff>=value:return False
    return True


def etf_available(record,cutoff):
    if not isinstance(record,dict) or not effective_now(record,cutoff):return False
    try:
        day=date.fromisoformat(record.get('source_asof',''))
        if day>datetime.fromtimestamp(cutoff/1000,timezone.utc).date():return False
        observed=record.get('observed_at')
        if observed:
            stamp=datetime.fromisoformat(observed.replace('Z','+00:00'))
            if stamp.tzinfo is None or int(stamp.timestamp()*1000)>cutoff:return False
    except (ValueError,TypeError):return False
    return True


def reviewed(record,cutoff):
    if not isinstance(record,dict):return False
    stamp=known_ms(record)
    return (effective_now(record,cutoff) and record.get('status')=='verified' and stamp is not None and stamp<=cutoff
            and isinstance(record.get('source_url'),str) and record['source_url'].startswith('https://')
            and re.fullmatch('[0-9a-f]{64}',str(record.get('source_hash',record.get('raw_payload_hash','')))) is not None
            and bool(record.get('reviewer')))


def resolve_sector(evidence,crosswalk,cutoff):
    unknown=lambda status,reason:{'sector_id':None,'sector_mapping_status':status,'reason':reason}
    if not reviewed(evidence,cutoff):return unknown('unmapped','industry-evidence-unavailable')
    memberships=[row for row in evidence.get('industry_records',[]) if row.get('plate_type')=='INDUSTRY']
    if not memberships:return unknown('unmapped','no-industry-membership')
    mappings=[]
    for industry in memberships:
        matches=[row for row in crosswalk if row.get('market')==evidence.get('market')
                 and row.get('vendor_taxonomy_id')==evidence.get('taxonomy_id')
                 and row.get('vendor_taxonomy_snapshot_hash')==evidence.get('taxonomy_snapshot_hash')
                 and row.get('industry_code')==industry.get('plate_code')]
        if not matches:return unknown('unmapped','exact-crosswalk-missing')
        if any(not reviewed(row,cutoff) for row in matches):return unknown('stale','crosswalk-unreviewed-or-future')
        if len({(row.get('sector_id'),row.get('target_sector_taxonomy_id'),row.get('target_taxonomy_version')) for row in matches})!=1:
            return unknown('ambiguous','multiple-crosswalk-mappings')
        mapping=matches[0]
        if not all(text(mapping.get(key)) for key in ('sector_id','target_sector_taxonomy_id','target_taxonomy_version','mapping_version')):
            return unknown('unmapped','taxonomy-version-missing')
        profile=evidence.get('profile_industry_label')
        if profile is not None and profile!=industry.get('plate_name') and profile not in mapping.get('reviewed_exact_profile_aliases',[]):
            return unknown('conflicting','profile-plate-industry-conflict')
        mappings.append(mapping)
    sectors={row['sector_id'] for row in mappings}
    if len(sectors)!=1:return unknown('conflicting','industry-sector-conflict')
    return {'sector_id':next(iter(sectors)),'sector_mapping_status':'verified','mapping_versions':sorted({row['mapping_version'] for row in mappings}),
            'industry_evidence_ids':[evidence.get('source_hash',evidence.get('raw_payload_hash'))],
            'effective_from':None,'effective_to':None,'historical_applicability':'unknown'}


def build_candidate(identity,bars,*,required_sessions,cutoff_ms,metadata,etf=None):
    """Derived numbers require exact recent sessions and supplied reviewed field-level units."""
    security=code(identity['code']);reasons=[]
    listing=metadata.get('listing_records',{}).get(security,{})
    listed=(reviewed(listing,cutoff_ms) and listing.get('code')==security and identity.get('stock_id') is not None
        and type(listing.get('stock_id')) is type(identity['stock_id']) and listing.get('stock_id')==identity['stock_id'])
    if not listed or listing.get('suspended') is not False:reasons.append('listing-or-status-unverified')
    basis=metadata.get('comparison_evidence',{}).get(security,{})
    comparable=(reviewed(basis,cutoff_ms) and basis.get('price_units')=='USD' and basis.get('turnover_units')=='USD'
                and basis.get('volume_units')=='shares' and basis.get('adjustment')=='forward-excluding-dividends')
    if not comparable:reasons.append('comparable-price-volume-turnover-basis-unverified')
    coverage=history_coverage(bars,expected_sessions=required_sessions[-252:],cutoff_ms=cutoff_ms)
    if coverage['status']!='complete':reasons.append('history-252-incomplete')
    by_day={row['session_date']:row for row in bars}
    recent_days=required_sessions[-20:]
    recent=[by_day.get(day) for day in recent_days]
    valid_recent=(len(recent_days)==20 and all(row and row['completed'] and row['currency']=='USD'
        and row['known_at_ms']<=cutoff_ms and row['adjustment']=='forward-excluding-dividends' for row in recent))
    if not valid_recent:reasons.append('latest-20-required-sessions-missing')
    if comparable and valid_recent:
        turnover=median(row['turnover'] for row in recent)
        price=recent[-1]['close'];change=price/recent[-2]['close']-1
        ranges=[max(row['high']-row['low'],abs(row['high']-previous['close']),abs(row['low']-previous['close']))
                for previous,row in zip(recent,recent[1:])][-14:]
        atr=sum(ranges)/len(ranges)/price
    else:turnover=price=change=atr=None
    sector=resolve_sector(metadata.get('industry_evidence',{}).get(security),metadata.get('sector_crosswalk',[]),cutoff_ms)
    issuer=metadata.get('issuer_relations',{}).get(security,{})
    issuer_ok=(reviewed(issuer,cutoff_ms) and issuer.get('code')==security
               and identity.get('stock_id') is not None and type(issuer.get('stock_id')) is type(identity['stock_id']) and issuer.get('stock_id')==identity['stock_id'] and text(issuer.get('issuer_id_namespace'))
               and text(issuer.get('issuer_group_id')) and issuer.get('relation_type') in {'issuer-security-table','filing-share-class','exchange-issuer-relation'})
    if sector['sector_mapping_status']!='verified':reasons.append('sector-'+sector['sector_mapping_status'])
    if not issuer_ok:reasons.append('issuer-identity-unresolved')
    # Registry is classification only; a literal Trust substring does not override verified ETF identity.
    is_etf=bool(etf and etf.get('classification_status')=='issuer-identity-only' and listed and etf_available(etf,cutoff_ms) and identity.get('stock_type') in {'ETF','FUND','TRUST'})
    if etf and not etf_available(etf,cutoff_ms):reasons.append('etf-observation-future-expired-or-invalid')
    asset='ETF' if is_etf else 'STOCK' if identity.get('stock_type') in {'STOCK','EQUITY'} and not (etf and etf.get('classification_status')=='issuer-identity-only') else 'UNKNOWN'
    if asset=='UNKNOWN':reasons.append('product-identity-unresolved')
    output={'code':security,'stock_id':identity.get('stock_id'),'name':identity.get('name'),'asset_type':asset,
        'price':price,'median20_turnover':turnover,'latest_turnover':recent[-1]['turnover'] if comparable and valid_recent else None,
        'latest_volume':recent[-1]['volume'] if comparable and valid_recent else None,'latest_return':change,'atr_fraction':atr,
        'reference_session_date':required_sessions[-1] if valid_recent else None,'valid_sessions':coverage['sessions'],'latest20_complete':bool(valid_recent),'comparison_basis_verified':bool(comparable),
        'listing_verified':bool(listed and listing.get('suspended') is False),**sector,
        'issuer_group_id':issuer.get('issuer_group_id') if issuer_ok else None,'issuer_status':'verified' if issuer_ok else 'unresolved',
        'reasons':reasons,'coverage':coverage,'metadata_current_only':True,'metadata_effective_from':None,'metadata_effective_to':None}
    if is_etf:
        output.update({key:etf.get(key) for key in ('issuer','benchmark_name','exposure_family','reset','etf_verification_url','source_asof')})
        output['signed_leverage']=int(etf['signed_leverage'])
        output['classification_verified']=True
    return output


def allocate(candidates,buckets,group_key,group_cap,*,identity_key=None):
    """Min-cost maximum flow: fill feasible quotas before ranked cost; no greedy false shortfall."""
    if len(candidates)>5000:raise ValueError('allocation-candidate-budget')
    graph={};assigned=[]
    def edge(a,b,capacity,cost=0):
        graph.setdefault(a,[]);graph.setdefault(b,[])
        forward=[b,len(graph[b]),capacity,cost];reverse=[a,len(graph[a]),0,-cost]
        graph[a].append(forward);graph[b].append(reverse)
        return forward
    source=('source',);sink=('sink',)
    for bucket,quota in buckets.items():edge(source,('bucket',bucket),quota)
    for rank,row in enumerate(sorted(candidates,key=lambda row:row['code'])):
        identity=row['code'];group=row[group_key]
        node=('candidate',identity)
        edge(node,('identity',row[identity_key]) if identity_key else ('group',group),1)
        for bucket,cost in sorted(row['allocation_ranks'].items()):
            if bucket in buckets:
                wire=edge(('bucket',bucket),node,1,cost*10000+rank)
                assigned.append((identity,bucket,wire))
    if identity_key:
        groups={}
        for row in candidates:
            existing=groups.setdefault(row[identity_key],row[group_key])
            if existing!=row[group_key]:raise ValueError('issuer-sector-conflict')
        for identity,group in sorted(groups.items()):edge(('identity',identity),('group',group),1)
    for group in sorted({row[group_key] for row in candidates}):edge(('group',group),sink,group_cap)
    total=0;nodes=list(graph)
    while total<sum(buckets.values()):
        distance={source:0};parent={}
        for _ in range(len(nodes)-1):
            changed=False
            for node in nodes:
                if node not in distance:continue
                for i,wire in enumerate(graph[node]):
                    other,_,capacity,cost=wire
                    if capacity and (other not in distance or distance[node]+cost<distance[other]):
                        distance[other]=distance[node]+cost;parent[other]=(node,i);changed=True
            if not changed:break
        if sink not in parent:break
        node=sink;steps=0
        while node!=source:
            steps+=1
            if steps>len(nodes):raise ValueError('allocation-unresolved')
            previous,index=parent[node];wire=graph[previous][index]
            wire[2]-=1;graph[node][wire[1]][2]+=1;node=previous
        total+=1
    return {identity:bucket for identity,bucket,wire in assigned if wire[2]==0}


def select_universe(candidates,pools,*,discovery_status=None):
    for row in candidates:
        code(row.get('code'))
    codes=[row['code'] for row in candidates]
    if len(codes)!=len(set(codes)):raise ValueError('duplicate-candidate-code')
    by_code={row['code']:dict(row) for row in candidates};rejected={};stocks=[];etfs=[]
    finite=lambda value:type(value) in (int,float) and math.isfinite(value)
    # Rank from comparable completed-bar returns/turnover, not unresolved3102 units.
    rankings={
        'winners':sorted([row for row in candidates if row['code'] in pools.get('winners',[]) and finite(row.get('latest_return')) and row['latest_return']>0],key=lambda row:(-row['latest_return'],row['code'])),
        'losers':sorted([row for row in candidates if row['code'] in pools.get('losers',[]) and finite(row.get('latest_return')) and row['latest_return']<0],key=lambda row:(row['latest_return'],row['code'])),
        'volume':sorted([row for row in candidates if row['code'] in pools.get('volume',[]) and finite(row.get('latest_turnover'))],key=lambda row:(-row['latest_turnover'],row['code']))}
    pool_ranks={key:{row['code']:i+1 for i,row in enumerate(rows)} for key,rows in rankings.items()}
    for row in candidates:
        identity=row['code'];fail=[]
        for flag,reason in [('listing_verified','listing-or-status-unverified'),('comparison_basis_verified','comparison-basis-unverified'),('latest20_complete','latest20-incomplete')]:
            if row.get(flag) is not True:fail.append(reason)
        valid_number=lambda value:type(value) in (int,float) and math.isfinite(value)
        if not valid_number(row.get('price')) or row['price']<5:fail.append('price-below5-or-unavailable')
        if not valid_number(row.get('median20_turnover')) or row['median20_turnover']<25000000:fail.append('median20-turnover-below25M-or-unavailable')
        if row.get('valid_sessions',0)<252:fail.append('history252-incomplete')
        if row['asset_type']=='STOCK':
            if row.get('sector_mapping_status')!='verified' or not row.get('sector_id'):fail.append('sector-unverified')
            if row.get('issuer_status')!='verified' or not row.get('issuer_group_id'):fail.append('issuer-unresolved')
            ranks={bucket:values[identity] for bucket,values in pool_ranks.items() if identity in values}
            if not ranks:fail.append('not-in-ranked-discovery-pools')
            if not fail:stocks.append(dict(row,allocation_ranks=ranks))
        elif row['asset_type']=='ETF':
            lev=row.get('signed_leverage')
            if row.get('classification_verified') is not True or type(lev) is not int or lev not in ETF_BUCKET or not row.get('exposure_family'):
                fail.append('etf-classification-unverified')
            if row.get('reset')!=('not_applicable' if lev==1 else 'daily'):fail.append('etf-reset-unverified')
            if not any(identity in values for values in pools.values()):fail.append('not-independently-discovered')
            if not fail:etfs.append(dict(row,allocation_ranks={ETF_BUCKET[lev]:1}))
        else:fail.append('product-identity-unresolved')
        if fail:rejected[identity]=fail
    # A provider security cannot become two companies/products through conflicting input rows.
    security_rows={}
    for row in stocks+etfs:
        key=type(row.get('stock_id')).__name__+':'+str(row.get('stock_id'))
        row['allocation_security_id']=key
        security_rows.setdefault(key,[]).append(row)
    bad_security=set()
    for key,rows in security_rows.items():
        identities={(row['asset_type'],row.get('issuer_group_id') if row['asset_type']=='STOCK' else
                    (row.get('exposure_family'),row.get('signed_leverage'))) for row in rows}
        if len(identities)>1:bad_security.update(row['code'] for row in rows)
    for identity in bad_security:rejected[identity]=['provider-security-identity-conflict']
    stocks=[row for row in stocks if row['code'] not in bad_security]
    etfs=[row for row in etfs if row['code'] not in bad_security]
    # Issuer cap is inside the flow: alternative classes may fill otherwise impossible buckets.
    issuer_sectors={}
    for row in stocks:issuer_sectors.setdefault(row['issuer_group_id'],set()).add(row['sector_id'])
    conflicts={issuer for issuer,sectors in issuer_sectors.items() if len(sectors)>1}
    for row in stocks:
        if row['issuer_group_id'] in conflicts:rejected[row['code']]=['issuer-sector-conflict']
    stocks=[row for row in stocks if row['issuer_group_id'] not in conflicts]
    for rank,row in enumerate(sorted(etfs,key=lambda r:(-(r.get('latest_turnover') or 0),-r['median20_turnover'],r['code']))):
        row['allocation_ranks']={ETF_BUCKET[row['signed_leverage']]:rank+1}
    stock_choice=allocate(stocks,STOCK_QUOTAS,'sector_id',16,identity_key='issuer_group_id')
    selected_issuers={by_code[identity]['issuer_group_id'] for identity in stock_choice}
    for row in stocks:
        if row['code'] not in stock_choice and row['issuer_group_id'] in selected_issuers:
            rejected[row['code']]=['duplicate-verified-issuer-class']
    etf_choice=allocate(etfs,ETF_QUOTAS,'exposure_family',2,identity_key='allocation_security_id')
    choices=stock_choice|etf_choice
    main=[dict(by_code[identity],selection_bucket=bucket,selection_reasons=sorted(key for key,values in pools.items() if identity in values),
               discovery_ranks={key:values[identity] for key,values in pool_ranks.items() if identity in values}) for identity,bucket in sorted(choices.items())]
    main_issuers={row.get('issuer_group_id') for row in main if row.get('issuer_group_id')}
    speculative=[];seen_ids=set()
    for row in sorted(candidates,key=lambda r:(-(r.get('median20_turnover') or 0),r['code'])):
        if row['code'] in choices or row['code'] in bad_security or row['asset_type']!='STOCK' or not row.get('listing_verified') or not row.get('comparison_basis_verified') or not row.get('latest20_complete'):continue
        if not finite(row.get('price')) or row['price']<1 or not finite(row.get('median20_turnover')) or row['median20_turnover']<5000000:continue
        flags=[label for yes,label in [(row['price']<5,'low-price'),(row['valid_sessions']<252,'short-history'),
            ((row.get('atr_fraction') or 0)>.08,'high-volatility'),(abs(row.get('latest_return') or 0)>.15,'large-move')] if yes]
        if not flags:continue
        group=row.get('issuer_group_id') or ('security:'+str(row.get('stock_id')) if row.get('stock_id') is not None else row['code'])
        if group in main_issuers or group in seen_ids:continue
        seen_ids.add(group);speculative.append(dict(row,speculative_flags=flags))
        if len(speculative)==10:break
    counts=Counter(choices.values())
    incomplete=any(value!='success' for value in (discovery_status or {}).values())
    shortfalls={bucket:max(0,quota-counts[bucket]) for bucket,quota in (STOCK_QUOTAS|ETF_QUOTAS).items()}
    return {'main':main,'speculative':speculative,'coverage':{'counts':dict(counts),'shortfalls':shortfalls,'rejections':rejected,
        'shortfall_status':'filled' if not any(shortfalls.values()) else 'budget-or-discovery-incomplete' if incomplete else 'coverage-or-identity-blocked' if rejected else 'eligible-pool-exhausted' if any(shortfalls.values()) else 'filled',
        'discovery_status':discovery_status or {},'issuer_deduplication':'reviewed-relations-only','rotation':'not-forced'}}
