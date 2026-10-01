"""Synthetic, offline protocol regressions; no credentials/network needed."""
import base64
import hashlib
import json
import traceback

import pytest

from connectors.moomoo_rest import (
    HOST, MAX_RESPONSE_BYTES, MoomooRESTConnector, ReadRequest, ReadResponse, RESTError,
)

NOW = 1790899200000
KEY = "synthetic-api-key"
SIGNATURE = b"synthetic-signature"


def quote(data):
    return {"ret_code": 0, "ret_msg": "success", "data": data}


def news(**changes):
    return dict({"news_id": "synthetic:1", "news_type": "POST", "title": "<em>Example</em>",
                 "publish_time": NOW // 1000, "url": "https://example.invalid/news"}, **changes)


def snapshot(**changes):
    return dict({"code": "US.AAPL", "name": "Synthetic", "update_time": NOW,
                 "data_date": "2026-10-02", "last_price": 12.5, "volume": 100,
                 "equity_valid": True, "trust_valid": False}, **changes)


class Harness:
    def __init__(self, payload=None, *, status=200, body=None, headers=None, failure=None):
        self.requests, self.signed = [], []
        self.response = ReadResponse(status, body if body is not None else json.dumps(
            payload if payload is not None else quote([])).encode(), headers or {})
        self.failure = failure
        self.client = MoomooRESTConnector(api_key=KEY, signer=self.sign, transport=self.send,
            clock_ms=lambda: NOW, nonce_factory=lambda: "synthetic_nonce-1")

    def sign(self, canonical):
        self.signed.append(canonical)
        return SIGNATURE

    def send(self, request):
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        return self.response


def test_bodyless_get_exact_trailing_newline_and_headers():
    h = Harness({"s": "ok", "d": []})
    result = h.client.positions("000123")
    r = h.requests[0]
    assert h.signed == [f"{NOW}\nGET\n/api/v1.0/accounts/000123/positions\n\n".encode()]
    assert r.method == "GET" and r.body == b"" and r.query == ""
    assert r.url == HOST + "/api/v1.0/accounts/000123/positions"
    assert r.headers == {"X-Api-Key": KEY, "Authorization": base64.b64encode(SIGNATURE).decode(),
                         "X-Timestamp": str(NOW), "X-Nonce": "synthetic_nonce-1"}
    assert r.timeout == 10
    assert result.private and result.status == "empty"


def test_unicode_news_query_signed_once_literal_title_and_timestamp_units():
    h = Harness(quote([news()]))
    result = h.client.search_news("半导体 & US", size=50, news_type=1, sort_type=2, lang="zh-CN")
    r = h.requests[0]
    expected = "symbol=%E5%8D%8A%E5%AF%BC%E4%BD%93+%26+US&size=50&news_type=1&sort_type=2&lang=zh-CN"
    assert r.query == expected
    assert r.url.endswith("?" + expected)
    assert h.signed[0] == f"{NOW}\nGET\n/api/v1.0/quote/find-news\n{expected}\n".encode()
    assert result.data[0]["title"] == "<em>Example</em>"
    assert result.data[0]["publish_time"] == NOW // 1000
    assert result.provider_time_unit == "seconds"
    assert result.requested_at_ms == result.retrieved_at_ms == NOW
    assert result.provider == "moomoo-rest" and not result.private


def test_snapshot_exact_json_bytes_digest_partial_and_preserved_flags():
    h = Harness(quote({"snapshot_list": [snapshot()]}))
    result = h.client.snapshot(["US.AAPL", "US.MSFT"])
    r = h.requests[0]
    assert r.body == b'{"code_list":["US.AAPL","US.MSFT"]}'
    assert r.method == "POST" and not r.query
    assert r.headers["Content-Type"] == "application/json"
    assert h.signed[0] == f"{NOW}\nPOST\n/api/v1.0/quote/snapshot\n\n{hashlib.sha256(r.body).hexdigest()}".encode()
    assert result.status == "partial" and result.missing_codes == ("US.MSFT",)
    assert result.data == [snapshot()]
    assert result.provider_time_unit == "milliseconds"
    assert "session_metrics" not in result.data[0]


@pytest.mark.parametrize("method,payload,path,query", [
    (lambda c: c.account_funds("000123", "USD"), {"s": "ok", "d": {"cash": "0007.00", "currency": "USD"}},
     "/api/v1.0/accounts/000123/funds", "currency=USD"),
    (lambda c: c.positions("000123"), {"s": "ok", "d": [{"code": "BMS.SYN", "position_side": "LONG",
       "qty": "002.000", "cost_price": "10.00", "cost_price_valid": False, "pl_val_valid": True}]},
     "/api/v1.0/accounts/000123/positions", ""),
    (lambda c: c.list_groups("CUSTOM"), quote({"group_list": [{"group_name": "自选", "group_type": "CUSTOM"}]}),
     "/api/v1.0/quote/user-security-group", "group_type=CUSTOM"),
    (lambda c: c.list_group_members("自选 & 1"), quote({"security_list": [{"code": "BMS.SYN", "name": "Synthetic",
       "lot_size": 100, "stock_type": "STOCK", "listing_date": "2020-01-01", "main_contract": False}]}),
     "/api/v1.0/quote/user-security", "group_name=%E8%87%AA%E9%80%89+%26+1"),
])
def test_remaining_reads_wire_and_private_preservation(method, payload, path, query):
    h = Harness(payload)
    result = method(h.client)
    assert result.private and result.status == "success"
    r = h.requests[0]
    assert (r.method, r.path, r.query, r.body) == ("GET", path, query, b"")
    assert h.signed == [f"{NOW}\nGET\n{path}\n{query}\n".encode()]
    expected = payload.get("d", payload.get("data"))
    if "data" in payload:
        expected = next(iter(expected.values()))
    assert result.data == expected


@pytest.mark.parametrize("call,payload", [
    (lambda c: c.search_news("US"), quote([])),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": []})),
    (lambda c: c.account_funds("1", "USD"), {"s": "ok", "d": {}}),
    (lambda c: c.positions("1"), {"s": "ok", "d": []}),
    (lambda c: c.list_groups(), quote({"group_list": []})),
    (lambda c: c.list_group_members("empty"), quote({"security_list": []})),
])
def test_successful_empty_not_failure(call, payload):
    h = Harness(payload)
    result = call(h.client)
    assert result.status == "empty"
    if result.endpoint == "snapshot":
        assert result.missing_codes == ("US.AAPL",)


@pytest.mark.parametrize("call", [
    lambda c: c.search_news(""), lambda c: c.search_news("\nprivate"),
    lambda c: c.search_news("x" * 513), lambda c: c.search_news("x", size=0),
    lambda c: c.search_news("x", size=51), lambda c: c.search_news("x", size=True),
    lambda c: c.search_news("x", news_type=4), lambda c: c.search_news("x", sort_type=3),
    lambda c: c.search_news("x", lang="invalid"),
    lambda c: c.snapshot([]), lambda c: c.snapshot("US.AAPL"),
    lambda c: c.snapshot(["US.AAPL"] * 401), lambda c: c.snapshot(["US.AAPL", "US.AAPL"]),
    lambda c: c.snapshot(["BMS.SYN"]), lambda c: c.snapshot(["MY.SYN"]),
    lambda c: c.snapshot(["US.AAPL/../write"]), lambda c: c.snapshot(["US.AAPL?x=1"]),
    lambda c: c.snapshot(["US.AAPL%2F"]), lambda c: c.snapshot(["US.aapl"]),
    lambda c: c.positions(123), lambda c: c.positions("1/../orders"),
    lambda c: c.positions("1?x=2"), lambda c: c.positions("１"), lambda c: c.positions(""),
    lambda c: c.account_funds("1", "usd"), lambda c: c.account_funds("1", "USD\n"),
    lambda c: c.list_groups("custom"), lambda c: c.list_groups("ADD"),
    lambda c: c.list_group_members("x" * 101), lambda c: c.list_group_members(""),
    lambda c: c.list_group_members("x\x00"),
])
def test_invalid_inputs_rejected_before_signer_transport(call):
    h = Harness()
    with pytest.raises(RESTError, match="invalid-input"):
        call(h.client)
    assert h.requests == h.signed == []


def test_bounds_accepted_and_no_mutation_surface():
    codes = ["US.S" + str(i) for i in range(400)]
    h = Harness(quote({"snapshot_list": []}))
    assert h.client.snapshot(codes).missing_codes == tuple(codes)
    h.response = ReadResponse(200, json.dumps(quote({"security_list": []})).encode())
    h.client.list_group_members("x" * 100)
    h.response = ReadResponse(200, json.dumps(quote([])).encode())
    h.client.search_news("x", size=1)
    for name in ("request", "post", "create_group", "add_security", "place_order", "save", "poll"):
        assert not hasattr(h.client, name)
    public = {name for name in dir(h.client) if not name.startswith("_")}
    assert public == {"search_news", "snapshot", "account_funds", "positions", "list_groups", "list_group_members"}


@pytest.mark.parametrize("call,payload", [
    (lambda c: c.search_news("x"), {"s": "ok", "d": []}),
    (lambda c: c.positions("1"), quote([])),
    (lambda c: c.search_news("x"), quote({})),
    (lambda c: c.search_news("x"), quote([news(publish_time="bad")])),
    (lambda c: c.search_news("x"), quote([news(publish_time=True)])),
    (lambda c: c.search_news("x"), quote([news(), news()])),
    (lambda c: c.search_news("x", size=1), quote([news(), news(news_id="synthetic:2")])),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(), snapshot()]})),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(code="US.MSFT")]})),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(equity_valid="yes")]})),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(update_time=True)]})),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(last_price="NaN")]})),
    (lambda c: c.snapshot(["US.AAPL"]), quote({"snapshot_list": [snapshot(volume=1.5)]})),
    (lambda c: c.account_funds("1", "USD"), {"s": "ok", "d": []}),
    (lambda c: c.account_funds("1", "USD"), {"s": "ok", "d": {"cash": 1.5}}),
    (lambda c: c.account_funds("1", "USD"), {"s": "ok", "d": {"cash": "NaN"}}),
    (lambda c: c.positions("1"), {"s": "ok", "d": [{"code": "US.AAPL", "position_side": "LONG", "qty": "Infinity"}]}),
    (lambda c: c.positions("1"), {"s": "ok", "d": [{"code": "US.AAPL", "position_side": "LONG", "pl_val_valid": 1}]}),
    (lambda c: c.list_groups(), quote({"group_list": [{"group_name": "x", "group_type": "UNKNOWN"}]})),
    (lambda c: c.list_groups("SYSTEM"), quote({"group_list": [{"group_name": "x", "group_type": "CUSTOM"}]})),
    (lambda c: c.list_group_members("x"), quote({"security_list": [{"code": "US.AAPL", "name": "A", "lot_size": True}]})),
    (lambda c: c.list_group_members("x"), quote({"security_list": [{"code": "US.AAPL", "name": "A"}] * 2})),
])
def test_malformed_endpoint_shapes_fail_closed(call, payload):
    with pytest.raises(RESTError, match="malformed-response"):
        call(Harness(payload).client)


@pytest.mark.parametrize("body", [b"not-json", b"\xff", b"[]", b"null",
    b'{"ret_code":0,"ret_code":1,"ret_msg":"x","data":[]}',
    b'{"ret_code":0,"ret_msg":"x","data":[NaN]}',
    b'{"ret_code":0,"ret_msg":"x","data":[1e999]}',
    b"x" * (MAX_RESPONSE_BYTES + 1),
    b'{"ret_code":true,"ret_msg":"x","data":[]}',
    b'{"ret_code":0,"ret_msg":"x"}',
    b'{"ret_code":0,"s":"ok","ret_msg":"x","data":[]}',
])
def test_malformed_json_envelopes_are_sanitized(body):
    with pytest.raises(RESTError, match="malformed-response") as caught:
        Harness(body=body).client.search_news("x")
    assert caught.value.__context__ is None


@pytest.mark.parametrize("status,kind", [(429, "rate-limited"), (500, "upstream-failed"),
    (503, "upstream-failed"), (403, "http-failed"), (201, "http-failed"), (302, "http-failed")])
def test_nonjson_http_failures_without_retry(status, kind):
    h = Harness(status=status, body=b"private-provider-error")
    with pytest.raises(RESTError) as caught:
        h.client.search_news("x")
    assert caught.value.kind == kind and len(h.requests) == 1
    assert "private-provider-error" not in str(caught.value)


@pytest.mark.parametrize("hint,expected", [("30", 30), ("-1", None), ("NaN", None),
    ("86401", None), ("private-provider-error", None),
    ("Thu, 01 Oct 2026 21:20:30 GMT", None)])
def test_retry_after_sanitization(hint, expected):
    h = Harness(status=429, body=b"private", headers={"Retry-After": hint})
    with pytest.raises(RESTError) as caught:
        h.client.search_news("x")
    assert caught.value.retry_after == expected


def test_retry_after_http_date():
    from email.utils import formatdate
    h = Harness(status=429, headers={"retry-after": formatdate(NOW / 1000 + 30, usegmt=True)})
    with pytest.raises(RESTError) as caught:
        h.client.search_news("x")
    assert caught.value.retry_after == 30


@pytest.mark.parametrize("account", [False, True])
def test_http_200_provider_failure_is_not_success(account):
    payload = {"s": "error", "errcode": -1200, "errmsg": "private-provider-error"} if account else {
        "ret_code": -9, "ret_msg": "private-provider-error"}
    h = Harness(payload)
    with pytest.raises(RESTError, match="provider-failed") as caught:
        h.client.positions("1") if account else h.client.search_news("x")
    assert "private-provider-error" not in str(caught.value)


@pytest.mark.parametrize("failure,kind", [(TimeoutError("private-provider-error"), "timeout"),
    (RuntimeError("private-provider-error"), "transport-failed")])
def test_transport_failure_privacy_and_no_retry(failure, kind):
    h = Harness(failure=failure)
    with pytest.raises(RESTError) as caught:
        h.client.positions("000123")
    assert caught.value.kind == kind and caught.value.__context__ is None
    assert "private-provider-error" not in "".join(traceback.format_exception(
        type(caught.value), caught.value, caught.value.__traceback__))
    assert len(h.requests) == 1


def test_sensitive_objects_have_safe_repr():
    h = Harness({"s": "ok", "d": {"cash": "9876543.21", "currency": "USD"}})
    result = h.client.account_funds("000123", "USD")
    rendering = repr((h.client, h.requests[0], h.response, result))
    for secret in (KEY, SIGNATURE.decode(), base64.b64encode(SIGNATURE).decode(),
                   "000123", "9876543.21", "X-Api-Key", "Authorization"):
        assert secret not in rendering


@pytest.mark.parametrize("attribute,value,kind", [
    ("_nonce_factory", lambda: "bad\nnonce", "nonce-failed"),
    ("_nonce_factory", lambda: "x" * 65, "nonce-failed"),
    ("_clock_ms", lambda: True, "clock-failed"),
    ("_clock_ms", lambda: 0, "clock-failed"),
    ("_signer", lambda _: "not-bytes", "signer-failed"),
    ("_signer", lambda _: b"", "signer-failed"),
])
def test_invalid_injected_values_fail_without_transport(attribute, value, kind):
    h = Harness()
    setattr(h.client, attribute, value)
    with pytest.raises(RESTError, match=kind):
        h.client.search_news("x")
    assert h.requests == []


@pytest.mark.parametrize("attribute", ["_signer", "_clock_ms", "_nonce_factory"])
def test_injected_errors_never_chain_private_exception(attribute):
    def fail(*_):
        raise RuntimeError("private-provider-error")
    h = Harness()
    setattr(h.client, attribute, fail)
    with pytest.raises(RESTError) as caught:
        h.client.search_news("x")
    assert caught.value.__context__ is None
    assert "private-provider-error" not in repr(caught.value)
    assert h.requests == []


@pytest.mark.parametrize("timeout", [0, -1, 31, True, float("nan"), float("inf")])
def test_timeout_bounds(timeout):
    with pytest.raises(RESTError, match="invalid-input"):
        MoomooRESTConnector(api_key=KEY, signer=lambda x: SIGNATURE,
            transport=lambda x: None, clock_ms=lambda: NOW, nonce_factory=lambda: "x", timeout=timeout)


def test_clock_cannot_go_backwards():
    h = Harness()
    ticks = iter([NOW, NOW - 1])
    h.client._clock_ms = lambda: next(ticks)
    with pytest.raises(RESTError, match="clock-failed"):
        h.client.search_news("x")


@pytest.mark.parametrize("key", ["", "bad\nkey", "bad\rkey", "非ascii", "x" * 513])
def test_api_key_cannot_inject_headers(key):
    with pytest.raises(RESTError, match="invalid-input"):
        MoomooRESTConnector(api_key=key, signer=lambda x: SIGNATURE,
            transport=lambda x: None, clock_ms=lambda: NOW, nonce_factory=lambda: "x")


def test_surrogate_input_cannot_escape_controlled_errors():
    h = Harness()
    with pytest.raises(RESTError, match="invalid-input"):
        h.client.search_news("bad\ud800")
    assert h.requests == h.signed == []


@pytest.mark.parametrize("data_date", ["2026-02-30", "2026-13-01", "01-10-2026"])
def test_invalid_snapshot_date(data_date):
    h = Harness(quote({"snapshot_list": [snapshot(data_date=data_date)]}))
    with pytest.raises(RESTError, match="malformed-response"):
        h.client.snapshot(["US.AAPL"])


@pytest.mark.parametrize("response", [None, ReadResponse(True, b"{}"), ReadResponse(200, "not-bytes"),
    ReadResponse(200, b"{}", {1: "bad"}), ReadResponse(200, b"{}", {"x": None})])
def test_malformed_transport_results(response):
    h = Harness()
    h.response = response
    with pytest.raises(RESTError, match="malformed-response"):
        h.client.search_news("x")
