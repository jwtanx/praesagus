"""Canonical offline readers and revision selection. Never backdate measured availability.

SQLite tables use exactly storage.HISTORY_COLUMNS. Generation CSV receipts retain
all sidecars; standalone CSV/SQLite requires an explicit receipt from its caller.
"""
from bisect import bisect_right
import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import re
import sqlite3

from storage import HISTORY_COLUMNS, canonical, manifests, private_read, sha

INTS = {'source_at_ms','raw_time_key','raw_date','raw_time_zone','retrieved_at_ms','known_at_ms',
        'volume_precision','price_known_at_ms','currency_known_at_ms'}
NUMBERS = {'open','high','low','close','volume','turnover'}
MAX_ROWS = 250000
MAX_FILES = 1000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_BYTES = 256 * 1024 * 1024

GAPS = {'membership','delistings','adjustment-vintage','first-availability'}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def valid_identity(value):
    return (type(value) is int and 0<value<=2**63-1 or isinstance(value,str)
            and re.fullmatch(r'[0-9]{1,19}',value) is not None and 0<int(value)<=2**63-1)


def normalize(raw):
    require(set(raw) == set(HISTORY_COLUMNS), 'canonical-history-columns')
    row = {key: None if value is None or value == '' else value for key, value in raw.items()}
    require(isinstance(row['code'], str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}', row['code']), 'invalid-code')
    require(date.fromisoformat(row['session_date']).isoformat() == row['session_date'], 'invalid-session')
    for key in INTS:
        value = row[key]
        if value is not None:
            require(type(value) is int or isinstance(value, str) and re.fullmatch(r'-?\d+', value), 'invalid-integer')
            row[key] = int(value)
    for key in ('source_at_ms','retrieved_at_ms','known_at_ms','price_known_at_ms'):
        require(type(row[key]) is int and row[key] >= 0, 'missing-availability')
    require(row['source_at_ms'] <= row['price_known_at_ms'] <= row['retrieved_at_ms'] and row['known_at_ms'] >= row['price_known_at_ms'], 'availability-order')
    if row['currency_known_at_ms'] is not None:
        require(0 <= row['currency_known_at_ms'] <= row['known_at_ms'], 'currency-availability-order')
    for key in NUMBERS:
        require(type(row[key]) is not bool, 'invalid-number')
        row[key] = float(row[key])
        require(math.isfinite(row[key]) and row[key] >= 0, 'invalid-number')
    require(0 < row['low'] <= min(row['open'],row['close']) <= max(row['open'],row['close']) <= row['high'], 'invalid-ohlc')
    value = row['completed']
    require(type(value) is bool or type(value) is int and value in (0,1) or value in ('True','False'), 'invalid-boolean')
    row['completed'] = value is True or type(value) is int and value == 1 or value == 'True'
    require(row['adjustment'] in {'unadjusted','forward-excluding-dividends','back-excluding-dividends'}, 'adjustment-unknown')
    require(isinstance(row['revision_vintage'],str) and bool(row['revision_vintage']), 'vintage-missing')
    return row


@dataclass
class History:
    rows: list
    receipts: list

    def __post_init__(self):
        self._index={}
        for row in self.rows:
            self._index.setdefault(row['code'],{}).setdefault(row['session_date'],[]).append(dict(row))
        self._index={code:{day:(tuple(r['known_at_ms'] for r in sorted(rows,key=lambda r:r['known_at_ms'])),
            tuple(sorted(rows,key=lambda r:r['known_at_ms']))) for day,rows in days.items()} for code,days in self._index.items()}

    def as_of(self, code, cutoff_ms, *, policy='strict', declared_gaps=()):
        require(policy in ('strict','research-retrospective'), 'unknown-policy')
        if policy == 'research-retrospective':
            require(GAPS <= set(declared_gaps), 'retrospective-gaps-must-be-declared')
        selected=[]
        cutoff_day=datetime.fromtimestamp(cutoff_ms/1000,timezone.utc).date().isoformat()
        for day,(times, revisions) in sorted(self._index.get(code,{}).items()):
            if day>cutoff_day:
                break
            index=bisect_right(times,cutoff_ms)-1 if policy=='strict' else len(times)-1
            if index>=0:
                selected.append(dict(revisions[index]))
        return selected

    def receipt(self, policy, declared_gaps=()):
        return {'policy':policy,'declared_gaps':sorted(declared_gaps), 'point_in_time':False, 'qualification':'insufficient-until-dated-universe-mandate-adjustment-evidence-reviewed',
                'inputs':self.receipts,'rows_sha256':sha(canonical(self.rows))}


def assemble(rows, receipts):
    unique = {}; identities = {}
    require(len(receipts)<=MAX_FILES,'input-file-budget')
    for receipt in receipts:
        for binding in receipt.get('identity_bindings',[]):
            require(isinstance(binding,dict),'invalid-identity-binding')
            security, identity = binding.get('code'), binding.get('stock_id')
            require(isinstance(security,str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,63}',security) and valid_identity(identity), 'identity-binding-missing')
            require(security not in identities or type(identities[security]) is type(identity) and identities[security] == identity, 'symbol-identity-conflict')
            identities[security] = identity
    for count,raw in enumerate(rows):
        require(count<MAX_ROWS*4,'input-observation-budget')
        row = normalize(raw)
        require(row['code'] in identities, 'identity-binding-missing')
        key = row['code'], row['session_date'], row['known_at_ms']
        # Re-observation receipt timestamps/hashes may differ without changing evidence.
        substantive = {k:v for k,v in row.items() if k not in ('retrieved_at_ms','revision_vintage')}
        if key in unique:
            prior = unique[key]
            require(substantive == {k:v for k,v in prior.items() if k not in ('retrieved_at_ms','revision_vintage')}, 'conflicting-same-known-revision')
            if canonical(row) < canonical(prior): unique[key] = row
        else: unique[key] = row
        require(len(unique)<=MAX_ROWS,'input-row-budget')
    return History([unique[key] for key in sorted(unique)], sorted(receipts,key=lambda r:canonical(r)))


def read_csv(paths, *, receipt):
    paths=sorted({str(Path(path).resolve()) for path in paths})
    require(len(paths)<=MAX_FILES,'input-file-budget')
    require(sum(Path(path).stat().st_size for path in paths)+len(canonical(receipt))<=MAX_TOTAL_BYTES,'aggregate-input-byte-budget')
    receipts=[]
    def stream():
        for path in paths:
            require(Path(path).stat().st_size<=MAX_BYTES,'input-byte-budget')
            import hashlib
            digest=hashlib.sha256()
            with open(path,'rb') as source:
                for chunk in iter(lambda:source.read(65536),b''):digest.update(chunk)
            receipts.append(dict(receipt,file_sha256=digest.hexdigest()))
            with open(path,newline='') as source:
                yield from csv.DictReader(source)
    # Bindings are supplied once; parsed rows are streamed, never accumulated twice.
    result=assemble(stream(),[receipt])
    result.receipts=receipts
    return result


def read_sqlite(path, *, receipt, table='ohlcv'):
    require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',table) is not None,'invalid-table')
    uri=Path(path).resolve().as_uri()+'?mode=ro'
    require(Path(path).stat().st_size<=MAX_BYTES,'input-byte-budget')
    require(sum(p.stat().st_size for p in (Path(path),Path(str(path)+'-wal')) if p.exists())+len(canonical(receipt))<=MAX_TOTAL_BYTES,'aggregate-input-byte-budget')
    with sqlite3.connect(uri,uri=True) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        cursor=connection.execute(f'SELECT * FROM "{table}"')
        columns=[item[0] for item in cursor.description]
        require(len(columns)==len(set(columns)),'duplicate-columns')
        result=assemble((dict(zip(columns,row)) for row in cursor),[dict(receipt,hash_scope='canonical-normalized-rows-in-readonly-transaction; mainfile-not-WAL-snapshot')])
        result.receipts[0]['snapshot_rows_sha256']=sha(canonical(result.rows))
        return result


def read_generations(parent, *, compatibility_id):
    paths=[]; receipts=[]
    require(sum(1 for _ in Path(parent).iterdir())<=MAX_FILES if Path(parent).exists() else True,'input-file-budget')
    # Bound actual candidate files before storage.manifests reads their contents.
    total=0
    if Path(parent).exists():
        for folder in Path(parent).iterdir():
            if folder.is_dir() and not folder.is_symlink():
                for artifact in folder.iterdir():
                    if artifact.is_file():
                        total+=artifact.stat().st_size
                        require(total<=MAX_TOTAL_BYTES,'aggregate-input-byte-budget')
    generations=manifests(parent,component='collection',compatibility_id=compatibility_id)
    require(len(generations)<=MAX_FILES,'input-file-budget')
    for _,folder,manifest in generations:
        required={'history.csv','identity_bindings.json','calendar.json','metadata_input.json'}
        require(required <= manifest['artifacts'].keys(),'generation-sidecars-missing')
        get=lambda name:json.loads(private_read(folder/name))
        calendar=get('calendar.json')
        require(sha(canonical(calendar['sessions']))==calendar['schedule_sha256'],'calendar-hash-mismatch')
        receipts.append({'manifest_sha256':sha(private_read(folder/'manifest.json')),
            'history_sha256':manifest['artifacts']['history.csv']['sha256'],
            'identity_bindings':get('identity_bindings.json'),'calendar':calendar,
            'metadata_input':get('metadata_input.json'),'adjustment_policy':manifest.get('adjustment_policy'),
            'as_of_ms':manifest['as_of_ms'],'historical_membership':manifest.get('history_interpretation')})
        paths.append((folder/'history.csv',manifest['artifacts']['history.csv']['sha256']))
    def stream():
        for path,expected_hash in paths:
            raw=private_read(path)
            require(sha(raw)==expected_hash,'history-hash-mismatch')
            yield from csv.DictReader(io.StringIO(raw.decode()))
    return assemble(stream(),receipts)


def validate_window(rows, sessions, calendar, *, cutoff_ms, currency='USD', adjustment='forward-excluding-dividends'):
    by_day={row['session_date']:row for row in rows}
    require(len(by_day)==len(rows),'duplicate-session')
    output=[]
    for day in sessions:
        row=by_day.get(day)
        require(row is not None,'missing-required-session')
        close=calendar.close_ms(day)
        require(row['completed'] and close<=cutoff_ms and row['price_known_at_ms']>=close and row['retrieved_at_ms']>=close,'incomplete-session')
        require(row['currency']==currency and row['adjustment']==adjustment,'incompatible-units')
        output.append(row)
    return output


def make_labels(history, code, origin, *, calendar, fit_cutoff_ms, origin_cutoff_ms,
                policy='strict', declared_gaps=()):
    features=history.as_of(code,origin_cutoff_ms,policy=policy,declared_gaps=declared_gaps)
    reference=validate_window(features,[origin],calendar,cutoff_ms=origin_cutoff_ms)[0]
    require(reference['known_at_ms']<=fit_cutoff_ms,'reference-not-available-at-fit')
    actuals=history.as_of(code,fit_cutoff_ms)  # Label admission is ALWAYS actual availability.
    labels=[]
    for horizon,sessions in calendar.windows(origin).items():
        record={'code':code,'origin':origin,'horizon':horizon,'sessions':sessions,
                'end':sessions[-1],'status':'pending','reference_close':reference['close']}
        try:
            window=validate_window(actuals,sessions,calendar,cutoff_ms=fit_cutoff_ms,
                                   currency=reference['currency'],adjustment=reference['adjustment'])
        except ValueError as error:
            record['reason']=str(error)
        else:
            record.update(status='complete',realized_low=min(r['low'] for r in window),
                realized_high=max(r['high'] for r in window),
                terminal_logreturn=math.log(window[-1]['close']/reference['close']),
                label_available_at=max(reference['known_at_ms'],max(r['known_at_ms'] for r in window)),
                end_at_ms=calendar.close_ms(sessions[-1]))
            record['low_return']=record['realized_low']/reference['close']-1
            record['high_return']=record['realized_high']/reference['close']-1
        labels.append(record)
    return origin_weights(labels)


def origin_weights(rows):
    unique={}
    for row in rows:
        key=row['code'],row['origin'],row['horizon']
        require(key not in unique or unique[key]==row,'conflicting-origin-horizon')
        unique[key]=dict(row)
    counts={}
    for row in unique.values():
        if row['status']=='complete':
            key=row['code'],row['origin'];counts[key]=counts.get(key,0)+1
    for row in unique.values():
        row['weight']=1/counts[row['code'],row['origin']] if row['status']=='complete' else 0
    return list(unique.values())


def purged_splits(rows, *, validation_start, holdout_start, fit_cutoff_ms, calendar):
    require(validation_start<holdout_start,'split-order')
    result={'train':[],'validation':[],'holdout':[],'purged':[]}
    for row in origin_weights(rows):
        split='train' if row['origin']<validation_start else 'validation' if row['origin']<holdout_start else 'holdout'
        boundary=validation_start if split=='train' else holdout_start if split=='validation' else None
        limit=calendar.open_ms(boundary) if boundary else fit_cutoff_ms+1
        if row['status']!='complete' or row['label_available_at']>fit_cutoff_ms or row['label_available_at']>=limit or row['end_at_ms']>=limit:
            result['purged'].append(row)
        else: result[split].append(row)
    for split in ('train','validation','holdout'): result[split]=origin_weights(result[split])
    result['status']={key:'ready' if result[key] else 'empty' for key in ('train','validation','holdout')}
    return result
