"""Bounded offline fixed50 preparation; no collection, review creation or training."""
from copy import deepcopy
import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from ingest import forecast_scenario as core
from ingest.private_market_store import PrivateMarketStore

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    '_refresh_private_export', ROOT / 'scripts/daily-market-brief/prepare_private_forecast.py')
exporter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exporter)
io_private = exporter.private_io
CONFIG_KEYS = {'schema_version', 'mode', 'store_root', 'review_directory', 'output_parent', 'items'}
ITEM_KEYS = {'ticker', 'market', 'currency', 'code', 'run_id', 'normalization_version',
             'normalization_dialect', 'template', 'finality'}
TEMPLATE_KEYS = (core.EVIDENCE | {'narrative'}) - {'bars'}


class RefreshError(ValueError):
    def __init__(self):
        super().__init__('private-refresh-invalid')


def need(value):
    if not value:
        raise RefreshError()


def validate_config(config):
    need(core._bounded(config, max_depth=12) and core._obj(config, CONFIG_KEYS))
    need(type(config['schema_version']) is int and config['schema_version'] == 1
         and config['mode'] == 'offline_store')
    need(type(config['items']) is list and len(config['items']) == 50)
    seen = set()
    for item in config['items']:
        need(core._obj(item, ITEM_KEYS))
        identity = {key: item[key] for key in core.ROW_IDENTITY}
        need(core._row_identity(identity))
        pair = (item['ticker'], item['market'])
        need(pair not in seen); seen.add(pair)
        need(item['code'] == ('US.' if item['market'] == 'US' else 'BMS.') + item['ticker'])
        need(item['run_id'] is None or type(item['run_id']) is str
             and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', item['run_id']))
        t = item['template']
        missing_input = t is None or item['run_id'] is None
        need(missing_input and item['normalization_version'] is None
             or type(item['normalization_version']) is int and item['normalization_version'] in (3, 4, 5, 6))
        need(item['normalization_dialect'] is None or core._text(item['normalization_dialect']))
        need(t is None and item['finality'] is None
             or type(item['finality']) is dict and len(item['finality']) <= 366)
        for day, stamp in (item['finality'] or {}).items():
            core._day(day); core._time(stamp)
        if t is None:
            continue
        need(core._obj(t, TEMPLATE_KEYS) and type(t['schema_version']) is int and t['schema_version'] == 3)
        need(t['classification'] in ('reviewed_real', 'authored_fixture'))
        for key, keys in (('instrument', core.INSTRUMENT), ('source', core.SOURCE),
                          ('calendar', core.CALENDAR), ('corporate_actions', core.ACTIONS),
                          ('rights', core.RIGHTS), ('narrative', core.NARRATIVE)):
            need(core._obj(t[key], keys))
        need({key: t['instrument'][key] for key in core.ROW_IDENTITY} == identity)
        need(t['source']['provider'] == 'moomoo-rest' and t['source']['basis'] == 'unadjusted')
        need(t['method'] in (core.GENERIC_METHOD, core.GENERIC_CASH_METHOD))
    need(len(exporter.encoded(config)) <= exporter.MAX_BYTES)
    return config


def _window(template, issue):
    """Schedule is an external reviewed declaration, never inferred from weekdays."""
    c = template['calendar']
    need(c['complete'] is True and core._time(c['known_at']) <= issue)
    need(c['mic'] == template['instrument']['mic'])
    need(type(c['sessions']) is list and 22 <= len(c['sessions']) <= 366)
    sessions = []
    zone = ZoneInfo(c['timezone'])
    start, end = core._day(c['coverage_start']), core._day(c['coverage_end'])
    need(start <= issue.astimezone(zone).date() <= end)
    for s in c['sessions']:
        need(core._obj(s, {'session_date', 'regular_close_at'}))
        day, close = core._day(s['session_date']), core._time(s['regular_close_at'])
        need(start <= day <= end and close.astimezone(zone).date() == day)
        sessions.append((s['session_date'], close))
    need(sessions == sorted(sessions) and len({s[0] for s in sessions}) == len(sessions)
         and all(sessions[n][1] < sessions[n+1][1] for n in range(len(sessions)-1)))
    completed = [s for s in sessions if s[1] <= issue]
    need(len(completed) >= 21 and len(completed) < len(sessions))
    target = sessions[len(completed)]
    need(issue < target[1])
    return completed[-21:], target


def _candidate(item, observations, issue):
    template = deepcopy(item['template'])
    window, target = _window(template, issue)
    expected = {day for day, _ in window}
    by_day = {day: [] for day in expected}
    for observation in observations:
        record = observation['record']
        if record['code'] == item['code'] and record['date'] in expected:
            by_day[record['date']].append(observation)
    bars, bindings = [], []
    for day, close in window:
        rows = by_day[day]
        if not rows:
            return None, [], ['history_missing_or_stale'], window[-1][0], target[0]
        # Equal observations may replay; conflicting versions never pick a winner.
        if len({row['semantic_hash'] for row in rows}) != 1:
            return None, [], ['history_conflict'], window[-1][0], target[0]
        row = min(rows, key=lambda r: (r['observation']['known_ms'], r['observation']['observed_at'],
                                     r['observation']['raw_hash'], core._hash(r['observation'])))
        record, meta = row['record'], row['observation']
        if (meta.get('normalization_version') != item['normalization_version']
                or meta.get('normalization_dialect') != item['normalization_dialect']
                or record['adjustment'] != 0 or not row['eligible_for_temporal_evidence']):
            return None, [], ['history_basis_or_time_unavailable'], window[-1][0], target[0]
        retrieved, ingested = core._time(meta['observed_at']), core._time(meta['ingested_at'])
        need(type(meta['known_ms']) is int)
        known = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=meta['known_ms'])
        settled = item['finality'].get(day)
        if settled is None or not close <= core._time(settled) <= retrieved <= ingested <= known <= issue:
            return None, [], ['finality_unavailable'], window[-1][0], target[0]
        if any(r['observation']['origin'] == 'synthetic' for r in rows):
            template['classification'] = 'authored_fixture'
        need(meta['origin'] in ('synthetic', 'trusted-capture') and core._sha(meta['raw_hash']))
        bars.append(dict(instrument_id=template['instrument']['instrument_id'], session_date=day,
            close_at=close.isoformat(), close=record['close'], currency=item['currency'], unit='traded_price',
            basis='unadjusted', scale_id=template['source']['scale_id'], vintage=template['source']['vintage'],
            source_url=template['source']['source_url'], source_sha256=meta['raw_hash'],
            source_publication_at=None, retrieved_at=meta['observed_at'], ingested_at=meta['ingested_at'],
            known_at=known.isoformat(timespec='microseconds'), settled_at=settled))
        bindings.append(dict(session_date=day, semantic_hash=row['semantic_hash'], revision=row['revision'],
                             observation=deepcopy(meta), source_ms=row['source_ms'], quality=row['quality']))
    template['bars'] = bars
    return template, bindings, [], window[-1][0], target[0]


def prepare(config, *, issued_at, store=None):
    """Deterministic memory-only preparation; exact review files are read, never made."""
    validate_config(config)
    issue = core._time(issued_at)
    reviews = io_private._path(config['review_directory'])
    need(not (reviews / '.git').exists())
    fd = io_private._directory(reviews); os.close(fd)
    # Validate all private destinations before even opening the store.
    parent = io_private._path(config['output_parent'])
    need(not (parent / '.git').exists())
    fd = io_private._directory(parent); os.close(fd)
    store_path = io_private._path(config['store_root'])
    need(not (store_path / '.git').exists())
    fd = io_private._directory(store_path); os.close(fd)
    store = PrivateMarketStore(store_path) if store is None else store
    cached = {}
    selectors = dict.fromkeys(item['run_id'] for item in config['items']
                              if item['template'] is not None and item['run_id'] is not None)
    for run_id in selectors:
        rows = store.query('history', issued_at, run_id=run_id, limit=5000)
        # The API is finite without pagination. Refuse potential truncation.
        need(len(rows) < 5000)
        cached[run_id] = rows
    items, ledger = [], []
    for item in config['items']:
        identity = {key: item[key] for key in ('ticker', 'market', 'currency')}
        try:
            reasons = []
            if item['template'] is None:
                reasons.append('template_missing')
            if item['run_id'] is None:
                reasons.append('history_unavailable')
            if reasons:
                evidence, bindings, reference, target = None, [], None, None
            else:
                evidence, bindings, reasons, reference, target = _candidate(item, cached[item['run_id']], issue)
        except (RefreshError, ValueError, TypeError, KeyError, OverflowError):
            evidence, bindings, reasons, reference, target = None, [], ['calendar_or_input_unavailable'], None, None
        admission, digest = None, core._hash(evidence) if evidence is not None else None
        if evidence is not None:
            review_path = reviews / (digest + '.json')
            try:
                admission = io_private.read_private_json(str(review_path))
            except FileNotFoundError:
                reasons.append('review_required')
            if admission is not None:
                # Invalid/misbound review never reaches exporter preflight as an accepted input.
                result = core.build_private_forecast_scenario(evidence, admission=admission,
                    issued_at=issued_at, report_cutoff=issued_at)
                if result['status'] != 'generated':
                    reasons.extend(result['reasons'])
                    if any(r in result['reasons'] for r in ('schema', 'admission_binding', 'admission_time')):
                        reasons.append('review_required')
                    admission = None
        items.append(dict(identity, evidence=evidence, admission=admission))
        ledger.append(dict(identity, reasons=sorted(set(reasons)), evidence_sha256=digest,
                           reference_session=reference, target_session=target,
                           evidence=evidence, store_bindings=bindings))
    batch = dict(schema_version=1, items=items)
    result = exporter.prepare_export(batch, batch_mode=True, issued_at=issued_at, report_cutoff=issued_at)
    rows = list(csv.DictReader(io.StringIO(result['csv_bytes'].decode())))
    for row, audit, entry in zip(rows, result['audit']['rows'], ledger):
        entry['status'] = row['status']
        entry['reasons'] = sorted(set(entry['reasons']) | set(filter(None, row['reasons'].split(';'))))
        audit['input_reasons'] = sorted(set(audit['input_reasons']) | set(entry['reasons']))
        row['reasons'] = ';'.join(entry['reasons'])
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=exporter.COLUMNS, lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)  # Existing CSV cells are already escaped.
    result['csv_bytes'] = stream.getvalue().encode()
    counts = dict(result['counts'])
    counts['review_required'] = sum('review_required' in entry['reasons'] for entry in ledger)
    counts['eligible_generated'] = sum(row['status'] == 'generated' and row['is_demo'] == 'False' for row in rows)
    status = 'ready' if counts['eligible_generated'] >= 35 else 'insufficient_coverage'
    # Deduplicate observation metadata: one100-bar capture may bind21bars.
    # Retain original metadata once, reference its digest from each bar.
    observations = {}
    for entry in ledger:
        for binding in entry['store_bindings']:
            meta = binding.pop('observation')
            observation_hash = core._hash(meta)
            observations[observation_hash] = meta
            binding['observation_sha256'] = observation_hash
    receipt = dict(schema_version=1, mode='offline_store', provider_refreshed=False,
        config_sha256=core._hash(config), issued_at=issued_at, status=status, counts=counts, items=ledger,
        observations=observations,
        notice='Private research only; reviewed declarations do not authenticate sources. No collection performed.')
    # Bound before any generation is written.
    need(len(exporter.encoded(receipt)) <= exporter.MAX_BYTES)
    return result, receipt


def run(config_path, *, issued_at=None):
    config = io_private.read_private_json(config_path, max_depth=12)
    stamp = issued_at or datetime.now(timezone.utc).isoformat()
    result, receipt = prepare(config, issued_at=stamp)
    folder = exporter.write_export(config['output_parent'], result)
    fd = None
    try:
        fd = io_private._directory(folder)
        io_private._write_file(fd, 'refresh-review.json', receipt)
        os.fsync(fd)
    except BaseException:
        if fd is not None:
            for name in ('refresh-review.json', '.refresh-review.json.pending',
                         'forecasts.csv', 'private-audit.json', 'manifest.json'):
                try: os.unlink(name, dir_fd=fd)
                except FileNotFoundError: pass
            os.rmdir(folder)
        raise
    finally:
        if fd is not None: os.close(fd)
    return dict(status=receipt['status'], mode='offline_store', provider_refreshed=False,
        counts=receipt['counts'], cutoff=stamp, csv_path=str(folder / 'forecasts.csv'),
        review_path=str(folder / 'refresh-review.json'),
        sessions=[{key: entry[key] for key in ('ticker', 'market', 'reference_session', 'target_session')}
                  for entry in receipt['items']])
