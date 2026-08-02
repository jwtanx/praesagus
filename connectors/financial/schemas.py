"""Canonical schemas for financial intelligence records with all investable fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TradeSignal(str, Enum):
    BUY = "buy"
    SHORT = "short"
    HOLD = "hold"
    WATCH = "watch"


class EventCategory(str, Enum):
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    SEC_FILING = "sec_filing"
    IPO = "ipo"
    MACRO = "macro"
    INSIDER = "insider"
    OTHER = "other"


@dataclass
class FinancialMetrics:
    """XBRL-derived metrics commonly used for investment analysis."""

    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    stockholders_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    long_term_debt: Optional[float] = None
    short_term_debt: Optional[float] = None
    shares_outstanding: Optional[float] = None
    research_and_development: Optional[float] = None
    goodwill: Optional[float] = None
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    period_end: Optional[str] = None
    fiscal_year: Optional[str] = None
    fiscal_period: Optional[str] = None
    currency: str = "USD"
    unit: str = "USD"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FilingRecord:
    """SEC filing record (10-Q, 10-K, 8-K, etc.)."""

    source_id: str
    cik: str
    ticker: str
    company_name: str
    form_type: str
    filing_date: str
    acceptance_datetime: str
    report_date: Optional[str]
    accession_number: str
    primary_document: str
    filing_url: str
    document_url: str
    description: Optional[str] = None
    items: List[str] = field(default_factory=list)
    is_amendment: bool = False
    metrics: Optional[FinancialMetrics] = None
    raw_xbrl_tags: Dict[str, Any] = field(default_factory=dict)
    investable_fields: List[str] = field(default_factory=list)
    ingest_ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.metrics:
            payload["metrics"] = self.metrics.to_dict()
        return payload


@dataclass
class InsiderTradeRecord:
    """Form 4 insider transaction with maximum detail for day-trading signals."""

    source_id: str
    cik: str
    ticker: str
    issuer_name: str
    accession_number: str
    filing_date: str
    acceptance_datetime: str
    reporting_owner_cik: str
    reporting_owner_name: str
    reporting_owner_title: Optional[str]
    is_director: bool
    is_officer: bool
    is_ten_percent_owner: bool
    is_other: bool
    officer_title: Optional[str]
    transaction_date: str
    transaction_code: str
    transaction_code_label: str
    equity_symbol: Optional[str]
    shares: float
    price_per_share: Optional[float]
    transaction_value: Optional[float]
    shares_owned_following: Optional[float]
    ownership_nature: Optional[str]
    acquired_disposed: str
    form_url: str
    document_url: str
    signal: TradeSignal = TradeSignal.WATCH
    signal_reason: str = ""
    latency_seconds: Optional[float] = None
    ingest_ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["signal"] = self.signal.value
        return payload


@dataclass
class NewsRecord:
    """Earliest company news with buy/short signal metadata."""

    source_id: str
    ticker: str
    company_name: str
    title: str
    summary: str
    link: str
    source_name: str
    published_at: str
    first_seen_at: str
    latency_ms: float
    keywords_matched: List[str] = field(default_factory=list)
    signal: TradeSignal = TradeSignal.WATCH
    signal_strength: float = 0.0
    signal_reason: str = ""
    categories: List[str] = field(default_factory=list)
    related_tickers: List[str] = field(default_factory=list)
    ingest_ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["signal"] = self.signal.value
        return payload


@dataclass
class CalendarEvent:
    """Financial calendar event for earnings, dividends, filings, and macro."""

    source_id: str
    ticker: Optional[str]
    company_name: Optional[str]
    event_type: EventCategory
    title: str
    event_date: str
    event_time: Optional[str] = None
    timezone: str = "America/New_York"
    description: Optional[str] = None
    form_type: Optional[str] = None
    estimated: bool = False
    impact: str = "medium"
    investable_fields: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    ingest_ts: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["event_type"] = self.event_type.value
        return payload


# All filterable field names exposed to the dashboard
FILING_FILTER_FIELDS = [
    "ticker",
    "cik",
    "company_name",
    "form_type",
    "filing_date",
    "acceptance_datetime",
    "report_date",
    "accession_number",
    "description",
    "is_amendment",
    "revenue",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "gross_profit",
    "operating_income",
    "total_assets",
    "total_liabilities",
    "stockholders_equity",
    "cash_and_equivalents",
    "operating_cash_flow",
    "free_cash_flow",
    "long_term_debt",
    "shares_outstanding",
    "current_ratio",
    "debt_to_equity",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "roe",
    "roa",
]

INSIDER_FILTER_FIELDS = [
    "ticker",
    "cik",
    "issuer_name",
    "reporting_owner_name",
    "reporting_owner_title",
    "is_director",
    "is_officer",
    "is_ten_percent_owner",
    "transaction_date",
    "transaction_code",
    "transaction_code_label",
    "shares",
    "price_per_share",
    "transaction_value",
    "shares_owned_following",
    "acquired_disposed",
    "acceptance_datetime",
    "filing_date",
    "signal",
    "latency_seconds",
]

NEWS_FILTER_FIELDS = [
    "ticker",
    "company_name",
    "title",
    "source_name",
    "published_at",
    "first_seen_at",
    "latency_ms",
    "signal",
    "signal_strength",
    "keywords_matched",
    "categories",
]

CALENDAR_FILTER_FIELDS = [
    "ticker",
    "company_name",
    "event_type",
    "title",
    "event_date",
    "event_time",
    "estimated",
    "impact",
    "form_type",
]
