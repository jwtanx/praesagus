#!/usr/bin/env python3
"""Project direct-REST private captures to a private analysis file or rights-gated Pages artifact."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ingest.daily_report_projection import project_public_market_snapshot, validate_market_snapshot
from ingest.private_market_store import REPO, PrivateMarketStore, decode, private, safe
from ingest.daily_report_projection import write_private_draft

MAX_RIGHTS_BYTES = 65536
MAX_UNIVERSE_BYTES = 4 * 1024 * 1024
PUBLIC_DIRECTORY = REPO / 'artifacts/daily-market-brief/market-snapshots'


def read_rights_evidence(path: str | Path) -> dict:
    """Read a private operator evidence record; never print its path or contents."""
    target = Path(path)
    def read():
        if not target.is_absolute() or target != target.resolve() or target.is_relative_to(REPO):
            raise ValueError()
        if any(part.lower() in {'public','www','htdocs','artifacts','dist'} for part in target.parts):
            raise ValueError()
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) not in (0o400,0o600):
                raise ValueError()
            raw = os.read(fd, MAX_RIGHTS_BYTES + 1)
            if len(raw) > MAX_RIGHTS_BYTES:
                raise ValueError()
            value = json.loads(raw.decode('utf-8'))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        finally:
            os.close(fd)
    return safe(read, category='rights-evidence-unavailable')


def read_universe(path: str | Path) -> dict:
    target = Path(path)
    def read():
        raw = target.read_bytes()
        if len(raw) > MAX_UNIVERSE_BYTES:
            raise ValueError()
        value = decode(raw)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    return safe(read, category='universe-unavailable')


def write_public_snapshot(destination: str | Path, snapshot: dict) -> None:
    """Atomically add one date-keyed static file; never overwrite an artifact."""
    validate_market_snapshot(snapshot, require_rights=True)
    target = Path(destination)
    def write():
        if not target.is_absolute() or target != target.resolve():
            raise ValueError()
        if target.parent != PUBLIC_DIRECTORY.resolve() or target.name != snapshot['report_date'] + '.json':
            raise ValueError()
        PUBLIC_DIRECTORY.mkdir(mode=0o755, parents=True, exist_ok=True)
        if PUBLIC_DIRECTORY.is_symlink() or not PUBLIC_DIRECTORY.is_dir():
            raise ValueError()
        raw = (json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
        temporary = None
        try:
            fd, name = tempfile.mkstemp(prefix='.market-snapshot-', dir=PUBLIC_DIRECTORY)
            temporary = Path(name)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fchmod(stream.fileno(), 0o644)
                os.fsync(stream.fileno())
            os.link(temporary, target, follow_symlinks=False)
            dir_fd = os.open(PUBLIC_DIRECTORY, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    safe(write, category='public-snapshot-not-written')


def run(*, root: str, universe_path: str, run_id: str, cutoff: str,
        private_output: str | None = None, public_output: str | None = None,
        rights_path: str | None = None) -> dict:
    if bool(private_output) == bool(public_output):
        raise ValueError('choose one output')
    if public_output and not rights_path:
        raise ValueError('rights evidence required')
    store = PrivateMarketStore(root)
    universe = read_universe(universe_path)
    rights = read_rights_evidence(rights_path) if public_output and rights_path else None
    snapshot = project_public_market_snapshot(
        store, universe, run_id=run_id, cutoff=cutoff, rights_evidence=rights,
    )
    if private_output:
        write_private_draft(private_output, {**snapshot, 'private_draft': True})
        return {'private_analysis_written': True, 'report_date': snapshot['report_date']}
    write_public_snapshot(public_output, snapshot)
    return {'public_snapshot_written': True, 'report_date': snapshot['report_date']}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, help='existing private market-store root')
    parser.add_argument('--universe', default='artifacts/daily-market-brief/watchlist-universe-five.json')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--cutoff', required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument('--private-output', help='new private analysis file inside an owned 0700 directory')
    output.add_argument('--public-output', help='new date-keyed artifact under artifacts/daily-market-brief/market-snapshots/')
    parser.add_argument('--rights-evidence', help='private operator-provisioned market/field permission record')
    args = parser.parse_args(argv)
    if args.public_output and not args.rights_evidence:
        parser.error('public output requires --rights-evidence')
    try:
        result = run(root=args.root, universe_path=args.universe, run_id=args.run_id,
                     cutoff=args.cutoff, private_output=args.private_output,
                     public_output=args.public_output, rights_path=args.rights_evidence)
    except Exception:
        print('Market snapshot projection failed; no provider or private-path details emitted.', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
