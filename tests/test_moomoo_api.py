from fastapi.testclient import TestClient

from backend.main import app
from connectors.moomoo_opend import OpenDUnavailableError, configured_connector


class FakeMoomooConnector:
    def search_news(self, keyword, max_count=10):
        return [{"title": f"News for {keyword}", "publish_time": "2026-09-30 09:00:00"}]

    def get_quotes(self, codes):
        return [{"code": code, "cur_price": 100.0} for code in codes]


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
