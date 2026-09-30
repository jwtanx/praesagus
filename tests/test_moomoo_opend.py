import pytest

from connectors.moomoo_opend import (
    MoomooOpenDConnector,
    OpenDAPIError,
    OpenDUnavailableError,
)


class FakeFrame:
    def to_dict(self, orient=None):
        assert orient == "records"
        return [{"title": "Earnings update", "publish_time": "2026-09-30 09:00:00"}]


class FakeContext:
    def __init__(self, host, port, status=0):
        self.host = host
        self.port = port
        self.status = status
        self.closed = False
        self.calls = []

    def get_search_news(self, keyword, max_count):
        self.calls.append(("news", keyword, max_count))
        return self.status, FakeFrame()

    def subscribe(self, codes, subtypes, **kwargs):
        self.calls.append(("subscribe", codes, subtypes, kwargs))
        return self.status, "ok"

    def get_stock_quote(self, codes):
        self.calls.append(("quote", codes))
        return self.status, [{"code": codes[0], "cur_price": 123.45}]

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
