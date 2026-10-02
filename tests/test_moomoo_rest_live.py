"""Offline security regressions. No real Keychain, broker or credential files."""
from dataclasses import replace
import builtins
import io
from pathlib import Path
import ssl
import subprocess
import traceback

import pytest

from connectors.moomoo_rest import MoomooRESTConnector, ReadRequest, RESTError
from connectors import moomoo_rest_live as live

PASSWORD = b"synthetic-passphrase"
PEM = b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nsynthetic\n-----END ENCRYPTED PRIVATE KEY-----"
HEADERS = {"X-Api-Key": "synthetic-key", "Authorization": "synthetic-signature",
           "X-Timestamp": "1790899200000", "X-Nonce": "synthetic-nonce"}


def request(**changes):
    return replace(ReadRequest("GET", "/api/v1.0/quote/find-news", "symbol=US&size=1", b"", HEADERS, 5), **changes)


def assert_private(error):
    assert error.__context__ is None
    rendering = repr(error) + str(error) + "".join(traceback.format_exception(type(error), error, error.__traceback__))
    for value in ("synthetic-passphrase", "private-provider-body", "synthetic-key", "synthetic-signature"):
        assert value not in rendering


def test_exact_keychain_service_account_login_only():
    calls = []
    def run(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, PASSWORD + b"\n")
    assert live.keychain_passphrase(runner=run) == PASSWORD
    assert calls == [["/usr/bin/security", "find-generic-password", "-s", live.SERVICE,
                     "-a", live.ACCOUNT, "-w", str(Path.home() / "Library/Keychains/login.keychain-db")]]


@pytest.mark.parametrize("result", [subprocess.CompletedProcess([], 1, PASSWORD),
    subprocess.CompletedProcess([], 0, b""), subprocess.CompletedProcess([], 0, "bad"),
    subprocess.CompletedProcess([], 0, b"x" * 4097), None])
def test_keychain_failure_shapes_sanitized(result):
    with pytest.raises(live.LiveReadError) as caught:
        live.keychain_passphrase(runner=lambda _: result)
    assert_private(caught.value)


def test_passphrase_keeps_significant_spaces_and_only_removes_cli_newline():
    assert live.keychain_passphrase(runner=lambda _: subprocess.CompletedProcess([], 0, b" x \n")) == b" x "


@pytest.mark.parametrize("failure", [RuntimeError("synthetic-passphrase"),
    subprocess.CalledProcessError(1, ["private-provider-body"], output=PASSWORD),
    subprocess.TimeoutExpired(["synthetic-passphrase"], 5, output=PASSWORD)])
def test_keychain_exception_does_not_retain_private_context(failure):
    def run(_):
        raise failure
    with pytest.raises(live.LiveReadError) as caught:
        live.keychain_passphrase(runner=run)
    assert_private(caught.value)


class FakeProcess:
    def __init__(self, argv, **kwargs):
        self.argv, self.kwargs = argv, kwargs
        self.stdout = io.BytesIO()
        self.stdout.fileno = lambda: 42
        self.killed = False
    def poll(self):
        return None if not self.killed else 0
    def wait(self, **kwargs):
        return 0
    def kill(self):
        self.killed = True


@pytest.mark.parametrize("case", ["success", "oversize", "timeout"])
def test_default_subprocess_runner_bounds_and_cleanup(monkeypatch, case):
    processes = []
    def popen(argv, **kwargs):
        p = FakeProcess(argv, **kwargs);processes.append(p);return p
    monkeypatch.setattr(live.subprocess, "Popen", popen)
    monkeypatch.setattr(live.select, "select", lambda r, w, x, timeout: (r if case != "timeout" else [], [], []))
    chunks = iter([PASSWORD + b"\n", b""] if case == "success" else [b"x" * 1024] * 6)
    monkeypatch.setattr(live.os, "read", lambda fd, size: next(chunks))
    if case == "success":
        assert live.keychain_passphrase() == PASSWORD
    else:
        with pytest.raises(live.LiveReadError) as caught:
            live.keychain_passphrase()
        assert_private(caught.value)
    p = processes[0]
    assert p.kwargs == {"stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE,
                       "stderr": subprocess.DEVNULL, "shell": False, "env": {"PATH": "/usr/bin:/bin"}}
    assert p.killed and p.stdout.closed


def test_explicit_private_pem_file_bounds(tmp_path):
    path = tmp_path / "private.pem";path.write_bytes(PEM);path.chmod(0o600)
    assert live.encrypted_pem(path) == PEM
    path.chmod(0o644)
    with pytest.raises(live.LiveReadError):live.encrypted_pem(path)
    path.chmod(0o600);path.write_bytes(b"x" * (live.MAX_PEM_BYTES + 1))
    with pytest.raises(live.LiveReadError):live.encrypted_pem(path)
    path.write_bytes(b"")
    with pytest.raises(live.LiveReadError):live.encrypted_pem(path)


def test_pem_rejects_repo_relative_symlink_missing_and_nonregular(tmp_path):
    target = tmp_path / "source";target.write_bytes(PEM);target.chmod(0o600)
    path = tmp_path / "private.pem";path.symlink_to(target)
    for value in (path, "private.pem", live.REPO_ROOT / "private.pem", tmp_path / "missing/private.pem", target):
        with pytest.raises(live.LiveReadError) as caught:live.encrypted_pem(value)
        assert_private(caught.value)
    path.unlink();path.mkdir()
    with pytest.raises(live.LiveReadError):live.encrypted_pem(path)


class FakeKey:
    def sign(self, canonical):
        self.canonical = canonical
        return b"s" * 64


def test_injected_signer_exact_bytes_and_safe_repr():
    key = FakeKey();calls = []
    def decode(pem, password):
        calls.append((pem, password));return key
    signer = live.EncryptedEd25519Signer(pem_loader=lambda: PEM, passphrase_loader=lambda: PASSWORD, key_decoder=decode)
    canonical = b"1790899200000\nGET\n/api/v1.0/quote/find-news\nsymbol=US\n"
    assert signer(canonical) == b"s" * 64 and key.canonical == canonical
    assert calls == [(PEM, PASSWORD)] and repr(signer) == "<EncryptedEd25519Signer>"
    assert set(vars(signer)) == {"_key"}


def crypto_key():
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.BestAvailableEncryption(PASSWORD))
    return key, pem


def test_real_ed25519_encrypted_key_signs_exact_canonical_in_memory():
    key, pem = crypto_key()
    signer = live.EncryptedEd25519Signer(pem_loader=lambda: pem, passphrase_loader=lambda: PASSWORD)
    canonical = b"1790899200000\nGET\n/api/v1.0/quote/find-news\nsymbol=US\n"
    signature = signer(canonical);key.public_key().verify(signature, canonical)
    assert len(signature) == 64
    from cryptography.exceptions import InvalidSignature
    with pytest.raises(InvalidSignature):key.public_key().verify(signature, canonical + b"changed")


def test_wrong_passphrase_and_non_ed25519_rejected():
    _, pem = crypto_key()
    with pytest.raises(live.LiveReadError) as caught:
        live.EncryptedEd25519Signer(pem_loader=lambda: pem, passphrase_loader=lambda: b"wrong")
    assert_private(caught.value)
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    other = ec.generate_private_key(ec.SECP256R1()).private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(PASSWORD))
    with pytest.raises(live.LiveReadError):
        live.EncryptedEd25519Signer(pem_loader=lambda: other, passphrase_loader=lambda: PASSWORD)


def test_missing_dependency_fails_closed_without_context(monkeypatch):
    original = builtins.__import__
    def import_module(name, *args, **kwargs):
        if name.startswith("cryptography"):raise ImportError("synthetic-passphrase")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", import_module)
    with pytest.raises(live.LiveReadError) as caught:
        live.EncryptedEd25519Signer(pem_loader=lambda: PEM, passphrase_loader=lambda: PASSWORD)
    assert_private(caught.value)


@pytest.mark.parametrize("pem,password", [(b"plaintext", PASSWORD), (PEM, b""), (PEM, "str"),
    (PEM, b"x" * 4097), (b"x" * 65537, PASSWORD)])
def test_signer_input_bounds(pem, password):
    with pytest.raises(live.LiveReadError):
        live.EncryptedEd25519Signer(pem_loader=lambda: pem, passphrase_loader=lambda: password)


def test_signer_decoder_and_sign_errors_sanitized():
    def fail(*_):raise RuntimeError("synthetic-passphrase")
    with pytest.raises(live.LiveReadError) as caught:
        live.EncryptedEd25519Signer(pem_loader=lambda: PEM, passphrase_loader=lambda: PASSWORD, key_decoder=fail)
    assert_private(caught.value)
    class BadKey:
        sign = fail
    signer = live.EncryptedEd25519Signer(pem_loader=lambda: PEM, passphrase_loader=lambda: PASSWORD, key_decoder=lambda *_: BadKey())
    with pytest.raises(live.LiveReadError) as caught:signer(b"canonical")
    assert_private(caught.value)
    for value in (b"", "string", b"x" * 65537):
        with pytest.raises(live.LiveReadError):signer(value)


class FakeResponse:
    def __init__(self, status=200, body=b'{"ret_code":0,"ret_msg":"ok","data":[]}', headers=None):
        self.status, self.body, self.headers = status, body, headers or {}
        self.reads = []
    def getheader(self, key, default=None):return self.headers.get(key, default)
    def read1(self, size):
        self.reads.append(size);result=self.body[:size];self.body=self.body[size:];return result


class FakeConnection:
    def __init__(self, response):
        self.response, self.calls, self.timeouts, self.closed = response, [], [], False
        self.sock = self
    def connect(self):self.calls.append("connect")
    def settimeout(self, value):self.timeouts.append(value)
    def request(self, *args, **kwargs):self.calls.append((args, kwargs))
    def getresponse(self):return self.response
    def close(self):self.closed=True


def harness(response=None, **options):
    c = FakeConnection(response or FakeResponse());factories=[]
    def factory(host, **kwargs):factories.append((host, kwargs));return c
    transport = live.SecureReadTransport(connection_factory=factory, **options)
    return transport, c, factories


def test_secure_https_preserves_wire_and_ignores_proxy_env(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid")
    monkeypatch.setenv("SSL_CERT_FILE", "/synthetic/untrusted.pem")
    # Explicit test context uses system default settings, not environment override.
    transport, c, factories = harness(context_factory=lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
    r = request();result = transport(r)
    assert result.status==200 and result.body.startswith(b'{"ret_code"')
    host, options = factories[0]
    assert host==live.HOSTNAME and options['port']==443
    assert options['context'].verify_mode==ssl.CERT_REQUIRED and options['context'].check_hostname
    assert options['context'].minimum_version==ssl.TLSVersion.TLSv1_2
    assert c.calls[1]==(("GET", r.path+"?"+r.query), {"body":None,"headers":HEADERS})
    assert c.closed and all(0 < x <= 5 for x in c.timeouts)
    assert repr(transport)=="<SecureReadTransport>"


def test_snapshot_post_body_identical_and_core_integration():
    transport,c,_=harness(FakeResponse(body=b'{"ret_code":0,"ret_msg":"ok","data":{"snapshot_list":[]}}'))
    core=MoomooRESTConnector(api_key="synthetic-key", signer=lambda _: b"s"*64, transport=transport,
        clock_ms=lambda:1790899200000,nonce_factory=lambda:"n")
    result=core.snapshot(["US.AAPL"])
    assert c.calls[1][0]==("POST","/api/v1.0/quote/snapshot")
    assert c.calls[1][1]['body']==b'{"code_list":["US.AAPL"]}'
    assert result.status=="empty" and result.missing_codes==("US.AAPL",)


@pytest.mark.parametrize("changes", [dict(path="//evil.invalid"), dict(path="/api/v1.0/quote/snapshot?x=1"),
    dict(method="DELETE"), dict(path="/api/v1.0/orders"), dict(path="/api/v1.0/accounts/1/positions"),
    dict(query="x=1\r\nAuthorization:secret"), dict(query="x=#bad"),dict(query="x="+"a"*8192),
    dict(timeout=True),dict(timeout=0),dict(timeout=31),dict(timeout=float('nan')),
    dict(body=b"GETbody"),dict(headers={**HEADERS,"Host":"evil.invalid"}),
    dict(headers={**HEADERS,"X-Api-Key":"bad\nsecret"}),dict(headers={}),
    dict(method="POST",path="/api/v1.0/quote/snapshot",query="",body=b"x"*32769)])
def test_request_rejection_before_connection(changes):
    transport,c,factories=harness()
    with pytest.raises(live.LiveReadError) as caught:transport(request(**changes))
    assert factories==[] and c.calls==[];assert_private(caught.value)


@pytest.mark.parametrize("status", [301,302,303,307,308])
def test_redirects_never_followed_or_credentials_forwarded(status):
    response=FakeResponse(status=status, headers={"Location":"https://evil.invalid/private-provider-body"})
    transport,c,factories=harness(response)
    with pytest.raises(live.LiveReadError,match="redirect-forbidden") as caught:transport(request())
    assert_private(caught.value)
    assert len(factories)==1 and len(c.calls)==2 and c.closed and response.reads==[]


@pytest.mark.parametrize("status",[401,403,429,500,503])
def test_no_error_bodies_only_bounded_retry_hint(status):
    response=FakeResponse(status=status,body=b"private-provider-body",headers={"Retry-After":"20","Secret":"private"})
    transport,c,_=harness(response);result=transport(request())
    assert result.status==status and result.body==b"" and result.headers=={"Retry-After":"20"}
    assert response.reads==[] and c.closed


@pytest.mark.parametrize("headers,body",[({"Content-Length":"99999999"},b"x"),
    ({"Content-Length":"-1"},b"x"),({"Content-Length":"2"},b"x"),
    ({"Content-Encoding":"gzip"},b"x"),({},b"x"*11)])
def test_response_size_encoding_and_truncation_bounds(headers,body):
    response=FakeResponse(body=body,headers=headers);transport,c,_=harness(response,max_response_bytes=10)
    with pytest.raises(live.LiveReadError) as caught:transport(request())
    assert_private(caught.value);assert c.closed
    assert all(n<=11 for n in response.reads)


def test_chunked_bound_and_deadline_expiry():
    ticks=iter([0,0,0,0,0,6])
    transport,c,_=harness(clock=lambda:next(ticks))
    with pytest.raises(live.LiveReadTimeout) as caught:transport(request())
    assert_private(caught.value);assert c.closed


@pytest.mark.parametrize("where", ["connect","request","getresponse","read1","close"])
def test_transport_failures_close_and_never_chain(where):
    transport,c,_=harness()
    def fail(*_,**kw):raise RuntimeError("private-provider-body")
    setattr(c.response if where=='read1' else c,where,fail)
    with pytest.raises(live.LiveReadError) as caught:transport(request())
    assert_private(caught.value)
    if where!='close':assert c.closed


def test_unverified_tls_context_rejected_before_connection():
    context=ssl._create_unverified_context()
    transport,c,factories=harness(context_factory=lambda:context)
    with pytest.raises(live.LiveReadError,match="tls-required"):transport(request())
    assert factories==[]


@pytest.mark.parametrize("limit",[0,-1,True,live.MAX_RESPONSE_BYTES+1])
def test_transport_config_bounds(limit):
    with pytest.raises(live.LiveReadError):live.SecureReadTransport(max_response_bytes=limit)


def test_socket_timeout_maps_to_core_timeout():
    transport,c,_=harness()
    def fail():raise TimeoutError("private-provider-body")
    c.connect=fail
    core=MoomooRESTConnector(api_key="synthetic-key",signer=lambda _:b"s"*64,transport=transport,
        clock_ms=lambda:1790899200000,nonce_factory=lambda:"n")
    with pytest.raises(RESTError) as caught:core.search_news("US")
    assert caught.value.kind=="timeout";assert_private(caught.value)


def test_no_logs_on_private_failure(capsys):
    def fail(_):raise RuntimeError("synthetic-passphrase")
    with pytest.raises(live.LiveReadError):live.keychain_passphrase(runner=fail)
    captured=capsys.readouterr();assert captured.out==captured.err==""


def test_pem_wrong_owner_rejected(tmp_path, monkeypatch):
    p=tmp_path/'private.pem';p.write_bytes(PEM);p.chmod(0o600)
    owner=p.stat().st_uid
    monkeypatch.setattr(live.os,'getuid',lambda:owner+1)
    with pytest.raises(live.LiveReadError):live.encrypted_pem(p)


def test_tls_failure_is_controlled_and_closes():
    transport,c,_=harness()
    def fail():raise ssl.SSLCertVerificationError('private-provider-body')
    c.connect=fail
    with pytest.raises(live.LiveReadError,match='tls-failed') as caught:transport(request())
    assert_private(caught.value);assert c.closed


def test_deadline_checked_after_each_body_chunk():
    clock=[0]
    response=FakeResponse();read=response.read1
    def slow_read(size):
        value=read(size);clock[0]=6;return value
    response.read1=slow_read
    transport,c,_=harness(response,clock=lambda:clock[0])
    with pytest.raises(live.LiveReadTimeout) as caught:transport(request())
    assert response.reads and c.closed;assert_private(caught.value)


def test_keychain_login_path_ignores_home_environment(monkeypatch):
    import pwd,os
    monkeypatch.setenv('HOME','/synthetic/attacker-home')
    calls=[]
    def run(argv):
        calls.append(argv);return subprocess.CompletedProcess(argv,0,PASSWORD)
    assert live.keychain_passphrase(runner=run)==PASSWORD
    assert calls[0][-1]==str(Path(pwd.getpwuid(os.getuid()).pw_dir)/'Library/Keychains/login.keychain-db')
    assert '/synthetic/attacker-home' not in calls[0][-1]
