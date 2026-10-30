#!/usr/bin/env python3
"""Typed, at-most-once operator for existing private delivery commands."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PYTHON = str(Path(sys.executable).absolute())
FOLDER = 'scripts/stock-research/'
QUALITY_FILES = {FOLDER+n+'.py' for n in ('quality_scorecard', 'evaluation', 'data', 'storage',
    'market_calendar', 'inference', 'model', 'features', 'ranking')} | {'harness/forecast_review.py'}
COMMON_FILES = {FOLDER+n+'.py' for n in ('run_and_deliver', 'inspect_delivery', 'run_reviewed_batch')}
ALIASES = {'quality-scorecard161', 'us30-reviewed155'}
LIMITS = {r: dict(work_seconds=60 if r=='quality-scorecard161' else 120,
    cleanup_seconds=2, rss_bytes=536870912, threads=1, retries=0) for r in ALIASES}
OUTPUTS = {'scorecard.json', 'scorecard.csv', 'scorecard.html', 'provenance.json'}
FILE_LIMIT, TOTAL_LIMIT, CONTROL_LIMIT = 32*1024**2, 128*1024**2, 2*1024**2
STREAM_LIMIT = 65536


class Held(ValueError):
    def __init__(self,reason,*,field=None,stage=None,reference=None):
        super().__init__(reason)
        self.field,self.stage,self.reference = field,stage,reference
        self.scope = None


def need(value, reason):
    if not value:
        raise Held(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def keys(value, required, optional=()):
    need(type(value) is dict and set(required) <= value.keys()
         and value.keys() <= set(required)|set(optional), 'unknown-or-missing-fields')


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate-json-key')
            result[key] = value
        return result
    def invalid(_):
        raise Held('nonfinite-json')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        need(depth <= 32 and count <= 300000, 'json-budget')
        if type(item) is dict:
            stack.extend((v, depth+1) for v in item.values())
        elif type(item) is list:
            stack.extend((v, depth+1) for v in item)
        elif type(item) is float:
            need(math.isfinite(item), 'nonfinite-json')
    return value


def now_ms():
    return time.time_ns()//1000000


def integer(value):
    need(type(value) is int and 0 <= value < 2**53, 'invalid-integer')
    return value


def path(value):
    need(type(value) is str and len(value) <= 4096, 'invalid-path')
    p = Path(value)
    need(p.is_absolute() and str(p)==value and '..' not in p.parts, 'absolute-canonical-path-required')
    need(not any(a.is_symlink() for a in (p, *p.parents)), 'symlink-forbidden')
    return p


def private_dir(value):
    p = path(str(value))
    try:
        info = p.stat()
    except FileNotFoundError:
        raise Held('required-directory-missing',field='private-directory',reference=dict(path=str(p))) from None
    if not (stat.S_ISDIR(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700):
        raise Held('private-directory-required',field='private-directory',reference=dict(path=str(p)))
    need(len(p.parts)>=4 and p!=Path.home() and not p.is_relative_to(ROOT), 'narrow-private-outside-repo-required')
    return p


def raw_file(value, *, private=True, limit=FILE_LIMIT):
    p = path(str(value))
    try:
        fd = os.open(p, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:
        raise Held('required-file-missing',reference=dict(path=str(p))) from None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        need(stat.S_ISREG(info.st_mode) and info.st_uid in ({os.getuid()} if private else {0, os.getuid()}), 'file-type-or-owner')
        need(stat.S_IMODE(info.st_mode)==0o600 if private else not info.st_mode&0o022, 'file-permissions')
        need(info.st_size<=limit, 'file-budget')
        raw = stream.read(limit+1)
        after = os.fstat(stream.fileno())
        need(len(raw)<=limit and (info.st_ino,info.st_size,info.st_mtime_ns)==
             (after.st_ino,after.st_size,after.st_mtime_ns), 'file-changed')
    return raw


def ref_shape(ref):
    keys(ref, ('path', 'sha256', 'bytes'))
    need(type(ref['sha256']) is str and re.fullmatch('[0-9a-f]{64}',ref['sha256']), 'invalid-sha256')
    need(integer(ref['bytes'])<=FILE_LIMIT, 'file-budget')


def reference(p):
    raw = raw_file(p)
    return dict(path=str(p), sha256=sha(raw), bytes=len(raw))


class Inputs:
    def __init__(self):
        self.raw = {}

    def read(self, ref, *, code=False, limit=FILE_LIMIT):
        ref_shape(ref)
        p = path(ref['path'])
        if not code:
            private_dir(p.parent)
        try:
            raw = raw_file(p, private=not code, limit=limit)
        except Held as error:
            error.field = error.field or ('runtime_files' if code else 'inputs')
            error.reference = dict(ref)
            raise
        if len(raw)!=ref['bytes'] or sha(raw)!=ref['sha256']:
            raise Held('hash-or-size-mismatch',field='runtime_files' if code else 'inputs',reference=dict(ref))
        self.raw[str(p)] = (raw, code)
        need(len(self.raw)<=256 and sum(len(v[0]) for v in self.raw.values())<=TOTAL_LIMIT, 'input-budget')
        return raw

    def document(self, ref):
        return decode(self.read(ref, limit=CONTROL_LIMIT))

    def unchanged(self):
        for name,(old,code) in self.raw.items():
            need(raw_file(name, private=not code)==old, 'input-changed')


def module_from_bytes(name, filename, raw):
    # No filesystem imports/pyc for the frozen standard-library-only helpers.
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(filename))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(filename)
    exec(compile(raw, str(filename), 'exec'), module.__dict__)
    return module


def sync_dir(directory):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write(directory, name, value):
    raw = value if type(value) is bytes else encoded(value)
    fd = os.open(directory/name, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    sync_dir(directory)


def stage(directory, name, plan_sha, **fields):
    write(directory, name, dict(plan_sha256=plan_sha, recorded_at_ms=now_ms(), **fields))


def prepare(plan_path, expected_sha):
    inputs = Inputs()
    private_dir(Path(plan_path).parent)
    raw = raw_file(plan_path, limit=CONTROL_LIMIT)
    need(sha(raw)==expected_sha, 'plan-hash-mismatch')
    plan = decode(raw)
    keys(plan, ('schema_version','workflow_id','runner','python','runtime_files','inputs',
                'attempt_parent','target_claim_parent','resources','expected_outputs'))
    need(type(plan['schema_version']) is int and plan['schema_version']==1, 'plan-version')
    need(type(plan['workflow_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,96}',plan['workflow_id']), 'workflow-id')
    runner = plan['runner']
    need(runner in ALIASES, 'unsupported-runner')
    need(encoded(plan['resources'])==encoded(LIMITS[runner]), 'resource-contract')
    ref_shape(plan['python'])
    need(plan['python']['path']==PYTHON, 'configured-python-required')
    runtime = Path(PYTHON).resolve()
    pyraw = raw_file(runtime, private=False)
    need(sha(pyraw)==plan['python']['sha256'] and len(pyraw)==plan['python']['bytes'], 'python-identity-mismatch')
    required = COMMON_FILES | (QUALITY_FILES if runner=='quality-scorecard161' else set())
    need(type(plan['runtime_files']) is list and len(plan['runtime_files'])==len(required), 'runtime-set')
    buffers = {}
    for ref in plan['runtime_files']:
        need(ref['path'] in {str(ROOT/n) for n in required} and ref['path'] not in buffers, 'runtime-set')
        buffers[ref['path']] = inputs.read(ref, code=True)
    private_dir(plan['attempt_parent'])
    private_dir(plan['target_claim_parent'])
    need(plan['attempt_parent']!=plan['target_claim_parent'], 'private-root-overlap')
    child = plan['inputs']
    if runner=='quality-scorecard161':
        keys(child, ('bundle','output_parent'))
        output = private_dir(child['output_parent'])
        bundle = inputs.document(child['bundle'])
        keys(bundle, ('schema_version','kind','analysis','financial_review'))
        need(type(bundle['schema_version']) is int and bundle['schema_version']==1
             and bundle['kind']=='quality-scorecard-inputs', 'child-bundle-schema')
        analysis = inputs.document(bundle['analysis'])
        financial = inputs.document(bundle['financial_review'])
        need(type(analysis['schema_version']) is int and analysis['schema_version']==1
             and analysis['qualification_policy'] is None and type(financial) is dict, 'evaluation-contract')
        cutoff = analysis['review_at']
        need(type(cutoff) is str and datetime.fromisoformat(cutoff.replace('Z','+00:00')).utcoffset() is not None,
             'frozen-review-time-required')
        expected = plan['expected_outputs']
        keys(expected, ('artifacts','summary','review_at'))
        need(expected['review_at']==cutoff and set(expected['artifacts'])==OUTPUTS, 'expected-output-contract')
        for entry in expected['artifacts'].values():
            keys(entry, ('sha256','bytes'))
            ref_shape(dict(path='/unused', **entry))
        target = output/('scorecard-'+child['bundle']['sha256'][:20])
        argv = [PYTHON,'-I','-B',str(ROOT/FOLDER/'quality_scorecard.py'),'--bundle',child['bundle']['path'],
                '--bundle-sha256',child['bundle']['sha256'],'--output-parent',str(output)]
    else:
        keys(child, ('bundle','child_release','inspection_bundle'))
        need(plan['expected_outputs'] is None, 'unexpected-output-contract')
        bundle = inputs.document(child['bundle'])
        release = inputs.document(child['child_release'])
        need(bundle.get('kind')=='praesagus-reviewed-inference-bundle'
             and release['bundle_sha256']==child['bundle']['sha256']
             and type(release['run_id']) is str and re.fullmatch('[A-Za-z0-9_-]{1,96}',release['run_id']), 'child-release-binding')
        output = private_dir(bundle['output_parent'])
        target = output/release['run_id']
        inspection = inputs.document(child['inspection_bundle'])
        descriptors = [d for d in inspection['products'] if d['product']=='us30']
        need(len(descriptors)==1 and descriptors[0]['bundle']==child['bundle']
             and descriptors[0]['release']==child['child_release'] and descriptors[0]['attempt']==str(target),
             'inspection-target-binding')
        argv = [PYTHON,'-I','-B',str(ROOT/FOLDER/'run_reviewed_batch.py'),'--bundle',child['bundle']['path'],
                '--bundle-sha256',child['bundle']['sha256'],'--release',child['child_release']['path']]
    need(Path(plan['target_claim_parent'])==output/'.run-and-deliver-claims','shared-target-claim-root-required')
    attempt = Path(plan['attempt_parent'])/plan['workflow_id']
    need(not target.is_relative_to(attempt) and not attempt.is_relative_to(target)
         and all(not Path(p).is_relative_to(target) and not Path(p).is_relative_to(attempt) for p in inputs.raw), 'output-input-overlap')
    need(not target.is_relative_to(Path(plan['target_claim_parent']))
         and not Path(plan['target_claim_parent']).is_relative_to(target), 'target-claim-overlap')
    need(len({str(Path(p).parent) for p,(_,code) in inputs.raw.items() if not code})<=12, 'root-budget')
    inspector = module_from_bytes('_delivery163', ROOT/FOLDER/'inspect_delivery.py', buffers[str(ROOT/FOLDER/'inspect_delivery.py')])
    return dict(plan=plan,sha=expected_sha,raw=raw,plan_path=str(plan_path),inputs=inputs,buffers=buffers,
                target=target,attempt=attempt,argv=argv,inspector=inspector)


def original_output(context, *, current=False):
    p = context['plan']
    if p['runner']=='quality-scorecard161':
        target = private_dir(context['target'])
        need({x.name for x in target.iterdir()}==OUTPUTS, 'child-output-set')
        refs = {}
        for name in sorted(OUTPUTS):
            expected = p['expected_outputs']['artifacts'][name]
            raw = raw_file(target/name)
            need(sha(raw)==expected['sha256'] and len(raw)==expected['bytes'], 'child-artifact-mismatch')
            refs[name] = dict(path=str(target/name), **expected)
        result = decode(raw_file(target/'scorecard.json'))
        provenance = decode(raw_file(target/'provenance.json'))
        need(result['summary']==p['expected_outputs']['summary'] and result['review_at']==p['expected_outputs']['review_at']
             and provenance['bundle']==p['inputs']['bundle'], 'child-result-binding')
        need(provenance['operations']==dict(provider_calls=0,fit=False,prediction=False,model_artifact_loaded=False), 'evaluation-operation-mismatch')
        return dict(status='evaluation-complete',artifacts=refs,counts=result['summary'],review_at=result['review_at'],
                    folder=str(target),promotion=False)
    ref = p['inputs']['inspection_bundle']
    view = context['inspector'].inspect(ref['path'],ref['sha256'],datetime.now(timezone.utc).isoformat())
    us = next(x for x in view['products'] if x['product']=='us30')
    context['current_readiness'] = view
    need(us['disposition'] in ('completed','partial'), 'original-us30-not-complete')
    result = dict(status='forecast-complete' if us['disposition']=='completed' else 'forecast-partial',
                  counts=us['historical_counts'],original_receipt=us['original_receipt'],
                  original_bundle=us['original_bundle'],completed_at_ms=us['completed_at_ms'],promotion=False)
    if current:
        result['current_readiness'] = view
    return result


def approval(context, ref):
    p = context['plan']
    a = context['inputs'].document(ref)
    keys(a, ('schema_version','kind','approved','plan_sha256','workflow_id','runner','not_before_ms',
             'expires_at_ms','resources','resources_confirmed','exclusive_local_run_confirmed','review_reference'))
    need(type(a['schema_version']) is int and a['schema_version']==1 and a['kind']=='run-and-deliver-execution'
         and a['approved'] is True and a['resources_confirmed'] is True
         and a['exclusive_local_run_confirmed'] is True, 'outer-approval-required')
    need(a['plan_sha256']==context['sha'] and a['workflow_id']==p['workflow_id'] and a['runner']==p['runner']
         and encoded(a['resources'])==encoded(p['resources']), 'outer-approval-binding')
    start,end = integer(a['not_before_ms']),integer(a['expires_at_ms'])
    need(0<end-start<=600000 and start<=now_ms()<end, 'outer-approval-expired-or-not-started')
    reserve = (p['resources']['work_seconds']+p['resources']['cleanup_seconds'])*1000
    need(now_ms()+reserve<end, 'insufficient-release-reserve')
    review = context['inputs'].document(a['review_reference'])
    need(review.get('approved') is True and review.get('plan_sha256')==context['sha']
         and review.get('workflow_id')==p['workflow_id'], 'outer-review-binding')
    if p['runner']=='us30-reviewed155':
        release = context['inputs'].document(p['inputs']['child_release'])
        bundle = context['inputs'].document(p['inputs']['bundle'])
        need(release.get('approved') is True and integer(release['not_before_ms'])<=now_ms()
             and now_ms()+reserve<min(integer(release['expires_at_ms']),integer(bundle['issue_before_ms'])), 'child-release-window')
    return a


def supervise(argv, limits, helper):
    """Reuse 155 observed process identity/scope semantics; drain bounded pipes."""
    env = {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS','NUMBA_NUM_THREADS','LOKY_MAX_CPU_COUNT'):
        env[key] = '1'
    started = time.monotonic()
    proc = subprocess.Popen(argv,cwd='/tmp',env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
    streams = selectors.DefaultSelector()
    captured = {'stdout':bytearray(),'stderr':bytearray()}
    for stream,name in ((proc.stdout,'stdout'),(proc.stderr,'stderr')):
        os.set_blocking(stream.fileno(),False)
        streams.register(stream,selectors.EVENT_READ,name)
    owned,groups = {},{proc.pid:None}
    reason,cleaned,peak,last,gap,samples = None,False,0,started,0.,0
    cleanup_error = None
    group_signal_denied = []

    def observe():
        table = helper.process_snapshot()
        need(proc.pid not in owned or proc.pid not in table or owned[proc.pid]==table[proc.pid][3], 'process-identity-changed')
        ids = helper.process_scope(table,proc.pid,owned)
        for pid in ids:
            if table[pid][1]==pid:
                groups.setdefault(pid,table[pid][3])
        if proc.pid in table:
            groups[proc.pid] = table[proc.pid][3]
        return table,ids

    def drain():
        for key,_ in streams.select(0):
            raw = os.read(key.fd,8192)
            if not raw:
                streams.unregister(key.fileobj)
                continue
            need(len(captured[key.data])+len(raw)<=STREAM_LIMIT,'child-output-budget')
            captured[key.data].extend(raw)

    try:
        while True:
            table,ids = observe()
            sampled = time.monotonic()
            gap = max(gap,sampled-last)
            last = sampled
            samples += 1
            peak = max(peak,sum(table[pid][2] for pid in ids))
            drain()
            need(gap<=1,'monitor-gap')
            need(peak<=limits['rss_bytes'],'resource-limit')
            need(sampled-started<limits['work_seconds'],'execution-timeout')
            if proc.poll() is not None:
                need(not observe()[1],'unexpected-descendants')
                while streams.get_map():
                    before = sum(map(len,captured.values()))
                    drain()
                    need(not streams.get_map() or sum(map(len,captured.values()))>before,'pipe-cleanup-unverified')
                break
            time.sleep(.025)
    except (Exception,KeyboardInterrupt) as error:
        reason = str(error) if isinstance(error,Held) else 'supervision-failed'
    finally:
        deadline = min(started+limits['work_seconds']+limits['cleanup_seconds'],time.monotonic()+limits['cleanup_seconds'])
        while time.monotonic()<deadline:
            try:
                table,ids = observe()
                for group,birth in groups.items():
                    if group in table and birth is not None and table[group][3]!=birth:
                        reason = reason or 'process-identity-changed'
                        continue
                    if birth is None and proc.poll() is not None and helper.group_state(group) is not False:
                        reason = reason or 'cleanup-ownership-unknown'
                        continue
                    try:
                        os.killpg(group,signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        # Fall through to birth-checked individual PID cleanup. Only
                        # independently observed group absence can verify cleanup.
                        if group not in group_signal_denied:
                            group_signal_denied.append(group)
                for pid in ids:
                    if table[pid][3]==owned[pid]:
                        try:
                            os.kill(pid,signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                proc.poll()
                if proc.returncode is not None and not observe()[1] and all(helper.group_state(g) is False for g in groups):
                    cleaned = True
                    break
            except (Exception,KeyboardInterrupt) as error:
                cleanup_error = type(error).__name__
                reason = reason or 'cleanup-monitor-failed'
                for group in groups:
                    try:
                        os.killpg(group,signal.SIGKILL)
                    except OSError:
                        pass
                break
            time.sleep(.02)
        streams.close()
        proc.stdout.close()
        proc.stderr.close()
    elapsed = time.monotonic()-started
    if not cleaned:
        reason = reason or 'cleanup-unverified'
    if not owned or peak<=0:
        reason = reason or 'rss-unobserved'
    if elapsed>limits['work_seconds']+limits['cleanup_seconds']:
        reason = reason or 'supervision-total-deadline'
    return dict(approved=reason is None and proc.returncode in (0,4) and cleaned,
                returncode=proc.returncode,reason=reason,cleanup_verified=cleaned,
                cleanup_error=cleanup_error,
                group_signal_denied=group_signal_denied,
                elapsed_seconds=elapsed,peak_group_rss_bytes=peak,max_sample_gap_seconds=gap,samples=samples,
                owned_pid_births=owned,owned_groups=groups,limits=limits,
                stdout=captured['stdout'].decode('utf-8',errors='replace'),stderr=captured['stderr'].decode('utf-8',errors='replace'),
                limitations='Sampled RSS/observed PID births and groups; not a hard cap or absolute peak. Descendants escaping before observation can be missed.')


def snapshot(context):
    base = context['attempt']/'runtime'
    base.mkdir(mode=0o700)
    for relative in sorted(QUALITY_FILES):
        destination = base/relative
        parent = base
        for part in Path(relative).parent.parts:
            parent = parent/part
            parent.mkdir(mode=0o700,exist_ok=True)
        write(destination.parent,destination.name,context['buffers'][str(ROOT/relative)])
    sync_dir(context['attempt'])
    argv = list(context['argv'])
    argv[3] = str(base/FOLDER/'quality_scorecard.py')
    return argv


def stage_read(context, name):
    p = context['attempt']/name
    value = decode(raw_file(p,limit=CONTROL_LIMIT))
    need(value['plan_sha256']==context['sha'],'stage-plan-mismatch')
    return value


def seal(context, *, adopted=False,readonly=False):
    attempt = context['attempt']
    claim = stage_read(context,'claim.json')
    need(claim['runner']==context['plan']['runner'] and claim['target']==str(context['target']), 'claim-target-binding')
    if not adopted:
        intent = stage_read(context,'dispatch-intent.json')
        supervision = stage_read(context,'supervisor.json')
        result = supervision['result']
        need(supervision['intent_sha256']==reference(attempt/'dispatch-intent.json')['sha256']
             and result['approved'] is True and result['cleanup_verified'] is True
             and type(result['returncode']) is int and result['returncode'] in (0,4)
             and encoded(result['limits'])==encoded(context['plan']['resources'])
             and type(result['peak_group_rss_bytes']) is int and 0<result['peak_group_rss_bytes']<=result['limits']['rss_bytes']
             and type(result['samples']) is int and result['samples']>0 and bool(result['owned_pid_births'])
             and bool(result['owned_groups']) and 0<=result['max_sample_gap_seconds']<=1
             and 0<=result['elapsed_seconds']<=result['limits']['work_seconds']+result['limits']['cleanup_seconds'], 'original-supervision-required')
        need(all(type(result[k]) in (int,float) and math.isfinite(result[k]) for k in
             ('max_sample_gap_seconds','elapsed_seconds')),'original-supervision-required')
        for mapping in (result['owned_pid_births'],result['owned_groups']):
            need(type(mapping) is dict and all(str(pid).isdigit() and int(pid)>0 and type(birth) is str and birth
                 for pid,birth in mapping.items()),'original-supervision-required')
        need(intent['canonical_argv']==context['argv'] and intent['target']==str(context['target'])
             and intent['cwd']=='/tmp', 'dispatch-binding')
        expected_argv = list(context['argv'])
        if context['plan']['runner']=='quality-scorecard161':
            expected_argv[3] = str(attempt/'runtime'/FOLDER/'quality_scorecard.py')
            for relative in QUALITY_FILES:
                need(raw_file(attempt/'runtime'/relative)==context['buffers'][str(ROOT/relative)], 'snapshot-changed')
            stdout = decode(result['stdout'].encode())
            need(result['returncode']==0 and stdout.get('status')=='scorecard-written'
                 and stdout.get('folder')==str(context['target'])
                 and stdout.get('artifacts')==context['plan']['expected_outputs']['artifacts']
                 and stdout.get('summary')==context['plan']['expected_outputs']['summary'], 'child-success-marker')
        need(intent['actual_argv']==expected_argv,'actual-dispatch-binding')
        outer = context['inputs'].document(claim['approval'])
        need(outer['plan_sha256']==context['sha'] and outer['workflow_id']==context['plan']['workflow_id']
             and outer['approved'] is True and outer['resources_confirmed'] is True
             and outer['exclusive_local_run_confirmed'] is True
             and encoded(outer['resources'])==encoded(context['plan']['resources'])
             and intent['approval_sha256']==claim['approval']['sha256']
             and outer['not_before_ms']<=intent['recorded_at_ms']<=supervision['recorded_at_ms']<outer['expires_at_ms'], 'original-approval-window')
        review = context['inputs'].document(outer['review_reference'])
        need(review.get('approved') is True and review.get('plan_sha256')==context['sha']
             and review.get('workflow_id')==context['plan']['workflow_id'],'outer-review-binding')
        target_key = sha(encoded(dict(runner=context['plan']['runner'],target=str(context['target']))))
        target_claim = decode(raw_file(Path(context['plan']['target_claim_parent'])/(target_key+'.json')))
        need(target_claim==dict(plan_sha256=context['sha'],workflow_id=context['plan']['workflow_id'],target=str(context['target'])), 'target-claim-binding')
    else:
        need(context['plan']['runner']=='us30-reviewed155' and claim['mode']=='adopt-historical-us30','adoption-binding')
    result = original_output(context)
    context['inputs'].unchanged()
    need(raw_file(context['plan_path'],limit=CONTROL_LIMIT)==context['raw'],'plan-changed')
    child_path = attempt/'child-verified.json'
    if not child_path.exists():
        if readonly:
            return dict(status='verified-child-unsealed',result=result,child_invoked=False)
        stage(attempt,'child-verified.json',context['sha'],result=result)
    else:
        need(stage_read(context,'child-verified.json')['result']==result,'child-result-changed')
    delivery_path = attempt/'delivery.json'
    evidence_hashes = {name:reference(attempt/name)['sha256'] for name in
                       (('claim.json','child-verified.json') if adopted else
                        ('claim.json','dispatch-intent.json','supervisor.json','child-verified.json'))}
    if not adopted:
        evidence_hashes['target-claim'] = sha(raw_file(Path(context['plan']['target_claim_parent'])/(target_key+'.json')))
    if delivery_path.exists():
        delivery = stage_read(context,'delivery.json')
        need(delivery['evidence_hashes']==evidence_hashes and delivery['result']==result
             and delivery['child_sha256']==reference(child_path)['sha256']
             and delivery['adopted_historical'] is adopted
             and delivery['status']==result['status'], 'delivery-evidence-binding')
        return delivery|dict(recovered=True,child_invoked=False)
    if readonly:
        return dict(status='verified-child-unsealed',result=result,child_invoked=False)
    stage(attempt,'delivery.json',context['sha'],status=result['status'],child_sha256=reference(child_path)['sha256'],
          evidence_hashes=evidence_hashes,result=result,adopted_historical=adopted,
          child_invoked=False if adopted else True)
    return stage_read(context,'delivery.json')|dict(recovered=True,child_invoked=False)


def _operate(context,mode,approval_ref):
    p,attempt,target = context['plan'],context['attempt'],context['target']
    if mode=='inspect':
        existing = attempt.exists()
        result = None
        durable = 'planned'
        blocker = None
        if existing:
            private_dir(attempt)
            if (attempt/'delivery.json').exists():
                claim = stage_read(context,'claim.json')
                result = seal(context,adopted=claim['mode']=='adopt-historical-us30',readonly=True)
                durable = 'outer-delivered'
            elif (attempt/'supervisor.json').exists():
                result = seal(context,readonly=True)
                durable = 'child-verified' if (attempt/'child-verified.json').exists() else 'child-finished-supervisor-recorded'
            elif (attempt/'dispatch-intent.json').exists():
                stage_read(context,'dispatch-intent.json')
                durable,blocker = 'dispatch-uncertain','original-supervision-missing'
            elif (attempt/'claim.json').exists():
                stage_read(context,'claim.json')
                durable,blocker = 'claimed','dispatch-absence-not-proven'
            else:
                durable,blocker = 'interrupted-before-claim','attempt-ownership-uncertain'
        elif target.exists():
            result = original_output(context,current=True)
            durable = 'retained-child' if p['runner']=='us30-reviewed155' else 'unsealed-child-files'
            if p['runner']=='quality-scorecard161':
                result['status']='unsealed-child-files'
                blocker='original-supervision-missing'
        context['inputs'].unchanged()
        need(raw_file(context['plan_path'],limit=CONTROL_LIMIT)==context['raw'],'plan-changed')
        return dict(status='inspection',workflow_id=p['workflow_id'],runner=p['runner'],target=str(target),
                    stage=durable,blocker=blocker,original=result,child_invoked=False,
                    current_readiness=context.get('current_readiness'),
                    next_action='Review the uncertain original attempt; never redispatch.' if blocker else
                    'Recover verified completed evidence, or request exact finite execution approval for a new unconsumed target.')
    if mode=='recover':
        context['phase']='recovery'
        if not attempt.exists():
            need(p['runner']=='us30-reviewed155','no-completed-supervised-workflow')
            original_output(context)  # Verify historical authority before creating any outer evidence.
            attempt.mkdir(mode=0o700)
            sync_dir(attempt.parent)
            stage(attempt,'claim.json',context['sha'],runner=p['runner'],target=str(target),mode='adopt-historical-us30')
        private_dir(attempt)
        claim = stage_read(context,'claim.json')
        return seal(context,adopted=claim['mode']=='adopt-historical-us30')
    need(approval_ref is not None,'finite-outer-approval-required')
    context['phase']='authorization'
    approved = approval(context,approval_ref)
    need(not attempt.exists() and not target.exists(),'attempt-or-target-consumed')
    context['inputs'].unchanged()
    context['phase']='claim'
    try:
        attempt.mkdir(mode=0o700)
    except FileExistsError:
        raise Held('attempt-or-target-consumed') from None
    sync_dir(attempt.parent)
    stage(attempt,'claim.json',context['sha'],runner=p['runner'],target=str(target),mode='execute',approval=approval_ref)
    target_key = sha(encoded(dict(runner=p['runner'],target=str(target))))
    try:
        write(Path(p['target_claim_parent']),target_key+'.json',dict(plan_sha256=context['sha'],workflow_id=p['workflow_id'],target=str(target)))
    except FileExistsError:
        raise Held('target-already-claimed') from None
    context['phase']='snapshot'
    argv = snapshot(context) if p['runner']=='quality-scorecard161' else context['argv']
    approval(context,approval_ref)
    need(not target.exists(),'attempt-or-target-consumed')
    context['inputs'].unchanged()
    context['phase']='dispatch'
    stage(attempt,'dispatch-intent.json',context['sha'],canonical_argv=context['argv'],actual_argv=argv,cwd='/tmp',target=str(target),approval_sha256=approval_ref['sha256'])
    helper = module_from_bytes('_supervisor163',ROOT/FOLDER/'run_reviewed_batch.py',context['buffers'][str(ROOT/FOLDER/'run_reviewed_batch.py')])
    supervision = supervise(argv,p['resources'],helper)
    context['phase']='supervision'
    stage(attempt,'supervisor.json',context['sha'],intent_sha256=reference(attempt/'dispatch-intent.json')['sha256'],result=supervision)
    need(supervision['approved'] is True,'child-failed-or-cleanup-unverified')
    need(now_ms()<approved['expires_at_ms'],'outer-approval-expired-after-child')
    if p['runner']=='quality-scorecard161':
        need(supervision['returncode']==0,'evaluation-child-failed')
        stdout = decode(supervision['stdout'].encode())
        need(stdout.get('status')=='scorecard-written' and stdout.get('folder')==str(target), 'child-success-marker')
    context['phase']='verification'
    return seal(context)|dict(recovered=False,child_invoked=True)


def operate(plan_path,plan_sha256,mode='inspect',approval_ref=None):
    need(mode in ('inspect','execute','recover'),'unsupported-mode')
    context = prepare(plan_path,plan_sha256)
    context['phase']=mode
    try:
        return _operate(context,mode,approval_ref)
    except Held as error:
        error.stage=error.stage or context['phase']
        error.scope=dict(workflow_id=context['plan']['workflow_id'],runner=context['plan']['runner'],target=str(context['target']))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--mode',choices=('inspect','execute','recover'),default='inspect')
    parser.add_argument('--approval')
    parser.add_argument('--approval-sha256')
    args = parser.parse_args(argv)
    try:
        need(sys.flags.isolated,'isolated-python-required')
        approval_ref = None
        if args.approval or args.approval_sha256:
            need(args.approval and args.approval_sha256,'approval-reference-incomplete')
            approval_ref = dict(path=args.approval,sha256=args.approval_sha256,bytes=len(raw_file(args.approval,limit=CONTROL_LIMIT)))
        result = operate(args.plan,args.plan_sha256,args.mode,approval_ref)
        print(json.dumps(result,allow_nan=False))
        return 0
    except (Exception,KeyboardInterrupt) as error:
        reason = str(error) if isinstance(error,Held) else 'missing-malformed-or-uncertain-evidence'
        authorization = any(x in reason for x in ('approval','release','review'))
        field = error.field if isinstance(error,Held) else None
        if not field and isinstance(error,KeyError):
            field = str(error.args[0]) if re.fullmatch('[A-Za-z0-9_.-]{1,96}',str(error.args[0])) else 'input-schema'
        print(json.dumps(dict(status='held',reason=reason,owner='Lead' if authorization else 'Engineer',
            stage=error.stage if isinstance(error,Held) and error.stage else 'input-validation',
            field=field or ('approval/release/review' if authorization else 'workflow-evidence'),
            reference=error.reference if isinstance(error,Held) else None,
            affected_scope=error.scope if isinstance(error,Held) else None,
            next_action='Obtain an exact reviewed finite approval for the pinned plan/current child window; preserve consumed attempts.' if authorization else
            'Locate the exact reviewed bytes or original successful supervision at the reported stage/reference; preserve uncertain claims and request review before any new attempt.'),allow_nan=False))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
