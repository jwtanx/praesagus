import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from backend.models import DashboardResponse, ResearchRequest, ResearchResponse, TrendDetailResponse, TrendsResponse
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

app = FastAPI(title="Praesagus API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
REQUESTS = Counter("praesagus_requests_total", "Total API requests")


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
            }
        )
    )


@app.get("/metrics")
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
