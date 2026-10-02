"""Explicit private capabilities for PRSG-31; import performs no I/O."""
from __future__ import annotations

import http.client
import math
import os
from pathlib import Path
import re
import select
import ssl
import stat
import subprocess
import time
from typing import Callable

from connectors.moomoo_rest import MAX_RESPONSE_BYTES, ReadRequest, ReadResponse, RESTError

HOSTNAME = "webapi.moomoo.com"
SERVICE = "praesagus.moomoo.private-key-passphrase"
ACCOUNT = "praesagus-lead"
_ERROR_KINDS = {"credential-unavailable", "key-unavailable", "invalid-request",
                "invalid-transport-config", "clock-failed", "tls-required", "tls-failed",
                "redirect-forbidden", "invalid-response", "encoded-response-forbidden",
                "response-too-large", "incomplete-response", "signer-failed"}
REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_PEM_BYTES = 65536
MAX_PASSPHRASE_BYTES = 4096


class LiveReadError(RESTError):
    """Sanitized capability failure, never provider/credential exception text."""


class LiveReadTimeout(LiveReadError, TimeoutError):
    """Timeout also maps to PRSG-31's timeout category."""


def _need(condition: bool, kind: str) -> None:
    if not condition:
        raise LiveReadError(kind)


def _call(fn: Callable, *args, kind: str, **kwargs):
    failure = None
    try:
        value = fn(*args, **kwargs)
    except TimeoutError:
        failure = "timeout"
    except ssl.SSLError:
        failure = "tls-failed"
    except Exception as error:
        failure = error.kind if type(error) is LiveReadError and error.kind in _ERROR_KINDS else kind
    if failure == "timeout":
        raise LiveReadTimeout("timeout")
    if failure:
        raise LiveReadError(failure)
    return value


def _security_process(argv: list[str]):
    """Fixed executable; bounded stdout, no shell, stdin, stderr or env secrets."""
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, shell=False, env={"PATH": "/usr/bin:/bin"})
    deadline = time.monotonic() + 5
    output = bytearray()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                raise TimeoutError()
            chunk = os.read(process.stdout.fileno(), min(1024, MAX_PASSPHRASE_BYTES + 2 - len(output)))
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > MAX_PASSPHRASE_BYTES + 1:
                raise ValueError()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        code = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(argv, code, bytes(output))
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()


def keychain_passphrase(*, runner: Callable = _security_process) -> bytes:
    """Exact service/account in login Keychain only; no scans or fallback."""
    def login_path():
        import pwd
        return str(Path(pwd.getpwuid(os.getuid()).pw_dir) / "Library/Keychains/login.keychain-db")
    login = _call(login_path, kind="credential-unavailable")
    argv = ["/usr/bin/security", "find-generic-password", "-s", SERVICE,
            "-a", ACCOUNT, "-w", login]
    result = _call(runner, argv, kind="credential-unavailable")
    # Validate inside the sanitizer too: injected results may have unsafe properties.
    def extract():
        _need(type(result.returncode) is int and result.returncode == 0
              and isinstance(result.stdout, bytes), "credential-unavailable")
        password = result.stdout[:-1] if result.stdout.endswith(b"\n") else result.stdout
        _need(0 < len(password) <= MAX_PASSPHRASE_BYTES, "credential-unavailable")
        return password
    return _call(extract, kind="credential-unavailable")


def encrypted_pem(path: Path | str) -> bytes:
    """Explicit private.pem read outside repository, owned/private regular file."""
    def read():
        p = Path(path)
        _need(p.is_absolute() and p.name == "private.pem"
              and not p.resolve().is_relative_to(REPO_ROOT), "key-unavailable")
        fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            _need(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                  and stat.S_IMODE(info.st_mode) & 0o077 == 0
                  and 0 < info.st_size <= MAX_PEM_BYTES, "key-unavailable")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(MAX_PEM_BYTES + 1)
            _need(0 < len(data) <= MAX_PEM_BYTES, "key-unavailable")
            return data
        finally:
            os.close(fd)
    return _call(read, kind="key-unavailable")


def _decode_key(pem: bytes, password: bytes):
    # Lazy imports keep the offline core usable without this optional dependency.
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = load_pem_private_key(pem, password=password)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError()
    return key


class EncryptedEd25519Signer:
    """Loads injected encrypted PEM/passphrase once; retains only decrypted key."""
    def __init__(self, *, pem_loader: Callable[[], bytes],
                 passphrase_loader: Callable[[], bytes], key_decoder: Callable = _decode_key):
        pem = _call(pem_loader, kind="key-unavailable")
        _need(isinstance(pem, bytes) and 0 < len(pem) <= MAX_PEM_BYTES
              and pem.strip().startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----")
              and pem.strip().endswith(b"-----END ENCRYPTED PRIVATE KEY-----"), "key-unavailable")
        password = _call(passphrase_loader, kind="credential-unavailable")
        _need(isinstance(password, bytes) and 0 < len(password) <= MAX_PASSPHRASE_BYTES,
              "credential-unavailable")
        self._key = _call(key_decoder, pem, password, kind="key-unavailable")

    def __call__(self, canonical: bytes) -> bytes:
        _need(isinstance(canonical, bytes) and 0 < len(canonical) <= 65536, "invalid-signing-input")
        signature = _call(lambda: self._key.sign(canonical), kind="signer-failed")
        _need(isinstance(signature, bytes) and len(signature) == 64, "signer-failed")
        return signature

    def __repr__(self):
        return "<EncryptedEd25519Signer>"


class SecureReadTransport:
    """Direct HTTPS quote/news reads only, with verified TLS and no redirects.

    Factories/clock are trusted offline test seams. Socket timeouts do not bound
    OS DNS resolution or a peer trickling response headers; see documented gates.
    """
    def __init__(self, *, connection_factory: Callable = http.client.HTTPSConnection,
                 context_factory: Callable = ssl.create_default_context,
                 clock: Callable = time.monotonic, max_response_bytes: int = MAX_RESPONSE_BYTES):
        _need(type(max_response_bytes) is int and 1 <= max_response_bytes <= MAX_RESPONSE_BYTES,
              "invalid-transport-config")
        self._factory, self._context_factory, self._clock = connection_factory, context_factory, clock
        self._limit = max_response_bytes

    def __repr__(self):
        return "<SecureReadTransport>"

    @staticmethod
    def _validate(request: ReadRequest):
        _need(isinstance(request, ReadRequest), "invalid-request")
        _need(type(request.timeout) in (int, float) and math.isfinite(request.timeout)
              and 0 < request.timeout <= 30, "invalid-request")
        _need((request.method, request.path) in (
            ("GET", "/api/v1.0/quote/find-news"), ("POST", "/api/v1.0/quote/snapshot")), "invalid-request")
        _need(isinstance(request.query, str) and len(request.query) <= 8192
              and re.fullmatch(r"[A-Za-z0-9%_.~+&=*-]*", request.query) is not None,
              "invalid-request")
        _need(isinstance(request.body, bytes) and len(request.body) <= 32768
              and (not request.body if request.method == "GET" else bool(request.body) and not request.query),
              "invalid-request")
        headers = dict(request.headers)
        required = {"X-Api-Key", "Authorization", "X-Timestamp", "X-Nonce"}
        _need(set(headers) == required | ({"Content-Type"} if request.body else set())
              and all(isinstance(v, str) and 0 < len(v) <= 8192 and v.isascii()
                      and not any(ord(c) < 32 or ord(c) == 127 for c in v) for v in headers.values())
              and (not request.body or headers["Content-Type"] == "application/json"), "invalid-request")
        return headers

    def __call__(self, request: ReadRequest) -> ReadResponse:
        headers = _call(self._validate, request, kind="invalid-request")
        def send():
            started = self._clock()
            _need(type(started) in (int, float) and math.isfinite(started), "clock-failed")
            deadline = started + request.timeout
            def remaining():
                now = self._clock()
                _need(type(now) in (int, float) and math.isfinite(now) and now >= started, "clock-failed")
                left = deadline - now
                if left <= 0:
                    raise TimeoutError()
                return left
            context = self._context_factory()
            _need(isinstance(context, ssl.SSLContext) and context.check_hostname
                  and context.verify_mode == ssl.CERT_REQUIRED, "tls-required")
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            connection = self._factory(HOSTNAME, port=443, timeout=remaining(), context=context)
            try:
                connection.connect()
                connection.sock.settimeout(remaining())
                target = request.path + ("?" + request.query if request.query else "")
                connection.request(request.method, target, body=request.body or None, headers=headers)
                connection.sock.settimeout(remaining())
                response = connection.getresponse()
                remaining()
                _need(type(response.status) is int and 100 <= response.status <= 599, "invalid-response")
                _need(not 300 <= response.status < 400, "redirect-forbidden")
                # Never retain error bodies or other response headers.
                retry = response.getheader("Retry-After")
                safe_headers = {"Retry-After": retry} if isinstance(retry, str) and len(retry) <= 128 else {}
                if response.status != 200:
                    return ReadResponse(response.status, b"", safe_headers)
                _need(response.getheader("Content-Encoding", "identity").lower() == "identity",
                      "encoded-response-forbidden")
                length = response.getheader("Content-Length")
                _need(length is None or (isinstance(length, str) and re.fullmatch(r"\d{1,10}", length)
                                        and int(length) <= self._limit), "response-too-large")
                chunks, size = [], 0
                while True:
                    connection.sock.settimeout(remaining())
                    chunk = response.read1(min(65536, self._limit + 1 - size))
                    remaining()
                    _need(isinstance(chunk, bytes), "invalid-response")
                    if not chunk:
                        break
                    size += len(chunk)
                    _need(size <= self._limit, "response-too-large")
                    chunks.append(chunk)
                _need(length is None or size == int(length), "incomplete-response")
                return ReadResponse(200, b"".join(chunks), {})
            finally:
                connection.close()
        return _call(send, kind="transport-failed")
