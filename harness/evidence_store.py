"""Synthetic-only offline evidence ledger. See EVIDENCE_STORE.md for the contract."""
import argparse
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EvidenceError(ValueError):
    """Invalid input, unavailable storage, or evidence integrity failure."""


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise EvidenceError(field + ' requires nonempty text of at most 512 characters')
    return value


def _time(value, field, nullable=False):
    if value is None and nullable:
        return None
    try:
        if not isinstance(value, str) or 'T' not in value:
            raise ValueError()
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            raise ValueError()
        return parsed.timestamp()
    except (ValueError, OverflowError, OSError):
        raise EvidenceError(field + ' requires an aware ISO timestamp') from None


def _date(value, field):
    try:
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError()
        date.fromisoformat(value)
    except ValueError:
        raise EvidenceError(field + ' requires YYYY-MM-DD') from None
    return value


def _zone(value, field):
    _text(value, field)
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise EvidenceError(field + ' requires an IANA timezone') from None


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _number(value, field, positive=True):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and not (value <= 0 if positive else value < 0)
    except OverflowError:
        valid = False
    if not valid:
        raise EvidenceError(field + ' requires a finite ' + ('positive' if positive else 'nonnegative') + ' number')
    return value


def _object_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceError('duplicate JSON key')
        obj[key] = value
    return obj


def _reject_constant(value):
    raise EvidenceError('nonfinite JSON number')


def _validate(raw):
    if not isinstance(raw, bytes):
        raise EvidenceError('ingest requires exact JSON bytes')
    try:
        batch = json.loads(raw.decode('utf-8'), object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise EvidenceError('invalid UTF-8 JSON batch') from None
    if not isinstance(batch, dict) or type(batch.get('schema_version')) is not int or batch['schema_version'] != 1:
        raise EvidenceError('unsupported batch schema version')
    if batch.get('origin') != 'synthetic':
        raise EvidenceError('only explicitly synthetic batches are supported')
    try:
        _json(batch).encode('utf-8')  # Reject nonfinite metadata and lone surrogates.
    except (ValueError, OverflowError, RecursionError, UnicodeError):
        raise EvidenceError('batch contains nonfinite or unsupported JSON values') from None
    provider = _text(batch.get('provider'), 'provider')
    _text(batch.get('run_id'), 'run_id')
    retrieved = _time(batch.get('retrieved_at'), 'retrieved_at')
    ingested = _time(batch.get('ingested_at'), 'ingested_at')
    if ingested < retrieved:
        raise EvidenceError('ingestion cannot precede retrieval')
    rights = batch.get('rights')
    if not isinstance(rights, dict) or rights.get('status') != 'synthetic-only':
        raise EvidenceError('rights.status must be synthetic-only')
    run = batch.get('run')
    if not isinstance(run, dict) or run.get('status') not in {'success', 'successful-empty', 'partial', 'failed'}:
        raise EvidenceError('invalid collection run status')
    _date(run.get('session'), 'run.session')
    universe = run.get('universe')
    if not isinstance(universe, list) or not universe or len(set(_text(x, 'universe instrument') for x in universe)) != len(universe):
        raise EvidenceError('run.universe requires unique instrument names')
    error = run.get('error_reason')
    if run['status'] in {'partial', 'failed'}:
        _text(error, 'error_reason')
    elif error is not None:
        raise EvidenceError('successful run cannot declare an error')
    for kind in ('bars', 'news'):
        if not isinstance(batch.get(kind), list):
            raise EvidenceError(kind + ' must be an explicit list')
    count = len(batch['bars']) + len(batch['news'])
    if run['status'] in {'failed', 'successful-empty'} and count:
        raise EvidenceError('failed/empty run cannot contain records')
    if run['status'] == 'success' and not count:
        raise EvidenceError('zero records require successful-empty status')
    versions = []
    for kind in ('bars', 'news'):
        for ordinal, record in enumerate(batch[kind]):
            if not isinstance(record, dict):
                raise EvidenceError('record must be an object')
            observed = _time(record.get('observed_at'), 'observed_at')
            if observed != retrieved:
                raise EvidenceError('record observation must equal batch retrieval')
            payload = {k: v for k, v in record.items() if k != 'observed_at'}
            if kind == 'bars':
                instrument = _text(record.get('instrument'), 'instrument')
                if instrument not in universe:
                    raise EvidenceError('bar instrument outside declared universe')
                for field in ('venue', 'adjustment_basis', 'currency'):
                    _text(record.get(field), field)
                zone = _zone(record.get('exchange_timezone'), 'exchange_timezone')
                session = _date(record.get('session'), 'session')
                if session != run['session']:
                    raise EvidenceError('bar session differs from collection session')
                if record.get('interval') != '1d' or record.get('session_type') != 'regular' or record.get('completed') is not True:
                    raise EvidenceError('only completed regular daily bars are supported; snapshots rejected')
                bar_at = _time(record.get('bar_at'), 'bar_at')
                complete = _time(record.get('completed_at'), 'completed_at')
                available = _time(record.get('available_at'), 'available_at')
                if not bar_at <= complete <= available <= observed:
                    raise EvidenceError('bar completion/availability violates observation order')
                if datetime.fromtimestamp(bar_at, zone).date().isoformat() != session:
                    raise EvidenceError('bar time differs from exchange-local session date')
                for field in ('open', 'high', 'low', 'close'):
                    _number(record.get(field), field)
                _number(record.get('volume'), 'volume', positive=False)
                if not record['low'] <= min(record['open'], record['close']) <= max(record['open'], record['close']) <= record['high']:
                    raise EvidenceError('invalid OHLC price ordering')
                if not isinstance(record.get('corporate_actions'), dict):
                    raise EvidenceError('corporate_actions metadata must be explicit object')
                _text(record.get('source_version'), 'source_version')
                identity = [provider, instrument, record['venue'], '1d', session, record['adjustment_basis'], bar_at]
                temporal = {'available_at': available, 'publication_at': None, 'flags': []}
            else:
                _text(record.get('item_id'), 'item_id')
                if record.get('source_tier') not in {'primary', 'secondary', 'vendor', 'social', 'unknown'}:
                    raise EvidenceError('explicit source_tier required')
                instruments = record.get('instruments')
                if not isinstance(instruments, list) or not instruments or any(not isinstance(x, str) or x not in universe for x in instruments):
                    raise EvidenceError('news instruments must belong to declared universe')
                for field in ('publication_raw', 'publication_timezone', 'publication_at', 'provider_available_at', 'event_cluster', 'url'):
                    if field not in record:
                        raise EvidenceError('news requires explicit nullable ' + field)
                for field in ('publication_raw', 'publication_timezone', 'event_cluster'):
                    if record[field] is not None:
                        _text(record[field], field)
                pub = _time(record['publication_at'], 'publication_at', nullable=True)
                available = _time(record['provider_available_at'], 'provider_available_at', nullable=True)
                if pub is not None and (record['publication_raw'] is None or record['publication_timezone'] is None):
                    raise EvidenceError('parsed publication requires raw timestamp and timezone')
                if record['publication_timezone'] is not None:
                    _zone(record['publication_timezone'], 'publication_timezone')
                url = record['url']
                if url is not None:
                    if not isinstance(url, str):
                        raise EvidenceError('news URL must be public HTTPS or null')
                    parsed = urlsplit(url)
                    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(x.isspace() for x in url):
                        raise EvidenceError('news URL must be public HTTPS or null')
                if not isinstance(record.get('content'), str):
                    raise EvidenceError('news content must be explicit text')
                content_hash = _hash(record['content'].encode('utf-8'))
                if record.get('content_hash') != content_hash:
                    raise EvidenceError('news content hash mismatch')
                _text(record.get('source_version'), 'source_version')
                flags = []
                if pub is None:
                    flags.append('publication_unknown')
                if available is None:
                    flags.append('availability_unknown')
                if pub is not None and pub > observed:
                    flags.append('publication_future')
                if available is not None and available > observed:
                    flags.append('availability_future')
                if pub is not None and available is not None and pub > available:
                    flags.append('publication_after_availability')
                # An offset/raw timestamp disagreement is retained and excluded, not repaired.
                if pub is not None:
                    try:
                        raw_pub = _time(record['publication_raw'], 'publication_raw')
                    except EvidenceError:
                        try:
                            local = datetime.fromisoformat(record['publication_raw'])
                            raw_pub = local.replace(tzinfo=ZoneInfo(record['publication_timezone'])).timestamp() if local.tzinfo is None else None
                        except (ValueError, OverflowError, OSError):
                            raw_pub = None  # Unparseable provider text is retained unchanged.
                    if raw_pub is not None and raw_pub != pub:
                        flags.append('publication_contradiction')
                identity = [provider, record['item_id']]
                temporal = {'available_at': available, 'publication_at': pub, 'flags': flags}
            versions.append((kind, ordinal, identity, payload, observed, temporal))
    return batch, versions


class EvidenceStore:
    """Private append-only synthetic ledger; each public operation closes its connection."""

    def __init__(self, root, lock_timeout=1.0):
        requested = Path(root).expanduser()
        if requested.is_symlink():
            raise EvidenceError('storage root must not be a symlink')
        self.root = requested.resolve()
        repo = Path(__file__).resolve().parents[1]
        if self.root == repo or repo in self.root.parents:
            raise EvidenceError('generated storage must be outside the repository')
        if type(lock_timeout) not in (int, float) or not 0 <= lock_timeout <= 5 or not math.isfinite(lock_timeout):
            raise EvidenceError('lock_timeout must be between zero and five seconds')
        self.lock_timeout = lock_timeout
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._private(self.root, directory=True)
        self.raw_dir = self.root / 'raw'
        self.raw_dir.mkdir(mode=0o700, exist_ok=True)
        self._private(self.raw_dir, directory=True)
        self.database = self.root / 'evidence.sqlite3'
        try:
            fd = os.open(self.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        self._private(self.database)
        with self._connection(initializing=True) as db:
            db.execute('BEGIN IMMEDIATE')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if version == 0 and not tables:
                db.execute('CREATE TABLE batches (raw_hash TEXT PRIMARY KEY, metadata TEXT NOT NULL)')
                db.execute('CREATE TABLE runs (id INTEGER PRIMARY KEY, provider TEXT NOT NULL, run_id TEXT NOT NULL, revision INTEGER NOT NULL, raw_hash TEXT NOT NULL REFERENCES batches, payload TEXT NOT NULL, UNIQUE(provider, run_id, revision), UNIQUE(raw_hash))')
                for table in ('bars', 'news'):
                    db.execute('CREATE TABLE ' + table + ' (id INTEGER PRIMARY KEY, identity TEXT NOT NULL, version_hash TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, available_at REAL, publication_at REAL, flags TEXT NOT NULL, UNIQUE(identity, version_hash), UNIQUE(identity, revision))')
                db.execute('CREATE TABLE observations (kind TEXT NOT NULL, version_id INTEGER NOT NULL, raw_hash TEXT NOT NULL REFERENCES batches, ordinal INTEGER NOT NULL, observed_at REAL NOT NULL, ingested_at REAL NOT NULL, known_at REAL NOT NULL, UNIQUE(raw_hash, kind, ordinal))')
                db.execute('CREATE INDEX observation_version ON observations(kind, version_id, known_at)')
                db.execute('PRAGMA user_version=1')
            elif version != 1 or tables != {'batches', 'runs', 'bars', 'news', 'observations'}:
                raise EvidenceError('unsupported or damaged database schema; no reset performed')
            expected = {
                'batches': {'raw_hash', 'metadata'},
                'runs': {'id', 'provider', 'run_id', 'revision', 'raw_hash', 'payload'},
                'bars': {'id', 'identity', 'version_hash', 'revision', 'payload', 'available_at', 'publication_at', 'flags'},
                'news': {'id', 'identity', 'version_hash', 'revision', 'payload', 'available_at', 'publication_at', 'flags'},
                'observations': {'kind', 'version_id', 'raw_hash', 'ordinal', 'observed_at', 'ingested_at', 'known_at'},
            }
            for table, columns in expected.items():
                if {row['name'] for row in db.execute('PRAGMA table_info(' + table + ')')} != columns:
                    raise EvidenceError('unsupported or damaged database columns; no reset performed')

    @staticmethod
    def _private(path, directory=False):
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) if directory else not stat.S_ISREG(info.st_mode)) or info.st_mode & 0o077:
            raise EvidenceError('storage must use private regular files/directories, without symlinks')

    @contextmanager
    def _connection(self, initializing=False):
        self._private(self.database)
        db = None
        try:
            db = sqlite3.connect(self.database, timeout=self.lock_timeout)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            if db.execute('PRAGMA user_version').fetchone()[0] not in ((0, 1) if initializing else (1,)):
                raise EvidenceError('unsupported database schema')
            yield db
            db.commit()
        except sqlite3.Error:
            if db is not None:
                db.rollback()
            raise EvidenceError('database operation failed (locked, invalid schema, or unavailable storage)') from None
        except Exception:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()

    def raw(self, raw_hash):
        """Read and verify exact original bytes; never silently skip damaged evidence."""
        if not isinstance(raw_hash, str) or len(raw_hash) != 64 or any(c not in '0123456789abcdef' for c in raw_hash):
            raise EvidenceError('invalid raw hash')
        self._private(self.raw_dir, directory=True)
        path = self.raw_dir / (raw_hash + '.json')
        try:
            self._private(path)
            raw = path.read_bytes()
        except OSError:
            raise EvidenceError('referenced raw batch is missing or unreadable') from None
        if _hash(raw) != raw_hash:
            raise EvidenceError('raw batch hash verification failed')
        return raw

    def _write_raw(self, raw, digest):
        self._private(self.raw_dir, directory=True)
        path = self.raw_dir / (digest + '.json')
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            self.raw(digest)
            return
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o400)
        # Persist directory entry before committing database references.
        directory_fd = os.open(self.raw_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def ingest(self, raw):
        """Validate a full bytes batch, archive raw, then atomically append its references."""
        batch, versions = _validate(raw)
        digest = _hash(raw)
        self._write_raw(raw, digest)
        counts = {'raw_hash': digest, 'batches_added': 0, 'runs_added': 0,
                  'bar_versions_added': 0, 'news_versions_added': 0, 'observations_added': 0}
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM batches WHERE raw_hash=?', (digest,)).fetchone():
                return counts
            metadata = {k: v for k, v in batch.items() if k not in ('bars', 'news')}
            db.execute('INSERT INTO batches VALUES (?, ?)', (digest, _json(metadata)))
            counts['batches_added'] = 1
            revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM runs WHERE provider=? AND run_id=?', (batch['provider'], batch['run_id'])).fetchone()[0]
            db.execute('INSERT INTO runs(provider,run_id,revision,raw_hash,payload) VALUES (?,?,?,?,?)', (batch['provider'], batch['run_id'], revision, digest, _json(batch['run'])))
            counts['runs_added'] = 1
            ingested = _time(batch['ingested_at'], 'ingested_at')
            for kind, ordinal, identity, payload, observed, temporal in versions:
                identity_json = _json(identity)
                version_hash = _hash(_json(payload).encode('utf-8'))
                existing = db.execute('SELECT id FROM ' + kind + ' WHERE identity=? AND version_hash=?', (identity_json, version_hash)).fetchone()
                if existing:
                    version_id = existing['id']
                else:
                    revision = db.execute('SELECT COALESCE(MAX(revision),0)+1 FROM ' + kind + ' WHERE identity=?', (identity_json,)).fetchone()[0]
                    cursor = db.execute('INSERT INTO ' + kind + '(identity,version_hash,revision,payload,available_at,publication_at,flags) VALUES (?,?,?,?,?,?,?)', (identity_json, version_hash, revision, _json(payload), temporal['available_at'], temporal['publication_at'], _json(temporal['flags'])))
                    version_id = cursor.lastrowid
                    counts[('bar' if kind == 'bars' else 'news') + '_versions_added'] += 1
                db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?)', (kind, version_id, digest, ordinal, observed, ingested, max(observed, ingested)))
                counts['observations_added'] += 1
        return counts

    def versions(self, kind, as_of=None, historical=False):
        """Return version history. Historical mode explicitly labels ineligible evidence."""
        if kind not in {'bars', 'news'}:
            raise EvidenceError('kind must be bars or news')
        cutoff = _time(as_of, 'as_of') if as_of is not None else None
        result = []
        with self._connection() as db:
            for row in db.execute('SELECT * FROM ' + kind + ' ORDER BY identity,revision'):
                observations = [dict(o) for o in db.execute('SELECT * FROM observations WHERE kind=? AND version_id=? ORDER BY known_at,raw_hash,ordinal', (kind, row['id']))]
                if not observations:
                    raise EvidenceError('version has no observation provenance')
                for observation in observations:
                    self.raw(observation['raw_hash'])
                flags = json.loads(row['flags'])
                known = min(o['known_at'] for o in observations)
                eligible = not flags and row['available_at'] is not None and (cutoff is None or (known <= cutoff and row['available_at'] <= cutoff))
                if not historical and not eligible:
                    continue
                # A replay at cutoff never reveals later observations of an eligible version.
                visible = observations if historical or cutoff is None else [o for o in observations if o['known_at'] <= cutoff]
                result.append({'identity': json.loads(row['identity']), 'revision': row['revision'],
                               'version_hash': row['version_hash'], 'record': json.loads(row['payload']),
                               'first_observed_at': min(o['observed_at'] for o in visible),
                               'first_known_at': known, 'observations': visible, 'flags': flags,
                               'eligible': eligible, 'view': 'historical-explanation' if historical else 'as-of-evidence'})
        return result

    def runs(self, as_of=None):
        """Stored coverage attempts only; absent runs never mean successful-empty."""
        cutoff = _time(as_of, 'as_of') if as_of is not None else None
        result = []
        with self._connection() as db:
            for row in db.execute('SELECT * FROM runs ORDER BY provider,run_id,revision'):
                raw = self.raw(row['raw_hash'])
                batch = json.loads(raw)
                known = max(_time(batch['retrieved_at'], 'retrieved_at'), _time(batch['ingested_at'], 'ingested_at'))
                if cutoff is None or known <= cutoff:
                    result.append({'provider': row['provider'], 'run_id': row['run_id'], 'revision': row['revision'], 'raw_hash': row['raw_hash'], 'retrieved_at': batch['retrieved_at'], 'ingested_at': batch['ingested_at'], 'rights': batch['rights'], **json.loads(row['payload'])})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path, help='private storage outside repository')
    sub = parser.add_subparsers(dest='command', required=True)
    ingest = sub.add_parser('ingest')
    ingest.add_argument('batch', type=Path)
    query = sub.add_parser('query')
    query.add_argument('kind', choices=('bars', 'news', 'runs'))
    query.add_argument('--as-of', required=True)
    query.add_argument('--historical', action='store_true')
    args = parser.parse_args()
    try:
        store = EvidenceStore(args.root)
        if args.command == 'ingest':
            result = store.ingest(args.batch.read_bytes())
        elif args.kind == 'runs':
            if args.historical:
                raise EvidenceError('runs do not support historical explanation mode')
            result = store.runs(args.as_of)
        else:
            result = store.versions(args.kind, args.as_of, args.historical)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    except (EvidenceError, OSError):
        parser.exit(2, 'Evidence operation rejected; check synthetic schema, timestamps and private storage integrity.\n')


if __name__ == '__main__':
    main()
