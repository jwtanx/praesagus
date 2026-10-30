#!/usr/bin/env python3
"""Offline-reviewed, single dated MY source gate. Default inspection is read-only.

This controller does not renew the expired 30 October capture window. A release
is a separate human decision, not something this program creates. All results
remain private source candidates, never financial/model admissions.

The original capability/calendar evidence is inspected with --packet and is
never an executable plan. The separately reviewed execution format uses a slim
XKLS calendar (the exact 21 frozen dates and settlement cutoff), strict purpose
and financial review documents, code/input references and a distinct release.
File references are {path, sha256, bytes}; paths/locators stay in private inputs.
The test module provides authored shape examples, not real approvals.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.abc
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import struct
import sys
import time
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/stock-research/run_reviewed_my_capture.py'
FOLDER = 'scripts/stock-research/'
RUNTIME = {str(SCRIPT.relative_to(ROOT)), FOLDER+'run_reviewed_batch.py',
           FOLDER+'run_and_deliver.py', 'scripts/market_collect.py',
           'ingest/__init__.py', 'ingest/market_collector.py', 'ingest/private_market_store.py',
           'connectors/__init__.py', 'connectors/moomoo_rest.py', 'connectors/moomoo_rest_live.py'}
LIMITS = dict(work_seconds=25, cleanup_seconds=2, rss_bytes=536870912, threads=1, retries=0)
START_MS = int(datetime(2026, 10, 29, 16, tzinfo=timezone.utc).timestamp()*1000)
END_MS = START_MS + 9*3600*1000
REFERENCE, TARGET = '2026-10-29', '2026-10-30'
DIALECT = 'bms_fixed20_hours_hypothesis_v1'
JOB = dict(kind='history', code='BMS.4707', end=REFERENCE, normalization_dialect=DIALECT)
COLLECTOR_PLAN = dict(schema_version=1, codes=[], news=[], history=[{k:v for k,v in JOB.items() if k!='kind'}])
DATES = [(date(2026, 10, 1)+timedelta(days=i)).isoformat() for i in range(29)
         if (date(2026, 10, 1)+timedelta(days=i)).weekday()<5]
FILE_LIMIT = 32*1024**2
PACKET_SHA = 'bc534eaa8740b270392a2e3cdc7c307c9498969c298fe3d6df2aa6270d53cfcb'


class Held(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Held(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def keys(value, expected):
    need(type(value) is dict and set(value)==set(expected), 'fields')


def integer(value):
    need(type(value) is int and 0<=value<2**53, 'integer')
    return value


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate-key')
            result[key] = value
        return result
    def invalid(_):
        raise Held('nonfinite')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop(); count += 1
        need(depth<=24 and count<=100000, 'json-budget')
        if type(item) is dict:
            stack.extend((v, depth+1) for v in item.values())
        elif type(item) is list:
            stack.extend((v, depth+1) for v in item)
        elif type(item) is float:
            need(math.isfinite(item), 'nonfinite')
    return value


def canonical(value):
    need(type(value) is str and len(value)<=4096, 'path')
    p = Path(value)
    need(p.is_absolute() and str(p)==value and '..' not in p.parts
         and not any(a.is_symlink() for a in (p, *p.parents)), 'canonical-path')
    return p


def private_dir(value):
    p = canonical(str(value)); info = p.stat()
    need(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700
         and info.st_uid==os.getuid(), 'private-directory')
    need(len(p.parts)>=4 and p!=Path.home() and not p.is_relative_to(ROOT)
         and not any(x.lower() in {'public','www','htdocs','artifacts','dist'} for x in p.parts)
         and not any((a/'.git').exists() for a in (p,*p.parents)), 'private-root')
    return p


def read_file(value, *, code=False):
    p = canonical(str(value))
    if not code:
        private_dir(p.parent)
    fd = os.open(p, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_uid in ({0,os.getuid()} if code else {os.getuid()}), 'file-owner-type')
        need(not before.st_mode&0o022 if code else stat.S_IMODE(before.st_mode)==0o600, 'file-mode')
        need(before.st_size<=FILE_LIMIT, 'file-budget')
        raw = stream.read(FILE_LIMIT+1); after = os.fstat(stream.fileno())
        need(len(raw)<=FILE_LIMIT and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
             (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns), 'file-changed')
    return raw


def reference(p, *, code=False):
    raw = read_file(p, code=code)
    return dict(path=str(p), sha256=sha(raw), bytes=len(raw))


def read_ref(ref, *, code=False):
    keys(ref, ('path','sha256','bytes'))
    need(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']), 'hash-shape')
    integer(ref['bytes']); raw = read_file(ref['path'], code=code)
    need(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'], 'hash-mismatch')
    return raw


def now_ms():
    return time.time_ns()//1000000


def deadline(started):
    need(type(started) in (float,int) and math.isfinite(started), 'work-deadline')
    elapsed = time.monotonic()-started
    need(0<=elapsed<25, 'work-deadline')
    return 25-elapsed


def window(now, *, reserve=0):
    integer(now)
    need(START_MS<now and now+reserve<END_MS, 'expired-or-outside-original-window')


def load_module(name, path, raw):
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec); module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def prepare(plan_path, expected, started):
    deadline(started)
    raw = read_file(plan_path); need(sha(raw)==expected, 'plan-hash')
    p = decode(raw)
    keys(p, ('schema_version','kind','reference','target','instrument','mic','run_id',
             'python','python_command','runtime_files','collector_plan','calendar','purpose','financial',
             'store_root','output_parent','locator','argv_sha256','limits'))
    need(type(p['schema_version']) is int and p['schema_version']==1
         and p['kind']=='single-my-capture' and p['reference']==REFERENCE
         and p['target']==TARGET and p['instrument']=='MY.4707' and p['mic']=='XKLS', 'scope')
    need(type(p['run_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',p['run_id']), 'run-id')
    keys(p['limits'], LIMITS)
    need(all(type(p['limits'][k]) is int and p['limits'][k]==v for k,v in LIMITS.items()), 'limits')
    # Clock rejection precedes runtime imports, store access and all locator use.
    window(now_ms(), reserve=27000); deadline(started)
    exe = canonical(p['python']['path'])
    need(exe==Path(sys.executable).resolve(), 'python')
    need(type(p['python_command']) is str and p['python_command']==str(Path(sys.executable).absolute())
         and Path(p['python_command']).resolve()==exe, 'python-command')
    read_ref(p['python'], code=True)
    need(type(p['runtime_files']) is list and len(p['runtime_files'])==len(RUNTIME), 'runtime-inventory')
    buffers = {}
    for ref in p['runtime_files']:
        name = str(canonical(ref['path']).relative_to(ROOT))
        need(name in RUNTIME and name not in buffers, 'runtime-inventory')
        buffers[name] = read_ref(ref, code=True)
    need(set(buffers)==RUNTIME, 'runtime-inventory')
    need(encoded(decode(read_ref(p['collector_plan'])))==encoded(COLLECTOR_PLAN), 'collector-scope')
    c = decode(read_ref(p['calendar']))
    keys(c, ('schema_version','calendar','timezone','reference','target','required_dates','settled_after_ms'))
    need(type(c['schema_version']) is int and c['schema_version']==1 and c['calendar']=='XKLS'
         and c['timezone']=='Asia/Kuala_Lumpur' and c['reference']==REFERENCE and c['target']==TARGET
         and c['required_dates']==DATES and type(c['settled_after_ms']) is int
         and c['settled_after_ms']==START_MS, 'calendar')
    for field, role in (('purpose','Lead'),('financial','Trader')):
        doc = decode(read_ref(p[field]))
        keys(doc, ('schema_version','kind','reviewer','approved','instrument','reference','target',
                   'effective_from','effective_to','reviewed_at_ms','conditions'))
        need(type(doc['schema_version']) is int and doc['schema_version']==1
             and doc['kind']==field and doc['reviewer']==role and doc['approved'] is True
             and doc['instrument']=='MY.4707' and doc['reference']==REFERENCE and doc['target']==TARGET
             and doc['effective_from']=='2026-10-01' and doc['effective_to']==TARGET
             and START_MS<=integer(doc['reviewed_at_ms'])<=now_ms(), 'review')
        expected_conditions = (dict(private_history_research=True, public_output=False) if field=='purpose' else
            dict(ordinary_equity=True, financial_currency='MYR', unit='traded_price', adjustment=0,
                 action_placement_reviewed=True, native_provider_currency=None, provider_security_id=None,
                 timezone_basis='hours_hypothesis_not_vendor_confirmed'))
        need(encoded(doc['conditions'])==encoded(expected_conditions), 'review-conditions')
    store, output = private_dir(p['store_root']), private_dir(p['output_parent'])
    need(store!=output and not store.is_relative_to(output) and not output.is_relative_to(store), 'root-overlap')
    keys(p['locator'], ('directory','app_key_name'))
    canonical(p['locator']['directory'])  # No credential file stat/open during preparation.
    need(type(p['locator']['app_key_name']) is str and re.fullmatch('[A-Za-z0-9_-]{1,80}',p['locator']['app_key_name']), 'locator')
    attempt = output/p['run_id']
    argv = [p['python_command'],str(ROOT/'scripts/market_collect.py'),'--root',str(store),
            '--plan',p['collector_plan']['path'],'--credential-directory',p['locator']['directory'],
            '--app-key-name',p['locator']['app_key_name'],'--run-id',p['run_id'],
            '--diagnostics','--diagnostic-receipt',str(attempt/'diagnostic.json')]
    need(sha(encoded(argv))==p['argv_sha256'], 'argv-hash')
    deadline(started)
    need(sum(map(len,buffers.values()))<=128*1024**2,'runtime-budget')
    return dict(plan=p, plan_path=str(plan_path), sha=expected, buffers=buffers, attempt=attempt, argv=argv)


def release_check(ctx, release_ref, started):
    r = decode(read_ref(release_ref)); p = ctx['plan']
    keys(r, ('schema_version','kind','plan_sha256','argv_sha256','run_id','reference','target',
             'not_before_ms','expires_at_ms','resources_confirmed','exclusive_provider_window',
             'source_authorized','limits'))
    current = now_ms(); window(current, reserve=27000); deadline(started)
    begin, end = integer(r['not_before_ms']), integer(r['expires_at_ms'])
    need(type(r['schema_version']) is int and r['schema_version']==1 and r['kind']=='lead-single-my-release'
         and r['plan_sha256']==ctx['sha'] and r['argv_sha256']==p['argv_sha256'] and r['run_id']==p['run_id']
         and r['reference']==REFERENCE and r['target']==TARGET
         and START_MS<begin<=current<current+27000<end<=END_MS and 0<end-begin<=600000
         and r['resources_confirmed'] is True and r['exclusive_provider_window'] is True
         and r['source_authorized'] is True and encoded(r['limits'])==encoded(LIMITS), 'release')
    return r


def write(directory, name, value):
    raw = encoded(value)
    fd = os.open(directory/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(directory, os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return dict(path=str(directory/name), sha256=sha(raw), bytes=len(raw))


def claim(ctx, release_ref, started, started_ms):
    p = ctx['plan']; directory = Path(p['store_root'])/'.reviewed-my-claims'
    try:directory.mkdir(mode=0o700)
    except FileExistsError:pass
    private_dir(directory)
    # Never erase claims after any failure. A partial reservation is held too.
    value = dict(plan_sha256=ctx['sha'], release=release_ref, run_id=p['run_id'])
    write(directory, 'release-'+release_ref['sha256']+'.json', value)
    write(directory, 'run-'+p['run_id']+'.json', value)
    ctx['attempt'].mkdir(mode=0o700); private_dir(ctx['attempt'])
    return write(ctx['attempt'], 'intent.json', dict(**value, started=started, started_ms=started_ms))


def helpers(ctx):
    b = ctx['buffers']
    h155 = load_module('_my155',ROOT/FOLDER/'run_reviewed_batch.py',b[FOLDER+'run_reviewed_batch.py'])
    h163 = load_module('_my163',ROOT/FOLDER/'run_and_deliver.py',b[FOLDER+'run_and_deliver.py'])
    return h155,h163


class VerifiedFinder(importlib.abc.MetaPathFinder):
    def __init__(self, ctx, helper):
        self.ctx,self.helper = ctx,helper

    def find_spec(self, fullname, path=None, target=None):
        rel = fullname.replace('.','/')
        name = rel+'/__init__.py' if rel+'/__init__.py' in RUNTIME else rel+'.py'
        if name in self.ctx['buffers']:
            loader = self.helper.BufferLoader(str(ROOT/name),self.ctx['buffers'][name])
            return importlib.util.spec_from_file_location(fullname,ROOT/name,loader=loader,
                submodule_search_locations=[str(ROOT/rel)] if name.endswith('/__init__.py') else None)
        candidate = importlib.machinery.PathFinder.find_spec(fullname,path)
        origin = getattr(candidate,'origin',None)
        need(not isinstance(origin,str) or origin in ('built-in','frozen')
             or not Path(origin).resolve().is_relative_to(ROOT), 'foreign-runtime-import')
        return None


def install_runtime(ctx, h155):
    # Fresh private subprocesses must not reuse a preloaded connector or executor.
    for name in ('connectors','ingest'):
        need(not any(n==name or n.startswith(name+'.') for n in sys.modules), 'preloaded-runtime')
    finder = VerifiedFinder(ctx,h155); sys.meta_path.insert(0,finder)
    import ingest.market_collector as collector
    import ingest.private_market_store as storage
    entry = load_module('_my_collector',ROOT/'scripts/market_collect.py',ctx['buffers']['scripts/market_collect.py'])
    return collector,storage,entry


def continuation(plan_path, plan_sha, release_ref, intent_ref):
    intent = decode(read_ref(intent_ref))
    keys(intent, ('plan_sha256','release','run_id','started','started_ms'))
    started = intent['started']; deadline(started)
    ctx = prepare(plan_path,plan_sha,started)
    release_check(ctx,release_ref,started)
    need(intent['plan_sha256']==ctx['sha'] and intent['release']==release_ref
         and intent['run_id']==ctx['plan']['run_id'] and integer(intent['started_ms'])<=now_ms()
         and Path(intent_ref['path'])==ctx['attempt']/'intent.json', 'intent')
    need(abs((now_ms()-intent['started_ms'])-(time.monotonic()-started)*1000)<=1000,'clock-discontinuity')
    value = dict(plan_sha256=ctx['sha'],release=release_ref,run_id=ctx['plan']['run_id'])
    directory = Path(ctx['plan']['store_root'])/'.reviewed-my-claims'
    for name in ('release-'+release_ref['sha256']+'.json','run-'+ctx['plan']['run_id']+'.json'):
        need(decode(read_file(directory/name))==value, 'claim')
    return ctx,started


def validate_rows(ctx, summary, store, cutoff):
    p = ctx['plan']
    keys(summary, ('schema_version','run_id','outcomes'))
    need(type(summary['schema_version']) is int and summary['schema_version']==2
         and summary['run_id']==p['run_id'] and type(summary['outcomes']) is list
         and len(summary['outcomes'])==1, 'collector-summary')
    outcome = summary['outcomes'][0]
    keys(outcome, ('job_id','status','attempt_id','failure','diagnostic_stage'))
    need(outcome['job_id']==sha(encoded(JOB)) and outcome['status']=='success'
         and outcome['failure'] is None and outcome['diagnostic_stage'] is None
         and type(outcome['attempt_id']) is str and re.fullmatch('[0-9a-f]{64}',outcome['attempt_id']), 'collector-outcome')
    with store._connection(readonly=True) as db:
        attempts_in_run = db.execute('SELECT id,kind FROM attempts WHERE run_id=? LIMIT 2',(p['run_id'],)).fetchall()
    need([(r[0],r[1]) for r in attempts_in_run]==[(outcome['attempt_id'],'history')], 'attempt-count')
    rows = store.query('history',cutoff,run_id=p['run_id'],limit=101)
    need(1<=len(rows)<=100,'row-count')
    dates, attempts, hashes = set(), set(), set()
    for row in rows:
        record, meta = row['record'],row['observation']
        stamp = record['date']
        need(type(stamp) is str and date.fromisoformat(stamp).isoformat()==stamp
             and '1900-01-01'<=stamp<=REFERENCE and stamp not in dates, 'dates-or-duplicates')
        dates.add(stamp)
        need(type(row['revision']) is int and row['revision']==1 and row['eligible_for_temporal_evidence'] is True, 'revised-or-unknown')
        need(record['code']=='BMS.4707' and record['provider']=='moomoo-rest'
             and type(record['adjustment']) is int and record['adjustment']==0 and type(record['close']) in (int,float)
             and math.isfinite(record['close']) and record['close']>0
             and record['normalization_dialect']==DIALECT and record['raw_time_zone_unit']=='hours_hypothesis'
             and type(record['time_zone']) is int and record['time_zone']==8
             and type(record['effective_offset_minutes']) is int and record['effective_offset_minutes']==480
             and record['raw_date']==int(stamp.replace('-',''))
             and record['unit_basis']=='operator_selected_hypothesis_not_vendor_confirmed', 'record-basis')
        need(meta['run_id']==p['run_id'] and meta['status']=='success' and meta['reason'] is None
             and meta['origin']=='trusted-capture' and type(meta['normalization_version']) is int
             and meta['normalization_version']==6
             and meta['normalization_dialect']==DIALECT and meta['record_count']==len(rows)
             and meta['query']==dict(code='BMS.4707',end=REFERENCE,ktype='2',autype='0',num='100')
             and meta['endpoint']=='/api/v1.0/quote/BMS.4707/history-kline'
             and START_MS<integer(meta['observed_ms'])<=integer(meta['ingested_ms'])
             ==integer(meta['known_ms'])<=now_ms(), 'source-provenance')
        need(row['source_ms'] is not None and type(row['source_ms']) is int
             and row['source_ms']==record['time_key'] and row['source_ms']<=meta['observed_ms'], 'source-clock')
        attempts.add(sha(encoded(meta))); hashes.add(meta['raw_hash'])
    need(set(DATES)<=dates and attempts=={outcome['attempt_id']} and len(hashes)==1
         and all(type(h) is str and re.fullmatch('[0-9a-f]{64}',h) for h in hashes), 'missing-closes-or-attempt')
    return dict(rows=len(rows),required_closes=len(DATES),raw_sha256=next(iter(hashes)),
                attempt_id=outcome['attempt_id'],financial_admission=False)


def guarded_killer(helper, process, birth):
    """Signal only a still-observed original worker group; uncertainty holds.

    The outer supervisor separately handles observed escaped descendants. This
    nested gate does not infer group ownership from a recycled numeric PID.
    """
    def kill(group, sig):
        need(type(group) is int and group==process.pid and group>0
             and sig in (signal.SIGTERM,signal.SIGKILL), 'nested-signal-scope')
        table = helper.process_snapshot(timeout=.25)
        row = table.get(group)
        if row is None and helper.group_state(group) is False:
            raise ProcessLookupError()
        need(birth is not None and row is not None and row[1]==group and row[3]==birth,
             'nested-cleanup-ownership-unknown')
        os.killpg(group,sig)
    return kill


def internal_cli(ctx, started, release_ref, intent_ref):
    h155,_ = helpers(ctx); collector,storage,entry = install_runtime(ctx,h155)
    write(ctx['attempt'],'cli-start.json',dict(plan_sha256=ctx['sha']))
    original_collect,original_supervise = collector.collect,collector.supervise

    def guarded(job, locator, **bounds):
        need(encoded(job)==encoded(JOB) and locator==ctx['plan']['locator'], 'worker-scope')
        continuation(ctx['plan_path'],ctx['sha'],release_ref,intent_ref)
        remaining = deadline(started)
        need(remaining>4,'worker-budget')
        import subprocess
        worker = {}
        def spawn(argv, **kwargs):
            need(argv==[sys.executable,collector.ENTRY,'--worker'], 'worker-argv')
            continuation(ctx['plan_path'],ctx['sha'],release_ref,intent_ref)
            proc = subprocess.Popen(internal_argv(ctx,'worker',release_ref,intent_ref),**kwargs)
            worker['process'] = proc
            # Always return an already-created child so the original supervisor
            # enters its cleanup path, even when initial ownership is unobserved.
            try:
                row = h155.process_snapshot(timeout=.25).get(proc.pid)
                worker['birth'] = row[3] if row and row[1]==proc.pid else None
            except Exception:
                worker['birth'] = None
            if worker['birth'] is None:
                # Do not send the authorization frame to an unobserved worker.
                # Returning the child still lets the original cleanup path run.
                proc.stdin.close()
            return proc
        def kill(group, sig):
            need('process' in worker,'nested-worker-unobserved')
            return guarded_killer(h155,worker['process'],worker['birth'])(group,sig)
        return original_supervise(job,locator,timeout=min(20,bounds['timeout'],remaining-2),
                                  cleanup=min(2,bounds['cleanup']),popen=spawn,killer=kill)

    def bounded_collect(store, plan, locator, *, run_id):
        need(encoded(plan)==encoded(COLLECTOR_PLAN) and locator==ctx['plan']['locator']
             and run_id==ctx['plan']['run_id'], 'collect-scope')
        # Includes empty/failed prior attempts; history-only lookup misses those.
        with store._connection(readonly=True) as db:
            need(db.execute('SELECT 1 FROM runs WHERE id=?',(run_id,)).fetchone() is None,'existing-run')
        remaining = deadline(started)
        need(remaining>4,'worker-budget')
        return original_collect(store,plan,locator,run_id=run_id,supervisor=guarded,
                                run_seconds=remaining,job_seconds=min(20,remaining-2),cleanup_seconds=2)
    entry.collect = bounded_collect
    output = io.StringIO()
    with redirect_stdout(output):
        code = entry.main(ctx['argv'][2:])
    need(code==0,'collector-failed'); deadline(started)
    summary = decode(output.getvalue())
    result = validate_rows(ctx,summary,storage.PrivateMarketStore(ctx['plan']['store_root']),
                           datetime.now(timezone.utc).isoformat())
    deadline(started); window(now_ms())
    write(ctx['attempt'],'candidate.json',dict(plan_sha256=ctx['sha'],summary=summary,result=result))
    deadline(started)
    return 0


def internal_worker(ctx, started, release_ref, intent_ref):
    # Validate the entire original framing before original worker_main can load a key.
    prefix = sys.stdin.buffer.read(4)
    need(len(prefix)==4,'worker-frame'); size = struct.unpack('!I',prefix)[0]
    need(0<size<=65536,'worker-frame')
    packet = sys.stdin.buffer.read(size)
    need(len(packet)==size and sys.stdin.buffer.read(1)==b'','worker-frame')
    frame = decode(packet); keys(frame,('version','job','job_digest','locator'))
    need(type(frame['version']) is int and frame['version']==1 and encoded(frame['job'])==encoded(JOB)
         and frame['job_digest']==sha(encoded(JOB)) and frame['locator']==ctx['plan']['locator'], 'worker-frame')
    deadline(started); window(now_ms(),reserve=22000)
    h155,_ = helpers(ctx); collector,_,_ = install_runtime(ctx,h155)
    write(ctx['attempt'],'worker-start.json',dict(plan_sha256=ctx['sha']))
    # No credentials are accessed before this final gate and single-use claim.
    continuation(ctx['plan_path'],ctx['sha'],release_ref,intent_ref)
    private_dir(ctx['plan']['locator']['directory'])
    deadline(started); window(now_ms(),reserve=22000)
    return collector.worker_main(io.BytesIO(prefix+packet),sys.stdout.buffer)


def internal_argv(ctx, stage, release_ref, intent_ref):
    # Isolated stdlib bootstrap checks the controller bytes BEFORE compiling
    # them. No unverified self import, bytecode cache or PYTHONPATH participates.
    raw = ctx['buffers'][str(SCRIPT.relative_to(ROOT))]
    bootstrap = ("import hashlib, pathlib, sys; "
        f"p=pathlib.Path({str(SCRIPT)!r}); f=p.open('rb'); b=f.read({len(raw)+1}); f.close(); "
        f"assert len(b)=={len(raw)} and hashlib.sha256(b).hexdigest()=={sha(raw)!r}; "
        "sys.argv[0]=str(p); exec(compile(b,str(p),'exec'),dict(__name__='__main__',__file__=str(p)))")
    return [ctx['plan']['python_command'],'-I','-B','-c',bootstrap,'--internal',stage,'--plan',ctx['plan_path'],
            '--plan-sha256',ctx['sha'],'--release-ref',encoded(release_ref).decode(),
            '--intent-ref',encoded(intent_ref).decode()]


def inspect_packet(path, expected):
    raw = read_file(path)
    need(expected==PACKET_SHA and sha(raw)==PACKET_SHA,'original-packet-hash')
    packet = decode(raw)
    need(packet['identity']['instrument_id']=='MY.4707' and
         packet['request']['query']=='end=2026-10-29&ktype=2&autype=0&num=100', 'packet-scope')
    return dict(status='HELD',reference=REFERENCE,target=TARGET,
                expired=now_ms()>=END_MS,source_released=False,
                dependencies=['Renewed exact-window financial mapping/action placement',
                              'Separate exact dated source-purpose and finite Lead release'],
                date_rollover=False,child_started=False)


def operate(plan_path, expected, mode='inspect', release_ref=None, *, entry_clock=None):
    # main supplies its entry clock, before argument parsing/decoding. Direct
    # callers get the same boundary here; no CLI clock override exists.
    started,started_ms = entry_clock or (time.monotonic(),now_ms())
    ctx = None
    dispatched = False
    try:
        need(mode in ('inspect','execute'),'mode')
        ctx = prepare(plan_path,expected,started)
        if mode=='inspect':
            return dict(status='HELD',reason='inspection-only-no-source-release',child_started=False)
        release_check(ctx,release_ref,started)
        intent_ref = claim(ctx,release_ref,started,started_ms)
        # Everything before child supervision consumes the same original budget.
        h155,h163 = helpers(ctx)
        remaining = deadline(started)
        need(remaining>2,'dispatch-budget')
        window(now_ms(),reserve=27000)
        limits = LIMITS|dict(work_seconds=remaining-.01)
        dispatched = True
        result = h163.supervise(internal_argv(ctx,'cli',release_ref,intent_ref),limits,h155)
        # Captured output is never copied into a receipt or user-facing error.
        result.pop('stdout',None); result.pop('stderr',None)
        write(ctx['attempt'],'supervisor.json',result)
        need(time.monotonic()-started<=27,'total-deadline')
        need(result['approved'] is True and result['returncode']==0
             and result['cleanup_verified'] is True,'supervision-held')
        deadline(started); window(now_ms())
        candidate = decode(read_file(ctx['attempt']/'candidate.json'))
        keys(candidate,('plan_sha256','summary','result')); need(candidate['plan_sha256']==ctx['sha'],'candidate')
        # Independently replay raw/store integrity in the parent, bound to this
        # exact run and attempt, inside the original work interval.
        _,storage,_ = install_runtime(ctx,h155)
        verified = validate_rows(ctx,candidate['summary'],storage.PrivateMarketStore(ctx['plan']['store_root']),
                                 datetime.now(timezone.utc).isoformat())
        need(verified==candidate['result'],'candidate-mismatch')
        deadline(started)
        # Final receipt is still a private candidate, requiring independent review.
        # A filesystem write can finish late. Never leave an acceptance marker;
        # these receipts are unsealed evidence even when the final check passes.
        write(ctx['attempt'],'completed.json',dict(status='unsealed-evidence',accepted=False,plan_sha256=ctx['sha'],
            candidate=reference(ctx['attempt']/'candidate.json'),supervisor=reference(ctx['attempt']/'supervisor.json'),
            work_elapsed_seconds=time.monotonic()-started,financial_admission=False))
        deadline(started); window(now_ms())
        return dict(status='PRIVATE_CANDIDATE',child_started=True,financial_admission=False)
    except (Exception,KeyboardInterrupt) as error:
        # Never expose arbitrary exception strings, private paths or locator values.
        reason = str(error) if type(error) is Held else 'input-or-execution-held'
        return dict(status='HELD',reason=reason,child_started=dispatched,
                    financial_admission=False)


def main(argv=None):
    entry_clock = (time.monotonic(),now_ms())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True); parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--mode',choices=('inspect','execute'),default='inspect')
    parser.add_argument('--packet',action='store_true',help='Read-only original dated capability packet')
    parser.add_argument('--release-ref'); parser.add_argument('--internal',choices=('cli','worker'))
    parser.add_argument('--intent-ref')
    args = parser.parse_args(argv)
    try:
        if args.internal:
            need(not args.packet and args.mode=='inspect' and args.release_ref and args.intent_ref,'internal-arguments')
            release_ref,intent_ref = decode(args.release_ref),decode(args.intent_ref)
            ctx,started = continuation(args.plan,args.plan_sha256,release_ref,intent_ref)
            return internal_worker(ctx,started,release_ref,intent_ref) if args.internal=='worker' else internal_cli(ctx,started,release_ref,intent_ref)
        if args.packet:
            need(args.mode=='inspect' and not args.release_ref and not args.intent_ref,'packet-inspection-only')
            result = inspect_packet(args.plan,args.plan_sha256)
        else:
            need(not args.intent_ref,'internal-arguments')
            result = operate(args.plan,args.plan_sha256,args.mode,decode(args.release_ref) if args.release_ref else None,
                             entry_clock=entry_clock)
    except (Exception,KeyboardInterrupt):
        if args.internal:return 2
        result = dict(status='HELD',reason='input-held',child_started=False)
    candidate = result['status']=='PRIVATE_CANDIDATE'
    payload = json.dumps(result,sort_keys=True)
    if candidate:
        try:deadline(entry_clock[0]); window(now_ms())
        except Held:
            result = dict(status='HELD',reason='final-output-deadline',child_started=True)
            payload = json.dumps(result,sort_keys=True); candidate = False
    print(payload)
    if candidate:
        # Even a blocked stdout cannot turn an over-budget run into exit zero.
        # Printed candidate status is provisional; receipts never grant admission.
        try:deadline(entry_clock[0]); window(now_ms())
        except Held:return 2
    return 0 if candidate else 2


if __name__=='__main__':
    raise SystemExit(main())
