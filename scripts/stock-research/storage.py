"""Exclusive local generations and hash-checked compatible state; no provider access."""
import csv
from datetime import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 1
HISTORY_COLUMNS = ('code','session_date','open','high','low','close','volume','turnover','currency','adjustment',
    'source','source_at_ms','raw_time_key','raw_date','raw_time_zone','time_zone_unit_status','time_zone_unit_source_url',
    'provider_finality_status','retrieved_at_ms','known_at_ms','revision_vintage','completed','completion_status',
    'volume_precision','currency_source_url','price_known_at_ms','currency_known_at_ms','currency_evidence_hash','currency_status')
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
MAX_HISTORY_ROWS = 250000
RESERVED = {'scripts','backend','frontend','ingest','connectors','tests','skills','plans','artifacts','.git','.agents',
            'agent-operations','harness','infra','docs','.venv'}


class StorageError(ValueError):
    pass


def need(condition, category='invalid-storage'):
    if not condition:
        raise StorageError(category)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def output_parent(value):
    path = Path(value).expanduser().resolve()
    if path.is_relative_to(ROOT):
        rel = path.relative_to(ROOT)
        need(bool(rel.parts) and rel.parts[0] not in RESERVED and not rel.parts[0].startswith('.'), 'output-code-path-forbidden')
        # An ignored parent directory, not just selected extensions, is required.
        check = subprocess.run(['git','-C',str(ROOT),'check-ignore','--no-index','--quiet',rel.as_posix()+'/'],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
        need(check.returncode == 0, 'output-parent-must-be-fully-gitignored: add the entire data parent in setup')
    return path


def private_read(path):
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600 and info.st_size <= MAX_ARTIFACT_BYTES, 'artifact-size-or-type')
        return stream.read(MAX_ARTIFACT_BYTES+1)


class Generation:
    def __init__(self, parent, *, generated_at=None, kind='stock-research-collection', compatibility_id=None, as_of_ms=None):
        self.parent = output_parent(parent)
        self.parent.mkdir(parents=True,exist_ok=True)
        stamp = generated_at or datetime.now(ZoneInfo('Asia/Kuala_Lumpur'))
        need(stamp.tzinfo is not None, 'generation-timezone-required')
        stamp = stamp.astimezone(ZoneInfo('Asia/Kuala_Lumpur'))
        self.path = self.parent / stamp.strftime('%Y-%m-%d_%H%M%S')
        self.path.mkdir(mode=0o700,exist_ok=False)
        self.manifest = {'schema_version':SCHEMA_VERSION,'kind':kind,'canonical_history_schema_version':1,
            'generated_at':stamp.isoformat(),'compatibility_id':compatibility_id,'as_of_ms':as_of_ms,'artifacts':{}}
        self.closed = False

    def write(self, name, data):
        need(not self.closed and isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:json|csv|joblib|xlsx)',name) is not None
             and name != 'manifest.json', 'invalid-artifact-name')
        need(isinstance(data,bytes) and len(data)<=MAX_ARTIFACT_BYTES,'artifact-size')
        fd=os.open(self.path/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        self.manifest['artifacts'][name]={'path':name,'sha256':sha(data),'bytes':len(data)}

    def json(self,name,value):
        self.write(name,canonical(value))

    def csv(self,name,rows,columns):
        stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore',lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key:json.dumps(row.get(key),sort_keys=True) if isinstance(row.get(key),(dict,list,tuple)) else row.get(key) for key in columns})
        self.write(name,stream.getvalue().encode())

    def finish(self,**metadata):
        need(not self.closed,'generation-already-finalized')
        need(not {'schema_version','kind','generated_at','compatibility_id','artifacts'} & metadata.keys(),'reserved-manifest-field')
        candidate = self.manifest | metadata
        validate_artifact_entries(candidate)
        validate_components(candidate)
        self.manifest.update(metadata)
        raw=canonical(self.manifest)
        fd=os.open(self.path/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
        self.closed=True
        return self.path


COMPONENT_KINDS = {'collection':'stock-research-collection','prediction':'stock-research-prediction','exports':'stock-research-exports'}
COMPONENT_REQUIRED = {'collection':{'history.csv','history_revisions.csv','state.json','metadata_input.json','identity_bindings.json','calendar.json','universe.json','coverage.json'},
    'prediction':{'predictions.json','outcomes.json'},'exports':{'master.csv','forecasts.csv','top20.csv','export_coverage.json','research.xlsx'}}


def validate_artifact_entries(value):
    entries=value.get('artifacts')
    need(isinstance(entries,dict),'manifest-artifacts')
    for name,entry in entries.items():
        need(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:json|csv|joblib|xlsx)',name) is not None
             and name!='manifest.json' and isinstance(entry,dict) and set(entry)=={'path','sha256','bytes'}
             and entry['path']==name,'artifact-reference')
        need(isinstance(entry['sha256'],str) and re.fullmatch('[0-9a-f]{64}',entry['sha256']) is not None
             and type(entry['bytes']) is int and 0<=entry['bytes']<=MAX_ARTIFACT_BYTES,'artifact-metadata')


def validate_components(value):
    if value.get('kind')!='stock-research-run':
        need('components' not in value and 'components_schema_version' not in value,'unexpected-components')
        return
    need(value.get('components_schema_version')==1 and type(value.get('components_schema_version')) is int,'component-version')
    components=value.get('components')
    need(isinstance(components,dict) and bool(components) and set(components)<=set(COMPONENT_KINDS),'component-allowlist')
    owned=set()
    for name,entry in components.items():
        need(isinstance(entry,dict) and set(entry)=={'schema_version','status','artifacts','compatibility_id'},'component-fields')
        need(type(entry['schema_version']) is int and entry['schema_version']==1,'component-version')
        need(isinstance(entry['status'],str) and entry['status'] in {'complete','partial','research-only','unavailable'},'component-status')
        names=entry['artifacts']
        need(isinstance(names,list) and all(isinstance(n,str) for n in names) and len(names)==len(set(names)),'component-artifacts')
        need(COMPONENT_REQUIRED[name]<=set(names) and set(names)<=set(value['artifacts']) and not owned.intersection(names),'component-artifacts')
        owned.update(names)
        need(isinstance(entry['compatibility_id'],str) and bool(entry['compatibility_id']),'component-compatibility')
        if name=='collection':need(entry['compatibility_id']==value.get('compatibility_id'),'component-compatibility')


def manifests(parent, *, kind=None, compatibility_id=None, component=None):
    need(component is None or component in COMPONENT_KINDS,'component-allowlist')
    parent=output_parent(parent)
    if not parent.exists():return []
    found=[]
    for folder in sorted(parent.iterdir()):
        if folder.is_symlink() or not folder.is_dir() or re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{6}',folder.name) is None:
            continue
        path=folder/'manifest.json'
        if not path.is_file():continue  # Incomplete generation is never latest state.
        try:
            value=json.loads(private_read(path))
            if value.get('schema_version')!=1 or value.get('kind')=='capability-pilot':continue
            if kind is not None and value.get('kind')!=kind:continue
            if component is not None:
                if value.get('is_demo') is True:continue
                if value.get('kind')=='stock-research-run':
                    validate_components(value)
                    if component not in value['components']:continue
                elif value.get('kind')!=COMPONENT_KINDS[component]:continue
            elif kind in {'stock-research-collection','stock-research-prediction'} and value.get('is_demo') is True:continue
            if value.get('kind')=='stock-research-run':validate_components(value)
            actual_compatibility=(value['components'][component]['compatibility_id'] if component is not None and value.get('kind')=='stock-research-run' else value.get('compatibility_id'))
            if compatibility_id is not None and actual_compatibility!=compatibility_id:continue
            validate_artifact_entries(value)
            stamp=datetime.fromisoformat(value['generated_at'])
            need(stamp.tzinfo is not None and stamp.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%Y-%m-%d_%H%M%S')==folder.name,'manifest-time')
            need(isinstance(value.get('artifacts'),dict),'manifest-artifacts')
            info=folder.stat()
            need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700,'generation-permissions')
            # Validate every referenced artifact, including unconsumed ones.
            for name,entry in value['artifacts'].items():
                need(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:json|csv|joblib|xlsx)',name) is not None
                     and isinstance(entry,dict) and entry.get('path')==name,'artifact-reference')
                artifact=folder/entry['path']
                need(artifact.parent==folder and not artifact.is_symlink() and artifact.resolve().is_relative_to(folder.resolve()),'unsafe-artifact')
                data=private_read(artifact)
                need(sha(data)==entry['sha256'] and len(data)==entry['bytes'],'artifact-hash-mismatch')
            found.append((stamp,folder,value))
        except (OSError,ValueError,TypeError,KeyError):
            raise StorageError('invalid-state-generation') from None
    return sorted(found,key=lambda item:(item[0],item[1].name))


def latest_state(parent,compatibility_id):
    matches=manifests(parent,component='collection',compatibility_id=compatibility_id)
    if not matches:return None
    _,folder,manifest=matches[-1]
    need('state.json' in manifest['artifacts'] and 'history.csv' in manifest['artifacts'],'state-artifacts-missing')
    state=json.loads(private_read(folder/'state.json'))
    need(state.get('schema_version')==1,'state-schema')
    rows=list(csv.DictReader(io.StringIO(private_read(folder/'history.csv').decode())))
    need(len(rows)<=MAX_HISTORY_ROWS,'history-row-budget')
    integer_fields={'source_at_ms','raw_time_key','raw_date','raw_time_zone','retrieved_at_ms','known_at_ms','volume_precision','price_known_at_ms','currency_known_at_ms'}
    number_fields={'open','high','low','close','volume','turnover'}
    histories={}
    failed=False
    try:
        from contracts import code,iso_date,integer
        for raw in rows:
            need(set(raw)==set(HISTORY_COLUMNS),'history-columns')
            row={key:None if value=='' else value for key,value in raw.items()}
            code(row.get('code'));iso_date(row.get('session_date'))
            for key in integer_fields:
                if row.get(key) is not None:row[key]=int(row[key])
            need(all(integer(row.get(key),0) for key in ('source_at_ms','retrieved_at_ms','known_at_ms','raw_time_key','raw_date','volume_precision')),'history-source-time')
            need(row['source_at_ms']<=row['retrieved_at_ms'] and row['source_at_ms']<=row['known_at_ms'],'history-source-time-order')
            for key in number_fields:
                row[key]=float(row[key]);need(math.isfinite(row[key]) and row[key]>=0,'history-numeric')
            need(row['low']>0 and row['low']<=min(row['open'],row['close'])<=max(row['open'],row['close'])<=row['high'],'history-price-range')
            need(row.get('completed') in {'True','False'},'history-completion-type')
            row['completed']=row['completed']=='True'
            histories.setdefault(row['code'],[]).append(row)
    except (ValueError,TypeError,KeyError,OverflowError):failed=True
    if failed:raise StorageError('invalid-cached-history')
    return {'folder':str(folder),'manifest':manifest,'state':state,'histories':histories,
            'metadata_input':json.loads(private_read(folder/'metadata_input.json')) if 'metadata_input.json' in manifest['artifacts'] else None}


def forecast_symbols(parent):
    symbols=set()
    for _,_,manifest in manifests(parent,component='prediction'):
        codes=manifest.get('pending_forecast_symbols',manifest.get('forecast_symbols',[]))
        need(isinstance(codes,list) and all(isinstance(code,str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}',code) for code in codes),'forecast-symbol-contract')
        symbols.update(codes)
    return symbols


def merge_history(previous,incoming):
    """Append-only generations preserve old rows; current state chooses newest known revision."""
    keyed={row['session_date']:dict(row) for row in previous};changes=[]
    need(len(keyed)==len(previous),'duplicate-cached-history')
    for row in incoming:
        old=keyed.get(row['session_date'])
        need(old is None or old['code']==row['code'],'history-identity-conflict')
        if old is not None and row['known_at_ms']<old['known_at_ms']:continue
        substantive=lambda item:{key:val for key,val in item.items() if key not in {'retrieved_at_ms','known_at_ms','revision_vintage','price_known_at_ms','currency_known_at_ms'}}
        if old is not None and row['known_at_ms']==old['known_at_ms'] and substantive(old)!=substantive(row):
            raise StorageError('conflicting-same-known-at-revision')
        if old!=row:
            value=dict(row)
            same=old is not None and substantive(old)==substantive(row)
            if same:
                value['known_at_ms']=old['known_at_ms']
                if old.get('price_known_at_ms') is not None:value['price_known_at_ms']=old['price_known_at_ms']
            changes.append({'code':row['code'],'session_date':row['session_date'],'old_hash':sha(canonical(old)) if old else None,
                            'new_hash':sha(canonical(value)),'known_at_ms':value['known_at_ms'],'revision_vintage':row['revision_vintage'],
                            'change_type':'reobserved' if same else 'revised' if old else 'new'})
            keyed[row['session_date']]=value
    return sorted(keyed.values(),key=lambda row:row['session_date']),changes
