from fastapi.testclient import TestClient
from datetime import date, timedelta
import math
import pytest

from backend.main import app, _calculate_moomoo_session_direction
from connectors.moomoo_opend import OpenDAPIError, OpenDUnavailableError, configured_connector


class FakeMoomooConnector:
    def search_news(self, keyword, max_count=10):
        return [{"title": f"News for {keyword}", "publish_time": "2026-09-30 09:00:00"}]

    def get_quotes(self, codes):
        return [
            {"code": code, "last_price": 100.0, "prev_close_price": 99.0}
            for code in codes
        ]

    def get_history(self, code, start, end, max_count=100):
        self.history_call = (code, start, end, max_count)
        return [{"date": start, "close": 100.0}, {"date": end, "close": 101.0}]


def test_moomoo_news_endpoint_uses_connector_override():
    app.dependency_overrides[configured_connector] = FakeMoomooConnector
    try:
        response = TestClient(app).get("/api/v1/moomoo/news", params={"keyword": "AAPL", "max_count": 3})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert body["records"] == [{"title": "News for AAPL", "publish_time": "2026-09-30 09:00:00"}]
    assert body["count"] == 1
    assert body["retrieved_at"].endswith("+00:00")


def test_moomoo_quotes_endpoint_deduplicates_codes():
    app.dependency_overrides[configured_connector] = FakeMoomooConnector
    try:
        response = TestClient(app).get(
            "/api/v1/moomoo/quotes",
            params=[("codes", "US.AAPL"), ("codes", "US.AAPL"), ("codes", "US.MSFT")],
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert [row["moomoo_trend"]["status"] for row in body["records"]] == ["unavailable", "unavailable"]
    assert all(row["moomoo_trend"]["reason"] == "insufficient_history" for row in body["records"])
    assert all(row["last_price"] == 100.0 and row["prev_close_price"] == 99.0
               for row in body["records"])
    assert body["count"] == 2
    assert body["retrieved_at"].endswith("+00:00")


def test_moomoo_quotes_endpoint_returns_per_quote_moomoo_trend():
    class DirectionConnector:
        def get_quotes(self, codes):
            assert codes == ["US.BULL", "US.BEAR", "US.FLAT", "US.SHORT", "US.FAIL", "MY.1155"]
            # Bullish SMA trend intentionally conflicts with same-day down movement.
            return [
                {"code": code, "last_price": 90.0, "prev_close_price": 100.0}
                if code == "US.BULL"
                else {"code": code, "last_price": 110.0, "prev_close_price": 100.0}
                for code in codes
            ]

        def get_history(self, code, start, end, max_count=100):
            assert max_count == 100
            if code == "US.FAIL":
                raise OpenDAPIError("fixture history failure")
            histories = {
                "US.BULL": [100.0] * 15 + [110.0] * 5,
                "US.BEAR": [110.0] * 5 + [100.0] * 15,
                "US.FLAT": [100.0] * 20,
                "US.SHORT": [100.0] * 19,
            }
            return trend_history(histories[code])

    app.dependency_overrides[configured_connector] = DirectionConnector
    try:
        response = TestClient(app).get(
            "/api/v1/moomoo/quotes",
            params=[("codes", code) for code in ("US.BULL", "US.BEAR", "US.FLAT", "US.SHORT", "US.FAIL", "MY.1155")],
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    records = response.json()["records"]
    assert [record["moomoo_trend"]["status"] for record in records] == [
        "bullish", "bearish", "neutral", "unavailable", "unavailable", "unavailable"
    ]
    assert records[3]["moomoo_trend"]["reason"] == "insufficient_history"
    assert records[4]["moomoo_trend"]["reason"] == "history_unavailable"
    assert records[5]["moomoo_trend"]["reason"] == "unsupported_market_or_code"
    assert records[0]["last_price"] < records[0]["prev_close_price"]
    assert records[0]["moomoo_trend"]["status"] == "bullish"
    assert records[0]["moomoo_session_direction"]["signal"] == "bearish"
    assert records[0]["moomoo_session_direction"]["method"] == "last_price-vs-prev_close_price"
    assert records[-1]["code"] == "MY.1155" and records[-1]["last_price"] == 110.0


@pytest.mark.parametrize(
    "record,expected",
    [
        ({"last_price": 101.0, "prev_close_price": 100.0}, "bullish"),
        ({"last_price": 99.0, "prev_close_price": 100.0}, "bearish"),
        ({"last_price": 100.0, "prev_close_price": 100.0}, "neutral"),
        ({"last_price": 100.0}, "unavailable"),
        ({"last_price": True, "prev_close_price": 100.0}, "unavailable"),
        ({"last_price": float("nan"), "prev_close_price": 100.0}, "unavailable"),
        ({"last_price": 100.0, "prev_close_price": 0.0}, "unavailable"),
    ],
)
def test_moomoo_session_direction_uses_latest_vs_previous_close(record, expected):
    result = _calculate_moomoo_session_direction(record)
    assert result["signal"] == expected
    assert result["status"] == ("available" if expected != "unavailable" else "unavailable")


def test_moomoo_quotes_rejects_unqualified_or_incomplete_codes():
    client = TestClient(app)
    for code in ("AAPL", "US.", ".AAPL"):
        response = client.get("/api/v1/moomoo/quotes", params={"codes": code})
        assert response.status_code == 422


def test_moomoo_news_rejects_whitespace_keyword():
    response = TestClient(app).get("/api/v1/moomoo/news", params={"keyword": "   "})
    assert response.status_code == 422


def test_moomoo_news_rate_limit_returns_retry_after():
    from connectors.moomoo_opend import OpenDRateLimitError

    class LimitedConnector:
        def search_news(self, keyword, max_count=10):
            raise OpenDRateLimitError(17)

    app.dependency_overrides[configured_connector] = LimitedConnector
    try:
        response = TestClient(app).get("/api/v1/moomoo/news", params={"keyword": "AAPL"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "17"


def test_moomoo_endpoint_honors_configured_api_key(monkeypatch):
    monkeypatch.setenv("PRAESAGUS_API_KEY", "test-secret")
    app.dependency_overrides[configured_connector] = FakeMoomooConnector
    client = TestClient(app)
    try:
        denied = client.get("/api/v1/moomoo/news", params={"keyword": "AAPL"})
        allowed = client.get(
            "/api/v1/moomoo/news",
            params={"keyword": "AAPL"},
            headers={"X-API-Key": "test-secret"},
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_moomoo_endpoint_reports_unavailable_opend_as_503():
    class UnavailableConnector:
        def search_news(self, keyword, max_count=10):
            raise OpenDUnavailableError("OpenD is offline")

    app.dependency_overrides[configured_connector] = UnavailableConnector
    try:
        response = TestClient(app).get("/api/v1/moomoo/news", params={"keyword": "AAPL"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "OpenD is offline"


def test_moomoo_history_endpoint_returns_bounded_provenance_and_adjustment():
    connector = FakeMoomooConnector()
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get("/api/v1/moomoo/history", params={"code": "us.aapl", "window": "3M"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "US.AAPL" and body["window"] == "3M"
    assert body["start"] < body["end"]
    assert body["adjustment"] == "QFQ"
    assert body["count"] == 2 and body["series"][0]["date"] == body["start"]
    assert body["retrieved_at"].endswith("+00:00")
    assert connector.history_call == ("US.AAPL", body["start"], body["end"], 100)


def test_moomoo_history_empty_result_is_successful_and_explicit():
    class EmptyHistoryConnector:
        def get_history(self, code, start, end, max_count=100):
            return []

    app.dependency_overrides[configured_connector] = EmptyHistoryConnector
    try:
        response = TestClient(app).get("/api/v1/moomoo/history", params={"code": "US.AAPL"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert body["series"] == []
    assert body["count"] == 0
    assert body["code"] == "US.AAPL" and body["adjustment"] == "QFQ"
    assert body["retrieved_at"].endswith("+00:00")


def test_moomoo_history_month_boundary_and_default_window(monkeypatch):
    from datetime import datetime, timezone
    import backend.main as main

    class FrozenDateTime:
        @staticmethod
        def now(tz=None):
            assert tz is timezone.utc
            return datetime(2026, 3, 31, 9, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(main, "datetime", FrozenDateTime)
    connector = FakeMoomooConnector()
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get("/api/v1/moomoo/history")
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert (body["start"], body["end"], body["window"]) == ("2026-02-28", "2026-03-31", "1M")


def test_moomoo_history_honors_api_key(monkeypatch):
    monkeypatch.setenv("PRAESAGUS_API_KEY", "test-secret")
    app.dependency_overrides[configured_connector] = FakeMoomooConnector
    client = TestClient(app)
    try:
        denied = client.get("/api/v1/moomoo/history")
        allowed = client.get("/api/v1/moomoo/history", headers={"X-API-Key": "test-secret"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)
    assert denied.status_code == 401 and allowed.status_code == 200


def test_moomoo_history_rejects_non_us_symbols_before_provider_call():
    class MustNotCall:
        def get_history(self, *args, **kwargs):
            pytest.fail("invalid symbol reached OpenD")

    app.dependency_overrides[configured_connector] = MustNotCall
    try:
        for code in ("AAPL", "MY.1155", "US.", "US...", "US.AAPL extra"):
            response = TestClient(app).get("/api/v1/moomoo/history", params={"code": code})
            assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(configured_connector, None)


def test_moomoo_history_rejects_unsupported_window():
    response = TestClient(app).get("/api/v1/moomoo/history", params={"window": "1Y"})
    assert response.status_code == 422


def test_moomoo_history_maps_unavailable_and_provider_errors():
    class FailingConnector:
        def __init__(self, error): self.error = error
        def get_history(self, *args, **kwargs): raise self.error

    for error, status in ((OpenDUnavailableError("OpenD is offline"), 503), (OpenDAPIError("no entitlement"), 502)):
        app.dependency_overrides[configured_connector] = lambda error=error: FailingConnector(error)
        try:
            response = TestClient(app).get("/api/v1/moomoo/history")
        finally:
            app.dependency_overrides.pop(configured_connector, None)
        assert response.status_code == status


def trend_history(closes):
    start = date(2026, 9, 1)
    return [
        {"date": (start + timedelta(days=index)).isoformat(), "close": close}
        for index, close in enumerate(closes)
    ]


class TrendConnector:
    def __init__(self, histories=None, failures=None):
        self.histories = histories or {}
        self.failures = failures or {}
        self.calls = []

    def get_history(self, code, start, end, max_count=100):
        self.calls.append((code, start, end, max_count))
        if code in self.failures:
            raise self.failures[code]
        return self.histories.get(code, trend_history([100.0] * 20))


def test_moomoo_trends_labels_sma5_vs_sma20_and_returns_provenance():
    connector = TrendConnector({
        "US.BULL": trend_history([100.0] * 15 + [110.0] * 5),
        "US.BEAR": trend_history([110.0] * 5 + [100.0] * 15),
        "US.FLAT": trend_history([100.0] * 20),
    })
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get(
            "/api/v1/moomoo/trends",
            params=[("codes", "US.BULL"), ("codes", "US.BEAR"), ("codes", "US.FLAT")],
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    body = response.json()
    assert [row["status"] for row in body["results"]] == ["bullish", "bearish", "neutral"]
    assert body["count"] == 3
    assert body["window"] == "3M" and body["adjustment"] == "QFQ"
    assert body["provider"] == "Moomoo OpenD"
    assert body["method"] == "SMA-5 vs SMA-20 on daily adjusted closes"
    assert "not a forecast or recommendation" in body["note"]
    assert body["retrieved_at"].endswith("+00:00")
    bull = body["results"][0]
    assert bull["method"] == "SMA-5 vs SMA-20"
    assert (bull["fast_window"], bull["slow_window"]) == (5, 20)
    assert bull["fast_sma"] == 110.0 and bull["slow_sma"] == 102.5
    assert math.isclose(bull["spread_pct"], (110.0 / 102.5 - 1) * 100)
    assert bull["latest_bar_date"] == "2026-09-20"
    assert bull["retrieved_at"].endswith("+00:00")
    assert [call[0] for call in connector.calls] == ["US.BULL", "US.BEAR", "US.FLAT"]
    assert all(start < end and max_count == 100
               for _, start, end, max_count in connector.calls)


def test_moomoo_trends_marks_nineteen_bars_unavailable_not_bearish():
    connector = TrendConnector({"US.SHORT": trend_history([100.0] * 19)})
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get("/api/v1/moomoo/trends", params={"codes": "US.SHORT"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    row = response.json()["results"][0]
    assert row["status"] == "unavailable"
    assert row["reason"] == "insufficient_history"
    assert row["fast_sma"] is row["slow_sma"] is row["spread_pct"] is None
    assert row["latest_bar_date"] is None


def test_moomoo_trends_excludes_current_utc_date_bar(monkeypatch):
    import backend.main as main
    from datetime import datetime, timezone

    class FrozenDateTime:
        @staticmethod
        def now(tz=None):
            assert tz is timezone.utc
            return datetime(2026, 3, 31, 9, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(main, "datetime", FrozenDateTime)
    start = date(2026, 3, 1)
    rows = [
        {"date": (start + timedelta(days=index)).isoformat(), "close": 100.0}
        for index in range(20)
    ]
    rows.append({"date": "2026-03-31", "close": 10000.0})
    connector = TrendConnector({"US.TODAY": rows})
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get("/api/v1/moomoo/trends", params={"codes": "US.TODAY"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    row = response.json()["results"][0]
    assert row["status"] == "neutral"
    assert row["fast_sma"] == row["slow_sma"] == 100.0
    assert row["latest_bar_date"] == "2026-03-20"
    assert connector.calls[0][2] == "2026-03-31"


@pytest.mark.parametrize("bad_bar", [
    {"date": "not-a-date", "close": 100.0},
    {"date": "2026-09-01", "close": 0.0},
    {"date": "2026-09-01", "close": -1.0},
    {"date": "2026-09-01", "close": float("nan")},
    {"date": "2026-09-01", "close": float("inf")},
    {"date": "2026-09-01", "close": True},
])
def test_moomoo_trends_rejects_malformed_or_unusable_bars(bad_bar):
    connector = TrendConnector({"US.BAD": [*trend_history([100.0] * 19), bad_bar]})
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get("/api/v1/moomoo/trends", params={"codes": "US.BAD"})
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    row = response.json()["results"][0]
    assert row["status"] == "unavailable"
    assert row["reason"] == "invalid_history"
    assert row["fast_sma"] is row["slow_sma"] is row["spread_pct"] is None


def test_moomoo_trends_normalizes_and_deduplicates_before_history_calls():
    connector = TrendConnector()
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get(
            "/api/v1/moomoo/trends",
            params=[("codes", "us.aapl"), ("codes", "US.AAPL"), ("codes", "us.msft")],
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    assert [row["code"] for row in response.json()["results"]] == ["US.AAPL", "US.MSFT"]
    assert [call[0] for call in connector.calls] == ["US.AAPL", "US.MSFT"]


def test_moomoo_trends_rejects_invalid_symbols_before_provider_call():
    class MustNotCall:
        def get_history(self, *args, **kwargs):
            pytest.fail("invalid symbol reached OpenD")

    app.dependency_overrides[configured_connector] = MustNotCall
    try:
        for code in ("AAPL", "MY.1155", "US.", "US.AAPL extra"):
            response = TestClient(app).get("/api/v1/moomoo/trends", params={"codes": code})
            assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(configured_connector, None)


def test_moomoo_trends_rejects_batches_over_twenty_symbols():
    response = TestClient(app).get(
        "/api/v1/moomoo/trends",
        params=[("codes", f"US.S{i}") for i in range(21)],
    )
    assert response.status_code == 422


def test_moomoo_trends_preserves_per_symbol_unavailability_and_continues_batch():
    connector = TrendConnector(
        failures={"US.DOWN": OpenDUnavailableError("offline")},
    )
    app.dependency_overrides[configured_connector] = lambda: connector
    try:
        response = TestClient(app).get(
            "/api/v1/moomoo/trends",
            params=[("codes", "US.DOWN"), ("codes", "US.OK")],
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)

    assert response.status_code == 200
    rows = response.json()["results"]
    assert rows[0]["status"] == "unavailable" and rows[0]["reason"] == "opend_unavailable"
    assert rows[1]["status"] == "neutral"
    assert [call[0] for call in connector.calls] == ["US.DOWN", "US.OK"]


def test_moomoo_trends_honors_api_key(monkeypatch):
    monkeypatch.setenv("PRAESAGUS_API_KEY", "test-secret")
    app.dependency_overrides[configured_connector] = TrendConnector
    client = TestClient(app)
    try:
        denied = client.get("/api/v1/moomoo/trends", params={"codes": "US.AAPL"})
        allowed = client.get(
            "/api/v1/moomoo/trends", params={"codes": "US.AAPL"},
            headers={"X-API-Key": "test-secret"},
        )
    finally:
        app.dependency_overrides.pop(configured_connector, None)
    assert denied.status_code == 401
    assert allowed.status_code == 200
