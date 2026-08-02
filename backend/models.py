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


class FinancialSummaryResponse(BaseModel):
    latest_filings: List[Dict[str, Any]] = Field(default_factory=list)
    latest_insider_trades: List[Dict[str, Any]] = Field(default_factory=list)
    latest_news: List[Dict[str, Any]] = Field(default_factory=list)
    upcoming_events: List[Dict[str, Any]] = Field(default_factory=list)
    counts: Dict[str, Any] = Field(default_factory=dict)
    watchlist: List[str] = Field(default_factory=list)


class FinancialListResponse(BaseModel):
    records: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class FinancialFilterMetadataResponse(BaseModel):
    available_fields: Dict[str, List[str]] = Field(default_factory=dict)
    visible_fields: Dict[str, List[str]] = Field(default_factory=dict)
    active_filters: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    sort: Dict[str, str] = Field(default_factory=dict)
    sort_order: Dict[str, str] = Field(default_factory=dict)
    watchlist_tickers: List[str] = Field(default_factory=list)
