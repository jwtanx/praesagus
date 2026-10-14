#!/usr/bin/env python3
"""Prepare a private normal-report forecast bundle; never fetch or publish."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ingest.forecast_scenario import _bounded
from ingest.report_forecast import prepare_report_forecast, validator, REPORT_TEMPLATE_MAX_DEPTH

MAX_JSON = 2 * 1024 * 1024
FORBIDDEN = {'public', 'www', 'htdocs', 'artifacts', 'dist'}


class PreparationCLIError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PreparationCLIError('arguments-invalid')


def _path(value):
    p = Path(value)
    if (not p.is_absolute() or p != p.resolve() or p.is_relative_to(REPO)
            or any(part.lower() in FORBIDDEN for part in p.parts)
            or any((ancestor / '.git').exists() for ancestor in p.parents)):
        raise PreparationCLIError('private-path-invalid')
    return p


def _directory(path):
    """Open every directory without following symlinks, including ancestors."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise PreparationCLIError('private-path-invalid')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise PreparationCLIError('json-invalid')
        result[key] = value
    return result


def _constant(value):
    raise PreparationCLIError('json-invalid')


def read_private_json(value, *, max_depth=8):
    path = _path(value)
    parent = _directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) not in (0o400, 0o600) or info.st_size > MAX_JSON):
                raise PreparationCLIError('private-input-invalid')
            raw = stream.read(MAX_JSON + 1)
        if not 0 < len(raw) <= MAX_JSON:
            raise PreparationCLIError('json-invalid')
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        if not _bounded(data,max_depth=max_depth):
            raise PreparationCLIError('json-invalid')
        # 1e999 is valid JSON syntax but must not bypass finite-value validation.
        json.dumps(data, allow_nan=False)
        return data
    finally:
        os.close(parent)


def validate_prepared(report, universe, calendar, private_parent):
    keys, mapping = validator.validate_universe(Path('universe.json'), universe)
    context = (universe['effective_from'], keys, mapping, universe['taxonomy_id'], universe['groups'])
    if universe['effective_from'] > report['metadata']['date']:
        raise PreparationCLIError('universe-not-current')
    month = report['metadata']['date'][:7]
    with tempfile.TemporaryDirectory(prefix='.forecast-validation-', dir=private_parent) as temporary:
        root = Path(temporary)
        (root / 'financial-calendar').mkdir(mode=0o700)
        (root / 'daily-market-brief').mkdir(mode=0o700)
        _calendar = root / 'financial-calendar' / (month + '.json')
        _calendar.write_text(json.dumps(calendar, allow_nan=False), encoding='utf-8')
        _calendar.chmod(0o600)
        validator.validate_report(root / 'daily-market-brief' / (report['metadata']['date'] + '.json'),
                                  report, context, public=True, compact=True)


def _write_file(directory_fd, name, value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()
    if len(raw) > MAX_JSON:
        raise PreparationCLIError('output-too-large')
    temporary = '.' + name + '.pending'
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), 0o600); os.fsync(stream.fileno())
        os.link(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
    finally:
        os.unlink(temporary, dir_fd=directory_fd)


def write_bundle(path, result):
    """No replacement; each file atomic, pair not crash-atomic. Roll back errors."""
    parent = _directory(path.parent)
    directory = None
    created = False
    created_info = None
    try:
        os.mkdir(path.name, mode=0o700, dir_fd=parent); created = True
        created_info = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        directory = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        _write_file(directory, 'audit.json', result['audit'])
        _write_file(directory, 'prepared-report.json', result['report'])
        os.fsync(directory); os.fsync(parent)
    except BaseException:
        if directory is not None:
            for name in ('audit.json', 'prepared-report.json', '.audit.json.pending', '.prepared-report.json.pending'):
                try:os.unlink(name, dir_fd=directory)
                except FileNotFoundError:pass
        if created:
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            owned = os.fstat(directory) if directory is not None else created_info
            if owned is not None and (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                os.rmdir(path.name, dir_fd=parent)
        raise
    finally:
        if directory is not None:os.close(directory)
        os.close(parent)


def main(argv=None):
    stage = 'arguments-invalid'
    try:
        parser = Parser(description=__doc__)
        for name in ('template', 'universe', 'calendar', 'issued-at', 'cutoff', 'output-directory'):
            parser.add_argument('--' + name, required=True)
        parser.add_argument('--evidence'); parser.add_argument('--admission')
        parser.add_argument('--template-reviewed', action='store_true')
        args = parser.parse_args(argv)
        if bool(args.evidence) != bool(args.admission):
            raise PreparationCLIError('arguments-invalid')
        stage = 'private-input-invalid'
        template, universe, calendar = (read_private_json(getattr(args,name),max_depth=REPORT_TEMPLATE_MAX_DEPTH if name=='template' else 8)
                                       for name in ('template','universe','calendar'))
        evidence = read_private_json(args.evidence) if args.evidence else None
        admission = read_private_json(args.admission) if args.admission else None
        output = _path(args.output_directory)
        fd = _directory(output.parent); os.close(fd)
        if output.exists() or output.is_symlink():
            raise PreparationCLIError('output-exists')
        stage = 'preparation-invalid'
        result = prepare_report_forecast(template, evidence=evidence, admission=admission,
                                         issued_at=args.issued_at, report_cutoff=args.cutoff,
                                         template_reviewed=args.template_reviewed)
        stage = 'report-validation-failed'
        validate_prepared(result['report'], universe, calendar, output.parent)
        stage = 'private-write-failed'
        write_bundle(output, result)
        print(json.dumps(dict(status='prepared' if result['status']=='generated' else 'withheld',
                              reasons=result['reasons'], forecast_generated_count=int(result['status']=='generated'))))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError):
        # Never interpolate paths, provider/user values or underlying exceptions.
        print(json.dumps(dict(status='failed', reason=stage)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
