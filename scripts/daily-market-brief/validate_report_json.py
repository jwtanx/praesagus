#!/usr/bin/env python3
"""Validate structured, dated Praesagus daily market brief JSON before publishing."""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_SECTIONS = {'outlook','top10','calendar','swing','etfs','news','trends','score'}
SOURCE_URL_KEYS = {'url'}
UNIVERSE_ROLES = {'benchmark','sector','industry_overlay','sector_group'}

def fail(path: Path, message: str) -> None:
    raise ValueError(f'{path}: {message}')

def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        fail(path, f'invalid JSON ({exc})')

def valid_date(value, path, field='date'):
    if not isinstance(value, str): fail(path, f'{field} must be YYYY-MM-DD')
    try: date.fromisoformat(value)
    except ValueError: fail(path, f'invalid {field}: {value!r}')

def validate_sources(sources, path, location):
    if not isinstance(sources, list): fail(path, f'{location}.sources must be a list')
    for i, source in enumerate(sources):
        if not isinstance(source, dict) or not isinstance(source.get('label'), str) or not source['label'].strip():
            fail(path, f'{location}.sources[{i}] requires a label')
        url=source.get('url','')
        parsed=urlparse(url) if isinstance(url,str) else None
        if not parsed or parsed.scheme!='https' or not parsed.netloc:
            fail(path, f'{location}.sources[{i}].url must be HTTPS')

def validate_rich(item, path, location):
    if not isinstance(item,dict) or not isinstance(item.get('text'),str): fail(path,f'{location} requires text')
    validate_sources(item.get('sources',[]),path,location)

def validate_universe(path: Path, d):
    if not isinstance(d,dict) or d.get('schema_version')!=1: fail(path,'schema_version must be 1')
    if not isinstance(d.get('taxonomy_id'),str) or not d['taxonomy_id'].strip(): fail(path,'taxonomy_id is required')
    valid_date(d.get('effective_from'),path,'effective_from')
    if d.get('count_per_group')!=10: fail(path,'count_per_group must be 10')
    for key in ('selection_method','collection_policy'):
        if not isinstance(d.get(key),str) or not d[key].strip(): fail(path,f'{key} is required')
    validate_sources(d.get('sources'),path,'universe')
    groups=d.get('groups')
    if not isinstance(groups,list) or not groups: fail(path,'groups must be a nonempty list')
    keys=[]; universe={}
    for gi,g in enumerate(groups):
        loc=f'groups[{gi}]'
        if not isinstance(g,dict): fail(path,f'{loc} must be an object')
        for key in ('key','label','emoji','role','classification'):
            if not isinstance(g.get(key),str) or not g[key].strip(): fail(path,f'{loc}.{key} is required')
        if g['role'] not in UNIVERSE_ROLES: fail(path,f'{loc}.role is invalid')
        keys.append(g['key'])
        items=g.get('instruments')
        if not isinstance(items,list) or len(items)!=10 or g.get('count')!=10:
            fail(path,f'{loc} must define exactly 10 instruments')
        group_symbols=set()
        for ii,item in enumerate(items):
            iloc=f'{loc}.instruments[{ii}]'
            required=('ticker','name','country','market','currency','asset_type','sector_category','sector','sector_emoji','classification')
            if not isinstance(item,dict) or any(not isinstance(item.get(k),str) or not item[k].strip() for k in required):
                fail(path,f'{iloc} is missing required text fields')
            if item['sector_category']!=g['key'] or item['sector']!=g['label'] or item['sector_emoji']!=g['emoji']:
                fail(path,f'{iloc} group metadata does not match its parent')
            if item['country'] not in {'us','my'} or item['market']!=item['country'].upper():
                fail(path,f'{iloc} country/market must be us/US or my/MY')
            if item['currency']!=('USD' if item['country']=='us' else 'MYR'):
                fail(path,f'{iloc} currency does not match country')
            if item['asset_type'] not in {'equity','etf'}: fail(path,f'{iloc}.asset_type must be equity or etf')
            if (g['role']=='benchmark') != (item['asset_type']=='etf'):
                fail(path,f'{iloc} benchmark group membership must match ETF asset type')
            symbol=(item['market'],item['ticker'])
            if symbol in group_symbols or symbol in universe: fail(path,f'duplicate instrument: {symbol[0]}:{symbol[1]}')
            group_symbols.add(symbol); universe[symbol]={'group':g['key'],'asset_type':item['asset_type'],'country':item['country'],'currency':item['currency']}
    if len(keys)!=len(set(keys)): fail(path,'group keys must be unique')
    expected={'benchmarks','financials','technology','semiconductors','healthcare','consumer-staples','consumer-discretionary','energy','industrials-transport-logistics','materials-plantation'}
    if set(keys)!=expected: fail(path,f'groups must cover exactly {sorted(expected)}')
    return keys,universe

def validate_report(path: Path, d, universe_data=None):
    if not isinstance(d,dict) or d.get('schema_version')!=2: fail(path,'schema_version must be 2')
    # HTML markup belongs in the shared viewer, never in the report data.
    def has_html_key(x):
        if isinstance(x,dict): return any(k.lower() in {'html','html_fragment','markup'} or has_html_key(v) for k,v in x.items())
        if isinstance(x,list): return any(has_html_key(v) for v in x)
        if isinstance(x,str): return bool(re.search(r'<\s*/?\s*[a-z][^>]*>',x,re.I))
        return False
    if has_html_key(d): fail(path,'report JSON must contain structured data, not HTML fragments')
    meta=d.get('metadata')
    if not isinstance(meta,dict): fail(path,'metadata must be object')
    valid_date(meta.get('date'),path,'metadata.date')
    if path.stem!=meta['date']:fail(path,'filename must match metadata.date')
    for key in ('title','subtitle'):
        if not isinstance(meta.get(key),str) or not meta[key].strip():fail(path,f'metadata.{key} is required')
    try:
        as_of=datetime.fromisoformat(meta.get('as_of',''))
        if as_of.tzinfo is None: fail(path,'metadata.as_of needs a timezone')
    except (TypeError,ValueError):fail(path,'metadata.as_of must be ISO-8601 with timezone')
    summary=d.get('summary')
    if not isinstance(summary,list) or not summary:fail(path,'summary must be a nonempty list')
    for i,item in enumerate(summary):
        if not isinstance(item,dict) or any(not isinstance(item.get(k),str) or not item[k].strip() for k in ('label','title','summary')):fail(path,f'summary[{i}] requires label/title/summary')
    sections=d.get('sections')
    if not isinstance(sections,dict) or set(sections)!=REQUIRED_SECTIONS:fail(path,f'sections must contain exactly {sorted(REQUIRED_SECTIONS)}')
    for name,section in sections.items():
        if not isinstance(section,dict):fail(path,f'sections.{name} must be object')
        for key in ('title','kicker'):
            if not isinstance(section.get(key),str) or not section[key].strip():fail(path,f'sections.{name}.{key} required')
        for i,p in enumerate(section.get('description',[])):validate_rich(p,path,f'sections.{name}.description[{i}]')
        for ti,table in enumerate(section.get('tables',[])):
            if not isinstance(table,dict) or not isinstance(table.get('columns'),list) or not table['columns'] or not isinstance(table.get('rows'),list):fail(path,f'sections.{name}.tables[{ti}] requires columns/rows')
            for ri,row in enumerate(table['rows']):
                if not isinstance(row,list) or len(row)!=len(table['columns']):fail(path,f'sections.{name}.tables[{ti}].rows[{ri}] column count mismatch')
                for ci,value in enumerate(row):validate_rich(value,path,f'sections.{name}.tables[{ti}].rows[{ri}][{ci}]')
        for ii,item in enumerate(section.get('items',[])):
            if not isinstance(item,dict) or not isinstance(item.get('title'),str):fail(path,f'sections.{name}.items[{ii}] requires title')
            for pi,p in enumerate(item.get('paragraphs',[])):validate_rich(p,path,f'sections.{name}.items[{ii}].paragraphs[{pi}]')
        for ni,note in enumerate(section.get('notes',[])):validate_rich(note,path,f'sections.{name}.notes[{ni}]')
    config=d.get('watchlist_config')
    if not isinstance(config,dict) or config.get('count_per_group',config.get('count_per_sector'))!=10:fail(path,'watchlist_config count_per_group (or legacy count_per_sector) must be 10')
    groups=config.get('groups')
    if not isinstance(groups,list) or not groups:fail(path,'watchlist_config.groups must be nonempty')
    group_keys=[g.get('key') for g in groups if isinstance(g,dict)]
    if len(group_keys)!=len(groups) or len(group_keys)!=len(set(group_keys)) or 'semiconductors' not in group_keys:fail(path,'watchlist groups must have unique keys and include semiconductors')
    for i,g in enumerate(groups):
        if any(not isinstance(g.get(k),str) or not g[k].strip() for k in ('key','label','emoji')):fail(path,f'watchlist_config.groups[{i}] needs key, label and emoji')
    if universe_data and meta['date']>=universe_data[0]:
        universe_keys,universe=universe_data[1],universe_data[2]
        if config.get('taxonomy_id')!=universe_data[3]:fail(path,f'watchlist_config.taxonomy_id must be {universe_data[3]} for reports on/after {universe_data[0]}')
        if group_keys!=universe_keys:fail(path,'watchlist groups must match the current daily collection universe in priority order')
        expected_groups={g['key']:g for g in universe_data[4]}
        for g in groups:
            expected=expected_groups[g['key']]
            if g.get('label')!=expected['label'] or g.get('emoji')!=expected['emoji']:
                fail(path,f'watchlist group metadata does not match current universe: {g["key"]}')
    forecasts=d.get('forecasts')
    expected_total=10*len(group_keys)
    if not isinstance(forecasts,list) or len(forecasts)!=expected_total:fail(path,f'forecasts must contain {expected_total} entries (10 for each of {len(group_keys)} groups)')
    symbols=set();sector_counts={key:0 for key in group_keys}
    for i,f in enumerate(forecasts):
        if not isinstance(f,dict):fail(path,f'forecasts[{i}] must be object')
        required=('market','country','asset_type','ticker','name','sector','sector_category','sector_emoji','currency','current_price','price_as_of','direction','direction_label','estimated_mid_case','estimated_range','scenario')
        if any(not isinstance(f.get(k),str) or not f[k].strip() for k in required):fail(path,f'forecasts[{i}] missing required text fields')
        for numeric in ('current_price_value','estimated_mid_case_value','range_low_value','range_high_value'):
            if not isinstance(f.get(numeric),(int,float)) or isinstance(f[numeric],bool) or f[numeric]<=0:fail(path,f'forecasts[{i}].{numeric} must be positive numeric data')
        if f['range_low_value']>f['range_high_value']:fail(path,f'forecasts[{i}] range low exceeds range high')
        if f['currency'] not in {'USD','MYR'}:fail(path,f'forecasts[{i}].currency must be USD or MYR')
        if f['direction'] not in {'up','flat','down'}:fail(path,f'forecasts[{i}].direction must be up, flat, or down')
        if f['country'] not in {'us','my'}:fail(path,f'forecasts[{i}].country must be us or my')
        if f['sector_category'] not in sector_counts:fail(path,f'forecasts[{i}].sector_category is not in watchlist_config.groups')
        sector_counts[f['sector_category']]+=1
        if universe_data and meta['date']>=universe_data[0]:
            instrument=universe.get((f['market'].upper(),f['ticker']))
            if not instrument:fail(path,f'forecasts[{i}] instrument is not in the current collection universe')
            if instrument['group']!=f['sector_category'] or instrument['asset_type']!=f['asset_type'] or instrument['country']!=f['country'] or instrument['currency']!=f['currency']:
                fail(path,f'forecasts[{i}] classification does not match the current collection universe')
        if not isinstance(f.get('confidence'),str) or not f['confidence'].strip():fail(path,f'forecasts[{i}].confidence required')
        if f['ticker'] in symbols:fail(path,f'duplicate ticker: {f["ticker"]}')
        symbols.add(f['ticker']);validate_sources(f.get('sources',[]),path,f'forecasts[{i}]')
    for key,count in sector_counts.items():
        if count!=10:fail(path,f'watchlist group {key} has {count} tickers; expected 10')
    cal=d.get('calendar')
    if not isinstance(cal,dict) or cal.get('timezone')!='Asia/Kuala_Lumpur' or not re.fullmatch(r'\d{4}-\d{2}',str(cal.get('month',''))):fail(path,'calendar requires timezone Asia/Kuala_Lumpur and YYYY-MM month')
    if not isinstance(cal.get('events'),list) or not cal['events']:fail(path,'calendar.events must be nonempty')
    for i,event in enumerate(cal['events']):
        loc=f'calendar.events[{i}]'
        if not isinstance(event,dict):fail(path,f'{loc} must be object')
        valid_date(event.get('date'),path,f'{loc}.date')
        if event.get('date_end'):
            valid_date(event['date_end'],path,f'{loc}.date_end')
            if event['date_end'] < event['date']:fail(path,f'{loc}.date_end precedes date')
        if event.get('kind') not in {'event','market-closure'}:fail(path,f'{loc}.kind invalid')
        for key in ('title','time','summary','details'):
            if not isinstance(event.get(key),str) or not event[key].strip():fail(path,f'{loc}.{key} required')
        validate_sources(event.get('sources',[]),path,loc)
    if not isinstance(d.get('footer'),str) or not d['footer'].strip():fail(path,'footer is required')
    return len(forecasts),len(cal['events']),sector_counts

def validate_index(path:Path,d,json_files):
    if not isinstance(d,dict) or d.get('schema_version')!=1:fail(path,'schema_version must be 1')
    reports=d.get('reports')
    if not isinstance(reports,list) or not reports:fail(path,'reports must be nonempty')
    dates=[]
    for i,item in enumerate(reports):
        if not isinstance(item,dict):fail(path,f'reports[{i}] must be object')
        valid_date(item.get('date'),path,f'reports[{i}].date')
        if not isinstance(item.get('label'),str) or not item['label'].strip():fail(path,f'reports[{i}].label required')
        dates.append(item['date'])
        if item['date']+'.json' not in json_files:fail(path,f'missing JSON report for {item["date"]}')
    if len(dates)!=len(set(dates)):fail(path,'duplicate report dates')
    if d.get('latest') not in dates or d['latest']!=max(dates):fail(path,'latest must be the newest indexed report')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reports-dir',type=Path,default=Path('artifacts/daily-market-brief'))
    ap.add_argument('--universe',type=Path,default=Path('artifacts/daily-market-brief/watchlist-universe.json'))
    ap.add_argument('--date',help='validate one YYYY-MM-DD report')
    a=ap.parse_args();root=a.reports_dir
    universe_json=read_json(a.universe)
    universe_keys,universe_map=validate_universe(a.universe,universe_json)
    effective_from=universe_json['effective_from']
    universe_data=(effective_from,universe_keys,universe_map,universe_json['taxonomy_id'],universe_json['groups'])
    print(f'OK {a.universe}: {len(universe_keys)} groups, {len(universe_map)} instruments; effective {effective_from}')
    candidates=[root/f'{a.date}.json'] if a.date else sorted(root.glob('????-??-??.json'))
    if not candidates:raise ValueError(f'{root}: no dated JSON reports found')
    file_names={p.name for p in root.glob('????-??-??.json')};total=0
    for p in candidates:
        n,events,counts=validate_report(p,read_json(p),universe_data);total+=1
        breakdown=', '.join(f'{key}={count}' for key,count in counts.items())
        print(f'OK {p}: {n} forecasts ({breakdown}), {events} calendar events')
    idx=root/'reports.json'
    validate_index(idx,read_json(idx),file_names)
    print(f'OK {idx}: {len(read_json(idx)["reports"])} report dates indexed')
if __name__=='__main__':
    try:main()
    except ValueError as exc:print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
