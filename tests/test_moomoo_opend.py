import pytest

from connectors.moomoo_opend import (
    MoomooOpenDConnector,
    OpenDAPIError,
    OpenDUnavailableError,
    OpenDRateLimitError,
    SlidingWindowRateLimiter,
)


class FakeFrame:
    def to_dict(self, orient=None):
        assert orient == "records"
        return [{"title": "Earnings update", "publish_time": "2026-09-30 09:00:00"}]


class FakeContext:
    def __init__(self, host, port, status=0, history=None):
        self.host = host
        self.port = port
        self.status = status
        self.closed = False
        self.calls = []
        self.history = history if history is not None else [
            {"time_key": "2026-10-02 16:00:00", "close": 200.0},
            {"time_key": "2026-10-05 16:00:00", "close": "201.5"},
        ]

    def get_search_news(self, keyword, max_count):
        self.calls.append(("news", keyword, max_count))
        return self.status, FakeFrame()

    def subscribe(self, codes, subtypes, **kwargs):
        self.calls.append(("subscribe", codes, subtypes, kwargs))
        return self.status, "ok"

    def get_stock_quote(self, codes):
        self.calls.append(("quote", codes))
        return self.status, [{"code": codes[0], "cur_price": 123.45}]

    def request_history_kline(self, code, **kwargs):
        self.calls.append(("history", code, kwargs))
        return self.status, self.history, b"next-page-must-not-be-requested"

    def close(self):
        self.closed = True


def test_news_search_converts_records_and_closes_context():
    contexts = []

    def factory(**kwargs):
        context = FakeContext(**kwargs)
        contexts.append(context)
        return context

    connector = MoomooOpenDConnector(
        host="opend.local", port=11222, context_factory=factory, ret_ok=0
    )

    result = connector.search_news("AAPL", max_count=5)

    assert result == [{"title": "Earnings update", "publish_time": "2026-09-30 09:00:00"}]
    assert contexts[0].host == "opend.local"
    assert contexts[0].port == 11222
    assert contexts[0].calls == [("news", "AAPL", 5)]
    assert contexts[0].closed


def test_quote_call_subscribes_then_fetches_and_closes():
    contexts = []

    def factory(**kwargs):
        context = FakeContext(**kwargs)
        contexts.append(context)
        return context

    connector = MoomooOpenDConnector(context_factory=factory, ret_ok=0, quote_subtype="BASIC")

    result = connector.get_quotes(["US.AAPL"])

    assert result == [{"code": "US.AAPL", "cur_price": 123.45}]
    assert contexts[0].calls[0] == (
        "subscribe",
        ["US.AAPL"],
        ["BASIC"],
        {"is_first_push": False, "subscribe_push": False},
    )
    assert contexts[0].calls[1] == ("quote", ["US.AAPL"])
    assert contexts[0].closed


def test_history_requests_one_bounded_adjusted_daily_close_page_and_closes():
    contexts = []

    def factory(**kwargs):
        context = FakeContext(**kwargs)
        contexts.append(context)
        return context

    connector = MoomooOpenDConnector(
        context_factory=factory, ret_ok=0,
        history_ktype="DAY", history_autype="QFQ", history_close_field="CLOSE",
    )
    result = connector.get_history("US.AAPL", "2026-09-05", "2026-10-05", max_count=100)

    assert result == [
        {"date": "2026-10-02", "close": 200.0},
        {"date": "2026-10-05", "close": 201.5},
    ]
    call = contexts[0].calls[0]
    assert call[0:2] == ("history", "US.AAPL")
    assert call[2] == {
        "start": "2026-09-05", "end": "2026-10-05", "ktype": "DAY", "autype": "QFQ",
        "fields": ["CLOSE"], "max_count": 100, "page_req_key": None, "extended_time": False,
    }
    assert contexts[0].closed


def test_history_preserves_exchange_local_session_date_without_utc_conversion():
    context = FakeContext(
        host="localhost", port=11111,
        history=[{"time_key": "2026-10-05 00:30:00", "close": 201.5}],
    )
    connector = MoomooOpenDConnector(
        context_factory=lambda **kwargs: context, ret_ok=0,
        history_ktype="DAY", history_autype="QFQ", history_close_field="CLOSE",
    )
    rows = connector.get_history("US.AAPL", "2026-10-05", "2026-10-05")
    assert rows == [{"date": "2026-10-05", "close": 201.5}]


@pytest.mark.parametrize("history", [
    [{"time_key": "2026-10-05 16:00:00", "close": float("nan")}],
    [{"time_key": "2026-10-05 16:00:00", "close": 0}],
    [{"time_key": "2026-10-06 16:00:00", "close": 100}],
    [{"time_key": "2026-10-05", "close": 100}],
    [{"time_key": "2026-10-05T16:00:00", "close": 100}],
    [{"time_key": "2026-10-05 16:00", "close": 100}],
    [{"time_key": "2026-10-05 16:00:00", "close": True}],
    [{"time_key": "2026-10-05 16:00:00", "close": 100}, {"time_key": "2026-10-05 17:00:00", "close": 101}],
    [{"time_key": "2026-10-06 16:00:00", "close": 100}, {"time_key": "2026-10-05 16:00:00", "close": 101}],
])
def test_history_rejects_invalid_points_and_still_closes(history):
    contexts = []
    def factory(**kwargs):
        context = FakeContext(**kwargs, history=history)
        contexts.append(context)
        return context
    connector = MoomooOpenDConnector(context_factory=factory, ret_ok=0,
        history_ktype="DAY", history_autype="QFQ", history_close_field="CLOSE")
    with pytest.raises(OpenDAPIError):
        connector.get_history("US.AAPL", "2026-10-01", "2026-10-05")
    assert contexts[0].closed


@pytest.mark.parametrize("args", [
    ("MY.1155", "2026-10-01", "2026-10-05", 100),
    ("US.AAPL", "2026-10-06", "2026-10-05", 100),
    ("US.AAPL", "2026-10-01", "2026-10-05", 101),
])
def test_history_rejects_invalid_bounds_before_opening_context(args):
    connector = MoomooOpenDConnector(
        context_factory=lambda **kwargs: pytest.fail("invalid input opened OpenD"), ret_ok=0,
        history_ktype="DAY", history_autype="QFQ", history_close_field="CLOSE")
    with pytest.raises(OpenDAPIError):
        connector.get_history(*args)


def test_history_open_d_failure_still_closes_context():
    contexts = []
    def factory(**kwargs):
        context = FakeContext(**kwargs, status=-1)
        contexts.append(context)
        return context
    connector = MoomooOpenDConnector(context_factory=factory, ret_ok=0,
        history_ktype="DAY", history_autype="QFQ", history_close_field="CLOSE")
    with pytest.raises(OpenDAPIError, match="historical k-line request failed"):
        connector.get_history("US.AAPL", "2026-10-01", "2026-10-05")
    assert contexts[0].closed


def test_failed_opend_status_still_closes_context():
    contexts = []

    def factory(**kwargs):
        context = FakeContext(**kwargs, status=-1)
        contexts.append(context)
        return context

    connector = MoomooOpenDConnector(context_factory=factory, ret_ok=0)

    with pytest.raises(OpenDAPIError, match="news search failed"):
        connector.search_news("AAPL")
    assert contexts[0].closed


def test_missing_sdk_is_reported_without_opening_connection(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def import_without_moomoo(name, *args, **kwargs):
        if name == "moomoo":
            raise ImportError("missing in test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_moomoo)
    with pytest.raises(OpenDUnavailableError, match="install moomoo-api"):
        MoomooOpenDConnector().search_news("AAPL")


def test_news_search_rate_limiter_enforces_rolling_quota():
    now = [0.0]
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=30, clock=lambda: now[0])

    limiter.acquire()
    limiter.acquire()
    with pytest.raises(OpenDRateLimitError) as exc:
        limiter.acquire()
    assert exc.value.retry_after == 30

    now[0] = 30.0
    limiter.acquire()


def test_non_finite_numbers_are_json_safe():
    from connectors.moomoo_opend import _json_value

    assert _json_value(float("nan")) is None
    assert _json_value(float("inf")) is None
