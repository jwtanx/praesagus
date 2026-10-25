"""Finite released history collection followed by exact-reviewed fixed50 export."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path
import re
import time

from ingest import market_collector as collector
from ingest import private_forecast_refresh as refresh
from ingest.private_market_store import PrivateMarketStore

io = refresh.io_private
CONFIG_KEYS = {'schema_version', 'fixed50_config', 'credential_locator_file', 'plans', 'run_prefix',
               'minimum_start_interval', 'job_seconds', 'cleanup_seconds', 'total_seconds', 'receipt_parent'}
RELEASE_KEYS = {'schema_version', 'config_sha256', 'not_before', 'expires_at', 'one_use_id',
                'source_rights_reference', 'reviewers', 'runtime_sha256'}
RUNTIME_PATHS = ('ingest/private_forecast_pipeline.py', 'ingest/private_forecast_refresh.py',
    'ingest/forecast_scenario.py', 'ingest/market_collector.py', 'ingest/private_market_store.py',
    'connectors/moomoo_rest.py', 'connectors/moomoo_rest_live.py', 'scripts/market_collect.py',
    'scripts/daily-market-brief/prepare_private_forecast.py',
    'scripts/daily-market-brief/prepare_forecast_report.py', 'scripts/daily-market-brief/run_current_forecast.py')


class PipelineError(ValueError):
    def __init__(self):
        super().__init__('private-pipeline-unavailable')


def need(value):
    if not value:
        raise PipelineError()


def runtime_hashes():
    return {name: hashlib.sha256((refresh.ROOT / name).read_bytes()).hexdigest() for name in RUNTIME_PATHS}


def number(value, *, maximum):
    need(type(value) in (int, float) and math.isfinite(value) and 0 < value <= maximum)
    return value


def directory(value):
    path = io._path(value)
    need(not (path / '.git').exists())
    fd = io._directory(path); os.close(fd)
    return path


def write(path, name, payload):
    fd = io._directory(path)
    try:
        io._write_file(fd, name, payload)
        os.fsync(fd)
    finally:
        os.close(fd)


def preflight(config_path, release_path, *, wall):
    """Validate every request/binding before claim or credential material access."""
    config = io.read_private_json(config_path, max_depth=12)
    release = io.read_private_json(release_path, max_depth=12)
    need(refresh.core._obj(config, CONFIG_KEYS) and type(config['schema_version']) is int
         and config['schema_version'] == 1)
    need(refresh.core._obj(release, RELEASE_KEYS) and type(release['schema_version']) is int
         and release['schema_version'] == 1)
    need(release['config_sha256'] == refresh.core._hash(config) and release['reviewers'] == ['Lead', 'Trader'])
    need(refresh.core._text(release['source_rights_reference']) and release['runtime_sha256'] == runtime_hashes())
    for value in (config['run_prefix'], release['one_use_id']):
        need(type(value) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,120}', value))
    number(config['minimum_start_interval'], maximum=600)
    number(config['job_seconds'], maximum=20)
    number(config['cleanup_seconds'], maximum=2)
    number(config['total_seconds'], maximum=600)
    now = refresh.core._time(wall())
    start, expiry = (refresh.core._time(release[key]) for key in ('not_before', 'expires_at'))
    need(start <= now < expiry)
    fixed = io.read_private_json(config['fixed50_config'], max_depth=12)
    refresh.validate_config(fixed)
    # Release binds the complete fixed50 template/config bytes by hash, in addition
    # to the orchestrator config hash (which contains only this path).
    need(type(config['plans']) is list and 1 <= len(config['plans']) <= 50)
    jobs, seen = [], set()
    index = {(item['code']): item for item in fixed['items']}
    for group, plan_info in enumerate(config['plans']):
        need(refresh.core._obj(plan_info, {'path', 'sha256', 'run_seconds', 'fixed50_sha256'}))
        need(plan_info['fixed50_sha256'] == refresh.core._hash(fixed))
        number(plan_info['run_seconds'], maximum=300)
        plan = io.read_private_json(plan_info['path'])
        need(plan_info['sha256'] == refresh.core._hash(plan))
        need(plan.get('codes') == [] and plan.get('news') == [])
        for job in collector.validate_plan(plan):
            code = job.get('code')
            need(job['kind'] == 'history' and code in index and code not in seen)
            seen.add(code)
            need(len(seen) <= 50)
            run_id = config['run_prefix'] + '-' + str(len(jobs)+1).zfill(3)
            item = index[code]
            if item['template'] is not None:
                # The caller freezes the exact future vintage; no template or
                # financial decisions are rewritten by the orchestrator.
                need(item['template']['source']['vintage'] == run_id)
                need(item['normalization_version'] == collector.normalization_for(job,current=True)
                     and item['normalization_dialect'] == job.get('normalization_dialect'))
                window, _ = refresh._window(item['template'], now)
                need(job['end'] == window[-1][0])
                cutoff = item['finality'].get(window[-1][0])
                need(cutoff is not None and refresh.core._time(cutoff) <= now)
                need(item['template']['rights']['history_collection'] == 'permitted'
                     and item['template']['rights']['private_retention_research'] == 'permitted')
            jobs.append(dict(job=job, group=group, run_id=run_id,
                             job_sha256=collector.job_digest(job), plan_sha256=plan_info['sha256']))
    need(bool(jobs))
    parent = directory(config['receipt_parent'])
    directory(fixed['output_parent']); directory(fixed['review_directory'])
    store_path = directory(fixed['store_root'])
    store = PrivateMarketStore(store_path)
    # A bounded exact-id read also rejects existing failed/empty runs, which a
    # history-row query alone cannot detect. No raw data or credentials read here.
    with store._connection(readonly=True) as db:
        for entry in jobs:
            need(db.execute('SELECT 1 FROM runs WHERE id=? LIMIT 1', (entry['run_id'],)).fetchone() is None)
    # Validate just the locator references/path. Existing worker alone opens keys.
    locator = io.read_private_json(config['credential_locator_file'])
    credential_root = collector.validate_locator(locator)
    directory(str(credential_root))
    return config, release, fixed, jobs, parent, store, locator


def execute(config_path, release_path, *, wall=collector.utc_now, clock=time.monotonic,
            sleep=time.sleep, supervisor=None):
    """No retries. Pacing/deadlines bound dispatch, not arbitrary synchronous I/O."""
    initial = clock()
    config, release, fixed, jobs, parent, store, locator = preflight(config_path, release_path, wall=wall)
    need(clock() >= initial)
    parent_fd = io._directory(parent)
    lock_parent = io._directory(store.root)
    lock_fd = None
    lock_created = False
    operation = None
    try:
        lock_fd = os.open('.collector.lock', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                          0o600, dir_fd=lock_parent)
        lock_created = True
        claim_name = '.claim-' + release['one_use_id'] + '.json'
        io._write_file(parent_fd, claim_name, dict(release_sha256=refresh.core._hash(release),
                                                   claimed_at=wall(), run_prefix=config['run_prefix']))
        # Exclusive run folder; failed claims remain consumed, never auto-retry.
        os.mkdir(config['run_prefix'], mode=0o700, dir_fd=parent_fd)
        operation = parent / config['run_prefix']
        write(operation, 'started.json', dict(config_sha256=refresh.core._hash(config),
            release_sha256=refresh.core._hash(release), runtime_sha256=runtime_hashes(), jobs=jobs, started_at=wall()))
        deadline = initial + config['total_seconds']
        expiry = refresh.core._time(release['expires_at'])
        last_clock, last_wall, last_start = clock(), refresh.core._time(wall()), None
        group_deadlines = {}
        outcomes = []
        dispatches = []
        failed = None
        resumed = deepcopy(fixed)
        for item in resumed['items']:
            item['run_id'] = None  # Never carry old capture selectors into online output.
        by_code = {item['code']: item for item in resumed['items']}
        def remaining(group):
            nonlocal last_clock, last_wall
            tick, stamp = clock(), refresh.core._time(wall())
            if tick < last_clock or stamp < last_wall:
                raise PipelineError()
            last_clock, last_wall = tick, stamp
            return min(deadline-tick, group_deadlines[group]-tick, (expiry-stamp).total_seconds())
        for entry in jobs:
            group = entry['group']
            if group not in group_deadlines:
                group_deadlines[group] = min(deadline, clock()+config['plans'][group]['run_seconds'])
            # Pacing is outside collect, so its timeout cannot be consumed by a
            # hidden supervisor sleep. Clock/expiry checked after every wait.
            try:
                available = remaining(group)
                while last_start is not None and clock()-last_start < config['minimum_start_interval']:
                    wait = config['minimum_start_interval']-(clock()-last_start)
                    need(available > config['cleanup_seconds'])
                    sleep(min(wait, available-config['cleanup_seconds'], 1.0))
                    available = remaining(group)
                if available <= config['cleanup_seconds']:
                    failed = 'budget_or_expiry'; break
                current_item = by_code[entry['job']['code']]
                if current_item['template'] is not None:
                    window, _ = refresh._window(current_item['template'],refresh.core._time(wall()))
                    need(entry['job']['end'] == window[-1][0])
                started = clock()
                need(last_start is None or started-last_start >= config['minimum_start_interval'])
                plan = dict(schema_version=1, codes=[], news=[], history=[
                    {k: v for k, v in entry['job'].items() if k != 'kind'}])
                def dispatch(job, credentials, *, timeout, cleanup):
                    nonlocal last_start
                    left = remaining(group)
                    need(left > cleanup)
                    actual_start = clock()
                    need(last_start is None or actual_start-last_start >= config['minimum_start_interval'])
                    last_start = actual_start
                    dispatches.append(dict(code=job['code'],run_id=entry['run_id'],started_monotonic=actual_start))
                    worker = collector.supervise if supervisor is None else supervisor
                    return worker(job, credentials, timeout=min(timeout,left-cleanup),cleanup=cleanup)
                result = collector.collect(store, plan, locator, run_id=entry['run_id'],
                    supervisor=dispatch,
                    clock=clock, wall=wall, job_seconds=min(config['job_seconds'],available-config['cleanup_seconds']),
                    cleanup_seconds=config['cleanup_seconds'], run_seconds=min(300,available))
                need(len(result) == 1)
                outcome = result[0]
                record = dict(code=entry['job']['code'], run_id=entry['run_id'], group=group,
                    plan_sha256=entry['plan_sha256'], job_sha256=entry['job_sha256'],
                    started_monotonic=started, completed_monotonic=clock(), status=outcome.status,
                    failure=outcome.failure, attempt_id=outcome.attempt_id,
                    normalization_version=outcome.normalization_version)
                outcomes.append(record)
                # Empty success is not21-session coverage; stop rather than
                # fetching later names after a known unusable first response.
                if outcome.failure is not None or outcome.status != 'success':
                    failed = 'upstream_or_capture_failure'; break
                available = remaining(group)
                if available <= 0:
                    failed = 'budget_or_expiry'; break
                row = by_code[entry['job']['code']]
                row['run_id'] = entry['run_id']
                row['normalization_version'] = outcome.normalization_version
                row['normalization_dialect'] = entry['job'].get('normalization_dialect')
                # Validate actual required21 coverage before another provider call.
                # This is preparation, never an admission creation.
                if row['template'] is not None:
                    candidates = store.query('history', wall(), run_id=entry['run_id'],limit=5000)
                    need(len(candidates) < 5000)
                    evidence, _, reasons, _, _ = refresh._candidate(row,candidates,refresh.core._time(wall()))
                    if evidence is None or reasons:
                        failed = 'history_or_finality_unavailable'; break
            except (ValueError, TypeError, KeyError, OSError, OverflowError):
                failed = 'clock_integrity_or_input_failure'; break
        attempted_ids = {row['run_id'] for row in dispatches}
        unattempted = [dict(code=e['job']['code'],run_id=e['run_id'],reason=failed)
                       for e in jobs if e['run_id'] not in attempted_ids]
        capture_receipt = dict(schema_version=1, mode='online', status='collection_failed' if failed else 'captured',
            failure=failed, config_sha256=refresh.core._hash(config),release_sha256=refresh.core._hash(release),
            started_monotonic=initial, completed_monotonic=clock(), provider_calls=len(dispatches),dispatches=dispatches,
            planned_jobs=len(jobs), retries=0, outcomes=outcomes, unattempted=unattempted)
        write(operation,'collection.json',capture_receipt)
        write(operation,'captured-config.json',resumed)
        if failed:
            write(operation,'missing-ledger.json',dict(items=[dict(ticker=item['ticker'],market=item['market'],
                currency=item['currency'],status='withheld',reasons=[failed]) for item in fixed['items']]))
            return dict(status='collection_failed',mode='online',provider_refreshed=False,
                        attempted_jobs=len(dispatches),planned_jobs=len(jobs),retries=0,
                        reason=failed,receipt_path=str(operation/'collection.json')),1
        # Sample actual issuance after collection. Reviews must already match
        # exact new observations; no old approval hash is ever rewritten.
        cutoff = wall()
        need(clock() <= deadline and refresh.core._time(cutoff) < expiry)
        result, review = refresh.prepare(resumed, issued_at=cutoff, store=store)
        write(operation,'candidate-review.json',review)
        need(clock() <= deadline and refresh.core._time(wall()) < expiry)
        folder = refresh.exporter.write_export(resumed['output_parent'],result)
        summary = dict(status=review['status'],mode='online',provider_refreshed=True,
            attempted_jobs=len(dispatches),planned_jobs=len(jobs),retries=0,counts=review['counts'],
            refreshed_codes=[e['job']['code'] for e in jobs],
            cutoff=cutoff,csv_path=str(folder/'forecasts.csv'),review_path=str(operation/'candidate-review.json'),
            resume_config=str(operation/'captured-config.json'),receipt_path=str(operation/'collection.json'),
            next_action='none' if review['status']=='ready' else 'review_required' if review['counts']['review_required'] else 'resolve_inputs')
        summary['artifacts'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (operation/'collection.json',operation/'captured-config.json',
                         operation/'candidate-review.json',folder/'forecasts.csv',
                         folder/'private-audit.json',folder/'manifest.json')}
        write(operation,'completed.json',summary)
        return summary,0 if review['status']=='ready' else 2
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if lock_created:
            os.unlink('.collector.lock',dir_fd=lock_parent)
        os.close(lock_parent)
        os.close(parent_fd)


def run_offline(config_path):
    return refresh.run(config_path)
