"""Private append-only point observations. No credential/network capabilities."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
from urllib.parse import parse_qsl, urlsplit

from connectors.moomoo_rest import ReadRequest, ReadResponse, RESTError

APP_ID = 0x50524D36
SCHEMA_VERSION = 1
MAX_RAW = 2 * 1024 * 1024
REPO = Path(__file__).resolve().parents[1]
SECRET_KEYS = {'authorization', 'x-api-key', 'api_key', 'apikey', 'appkey', 'appkeyid',
               'signature', 'nonce', 'password', 'passphrase', 'private_key', 'token',
               'access_token', 'refresh_token', 'headers', 'account_id', 'acc_id'}
SECRET_TAGS = {re.sub(r'[^a-z0-9]', '', key) for key in SECRET_KEYS}


def secret_key(key):
    return re.sub(r'[^a-z0-9]', '', key.lower()) in SECRET_TAGS


DDL = {
    'runs': 'CREATE TABLE runs (id TEXT PRIMARY KEY, provider TEXT NOT NULL)',
    'attempts': '''CREATE TABLE attempts (id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
        kind TEXT NOT NULL, known_ms INTEGER NOT NULL, metadata TEXT NOT NULL)''',
    'versions': '''CREATE TABLE versions (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, identity TEXT NOT NULL,
        semantic_hash TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, source_ms INTEGER,
        UNIQUE(kind,identity,semantic_hash), UNIQUE(kind,identity,revision))''',
    'observations': '''CREATE TABLE observations (attempt_id TEXT NOT NULL REFERENCES attempts(id),
        version_id INTEGER NOT NULL REFERENCES versions(id), ordinal INTEGER NOT NULL,
        PRIMARY KEY(attempt_id,ordinal))''',
}
for _table in list(DDL):
    for _action in ('UPDATE', 'DELETE'):
        _name = _table + '_' + _action.lower()
        DDL[_name] = f"CREATE TRIGGER {_name} BEFORE {_action} ON {_table} BEGIN SELECT RAISE(ABORT,'immutable'); END"


class MarketStoreError(ValueError):
    """Controlled categories; no path/provider/credential exception data."""


def need(condition, category='invalid-input'):
    if not condition:
        raise MarketStoreError(category)


def safe(fn, *args, category='storage-failed', **kwargs):
    failed = False
    try:
        result = fn(*args, **kwargs)
    except Exception:
        failed = True
    if failed:
        raise MarketStoreError(category)
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


TIMESTAMP = re.compile(
    r'[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
    r'(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])'
)


def parse_aware(value):
    """Reject unsupported precision/offset forms before datetime can normalize."""
    def parse():
        need(isinstance(value, str) and TIMESTAMP.fullmatch(value) is not None)
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(parsed.utcoffset() is not None)
        return parsed
    return safe(parse, category='invalid-time')


def aware_ms(value, round_up=False):
    def parse():
        parsed = parse_aware(value)
        delta = parsed.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        micros = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        stamp = (micros + (999 if round_up else 0)) // 1000
        need(micros >= 0 and stamp <= 2**63 - 1)
        return stamp
    return safe(parse, category='invalid-time')


def text(value, maximum=512):
    return (isinstance(value, str) and 0 < len(value) <= maximum
            and bool(value.strip()) and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value))


def source_ms(value, unit):
    if value is None:
        return None
    need(type(value) is int and 0 <= value <= (2**63 - 1) // unit, 'invalid-response')
    return value * unit


def private(path, directory=False, readonly=False):
    info = path.lstat()
    need((stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
         and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o400 if readonly else 0o600),
         'unsafe-storage')


def pairs(values):
    result = {}
    for key, value in values:
        need(key not in result, 'invalid-response')
        result[key] = value
    return result


def check_secrets(value, secrets=()):
    if isinstance(value, dict):
        for key, item in value.items():
            need(not secret_key(key), 'secret-rejected')
            check_secrets(item, secrets)
    elif isinstance(value, list):
        for item in value:
            check_secrets(item, secrets)
    elif isinstance(value, str):
        if value.startswith(('http://', 'https://')):
            parsed = urlsplit(value)
            need(not parsed.username and not parsed.password and not any(secret_key(k) for k, _ in parse_qsl(parsed.query)), 'secret-rejected')
        need(not any(secret in value for secret in secrets)
             and '-----BEGIN ' not in value, 'secret-rejected')
    elif isinstance(value, float):
        need(math.isfinite(value), 'invalid-response')


def decode(raw, secrets=()):
    def load():
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=lambda _: need(False, 'invalid-response'))
        check_secrets(value, secrets)
        canonical(value).encode('utf-8')
        return value
    return safe(load, category='invalid-response')


def request_meta(request):
    need(isinstance(request, ReadRequest))
    secrets = tuple(value for key, value in request.headers.items()
                    if key.lower() in {'x-api-key', 'authorization', 'x-nonce'}
                    and isinstance(value, str) and len(value) >= 8)
    need(isinstance(request.body, bytes) and len(request.body) <= MAX_RAW
         and isinstance(request.query, str) and len(request.query) <= 8192)
    if (request.method, request.path) == ('POST', '/api/v1.0/quote/snapshot'):
        body = decode(request.body, secrets)
        need(isinstance(body, dict) and set(body) == {'code_list'} and not request.query)
        codes = body['code_list']
        need(isinstance(codes, list) and 1 <= len(codes) <= 400
             and all(isinstance(c, str) and re.fullmatch(r'US\.[A-Z][A-Z0-9.-]{0,59}', c) for c in codes)
             and len(set(codes)) == len(codes))
        return 'snapshot', {'codes': codes}, secrets
    need((request.method, request.path) == ('GET', '/api/v1.0/quote/find-news') and not request.body)
    query = parse_qsl(request.query, keep_blank_values=True, strict_parsing=True)
    need(len(query) == len(dict(query)))
    filters = dict(query)
    need(set(filters) <= {'symbol', 'size', 'news_type', 'sort_type', 'lang'}
         and {'symbol', 'size'} <= set(filters) and text(filters['symbol'])
         and re.fullmatch(r'\d{1,2}', filters['size']) and 1 <= int(filters['size']) <= 50)
    need('news_type' not in filters or filters['news_type'] in ('1', '2', '3'))
    need('sort_type' not in filters or filters['sort_type'] in ('1', '2'))
    need('lang' not in filters or filters['lang'] in ('en', 'ja', 'zh-CN', 'zh-HK'))
    check_secrets(filters, secrets)
    return 'news', filters, secrets


def normalized(raw, kind, request, secrets=(), *, version=2):
    need(type(version) is int and version in (1,2), 'invalid-response')
    value = decode(raw, secrets)
    need(isinstance(value, dict) and set(value) == {'ret_code', 'ret_msg', 'data'}
         and type(value['ret_code']) is int and value['ret_code'] == 0
         and isinstance(value['ret_msg'], str), 'invalid-response')
    rows = value['data']
    if kind == 'snapshot':
        need(isinstance(rows, dict) and set(rows) == {'snapshot_list'}, 'invalid-response')
        rows = rows['snapshot_list']
    need(isinstance(rows, list) and len(rows) <= (len(request['codes']) if kind == 'snapshot' else int(request['size'])), 'invalid-response')
    result, seen = [], set()
    for row in rows:
        need(isinstance(row, dict), 'invalid-response')
        if kind == 'snapshot':
            code = row.get('code')
            need(code in request['codes'] and code not in seen, 'invalid-response');seen.add(code)
            for key, item in row.items():
                if key.endswith('_valid'):
                    need(type(item) is bool, 'invalid-response')
                # Historical/auxiliary prices are not consumed as current quotes.
                if version==2 and key=='prev_close_price' and item is None:continue
                if key in ('last_price', 'open_price', 'high_price', 'low_price',
                           'prev_close_price', 'volume', 'turnover', 'turnover_rate'):
                    need(type(item) in (int, float) and math.isfinite(item) and item >= 0, 'invalid-response')
            need('last_price' in row and 'volume' in row and type(row['volume']) is int, 'invalid-response')
            stamp = source_ms(row.get('update_time'), 1)
            market_date = row.get('data_date')
            if market_date is not None:
                need(isinstance(market_date, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', market_date), 'invalid-response')
                safe(date.fromisoformat, market_date, category='invalid-response')
            payload = {'provider': 'moomoo-rest', 'code': code, 'quote_time_ms': row.get('update_time'),
                       'market_date': market_date, 'price': row['last_price'], 'volume': row['volume'],
                       'currency': None, 'session': None, 'adjustment': None, 'source_timezone': 'UTC', 'market_timezone': None,
                       'validity': {k: v for k, v in row.items() if k.endswith('_valid')}}
            if version==2:
                payload.update(normalization_version=2,provider_prev_close=row.get('prev_close_price'))
            identity = ['moomoo-rest', code, stamp]
        else:
            key = row.get('news_id');need(text(key) and key not in seen, 'invalid-response');seen.add(key)
            need(isinstance(row.get('title'), str) and len(row['title']) <= 8192 and text(row.get('url'), 8192), 'invalid-response')
            url = urlsplit(row['url'])
            need(url.scheme == 'https' and url.hostname and not url.username and not url.password
                 and not any(secret_key(k) for k, _ in parse_qsl(url.query)), 'invalid-response')
            stamp = source_ms(row.get('publish_time'), 1000)
            need(row.get('news_type') in ('POST', 'NOTICE', 'REPORT'), 'invalid-response')
            payload = {'provider': 'moomoo-rest', 'item_id': key, 'title': row['title'], 'url': row['url'],
                       'news_type': row['news_type'], 'publication_seconds': row.get('publish_time'),
                       'provider_available_at': None, 'source_timezone': 'UTC'}
            identity = ['moomoo-rest', key]
        result.append((canonical(identity), canonical(payload), stamp))
    return result


@dataclass(frozen=True, repr=False)
class StoredAttempt:
    attempt_id: str
    status: str
    added: bool
    raw_hash: str | None
    def __repr__(self):
        return '<StoredMarketAttempt>'


class PrivateMarketStore:
    def __init__(self, root, *, create=False, public_roots=(), lock_timeout=1.0):
        def setup():
            p = Path(root)
            need(p.is_absolute() and p == p.resolve() and not p.is_relative_to(REPO)
                 and not any(part.lower() in {'public', 'www', 'htdocs', 'artifacts', 'dist'} for part in p.parts)
                 and not any(p.is_relative_to(Path(r).resolve()) for r in public_roots), 'unsafe-storage')
            need(type(lock_timeout) in (float, int) and math.isfinite(lock_timeout) and 0 < lock_timeout <= 5)
            self.root, self.raw_dir, self.database = p, p / 'raw', p / 'market.sqlite3'
            self.lock_timeout = lock_timeout
            if create:
                p.mkdir(mode=0o700, exist_ok=True)
                private(p, directory=True)
                self.raw_dir.mkdir(mode=0o700, exist_ok=True)
                if not self.database.exists():
                    fd = os.open(self.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600);os.close(fd)
                    with self._connection(initializing=True) as db:
                        db.execute('BEGIN IMMEDIATE')
                        for sql in DDL.values():db.execute(sql)
                        db.execute(f'PRAGMA application_id={APP_ID}')
                        db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            self._paths()
            with self._connection(readonly=True):pass
        safe(setup)

    def __repr__(self):
        return '<PrivateMarketStore>'

    def _paths(self):
        private(self.root, directory=True);private(self.raw_dir, directory=True);private(self.database)
        with self.database.open('rb') as f:header = f.read(20)
        need(not (header.startswith(b'SQLite format 3') and any(v == 2 for v in header[18:20])), 'unsupported-journal')
        for suffix in ('-journal', '-wal', '-shm'):
            p = Path(str(self.database) + suffix)
            need(not p.exists() and not p.is_symlink(), 'journal-present')

    @contextmanager
    def _connection(self, *, readonly=False, initializing=False):
        self._paths()
        db = None
        error = False
        try:
            db = sqlite3.connect(self.database.as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=self.lock_timeout)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            if readonly:db.execute('PRAGMA query_only=ON')
            if not initializing:
                need(db.execute('PRAGMA application_id').fetchone()[0] == APP_ID
                     and db.execute('PRAGMA user_version').fetchone()[0] == SCHEMA_VERSION, 'unknown-schema')
                schema = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))
                need(schema == DDL and db.execute('PRAGMA journal_mode').fetchone()[0] == 'delete', 'unknown-schema')
            yield db
            if not readonly:db.commit()
        except Exception:
            if db is not None:db.rollback()
            error = True
        finally:
            if db is not None:db.close()
        if error:raise MarketStoreError('database-failed')

    def raw(self, raw_hash):
        def read():
            need(isinstance(raw_hash, str) and re.fullmatch(r'[0-9a-f]{64}', raw_hash))
            self._paths();p = self.raw_dir / (raw_hash + '.json');private(p, readonly=True)
            with p.open('rb') as f:body = f.read(MAX_RAW + 1)
            need(len(body) <= MAX_RAW and digest(body) == raw_hash, 'raw-integrity-failed')
            return body
        return safe(read)

    def _archive(self, raw, raw_hash):
        self._paths()
        p = self.raw_dir / (raw_hash + '.json')
        if p.exists() or p.is_symlink():self.raw(raw_hash);return
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
        with os.fdopen(fd, 'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        fd = os.open(self.raw_dir, os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def ingest(self, request, response, *, run_id, observed_at, ingested_at, origin='trusted-capture'):
        def append():
            need(origin in ('synthetic', 'trusted-capture'))
            need(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id))
            with self._connection(readonly=True):pass
            observed, ingested = aware_ms(observed_at, True), aware_ms(ingested_at, True)
            need(ingested >= observed and parse_aware(ingested_at) >= parse_aware(observed_at))
            kind, query, secrets = request_meta(request)
            need(isinstance(response, ReadResponse) and type(response.status) is int
                 and (response.status == 0 or 100 <= response.status <= 599))
            version=2 if kind=='snapshot' else 1
            records, raw_hash, raw = [], None, None
            reason = None
            if response.status != 200:
                status, reason = 'failed', 'transport-failed' if response.status == 0 else 'http-failed'
            else:
                valid = False
                try:
                    need(isinstance(response.body, bytes) and 0 < len(response.body) <= MAX_RAW)
                    records = normalized(response.body, kind, query, secrets, version=version)
                    valid = True
                except Exception:
                    pass
                if not valid:
                    status, reason = 'failed', 'invalid-response'
                    records = []
                else:
                    raw, raw_hash = response.body, digest(response.body)
                    status = 'success' if records else 'successful-empty' if kind == 'news' else 'all-missing'
                    if kind == 'snapshot' and records and len(records) < len(query['codes']):status = 'partial'
            missing = [code for code in query.get('codes', []) if not any(json.loads(r[1])['code'] == code for r in records)]
            meta = {'origin': origin, 'capture_authenticity': 'caller-supplied-unverified', 'provider': 'moomoo-rest', 'run_id': run_id, 'kind': kind, 'query': query,
                    'observed_at': observed_at, 'ingested_at': ingested_at, 'observed_ms': observed, 'ingested_ms': ingested, 'known_ms': max(observed, ingested),
                    'raw_hash': raw_hash, 'status': status, 'reason': reason, 'missing_codes': missing,
                    'unsupported_markets': {'MY': 'unattempted-unsupported'}, 'record_count': len(records),
                    'rights_status': 'unconfirmed', 'connector': 'moomoo-rest-capture', 'endpoint': request.path}
            if kind=='snapshot':meta['normalization_version']=version
            attempt_id = digest(canonical(meta).encode())
            if raw is not None:self._archive(raw, raw_hash)
            with self._connection() as db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('SELECT 1 FROM attempts WHERE id=?', (attempt_id,)).fetchone():return StoredAttempt(attempt_id, status, False, raw_hash)
                db.execute('INSERT OR IGNORE INTO runs VALUES (?,?)', (run_id, 'moomoo-rest'))
                db.execute('INSERT INTO attempts VALUES (?,?,?,?,?)', (attempt_id, run_id, kind, meta['known_ms'], canonical(meta)))
                for ordinal, (identity, payload, source) in enumerate(records):
                    hashed = digest(payload.encode())
                    existing = db.execute('SELECT id FROM versions WHERE kind=? AND identity=? AND semantic_hash=?', (kind, identity, hashed)).fetchone()
                    if existing:version_id = existing[0]
                    else:
                        revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM versions WHERE kind=? AND identity=?', (kind, identity)).fetchone()[0]
                        version_id = db.execute('INSERT INTO versions(kind,identity,semantic_hash,revision,payload,source_ms) VALUES (?,?,?,?,?,?)', (kind, identity, hashed, revision, payload, source)).lastrowid
                    db.execute('INSERT INTO observations VALUES (?,?,?)', (attempt_id, version_id, ordinal))
            return StoredAttempt(attempt_id, status, True, raw_hash)
        return safe(append)

    @staticmethod
    def _meta(row):
        meta = json.loads(row['metadata'])
        need(digest(canonical(meta).encode()) == row['id'] and meta['known_ms'] == row['known_ms']
             and meta['known_ms'] == max(meta['observed_ms'], meta['ingested_ms'])
             and meta['observed_ms'] == aware_ms(meta['observed_at'], True) and meta['ingested_ms'] == aware_ms(meta['ingested_at'], True)
             and meta['run_id'] == row['run_id'] and meta['kind'] == row['kind'], 'database-integrity-failed')
        version=meta.get('normalization_version',1)
        need(type(version) is int and version in (1,2)
             and (meta['kind']=='snapshot' or version==1), 'database-integrity-failed')
        return meta

    def attempts(self, cutoff, *, limit=1000):
        def query():
            stamp = aware_ms(cutoff);need(type(limit) is int and 1 <= limit <= 1000)
            with self._connection(readonly=True) as db:
                result = []
                for row in db.execute('SELECT * FROM attempts WHERE known_ms<=? ORDER BY known_ms,id LIMIT ?', (stamp, limit)):
                    meta = self._meta(row)
                    if meta['raw_hash'] is not None:self.raw(meta['raw_hash'])
                    result.append(meta)
                return result
        return safe(query)

    def query(self, kind, cutoff, *, mode='strict', limit=1000):
        def read():
            need(kind in ('snapshot', 'news') and mode in ('strict', 'observation-known'))
            stamp = aware_ms(cutoff);need(type(limit) is int and 1 <= limit <= 1000)
            sql = '''SELECT v.*,a.id AS aid,a.run_id,a.kind AS akind,a.known_ms,a.metadata,o.ordinal
                FROM versions v JOIN observations o ON o.version_id=v.id JOIN attempts a ON a.id=o.attempt_id
                WHERE v.kind=? AND a.known_ms<=? AND (v.source_ms<=? OR (v.source_ms IS NULL AND ?='observation-known'))
                ORDER BY v.identity,v.revision,a.known_ms,a.id LIMIT ?'''
            result = []
            with self._connection(readonly=True) as db:
                for row in db.execute(sql, (kind, stamp, stamp, mode, limit)):
                    meta = self._meta({'id': row['aid'], 'run_id': row['run_id'], 'kind': row['akind'], 'known_ms': row['known_ms'], 'metadata': row['metadata']})
                    need(row['semantic_hash'] == digest(row['payload'].encode()), 'database-integrity-failed')
                    record = json.loads(row['payload'])
                    exact = normalized(self.raw(meta['raw_hash']), kind, meta['query'], version=meta.get('normalization_version',1))
                    need(0 <= row['ordinal'] < len(exact) and exact[row['ordinal']] == (row['identity'], row['payload'], row['source_ms']), 'database-integrity-failed')
                    quality = ['availability_unknown'] if kind == 'news' else ['currency_unknown', 'session_unknown', 'adjustment_unknown', 'point_observation_not_bar']
                    if row['source_ms'] is None:quality.append('source_time_unknown')
                    elif row['source_ms'] > aware_ms(meta['observed_at']):quality.append('source_time_after_observation')
                    if kind == 'snapshot' and record['price'] == 0:quality.append('price_unusable')
                    result.append({'record': record, 'revision': row['revision'], 'semantic_hash': row['semantic_hash'],
                                   'observation': meta, 'quality': quality, 'view': mode, 'source_ms': row['source_ms'],
                                   'eligible_for_temporal_evidence': row['source_ms'] is not None and row['source_ms'] <= aware_ms(meta['observed_at']) and (kind != 'snapshot' or record['price'] > 0)})
            return result
        return safe(read)


    def select_snapshots(self, run_id, cutoff, expected_codes):
        """Complete as-of run view, bounded selection; not a run completion claim."""
        def select():
            need(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id))
            stamp = aware_ms(cutoff)
            request = ReadRequest('POST', '/api/v1.0/quote/snapshot', '',
                                  canonical({'code_list': expected_codes}).encode(), {}, 1)
            _, universe, _ = request_meta(request)
            codes = universe['codes'];expected = set(codes)
            requested, returned, eligible = set(), set(), set()
            statuses = dict.fromkeys(('success', 'partial', 'all-missing', 'failed'), 0)
            quality = ['currency_unknown', 'session_unknown', 'adjustment_unknown',
                       'prior_close_unknown', 'point_observation_not_bar']
            states = {code: {'candidate': None, 'excluded': {}} for code in codes}
            with self._connection(readonly=True) as db:
                db.execute('BEGIN')
                attempts = db.execute("SELECT * FROM attempts WHERE run_id=? AND kind='snapshot' AND known_ms<=? ORDER BY known_ms,id", (run_id, stamp))
                run_checked = False
                for attempt in attempts:
                    if not run_checked:
                        run = db.execute('SELECT provider FROM runs WHERE id=?', (run_id,)).fetchone()
                        need(run is not None and run['provider'] == 'moomoo-rest', 'database-integrity-failed')
                        run_checked = True
                    meta = self._meta(attempt)
                    need(isinstance(meta['query'], dict) and set(meta['query']) == {'codes'},
                         'database-integrity-failed')
                    _, query, _ = request_meta(ReadRequest('POST', '/api/v1.0/quote/snapshot', '',
                        canonical({'code_list': meta['query']['codes']}).encode(), {}, 1))
                    need(set(query['codes']) == expected, 'universe-mismatch')
                    need(meta['ingested_ms'] >= meta['observed_ms']
                         and parse_aware(meta['ingested_at']) >= parse_aware(meta['observed_at'])
                         and meta['origin'] in ('synthetic', 'trusted-capture')
                         and meta['capture_authenticity'] == 'caller-supplied-unverified'
                         and meta['rights_status'] == 'unconfirmed'
                         and meta['provider'] == 'moomoo-rest'
                         and meta['connector'] == 'moomoo-rest-capture'
                         and meta['endpoint'] == '/api/v1.0/quote/snapshot', 'database-integrity-failed')
                    requested.update(query['codes'])
                    records = [] if meta['raw_hash'] is None else normalized(self.raw(meta['raw_hash']), 'snapshot', query, version=meta.get('normalization_version',1))
                    count = len(records)
                    status = ('failed' if meta['raw_hash'] is None else 'all-missing' if not count
                              else 'success' if count == len(codes) else 'partial')
                    returned_codes = {json.loads(r[1])['code'] for r in records}
                    missing = [code for code in query['codes'] if code not in returned_codes]
                    need(type(meta['record_count']) is int and meta['record_count'] == count
                         and meta['status'] == status and meta['missing_codes'] == missing
                         and (meta['reason'] in ('transport-failed', 'http-failed', 'invalid-response')
                              if status == 'failed' else meta['reason'] is None),
                         'database-integrity-failed')
                    statuses[status] += 1
                    observations = db.execute("""SELECT o.ordinal,v.* FROM observations o
                        LEFT JOIN versions v ON v.id=o.version_id WHERE o.attempt_id=? ORDER BY o.ordinal""", (attempt['id'],))
                    seen = 0
                    for row in observations:
                        need(seen < count and row['ordinal'] == seen and row['kind'] == 'snapshot'
                             and row['semantic_hash'] == digest(row['payload'].encode())
                             and records[seen] == (row['identity'], row['payload'], row['source_ms']),
                             'database-integrity-failed')
                        seen += 1
                        record = json.loads(row['payload']);code = record['code'];source = row['source_ms']
                        returned.add(code)
                        reasons = []
                        if source is None:reasons.append('source_time_unknown')
                        else:
                            if source > stamp:reasons.append('source_time_after_cutoff')
                            if source > aware_ms(meta['observed_at']):reasons.append('source_time_after_observation')
                        if record['price'] <= 0:reasons.append('price_unusable')
                        state = states[code]
                        if reasons:
                            for reason in reasons:state['excluded'][reason] = state['excluded'].get(reason, 0) + 1
                            continue
                        eligible.add(code)
                        provenance = {key: meta[key] for key in ('raw_hash', 'observed_at', 'ingested_at',
                            'known_ms', 'origin', 'capture_authenticity', 'rights_status', 'provider', 'connector')}
                        provenance.update(attempt_id=attempt['id'], semantic_hash=row['semantic_hash'], source_ms=source)
                        candidate = state['candidate']
                        if candidate is None or source > candidate['source_ms']:
                            state['candidate'] = dict(source_ms=source, record=record, provenance=provenance,
                                semantic_hash=row['semantic_hash'], count=1, conflict=None)
                        elif source == candidate['source_ms']:
                            candidate['count'] += 1
                            if row['semantic_hash'] != candidate['semantic_hash'] and candidate['conflict'] is None:
                                candidate['conflict'] = provenance
                    need(seen == count, 'database-integrity-failed')
            selected, conflicted, quotes = set(), set(), {}
            for code in codes:
                state = states[code];candidate = state['candidate']
                gaps = list(quality[:4])
                entry = dict(quote=None, provenance=None, quality=list(quality), gap_reasons=gaps,
                             excluded_counts=state['excluded'], latest_observation_count=0,
                             replay_count=0, conflict_provenance=[])
                if candidate is None:
                    gaps.append('no_eligible_quote' if code in returned else
                                'no_returned_quote' if requested else 'no_available_attempts')
                else:
                    entry['latest_observation_count'] = candidate['count']
                    if candidate['conflict'] is not None:
                        conflicted.add(code);gaps.append('same_time_conflict');entry['replay_count'] = None
                        entry['conflict_provenance'] = [candidate['provenance'], candidate['conflict']]
                    else:
                        selected.add(code)
                        entry.update(quote={**candidate['record'], 'prior_close': None},
                                     provenance=candidate['provenance'], replay_count=candidate['count']-1)
                quotes[code] = entry
            groups = dict(expected=expected, requested=requested, returned=returned, eligible=eligible,
                          selected=selected, missing=expected-returned, conflicted=conflicted)
            return dict(run_id=run_id, cutoff=cutoff, view_complete=True,
                        status='available' if requested else 'no_available_attempts',
                        coverage={name: {'codes': [code for code in codes if code in group], 'count': len(group)}
                                  for name, group in groups.items()},
                        attempt_status_counts=statuses, quotes=quotes)
        return safe(select)


class CaptureTransport:
    """Explicit trusted-response capture before core decode; no default transport."""
    def __init__(self, store, transport, *, run_id, observed_clock, ingestion_clock, origin='trusted-capture'):
        self._store, self._transport, self._run = store, transport, run_id
        self._observed, self._ingested, self._origin = observed_clock, ingestion_clock, origin
    def __repr__(self):return '<PrivateMarketCapture>'
    def __call__(self, request):
        failed = False
        try:response = self._transport(request)
        except Exception:failed = True
        if failed:response = ReadResponse(0, b'')
        safe(lambda: self._store.ingest(request, response, run_id=self._run, observed_at=self._observed(), ingested_at=self._ingested(), origin=self._origin), category='capture-failed')
        if failed:raise RESTError('transport-failed')
        return response
