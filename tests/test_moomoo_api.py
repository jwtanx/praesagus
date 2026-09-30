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
    assert response.json() == {
        "records": [{"title": "News for AAPL", "publish_time": "2026-09-30 09:00:00"}],
        "count": 1,
    }


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
    assert response.json() == {
        "records": [
            {"code": "US.AAPL", "cur_price": 100.0},
            {"code": "US.MSFT", "cur_price": 100.0},
        ],
        "count": 2,
    }


def test_moomoo_quotes_requires_market_qualified_codes():
    response = TestClient(app).get("/api/v1/moomoo/quotes", params={"codes": "AAPL"})
    assert response.status_code == 422


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
