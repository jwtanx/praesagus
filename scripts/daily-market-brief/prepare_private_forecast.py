#!/usr/bin/env python3
"""Export admitted private-only research scenarios; never fetch, fit or publish."""
from copy import deepcopy
import csv
import hashlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from ingest.forecast_scenario import (build_private_forecast_scenario, PRIVATE_PURPOSE,
    PRIVATE_RESULT_KEYS, _bounded, _hash, _row_identity, _time)

# Reuse the reviewed private reader/path/descriptor-safe JSON writer. No public
# calculator, report mapper, public validation or report output is called.
_spec = importlib.util.spec_from_file_location('_private_forecast_io', Path(__file__).with_name('prepare_forecast_report.py'))
private_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(private_io)
MAX_ITEMS = 50
MAX_BYTES = private_io.MAX_JSON
IDENTITY = ('ticker', 'market', 'currency')
NOTICE = ('Private research only. Uncalibrated next-close model range, not whole-window '
          'intraday extrema or measured 95 percent coverage. Not executable prices. '
          'Declared reviews/hashes do not authenticate sources or reviewers; public use is not granted.')
COLUMNS = ('purpose', 'ticker', 'market', 'currency', 'status', 'reasons', 'classification', 'is_demo',
    'reference_session', 'reference_close_at', 'reference_close', 'target_session', 'target_close_at',
    'issued_at', 'report_cutoff', 'point', 'low', 'high', 'direction', 'method_id', 'observations',
    'horizon_sessions', 'calibration_status', 'range_scope', 'mu', 'sample_sd', 'provider', 'source_url',
    'public_derived_forecast', 'evidence_sha256', 'admission_sha256', 'result_sha256')


class PrivateForecastExportError(ValueError):
    def __init__(self):
        super().__init__('private-forecast-export-invalid-input')


def need(value):
    if not value:
        raise PrivateForecastExportError()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def _identity(evidence):
    need(type(evidence) is dict and type(evidence.get('instrument')) is dict)
    identity = {k: evidence['instrument'].get(k) for k in IDENTITY}
    need(_row_identity(identity))
    schema = evidence.get('schema_version')
    need(type(schema) is int and schema in (1, 2, 3))
    need(schema == 3 or identity == dict(ticker='SPY', market='US', currency='USD'))
    return identity


def _inputs(payload, batch_mode):
    """Preflight every identity/purpose/binding before any scenario calculation."""
    if batch_mode:
        need(_bounded(payload, max_depth=12) and len(encoded(payload)) <= MAX_BYTES)
        need(type(payload) is dict and set(payload) == {'schema_version', 'items'}
             and type(payload['schema_version']) is int and payload['schema_version'] == 1
             and type(payload['items']) is list and len(payload['items']) <= MAX_ITEMS)
        items = payload['items']
    else:
        need(type(payload) is dict and set(payload) == {'evidence', 'admission'})
        need(all(_bounded(value) for value in payload.values()))
        items = [dict(_identity(payload['evidence']), **payload)]
    seen = set()
    for item in items:
        need(type(item) is dict and set(item) == set(IDENTITY) | {'evidence', 'admission'})
        identity = {k: item[k] for k in IDENTITY}
        need(_row_identity(identity))
        key = (identity['ticker'], identity['market'])
        need(key not in seen); seen.add(key)
        evidence, admission = item['evidence'], item['admission']
        if evidence is not None:
            need(_identity(evidence) == identity)
        if admission is not None:
            # A public admission is never converted into private-purpose permission.
            need(type(admission) is dict and admission.get('purpose') == PRIVATE_PURPOSE)
            if evidence is not None and 'evidence_sha256' in admission:
                need(admission['evidence_sha256'] == _hash(evidence))
    return items


def csv_cell(value):
    if value is None:
        return ''
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', "'")):
        return "'" + value
    return value  # Numeric negatives remain numbers, not escaped text.


def prepare_export(payload, *, batch_mode, issued_at, report_cutoff):
    """Return bounded CSV bytes and private audit; no I/O or admission creation."""
    try:
        need(type(batch_mode) is bool and _time(issued_at) <= _time(report_cutoff))
        items = _inputs(payload, batch_mode)
        rows, audits = [], []
        for item in items:
            evidence, admission = item['evidence'], item['admission']
            identity = {k: item[k] for k in IDENTITY}
            missing = [k + '_missing' for k in ('evidence', 'admission') if item[k] is None]
            result = build_private_forecast_scenario(evidence,
                admission=admission if evidence is not None else None,
                issued_at=issued_at, report_cutoff=report_cutoff)
            need(type(result) is dict and set(result) == PRIVATE_RESULT_KEYS
                 and result['purpose'] == PRIVATE_PURPOSE and result['status'] in ('generated', 'withheld'))
            generated = result['status'] == 'generated'
            if generated:
                need({k: result['instrument'][k] for k in IDENTITY} == identity)
            provenance = result['provenance'] if generated else {}
            audit = provenance.get('audit', {})
            estimates = result['estimates'] if generated else {}
            source, rights = provenance.get('source', {}), provenance.get('rights', {})
            evidence_hash = _hash(evidence) if evidence is not None else None
            admission_hash = _hash(admission) if admission is not None else None
            result_hash = _hash(result)
            reasons = sorted(set(result['reasons']) | set(missing))
            row = dict.fromkeys(COLUMNS)
            row.update(identity, purpose=PRIVATE_PURPOSE, status=result['status'], reasons=';'.join(reasons),
                classification=result['classification'], is_demo=(result['classification'] == 'fixture_only'
                    or type(evidence) is dict and evidence.get('classification') == 'authored_fixture'),
                issued_at=issued_at, report_cutoff=report_cutoff, calibration_status='uncalibrated' if generated else 'unavailable',
                range_scope='next_close_not_intraday_extrema_no_measured_95pct_coverage',
                evidence_sha256=evidence_hash, admission_sha256=admission_hash, result_sha256=result_hash)
            if generated:
                row.update({k: audit[k] for k in ('reference_session', 'reference_close_at', 'reference_close',
                    'target_session', 'target_close_at', 'observations', 'horizon_sessions')})
                row.update(direction=estimates['direction'], method_id=provenance['method']['method_id'],
                    point=f"{estimates['display_point']:.2f}", low=f"{estimates['display_low']:.2f}",
                    high=f"{estimates['display_high']:.2f}", mu=estimates['mu'], sample_sd=estimates['sample_sd'],
                    provider=source['provider'], source_url=source['source_url'],
                    public_derived_forecast=rights['public_derived_forecast'])
            rows.append(row)
            audits.append(dict(identity, input_reasons=missing, evidence_sha256=evidence_hash,
                admission_sha256=admission_hash, result_sha256=result_hash, result=deepcopy(result)))
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_cell(v) for k, v in row.items()})
        csv_bytes = stream.getvalue().encode('utf-8')
        counts = dict(total=len(rows), generated=sum(r['status'] == 'generated' for r in rows),
                      withheld=sum(r['status'] == 'withheld' for r in rows), is_demo=sum(r['is_demo'] for r in rows))
        audit = dict(schema_version=1, purpose=PRIVATE_PURPOSE, notice=NOTICE, issued_at=issued_at,
            report_cutoff=report_cutoff, input_hash_scheme='sha256-sorted-compact-ascii-json',
            input_sha256=_hash(payload), counts=counts, rows=audits)
        need(len(csv_bytes) <= MAX_BYTES and len(encoded(audit)) <= MAX_BYTES)
        return dict(csv_bytes=csv_bytes, audit=audit, counts=counts)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, UnicodeError):
        raise PrivateForecastExportError() from None


def _write_csv(directory, data):
    name = '.forecasts.csv.pending'
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fchmod(stream.fileno(), 0o600); os.fsync(stream.fileno())
        os.link(name, 'forecasts.csv', src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
    finally:
        os.unlink(name, dir_fd=directory)


def write_export(output_parent, result, *, generated_at=None):
    """Exclusive UTC generation; error rollback, not a crash-atomic three-file commit."""
    parent_path = private_io._path(output_parent)
    need(not (parent_path / '.git').exists())
    parent = private_io._directory(parent_path)
    directory = None; created = False; created_info = None
    stamp = datetime.now(timezone.utc) if generated_at is None else generated_at
    try:
        need(type(stamp) is datetime and stamp.tzinfo is not None)
        stamp = stamp.astimezone(timezone.utc)
        name = stamp.strftime('%Y-%m-%d_%H%M%S')
        os.mkdir(name, mode=0o700, dir_fd=parent); created = True
        created_info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        audit_bytes = (json.dumps(result['audit'], sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()
        manifest = dict(schema_version=1, kind='private-forecast-csv', purpose=PRIVATE_PURPOSE, created_at=stamp.isoformat(),
            notice=NOTICE, counts=result['counts'], is_demo=bool(result['counts']['is_demo']), input_sha256=result['audit']['input_sha256'],
            input_hash_scheme=result['audit']['input_hash_scheme'], model_status='research_only_uncalibrated',
            source_status='caller_admission_not_independently_authenticated', public_use='not_granted_by_export',
            artifacts={key: dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
                for key, data in (('forecasts.csv', result['csv_bytes']), ('private-audit.json', audit_bytes))})
        _write_csv(directory, result['csv_bytes'])
        private_io._write_file(directory, 'private-audit.json', result['audit'])
        private_io._write_file(directory, 'manifest.json', manifest)
        os.fsync(directory); os.fsync(parent)
        return parent_path / name
    except BaseException:
        if directory is not None:
            for filename in ('forecasts.csv', '.forecasts.csv.pending', 'private-audit.json', '.private-audit.json.pending',
                             'manifest.json', '.manifest.json.pending'):
                try: os.unlink(filename, dir_fd=directory)
                except FileNotFoundError: pass
        if created:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            owned = os.fstat(directory) if directory is not None else created_info
            if owned is not None and (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                os.rmdir(name, dir_fd=parent)
        raise
    finally:
        if directory is not None: os.close(directory)
        os.close(parent)


def main(argv=None):
    stage = 'arguments-invalid'
    try:
        parser = private_io.Parser(description=__doc__)
        parser.add_argument('--evidence'); parser.add_argument('--admission'); parser.add_argument('--batch')
        for name in ('issued-at', 'cutoff', 'output-parent'):
            parser.add_argument('--' + name, required=True)
        args = parser.parse_args(argv)
        need((args.batch is not None and args.evidence is None and args.admission is None)
             or args.batch is None and bool(args.evidence) and bool(args.admission))
        stage = 'private-input-invalid'
        if args.batch is not None:
            payload = private_io.read_private_json(args.batch, max_depth=12)
        else:
            payload = {k: private_io.read_private_json(getattr(args, k)) for k in ('evidence', 'admission')}
        parent = private_io._path(args.output_parent)
        need(not (parent / '.git').exists())
        fd = private_io._directory(parent); os.close(fd)
        stage = 'preparation-invalid'
        result = prepare_export(payload, batch_mode=args.batch is not None,
                                issued_at=args.issued_at, report_cutoff=args.cutoff)
        stage = 'private-write-failed'
        write_export(str(parent), result)
        print(json.dumps(dict(status='prepared' if result['counts']['generated'] else 'withheld', counts=result['counts'])))
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, RuntimeError):
        print(json.dumps(dict(status='failed', reason=stage)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
