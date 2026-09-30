#!/usr/bin/env python3
"""Validate dated daily-market-brief JSON and its reports.json index."""
from __future__ import annotations
import argparse, json, re, sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_SECTIONS = {'outlook','top10','calendar','swing','etfs','news','trends','score'}
URL_RE = re.compile(r'''href=["']([^"']+)["']''', re.I)

def fail(path: Path, message: str) -> None:
    raise ValueError(f'{path}: {message}')

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        fail(path, f'invalid JSON ({e})')

def valid_date(value, path):
    if not isinstance(value, str): fail(path, 'date must be YYYY-MM-DD string')
    try: date.fromisoformat(value)
    except ValueError: fail(path, f'invalid date: {value!r}')

def validate_report(path: Path, data):
    if not isinstance(data, dict): fail(path, 'root must be object')
    if data.get('schema_version') != 1: fail(path, 'schema_version must be 1')
    meta=data.get('metadata')
    if not isinstance(meta,dict): fail(path,'metadata must be object')
    valid_date(meta.get('date'),path)
    if path.stem != meta['date']: fail(path,'filename must match metadata.date')
    if not isinstance(meta.get('title'),str) or not meta['title'].strip(): fail(path,'metadata.title is required')
    try:
        as_of=datetime.fromisoformat(meta.get('as_of',''))
        if as_of.tzinfo is None: fail(path,'metadata.as_of must include timezone')
    except (TypeError,ValueError): fail(path,'metadata.as_of must be ISO-8601 with timezone')
    summary=data.get('summary')
    if not isinstance(summary,list) or not summary: fail(path,'summary must be a nonempty list')
    for i,item in enumerate(summary):
        if not isinstance(item,dict) or any(not isinstance(item.get(k),str) or not item[k].strip() for k in ('label','title','summary')): fail(path,f'summary[{i}] requires label/title/summary')
    sections=data.get('sections')
    if not isinstance(sections,dict) or set(sections)!=REQUIRED_SECTIONS: fail(path,f'sections must contain exactly {sorted(REQUIRED_SECTIONS)}')
    for name,section in sections.items():
        if not isinstance(section,dict) or not isinstance(section.get('html'),str) or not section['html'].strip(): fail(path,f'sections.{name}.html is required')
        for url in URL_RE.findall(section['html']):
            if url.startswith('#'): continue
            parsed=urlparse(url)
            if parsed.scheme!='https' or not parsed.netloc: fail(path,f'unsafe or invalid source link in {name}: {url}')
    rows=re.findall(r'<tr\b[^>]*class=["\'][^"\']*forecast-row',sections['top10']['html'],re.I)
    if len(rows)<1: fail(path,'top10 section must include forecast rows')
    if not isinstance(data.get('footer'),str) or not data['footer'].strip(): fail(path,'footer is required')
    return len(rows)

def validate_index(path: Path, data, json_files):
    if not isinstance(data,dict) or data.get('schema_version')!=1: fail(path,'schema_version must be 1')
    reports=data.get('reports')
    if not isinstance(reports,list) or not reports: fail(path,'reports must be a nonempty list')
    seen=[]
    for i,r in enumerate(reports):
        if not isinstance(r,dict): fail(path,f'reports[{i}] must be object')
        valid_date(r.get('date'),path)
        if not isinstance(r.get('label'),str) or not r['label'].strip(): fail(path,f'reports[{i}].label required')
        seen.append(r['date'])
        if r['date']+'.json' not in json_files: fail(path,f'missing JSON file for {r["date"]}')
    if len(seen)!=len(set(seen)): fail(path,'duplicate report dates')
    if data.get('latest') not in seen: fail(path,'latest must match a date in reports')
    if data['latest']!=max(seen): fail(path,'latest must be newest date')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--reports-dir',type=Path,default=Path('artifacts/daily-market-brief'))
    ap.add_argument('--date',help='validate only YYYY-MM-DD.json')
    args=ap.parse_args(); root=args.reports_dir
    files={p.name for p in root.glob('????-??-??.json')}
    if args.date:
        valid_date(args.date,root)
        candidates=[root/f'{args.date}.json']
    else: candidates=sorted(root.glob('????-??-??.json'))
    if not candidates: raise ValueError(f'{root}: no dated report JSON found')
    total=0
    for p in candidates:
        rows=validate_report(p,load_json(p));total+=rows
        print(f'OK {p}: {rows} forecast row(s)')
    idx=root/'reports.json'
    if not idx.exists(): fail(idx,'required report index missing')
    validate_index(idx,load_json(idx),files)
    print(f'OK {idx}: {len(load_json(idx)["reports"])} report(s) indexed; {total} forecast row(s) validated')
if __name__=='__main__':
    try: main()
    except ValueError as e: print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
