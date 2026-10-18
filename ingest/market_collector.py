"""Explicit private collection. Credentials/network worker never opens SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time
from urllib.parse import urlencode

from connectors.moomoo_rest import MoomooRESTConnector, ReadRequest, ReadResponse, RESTError
from connectors.moomoo_rest_live import (EncryptedEd25519Signer, SecureReadTransport,
                                        encrypted_pem, keychain_passphrase)
from ingest.private_market_store import (MAX_RAW, REPO, PrivateMarketStore, canonical,
    decode, normalized, parse_aware, private, request_meta, safe, MarketStoreError, HISTORY_STAGES, valid_structure, unavailable_structure)

MAX_INPUT = 65536
MAX_HEADER = 4096
MAX_OUTPUT = MAX_RAW + MAX_HEADER + 4
ENTRY = str(REPO / 'scripts/market_collect.py')
FAILURES = frozenset({'credentials', 'timeout', 'transport', 'invalid-response', 'rate-limited',
    'upstream-failed', 'http-failed', 'worker-failed', 'deadline', 'bad-frame', 'cleanup-failed',
    'run-budget', 'storage-failed', 'clock-order'})


class CollectorError(ValueError):
    """Controlled failure only; never exception/provider/credential text."""


def require(condition):
    if not condition:raise CollectorError('collector-invalid-input')


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def job_request(job):
    require(isinstance(job, dict))
    if job.get('kind') == 'snapshot':
        require(set(job) == {'kind', 'codes'})
        request = ReadRequest('POST', '/api/v1.0/quote/snapshot', '',
            canonical({'code_list': job['codes']}).encode(), {}, 10)
    elif job.get('kind') == 'history':
        require(set(job) == {'kind','code','end'} and isinstance(job['code'],str)
                and (re.fullmatch(r'US\.[A-Z][A-Z0-9.-]*',job['code']) or job['code']=='BMS.1155')
                and isinstance(job['end'],str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',job['end']))
        request = ReadRequest('GET',f"/api/v1.0/quote/{job['code']}/history-kline",
            urlencode([('end',job['end']),('ktype',2),('autype',0),('num',100)]),b'',{},10)
    else:
        require(set(job) == {'kind', 'keyword', 'size', 'lang'} and job['kind'] == 'news'
                and type(job['size']) is int and isinstance(job['keyword'], str))
        request = ReadRequest('GET', '/api/v1.0/quote/find-news',
            urlencode([('symbol', job['keyword']), ('size', job['size']), ('sort_type', 2), ('lang', job['lang'])]), b'', {}, 10)
    request_meta(request)
    return request


def validate_plan(plan):
    require(isinstance(plan, dict) and set(plan) in ({'schema_version', 'codes', 'news'},
            {'schema_version', 'codes', 'news', 'history'})
            and type(plan['schema_version']) is int and plan['schema_version'] == 1
            and isinstance(plan['codes'], list) and isinstance(plan['news'], list)
            and len(plan['news']) <= 10)
    jobs = []
    if plan['codes']:jobs.append({'kind': 'snapshot', 'codes': plan['codes']})
    history=plan.get('history',[])
    require(isinstance(history,list) and len(history)<=30
            and all(isinstance(item,dict) and set(item)=={'code','end'} for item in history)
            and len({item.get('code') for item in history})==len(history))
    for item in history:jobs.append({'kind':'history',**item})
    for query in plan['news']:
        require(isinstance(query, dict) and set(query) == {'keyword', 'size', 'lang'})
        jobs.append({'kind': 'news', **query})
    require(bool(jobs))
    for job in jobs:job_request(job)
    require(len({job_digest(j) for j in jobs}) == len(jobs))
    return jobs


def job_digest(job):
    return hashlib.sha256(canonical(job).encode()).hexdigest()


def validate_locator(locator):
    require(isinstance(locator, dict) and set(locator) == {'directory', 'app_key_name'}
            and isinstance(locator['directory'], str) and len(locator['directory']) <= 4096
            and isinstance(locator['app_key_name'], str)
            and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', locator['app_key_name'])
            and locator['app_key_name'] != 'private.pem')
    root = Path(locator['directory'])
    require(root.is_absolute() and root == root.resolve() and not root.is_relative_to(REPO)
            and not any(p.lower() in {'public', 'www', 'htdocs', 'artifacts', 'dist'} for p in root.parts))
    return root


def load_credentials(locator, *, signer_factory=EncryptedEd25519Signer, passphrase_loader=keychain_passphrase):
    def load():
        root = validate_locator(locator);private(root, directory=True)
        pem = encrypted_pem(root / 'private.pem')
        key_file = root / locator['app_key_name']
        private(key_file, readonly=(key_file.lstat().st_mode & 0o777 == 0o400))
        fd = os.open(key_file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as f:
            info = os.fstat(f.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and stat.S_IMODE(info.st_mode) in (0o400, 0o600))
            raw = f.read(514)
        if raw.endswith(b'\n'):raw = raw[:-1]
        require(0 < len(raw) <= 512)
        key = raw.decode('ascii')
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,512}', key) is not None)
        signer = signer_factory(pem_loader=lambda: pem,
                                passphrase_loader=passphrase_loader)
        return key, signer
    return safe(load, category='credentials-unavailable')


@dataclass(frozen=True, repr=False)
class WorkerReply:
    response: ReadResponse | None
    observed_at: str | None
    failure: str | None
    cleanup_ok: bool = True
    diagnostic_stage: str | None = None
    normalization_version: int | None = None
    diagnostic_structure: dict | None = None
    def __repr__(self):return '<PrivateCollectorReply>'


@dataclass(frozen=True, repr=False)
class JobOutcome:
    job_id: str
    status: str
    attempt_id: str | None
    failure: str | None
    diagnostic_stage: str | None = None
    normalization_version: int | None = None
    diagnostic_structure: dict | None = None
    def __repr__(self):return '<PrivateCollectorOutcome>'


def valid_stage(job, status, failure, stage, *, legacy=False):
    eligible = job.get('kind') == 'history' and status == 200 and failure == 'invalid-response'
    if eligible:
        return (legacy and stage is None) or type(stage) is str and stage in HISTORY_STAGES
    return stage is None


def normalization_for(job, version=None, *, current=False):
    expected = (4 if current else 3) if job.get('kind')=='history' else 2 if job.get('kind')=='snapshot' else 1
    if version is None:return expected
    require(type(version) is int and (job.get('kind')=='history' and version in (3,4)
            or job.get('kind')=='snapshot' and version==2 or job.get('kind')=='news' and version==1))
    return version


def valid_diagnostic_structure(job, status, failure, stage, version, structure):
    eligible=job.get('kind')=='history' and status==200 and failure=='invalid-response' and version==4
    if not eligible:return structure is None
    return (valid_structure(structure) and
            (stage!='decode-screen' or structure['status']=='unavailable'))


def encode_reply(job, response, observed_at, failure=None, retry_after=None, diagnostic_stage=None,
                 *, frame_version=2, normalization_version=None, diagnostic_structure=None):
    require(failure is None or type(failure) is str and failure in FAILURES)
    require(valid_stage(job, response.status, failure, diagnostic_stage))
    require(failure is None or response.body == b'')
    require(type(frame_version) is int and frame_version in (2,3))
    version=normalization_for(job,normalization_version,current=frame_version==3)
    require(frame_version!=2 or normalization_version is None and diagnostic_structure is None)
    require(frame_version!=3 or version==normalization_for(job,current=True))
    require(valid_diagnostic_structure(job,response.status,failure,diagnostic_stage,version,diagnostic_structure))
    header = {'version': frame_version, 'job_digest': job_digest(job), 'status': response.status,
              'observed_at': observed_at, 'failure': failure, 'body_size': len(response.body),
              'retry_after': retry_after, 'diagnostic_stage': diagnostic_stage}
    if frame_version==3:header.update(normalization_version=version,diagnostic_structure=diagnostic_structure)
    payload = canonical(header).encode()
    require(len(payload) <= MAX_HEADER and len(response.body) <= MAX_RAW)
    return struct.pack('!I', len(payload)) + payload + response.body


def parse_reply(raw, job):
    require(isinstance(raw, bytes) and 4 <= len(raw) <= MAX_OUTPUT)
    size = struct.unpack('!I', raw[:4])[0]
    require(0 < size <= MAX_HEADER and len(raw) >= 4 + size)
    header = decode(raw[4:4+size])
    keys = {'version', 'job_digest', 'status', 'observed_at', 'failure', 'body_size', 'retry_after'}
    require(isinstance(header, dict) and type(header.get('version')) is int
            and header['version'] in (1,2,3)
            and set(header) == (keys if header['version']==1 else keys | {'diagnostic_stage'}
                 if header['version']==2 else keys | {'diagnostic_stage','normalization_version','diagnostic_structure'}))
    stage = header.get('diagnostic_stage')
    version=normalization_for(job,header.get('normalization_version'))
    structure=header.get('diagnostic_structure')
    require(header['version']!=3 or version==normalization_for(job,current=True)
            and header['normalization_version'] is not None)
    require(valid_diagnostic_structure(job,header['status'],header['failure'],stage,version,structure))
    require(header['job_digest'] == job_digest(job)
            and type(header['body_size']) is int and 0 <= header['body_size'] <= MAX_RAW
            and len(raw) == 4 + size + header['body_size']
            and type(header['status']) is int and (header['status'] == 0 or 100 <= header['status'] <= 599)
            and (header['failure'] is None or type(header['failure']) is str and header['failure'] in FAILURES)
            and (header['retry_after'] is None or type(header['retry_after']) is int and 0 <= header['retry_after'] <= 86400)
            and valid_stage(job, header['status'], header['failure'], stage, legacy=header['version']==1))
    require(parse_aware(header['observed_at']).utcoffset().total_seconds() == 0)
    body = raw[4+size:]
    if header['failure'] is None:
        require(header['status'] == 200)
        kind, query, _ = request_meta(job_request(job))
        normalized(body, kind, query, version=version)
    else:require(not body)
    return WorkerReply(ReadResponse(header['status'], body), header['observed_at'], header['failure'],
                       diagnostic_stage=stage,normalization_version=version,diagnostic_structure=structure)


def execute_job(job, locator, *, credentials=load_credentials, transport_factory=SecureReadTransport, clock=utc_now):
    """Worker memory only; shared policy screens headers/known secrets pre-IPC."""
    job_request(job);validate_locator(locator)
    version=normalization_for(job,current=True)
    def reply(response,observed,failure=None,*,stage=None,structure=None):
        return encode_reply(job,response,observed,failure,diagnostic_stage=stage,frame_version=3,
                            normalization_version=version,diagnostic_structure=structure)
    captured = None
    observed = None
    failure = None
    screening_rejected = False
    diagnostic_stage = None
    diagnostic_structure = None
    try:key, signer = credentials(locator)
    except Exception:failure = 'credentials'
    if failure:
        return reply(ReadResponse(0,b''),clock(),failure)
    def capture(request):
        nonlocal captured, observed, screening_rejected, diagnostic_stage, diagnostic_structure
        response = transport(request)
        require(isinstance(response, ReadResponse) and type(response.status) is int
                and 100 <= response.status <= 599)
        observed = clock();parse_aware(observed)
        captured = ReadResponse(response.status, b'')
        if response.status == 200:
            kind, query, secrets = request_meta(request)
            try:
                normalized(response.body, kind, query, (*secrets, key, locator['directory']),
                           version=version)
            except Exception as error:
                screening_rejected = True
                if kind == 'history':
                    stage = error.diagnostic_stage if type(error) is MarketStoreError else None
                    diagnostic_stage = stage if type(stage) is str and stage in HISTORY_STAGES else 'unknown'
                    structure=error.diagnostic_structure if type(error) is MarketStoreError else None
                    diagnostic_structure=structure if valid_structure(structure) else unavailable_structure()
                raise
        captured = response
        return response
    try:
        transport = transport_factory()
        client = MoomooRESTConnector(api_key=key, signer=signer, transport=capture,
            clock_ms=lambda: time.time_ns() // 1000000, nonce_factory=lambda: os.urandom(16).hex(), timeout=10)
        if job['kind'] == 'snapshot':client.snapshot(job['codes'])
        elif job['kind']=='history':client.history_kline(job['code'],job['end'],num=100,ktype=2,autype=0)
        else:client.search_news(job['keyword'], size=job['size'], sort_type=2, lang=job['lang'])
    except RESTError as error:
        failure = {'timeout':'timeout', 'rate-limited':'rate-limited', 'upstream-failed':'upstream-failed',
                   'http-failed':'http-failed', 'malformed-response':'invalid-response',
                   'provider-failed':'invalid-response'}.get(error.kind, 'transport')
        if not screening_rejected and job['kind']=='history' and captured is not None and captured.status==200:
            if error.kind in ('malformed-response','provider-failed'):
                diagnostic_stage='core-validation';diagnostic_structure=unavailable_structure()
    except Exception:failure = 'worker-failed'
    if screening_rejected:failure = 'invalid-response'
    if captured is None:return reply(ReadResponse(0,b''),clock(),failure or 'worker-failed')
    if failure:
        # The exact body is deliberately not emitted when shape/core validation fails.
        return reply(ReadResponse(captured.status,b''),observed,failure,stage=diagnostic_stage,structure=diagnostic_structure)
    return reply(ReadResponse(200,captured.body),observed)


def worker_main(stdin, stdout):
    failed = False
    job = None
    try:
        prefix = stdin.read(4)
        require(len(prefix) == 4)
        size = struct.unpack('!I', prefix)[0];require(0 < size <= MAX_INPUT)
        packet = stdin.read(size);require(len(packet) == size and stdin.read(1) == b'')
        data = decode(packet)
        require(isinstance(data, dict) and set(data) == {'version', 'job', 'job_digest', 'locator'}
                and type(data['version']) is int and data['version'] == 1)
        job = data['job'];job_request(job);require(data['job_digest'] == job_digest(job))
        frame = execute_job(job, data['locator'])
    except Exception:failed = True
    if failed:return 1
    stdout.write(frame);stdout.flush();return 0


def cleanup_process(process, budget, *, clock=time.monotonic, killpg=os.killpg):
    end = clock() + budget
    ok = True
    def send(sig):
        nonlocal ok
        try:killpg(process.pid, sig)
        except ProcessLookupError:pass
        except Exception:ok = False
    send(signal.SIGTERM)
    try:
        remaining = end-clock()
        if remaining > 0:process.wait(timeout=min(budget/2, remaining))
    except subprocess.TimeoutExpired:pass
    except Exception:ok = False
    send(signal.SIGKILL)
    try:
        remaining = end-clock()
        if process.poll() is None and remaining <= 0:ok = False
        elif remaining > 0:process.wait(timeout=remaining)
    except Exception:ok = False
    try:return ok and process.poll() is not None
    except Exception:return False


def supervise(job, locator, *, timeout=20.0, cleanup=2.0, popen=subprocess.Popen,
              clock=time.monotonic, killer=os.killpg):
    job_request(job);validate_locator(locator)
    require(type(timeout) in (int, float) and 0 < timeout <= 20
            and type(cleanup) in (int, float) and 0 < cleanup <= 2)
    data = canonical({'version': 1, 'job': job, 'job_digest': job_digest(job), 'locator': locator}).encode()
    require(len(data) <= MAX_INPUT)
    outgoing = struct.pack('!I', len(data)) + data
    deadline = clock() + timeout
    process = None
    failure = None
    raw = bytearray()
    sent = 0
    eof = False
    cleanup_ok = True
    try:
        process = popen([sys.executable, ENTRY, '--worker'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True,
            shell=False, cwd=str(REPO), env={'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1'})
        with selectors.DefaultSelector() as selector:
            os.set_blocking(process.stdin.fileno(), False);os.set_blocking(process.stdout.fileno(), False)
            selector.register(process.stdin, selectors.EVENT_WRITE, 'input')
            selector.register(process.stdout, selectors.EVENT_READ, 'output')
            while True:
                remaining = deadline-clock()
                if remaining <= 0:failure = 'deadline';break
                if eof and sent == len(outgoing):
                    try:process.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:failure = 'deadline'
                    break
                for key, _ in selector.select(remaining):
                    if key.data == 'input':
                        count = os.write(key.fileobj.fileno(), outgoing[sent:sent+65536]);sent += count
                        if sent == len(outgoing):selector.unregister(key.fileobj);key.fileobj.close()
                    else:
                        chunk = os.read(key.fileobj.fileno(), min(65536, MAX_OUTPUT+1-len(raw)))
                        if not chunk:eof = True;selector.unregister(key.fileobj)
                        else:
                            raw.extend(chunk)
                            if len(raw) > MAX_OUTPUT:failure = 'bad-frame';break
                            if len(raw) >= 4 and struct.unpack('!I', raw[:4])[0] > MAX_HEADER:failure = 'bad-frame';break
                if failure:break
        if failure is None and process.returncode != 0:failure = 'worker-failed'
    except Exception:failure = 'worker-failed'
    finally:
        if process is not None:
            cleanup_ok = cleanup_process(process, cleanup, clock=clock, killpg=killer)
            for stream in (process.stdin, process.stdout):
                try:
                    if stream is not None:stream.close()
                except Exception:cleanup_ok = False
    if not cleanup_ok:return WorkerReply(None,None,'cleanup-failed',False,normalization_version=normalization_for(job,current=True))
    if failure:return WorkerReply(None,None,failure,normalization_version=normalization_for(job,current=True))
    try:reply = parse_reply(bytes(raw), job)
    except Exception:return WorkerReply(None, None, 'bad-frame')
    return reply


def collect(store, plan, locator, *, run_id, supervisor=supervise, clock=time.monotonic,
            wall=utc_now, job_seconds=20.0, cleanup_seconds=2.0, run_seconds=300.0):
    jobs = validate_plan(plan);validate_locator(locator)
    require(isinstance(run_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id)
            and type(run_seconds) in (int, float) and 0 < run_seconds <= 300
            and type(job_seconds) in (int, float) and 0 < job_seconds <= 20
            and type(cleanup_seconds) in (int, float) and 0 < cleanup_seconds <= 2)
    end = clock() + run_seconds
    outcomes = []
    last_ingested = None
    for index, job in enumerate(jobs):
        remaining = end-clock()
        if remaining <= cleanup_seconds:
            outcomes.extend(JobOutcome(job_digest(j), 'unattempted', None, 'run-budget') for j in jobs[index:]);break
        try:
            started_time = parse_aware(wall())
            require(started_time.utcoffset().total_seconds() == 0
                    and (last_ingested is None or started_time >= last_ingested))
        except Exception:
            outcomes.append(JobOutcome(job_digest(job), 'not-persisted', None, 'clock-order'));break
        reply = supervisor(job, locator, timeout=min(job_seconds, remaining-cleanup_seconds), cleanup=cleanup_seconds)
        # Injected supervisors obey the same bounded failure/stage contract as IPC.
        if type(reply) is not WorkerReply or type(reply.cleanup_ok) is not bool:
            reply = WorkerReply(None, None, 'bad-frame')
        elif not reply.cleanup_ok:
            reply = WorkerReply(None, None, 'cleanup-failed', False)
        else:
            response_ok = reply.response is None or (
                isinstance(reply.response, ReadResponse) and type(reply.response.status) is int
                and (reply.response.status == 0 or 100 <= reply.response.status <= 599)
                and isinstance(reply.response.body, bytes) and len(reply.response.body) <= MAX_RAW)
            failure_ok = reply.failure is None or type(reply.failure) is str and reply.failure in FAILURES
            status = reply.response.status if response_ok and reply.response is not None else 0
            stage_ok = valid_stage(job,status,reply.failure,reply.diagnostic_stage,legacy=True)
            try:
                version=normalization_for(job,reply.normalization_version)
                structure_ok=valid_diagnostic_structure(job,status,reply.failure,reply.diagnostic_stage,version,reply.diagnostic_structure)
            except Exception:structure_ok=False
            if (not response_ok or not failure_ok or not stage_ok or not structure_ok
                    or reply.failure is not None and reply.response is not None and reply.response.body != b''):
                reply = WorkerReply(None, None, 'bad-frame')
        observed = reply.observed_at if reply.response is not None else wall()
        ingested = wall()
        clock_bad = False
        try:
            observed_time = parse_aware(observed);ingested_time = parse_aware(ingested)
            clock_bad = (ingested_time < observed_time or observed_time < started_time
                         or observed_time.utcoffset().total_seconds() != 0
                         or ingested_time.utcoffset().total_seconds() != 0
                         or (last_ingested is not None and observed_time < last_ingested))
        except Exception:clock_bad = True
        if clock_bad:
            outcomes.append(JobOutcome(job_digest(job), 'not-persisted', None, 'clock-order'));break
        over_budget = clock() >= end
        response = reply.response or ReadResponse(0, b'')
        failed = False
        try:stored = store.ingest(job_request(job),response,run_id=run_id,observed_at=observed,ingested_at=ingested,
                                 normalization_version=normalization_for(job,reply.normalization_version))
        except Exception:failed = True
        if failed:
            outcomes.append(JobOutcome(job_digest(job), 'not-persisted', None, 'storage-failed'));break
        last_ingested = ingested_time
        over_budget = over_budget or clock() >= end
        outcomes.append(JobOutcome(job_digest(job), stored.status, stored.attempt_id,
                                   reply.failure or ('run-budget' if over_budget else None),
                                   reply.diagnostic_stage if reply.failure=='invalid-response' else None,
                                   normalization_for(job,reply.normalization_version),
                                   reply.diagnostic_structure if reply.failure=='invalid-response' else None))
        if not reply.cleanup_ok or over_budget:
            reason = 'cleanup-failed' if not reply.cleanup_ok else 'run-budget'
            outcomes.extend(JobOutcome(job_digest(j), 'unattempted', None, reason) for j in jobs[index+1:])
            break
    return outcomes


class DiagnosticReceipt:
    """Preflight private new path before collection; inventory never stdout."""
    def __init__(self, destination):
        self.parent=None;self.fd=None;self.temporary=None;self.temp_created=False
        try:
            path=Path(destination)
            require(path.is_absolute() and path==path.resolve() and path.suffix=='.json'
                    and len(str(path))<=4096 and not path.is_relative_to(REPO)
                    and not any(part.lower() in {'public','www','htdocs','artifacts','dist'} for part in path.parts)
                    and not any((a/'.git').exists() or (a/'.git').is_symlink() for a in path.parents))
            parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
            try:
                for part in path.parent.parts[1:]:
                    child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
                    os.close(parent);parent=child
                info=os.fstat(parent)
                require(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700)
                try:os.stat(path.name,dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError:pass
                else:require(False)
                self.parent=parent;parent=None
            finally:
                if parent is not None:os.close(parent)
            self.name=path.name
            self.temporary='.history-receipt-'+os.urandom(16).hex()
            self.fd=os.open(self.temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.parent)
            self.temp_created=True
        except BaseException:
            self.close();raise

    def write(self, outcomes):
        require(type(outcomes) is list and len(outcomes)<=41)
        failures=[]
        for outcome in outcomes:
            require(type(outcome) is JobOutcome)
            if outcome.diagnostic_stage is None:
                require(outcome.diagnostic_structure is None);continue
            require(outcome.failure=='invalid-response' and type(outcome.diagnostic_stage) is str
                    and outcome.diagnostic_stage in HISTORY_STAGES)
            structure=outcome.diagnostic_structure if outcome.diagnostic_structure is not None else unavailable_structure()
            require(valid_structure(structure) and (outcome.diagnostic_stage!='decode-screen' or structure['status']=='unavailable'))
            failures.append(dict(diagnostic_stage=outcome.diagnostic_stage,structure=structure))
        require(len(failures)<=30)
        raw=(canonical(dict(schema_version=1,history_failures=failures))+'\n').encode()
        require(len(raw)<=MAX_INPUT and self.fd is not None)
        with os.fdopen(self.fd,'wb') as stream:
            self.fd=None;stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o600);os.fsync(stream.fileno())
        linked=False
        try:
            os.link(self.temporary,self.name,src_dir_fd=self.parent,dst_dir_fd=self.parent,follow_symlinks=False)
            linked=True;os.fsync(self.parent)
        except BaseException:
            if linked:
                target=os.stat(self.name,dir_fd=self.parent,follow_symlinks=False)
                owned=os.stat(self.temporary,dir_fd=self.parent,follow_symlinks=False)
                if (target.st_dev,target.st_ino)==(owned.st_dev,owned.st_ino):os.unlink(self.name,dir_fd=self.parent)
            raise

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None
        if self.parent is not None:
            try:
                if self.temp_created:
                    try:os.unlink(self.temporary,dir_fd=self.parent)
                    except FileNotFoundError:pass
            finally:os.close(self.parent);self.parent=None

    def __repr__(self):return '<PrivateHistoryDiagnosticReceipt>'
