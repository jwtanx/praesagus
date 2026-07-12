from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    s3_uri: Optional[str] = None
    ts: Optional[str] = None
    note: Optional[str] = None


class TrendItem(BaseModel):
    entity: str
    score: float
    mention_count: int = 0
    evidence: List[EvidenceItem] = Field(default_factory=list)
    last_seen: Optional[str] = None


class PlatformStatus(BaseModel):
    name: str
    label: str
    status: str
    last_run: str
    items_ingested: str


class PipelineDag(BaseModel):
    dag_id: str
    status: str
    last_run: str
    next_run: str


class DashboardSummary(BaseModel):
    top_trends: List[TrendItem]
    signal_count: int
    platform_count: int
    feature_store: str
    chart_data: Dict[str, Any]


class TrendsResponse(BaseModel):
    trends: List[TrendItem]


class TrendDetailResponse(BaseModel):
    trend: TrendItem
    timeline: List[Dict[str, Any]]


class DashboardResponse(BaseModel):
    summary: DashboardSummary


class PlatformsResponse(BaseModel):
    platforms: List[PlatformStatus]


class PipelineResponse(BaseModel):
    pipeline: Dict[str, Any]


class SettingsResponse(BaseModel):
    feature_table: str
    s3_bucket: str
    platform_count: int
    auth_enabled: bool


class ResearchRequest(BaseModel):
    skill_id: str
    prompt: str
    tickers: Optional[List[str]] = None
    context: Optional[str] = None


class ResearchResponse(BaseModel):
    request_id: str
    status: str
    skill_id: str
    prompt: str
    result: str
    created_at: str
