"""Opt-in single-host invocation metadata; no provider or raw-data operations."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import sqlite3
import stat
import uuid

REPO = Path(__file__).resolve().parents[2]
DB_NAME = 'financial-runs.sqlite3'
MAX_ROWS = 1000
SCHEMA = '''
CREATE TABLE runs (
 seq INTEGER PRIMARY KEY, run_id TEXT UNIQUE NOT NULL, dataset TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, state TEXT NOT NULL,
 yielded INTEGER NOT NULL DEFAULT 0, stored INTEGER NOT NULL DEFAULT 0,
 error_code TEXT);
CREATE TABLE retention (dataset TEXT PRIMARY KEY, pruned INTEGER NOT NULL,
 floor TEXT);
PRAGMA user_version=1;
'''
ERRORS = {'input-failed', 'authenticate-failed', 'fetch-failed', 'normalize-failed',
          'store-failed', 'interrupted', 'status-unavailable'}


class StatusError(Exception):
    def __init__(self, code='status-unavailable'):
        self.code = code
        super().__init__(code)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    if not isinstance(value, str) or ('T' not in value and ' ' not in value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (ValueError, OverflowError):
        return None


def _private(path, directory=False):
    info = path.lstat()
    if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)):
        raise StatusError()


def status_root():
    value = os.getenv('PRAESAGUS_RUN_STATUS_DIR')
    if value is None:
        return None
    try:
        root = Path(value)
        if (not value or not root.is_absolute() or root != root.resolve()
                or root.is_relative_to(REPO)
                or any(p.lower() in {'public', 'www', 'htdocs', 'artifacts', 'dist'} for p in root.parts)):
            raise StatusError()
        _private(root, directory=True)
        return root
    except Exception:
        raise StatusError() from None


def _file(path):
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
    except FileExistsError:
        pass
    _private(path)


def _open_connection(root, write=False):
    path = root / DB_NAME
    try:
        _private(path)
        if path.stat().st_size > 16 * 1024 * 1024:
            raise StatusError()
        connection = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'),
                                    uri=True, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout=5000')
        if connection.execute('PRAGMA user_version').fetchone()[0] != 1:
            connection.close()
            raise StatusError()
        return connection
    except Exception:
        raise StatusError() from None


@contextmanager
def _connect(root, write=False):
    connection = _open_connection(root, write)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _initialize(root):
    path = root / DB_NAME
    # Schema initialization is writer-only, under the common initialization lock.
    _file(root / 'schema.lock')
    fd = os.open(root / 'schema.lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not path.exists():
            _file(path)
            connection = sqlite3.connect(path, timeout=5)
            try:
                connection.execute('PRAGMA max_page_count=4096')
                connection.executescript(SCHEMA)
            finally:
                connection.close()
        _private(path)
    except Exception:
        raise StatusError() from None
    finally:
        os.close(fd)


def _prune(connection, dataset):
    # Pin last success within the 1000-row total, not in addition to that bound.
    success = connection.execute("SELECT seq FROM runs WHERE dataset=? AND state='succeeded' ORDER BY seq DESC LIMIT 1", (dataset,)).fetchone()
    pin = success[0] if success else -1
    keep = [r[0] for r in connection.execute("SELECT seq FROM runs WHERE dataset=? AND state!='running' AND seq!=? ORDER BY seq DESC LIMIT ?", (dataset, pin, MAX_ROWS - (pin != -1)))]
    keep.append(pin)
    marks = ','.join('?' for _ in keep)
    deleted = connection.execute(f"SELECT seq,started_at FROM runs WHERE dataset=? AND state!='running' AND seq NOT IN ({marks}) ORDER BY seq", [dataset, *keep]).fetchall()
    if deleted:
        connection.executemany('DELETE FROM runs WHERE seq=?', [(r[0],) for r in deleted])
        connection.execute('INSERT INTO retention(dataset,pruned,floor) VALUES(?,?,?) ON CONFLICT(dataset) DO UPDATE SET pruned=pruned+excluded.pruned,floor=excluded.floor', (dataset, len(deleted), deleted[-1][1]))


class Invocation:
    def __init__(self, root, run_id):
        self.root, self.run_id = root, run_id
        self.yielded = self.stored = 0

    def finish(self, state, error_code=None, now=None):
        if state not in {'succeeded', 'partial', 'failed'} or error_code not in ERRORS | {None}:
            raise StatusError()
        if (state == 'succeeded') != (error_code is None):
            raise StatusError()
        now = now or utc_now()
        end = timestamp(now)
        try:
            with _connect(self.root, write=True) as connection:
                connection.execute('BEGIN IMMEDIATE')
                row = connection.execute('SELECT * FROM runs WHERE run_id=?', (self.run_id,)).fetchone()
                if (not row or row['state'] != 'running' or not end
                        or end < timestamp(row['started_at'])
                        or type(self.stored) is not int or type(self.yielded) is not int
                        or not 0 <= self.stored <= self.yielded <= 9223372036854775807):
                    raise StatusError()
                connection.execute('UPDATE runs SET finished_at=?,state=?,yielded=?,stored=?,error_code=? WHERE run_id=? AND state=\'running\'', (now, state, self.yielded, self.stored, error_code, self.run_id))
                _prune(connection, row['dataset'])
        except Exception:
            raise StatusError() from None


@contextmanager
def invocation(dataset='filings', now=None):
    if dataset != 'filings':
        raise StatusError()
    root = status_root()
    if root is None:
        yield None
        return
    fd = None
    try:
        _file(root / (dataset + '.lock'))
        fd = os.open(root / (dataset + '.lock'), os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StatusError('run-busy') from None
        _initialize(root)
        read_status(root)  # Existing corrupt metadata fails before ingestion work.
        started = now or utc_now()
        if not timestamp(started):
            raise StatusError()
        run_id = str(uuid.uuid4())
        with _connect(root, write=True) as connection:
            connection.execute('BEGIN IMMEDIATE')
            # Holding the writer lock proves preceding running rows have no active
            # instrumented writer. Preserve unknown termination time and evidence.
            connection.execute("UPDATE runs SET state='unknown',error_code='interrupted' WHERE dataset=? AND state='running'", (dataset,))
            _prune(connection, dataset)
            connection.execute("INSERT INTO runs(run_id,dataset,started_at,state) VALUES(?,?,?,'running')", (run_id, dataset, started))
        yield Invocation(root, run_id)
    except StatusError:
        raise
    except Exception:
        raise StatusError() from None
    finally:
        if fd is not None:
            os.close(fd)


def _read_status(root):
    """Read-only snapshot; missing DB is distinct from corruption; no initialization."""
    path = root / DB_NAME
    if not path.exists():
        return {'availability': 'absent', 'runs': [], 'retention': None}
    with _connect(root) as connection:
        connection.execute('BEGIN')
        rows = connection.execute('SELECT * FROM runs WHERE dataset=? ORDER BY seq DESC LIMIT 1001', ('filings',)).fetchall()
        retention = connection.execute('SELECT pruned,floor FROM retention WHERE dataset=?', ('filings',)).fetchone()
        result = [dict(r) for r in rows]
        for row in result:
            try:
                identifier = uuid.UUID(row['run_id'])
            except (ValueError, TypeError, AttributeError):
                raise StatusError() from None
            state, error = row['state'], row['error_code']
            terminal = state in {'succeeded', 'partial', 'failed'}
            start, end = timestamp(row['started_at']), timestamp(row['finished_at'])
            if (identifier.version != 4 or str(identifier) != row['run_id']
                    or type(row['seq']) is not int or row['seq'] <= 0
                    or state not in {'running', 'unknown', 'succeeded', 'partial', 'failed'}
                    or not start
                    or type(row['yielded']) is not int or type(row['stored']) is not int
                    or not 0 <= row['stored'] <= row['yielded'] <= 9223372036854775807
                    or (terminal and (not end or end < start))
                    or (state == 'succeeded' and error is not None)
                    or (state in {'partial', 'failed'} and error not in ERRORS)
                    or (state == 'running' and (error is not None or row['finished_at'] is not None))
                    or (state == 'unknown' and (error != 'interrupted' or row['finished_at'] is not None))):
                raise StatusError()
        if retention and (type(retention['pruned']) is not int or retention['pruned'] < 0
                          or not timestamp(retention['floor'])):
            raise StatusError()
        return {'availability': 'present', 'runs': result,
                'retention': dict(retention) if retention else {'pruned': 0, 'floor': None}}


def read_status(root):
    """Sanitized, read-only snapshot; corrupt row/query/schema never escapes."""
    try:
        return _read_status(root)
    except Exception:
        raise StatusError() from None
