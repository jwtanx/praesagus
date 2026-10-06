import os
import re
import uuid
import math
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from backend.models import (
    DashboardResponse,
    FinancialFilterMetadataResponse,
    FinancialListResponse,
    FinancialSummaryResponse,
    ResearchRequest,
    ResearchResponse,
    TrendDetailResponse,
    TrendsResponse,
)
from backend.services import (
    build_dashboard_summary,
    build_pipeline_statuses,
    build_platform_statuses,
    build_trend_timeline,
    get_platform_detail,
    get_skill_detail,
    get_trend_detail,
    get_trends as fetch_trends,
    load_skill_catalog,
    load_platform_config,
)
from backend.financial_services import (
    build_financial_summary,
    get_calendar,
    get_filings,
    get_filter_metadata,
    get_insider_trades,
    get_news,
)
from connectors.moomoo_opend import (
    MoomooOpenDConnector,
    OpenDAPIError,
    OpenDRateLimitError,
    OpenDUnavailableError,
    configured_connector,
)
from backend.catalyst_services import get_catalysts

app = FastAPI(title="Praesagus API")
raw_origins = os.getenv("PRAESAGUS_CORS_ORIGINS", "http://localhost:5173")
configured_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials="*" not in configured_origins and bool(os.getenv("PRAESAGUS_CORS_ORIGINS")),
    allow_methods=["*"],
    allow_headers=["*"],
)
REQUESTS = Counter("praesagus_requests_total", "Total API requests")

MOOMOO_US_CODE = re.compile(r"^US\.[A-Z0-9]+(?:[.-][A-Z0-9]+)*$")


def _history_window(months: int, today):
    month_index = today.year * 12 + today.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    start = today.replace(year=year, month=month, day=min(today.day, monthrange(year, month)[1]))
    return start.isoformat(), today.isoformat()


def get_api_key(x_api_key: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    secret = os.getenv("PRAESAGUS_API_KEY")
    if not secret:
        return None
    token = x_api_key
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()
    if token != secret:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/trends", response_model=TrendsResponse)
def get_trends_endpoint(
    limit: int = Query(10, ge=1, le=100),
    source: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder({"trends": fetch_trends(limit=limit, source=source, query=query)}))


@app.get("/api/v1/trends/{entity}", response_model=TrendDetailResponse)
def get_trend_detail_endpoint(entity: str, api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    trend = get_trend_detail(entity)
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    return JSONResponse(
        content=jsonable_encoder(
            {
                "trend": trend,
                "timeline": build_trend_timeline(trend),
            }
        )
    )


@app.get("/api/v1/dashboard", response_model=DashboardResponse)
def get_dashboard(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder({"summary": build_dashboard_summary(limit=5)}))


@app.get("/api/v1/platforms")
def get_platforms(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder({"platforms": build_platform_statuses()}))


@app.get("/api/v1/platforms/{name}")
def get_platform_by_name(name: str, api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    platform = get_platform_detail(name)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return JSONResponse(content=jsonable_encoder({"platform": platform}))


@app.get("/api/v1/pipeline")
def get_pipeline(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder({"pipeline": build_pipeline_statuses()}))


@app.get("/api/v1/skills")
def get_skills(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder({"skills": load_skill_catalog()}))


@app.get("/api/v1/skills/{skill_id}")
def get_skill_detail_endpoint(skill_id: str, api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    skill = get_skill_detail(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return JSONResponse(content=jsonable_encoder({"skill": skill}))


@app.post("/api/v1/research")
def post_research(request: ResearchRequest, api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    if not get_skill_detail(request.skill_id):
        raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_id}")
    response = ResearchResponse(
        request_id=str(uuid.uuid4()),
        status="queued",
        skill_id=request.skill_id,
        prompt=request.prompt,
        result=f"Research request queued for {request.skill_id}.",
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    return JSONResponse(content=jsonable_encoder(response.dict()))


@app.get("/api/v1/settings")
def get_settings(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(
        content=jsonable_encoder(
            {
                "feature_table": os.getenv("PRAESAGUS_FEATURE_TABLE", "praesagus-feature-store-local"),
                "s3_bucket": os.getenv("PRAESAGUS_S3_BUCKET", "praesagus-raw-data-local"),
                "platform_count": len(load_platform_config()),
                "auth_enabled": bool(os.getenv("PRAESAGUS_API_KEY")),
                "api_base_url": os.getenv("PRAESAGUS_PUBLIC_API_BASE_URL", "http://localhost:8000"),
            }
        )
    )


@app.get("/api/v1/financial/summary", response_model=FinancialSummaryResponse)
def get_financial_summary(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder(build_financial_summary()))


@app.get("/api/v1/financial/catalysts")
def get_financial_catalysts(
    ticker: Optional[str] = Query(None, min_length=1, max_length=32),
    event_type: Optional[Literal["filing", "insider_trade", "news", "calendar"]] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10000),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    if ticker is not None and not ticker.strip():
        raise HTTPException(status_code=422, detail="ticker must not be blank")
    return get_catalysts(ticker=ticker, event_type=event_type, limit=limit, offset=offset)


@app.get("/api/v1/financial/filings", response_model=FinancialListResponse)
def get_financial_filings(
    limit: int = Query(50, ge=1, le=500),
    ticker: Optional[str] = Query(None),
    form_type: Optional[str] = Query(None),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    records = get_filings(limit=limit, ticker=ticker, form_type=form_type)
    return JSONResponse(content=jsonable_encoder({"records": records, "count": len(records)}))


@app.get("/api/v1/financial/insider-trades", response_model=FinancialListResponse)
def get_financial_insider_trades(
    limit: int = Query(50, ge=1, le=500),
    ticker: Optional[str] = Query(None),
    signal: Optional[str] = Query(None),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    records = get_insider_trades(limit=limit, ticker=ticker, signal=signal)
    return JSONResponse(content=jsonable_encoder({"records": records, "count": len(records)}))


@app.get("/api/v1/financial/news", response_model=FinancialListResponse)
def get_financial_news(
    limit: int = Query(50, ge=1, le=500),
    ticker: Optional[str] = Query(None),
    signal: Optional[str] = Query(None),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    records = get_news(limit=limit, ticker=ticker, signal=signal)
    return JSONResponse(content=jsonable_encoder({"records": records, "count": len(records)}))


@app.get("/api/v1/financial/calendar", response_model=FinancialListResponse)
def get_financial_calendar(
    limit: int = Query(100, ge=1, le=500),
    ticker: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    api_key: Optional[str] = Depends(get_api_key),
):
    REQUESTS.inc()
    records = get_calendar(limit=limit, ticker=ticker, event_type=event_type)
    return JSONResponse(content=jsonable_encoder({"records": records, "count": len(records)}))


@app.get("/api/v1/financial/filters", response_model=FinancialFilterMetadataResponse)
def get_financial_filters(api_key: Optional[str] = Depends(get_api_key)):
    REQUESTS.inc()
    return JSONResponse(content=jsonable_encoder(get_filter_metadata()))


@app.get("/api/v1/moomoo/news")
def get_moomoo_news(
    keyword: str = Query(..., min_length=1, max_length=200),
    max_count: int = Query(10, ge=1, le=100),
    connector: MoomooOpenDConnector = Depends(configured_connector),
    api_key: Optional[str] = Depends(get_api_key),
):
    """Search Moomoo news, notices, and ratings through OpenD."""
    REQUESTS.inc()
    try:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise HTTPException(status_code=422, detail="keyword must contain non-whitespace characters")
        records = connector.search_news(normalized_keyword, max_count=max_count)
    except OpenDRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except OpenDUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenDAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return JSONResponse(
        content=jsonable_encoder(
            {
                "records": records,
                "count": len(records),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )


@app.get("/api/v1/moomoo/quotes")
def get_moomoo_quotes(
    codes: List[str] = Query(..., min_length=1, max_length=20),
    connector: MoomooOpenDConnector = Depends(configured_connector),
    api_key: Optional[str] = Depends(get_api_key),
):
    """Fetch latest read-only quotes for market-qualified codes, e.g. US.AAPL."""
    REQUESTS.inc()
    normalized_codes = list(dict.fromkeys(code.strip().upper() for code in codes))
    if any(
        "." not in code
        or not code.split(".", 1)[0]
        or not code.split(".", 1)[1]
        or any(char.isspace() for char in code)
        for code in normalized_codes
    ):
        raise HTTPException(
            status_code=422,
            detail="Each code must be market-qualified, for example US.AAPL",
        )
    try:
        records = connector.get_quotes(normalized_codes)
    except OpenDUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenDAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return JSONResponse(
        content=jsonable_encoder(
            {
                "records": records,
                "count": len(records),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )


@app.get("/api/v1/moomoo/history")
def get_moomoo_history(
    code: str = Query("US.AAPL", min_length=4, max_length=14),
    window: Literal["1M", "3M"] = Query("1M"),
    connector: MoomooOpenDConnector = Depends(configured_connector),
    api_key: Optional[str] = Depends(get_api_key),
):
    """Fetch one bounded historical daily-close series through OpenD."""
    REQUESTS.inc()
    normalized_code = code.strip().upper()
    if len(normalized_code) > 14 or not MOOMOO_US_CODE.fullmatch(normalized_code):
        raise HTTPException(status_code=422, detail="Enter a valid US symbol, for example US.AAPL")
    months = 1 if window == "1M" else 3
    today = datetime.now(timezone.utc).date()
    start, end = _history_window(months, today)
    try:
        records = connector.get_history(normalized_code, start, end, max_count=100)
    except OpenDUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenDAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return JSONResponse(
        content=jsonable_encoder(
            {
                "code": normalized_code,
                "window": window,
                "start": start,
                "end": end,
                "adjustment": "QFQ",
                "series": records,
                "count": len(records),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    )


def _unavailable_moomoo_trend(code: str, retrieved_at: str, reason: str) -> Dict[str, Any]:
    return {
        "code": code,
        "status": "unavailable",
        "method": "SMA-5 vs SMA-20",
        "fast_window": 5,
        "slow_window": 20,
        "fast_sma": None,
        "slow_sma": None,
        "spread_pct": None,
        "latest_bar_date": None,
        "retrieved_at": retrieved_at,
        "reason": reason,
    }


def _calculate_moomoo_trend(code: str, records: Any, retrieved_at: str,
                            start: str, end: str) -> Dict[str, Any]:
    if not isinstance(records, (list, tuple)):
        return _unavailable_moomoo_trend(code, retrieved_at, "invalid_history")

    bars: List[tuple[date, float]] = []
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        for record in records:
            if not isinstance(record, dict):
                raise ValueError
            raw_date = record.get("date")
            close = record.get("close")
            if not isinstance(raw_date, str):
                raise ValueError
            bar_date = date.fromisoformat(raw_date)
            if (bar_date.isoformat() != raw_date or not start_date <= bar_date <= end_date
                    or type(close) not in (int, float) or not math.isfinite(close) or close <= 0):
                raise ValueError
            # The requested end date is today in UTC; its daily bar may still be forming.
            if bar_date < end_date:
                bars.append((bar_date, float(close)))
    except (OverflowError, TypeError, ValueError):
        return _unavailable_moomoo_trend(code, retrieved_at, "invalid_history")

    if any(left[0] >= right[0] for left, right in zip(bars, bars[1:])):
        return _unavailable_moomoo_trend(code, retrieved_at, "invalid_history")
    if len(bars) < 20:
        return _unavailable_moomoo_trend(code, retrieved_at, "insufficient_history")

    latest = bars[-20:]
    try:
        fast_sma = math.fsum(close for _, close in latest[-5:]) / 5
        slow_sma = math.fsum(close for _, close in latest) / 20
        spread_pct = (fast_sma - slow_sma) / slow_sma * 100
    except (OverflowError, ZeroDivisionError):
        return _unavailable_moomoo_trend(code, retrieved_at, "invalid_history")
    if not all(math.isfinite(value) for value in (fast_sma, slow_sma, spread_pct)):
        return _unavailable_moomoo_trend(code, retrieved_at, "invalid_history")

    status = "bullish" if fast_sma > slow_sma else "bearish" if fast_sma < slow_sma else "neutral"
    return {
        "code": code,
        "status": status,
        "method": "SMA-5 vs SMA-20",
        "fast_window": 5,
        "slow_window": 20,
        "fast_sma": fast_sma,
        "slow_sma": slow_sma,
        "spread_pct": spread_pct,
        "latest_bar_date": latest[-1][0].isoformat(),
        "retrieved_at": retrieved_at,
    }


@app.get("/api/v1/moomoo/trends")
def get_moomoo_trends(
    codes: List[str] = Query(..., min_length=1, max_length=20),
    connector: MoomooOpenDConnector = Depends(configured_connector),
    api_key: Optional[str] = Depends(get_api_key),
):
    """Compare SMA-5 and SMA-20 from bounded OpenD daily closes; descriptive only."""
    REQUESTS.inc()
    normalized_codes = list(dict.fromkeys(code.strip().upper() for code in codes))
    if any(not MOOMOO_US_CODE.fullmatch(code) for code in normalized_codes):
        raise HTTPException(status_code=422, detail="Each code must be a valid US symbol, for example US.AAPL")
    if len(normalized_codes) > 20:
        raise HTTPException(status_code=422, detail="At most 20 unique US symbols may be requested")

    today = datetime.now(timezone.utc).date()
    start, end = _history_window(3, today)
    results = []
    for code in normalized_codes:
        try:
            records = connector.get_history(code, start, end, max_count=100)
        except OpenDUnavailableError:
            results.append(_unavailable_moomoo_trend(
                code, datetime.now(timezone.utc).isoformat(), "opend_unavailable"
            ))
        except OpenDAPIError:
            results.append(_unavailable_moomoo_trend(
                code, datetime.now(timezone.utc).isoformat(), "history_unavailable"
            ))
        except Exception:
            results.append(_unavailable_moomoo_trend(
                code, datetime.now(timezone.utc).isoformat(), "history_unavailable"
            ))
        else:
            results.append(_calculate_moomoo_trend(
                code, records, datetime.now(timezone.utc).isoformat(), start, end
            ))

    retrieved_at = datetime.now(timezone.utc).isoformat()
    return JSONResponse(content=jsonable_encoder({
        "results": results,
        "count": len(results),
        "window": "3M",
        "adjustment": "QFQ",
        "provider": "Moomoo OpenD",
        "method": "SMA-5 vs SMA-20 on daily adjusted closes",
        "note": "Descriptive trend context only; not a forecast or recommendation.",
        "retrieved_at": retrieved_at,
    }))


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
