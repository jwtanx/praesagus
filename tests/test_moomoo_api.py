from fastapi.testclient import TestClient

from backend.main import app
from connectors.moomoo_opend import OpenDAPIError, OpenDUnavailableError, configured_connector


class FakeMoomooConnector:
    def search_news(self, keyword, max_count=10):
        return [{"title": f"News for {keyword}", "publish_time": "2026-09-30 09:00:00"}]

    def get_quotes(self, codes):
        return [{"code": code, "cur_price": 100.0} for code in codes]

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
    assert body["records"] == [
        {"code": "US.AAPL", "cur_price": 100.0},
        {"code": "US.MSFT", "cur_price": 100.0},
    ]
    assert body["count"] == 2
    assert body["retrieved_at"].endswith("+00:00")


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
