"""Financial intelligence services for dashboard API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from connectors.financial.filters import apply_filters, load_filter_config, project_visible_fields
from connectors.financial.schemas import (
    CALENDAR_FILTER_FIELDS,
    FILING_FILTER_FIELDS,
    INSIDER_FILTER_FIELDS,
    NEWS_FILTER_FIELDS,
)
from connectors.financial.storage import get_data_dir, load_dataset

DEFAULT_FILTERS_PATH = (
    Path(__file__).resolve().parents[1] / "ingest" / "config" / "financial_filters.yaml"
)
DEFAULT_WATCHLIST_PATH = (
    Path(__file__).resolve().parents[1] / "ingest" / "config" / "financial_watchlist.yaml"
)


def _sort_order(config, dataset: str) -> str:
    orders = getattr(config, "sort", {}) if hasattr(config, "sort") else {}
    # sort_order is stored separately in yaml - load raw for sort_order
    return "desc"


def load_watchlist_tickers() -> List[str]:
    import yaml

    if not DEFAULT_WATCHLIST_PATH.exists():
        return []
    payload = yaml.safe_load(DEFAULT_WATCHLIST_PATH.read_text(encoding="utf-8")) or {}
    return [item["ticker"] for item in payload.get("watchlist", []) if item.get("ticker")]


def get_filter_metadata() -> Dict[str, Any]:
    config = load_filter_config(DEFAULT_FILTERS_PATH)
    import yaml

    raw = {}
    if DEFAULT_FILTERS_PATH.exists():
        raw = yaml.safe_load(DEFAULT_FILTERS_PATH.read_text(encoding="utf-8")) or {}
    return {
        "available_fields": {
            "filings": FILING_FILTER_FIELDS,
            "insider_trades": INSIDER_FILTER_FIELDS,
            "news": NEWS_FILTER_FIELDS,
            "calendar": CALENDAR_FILTER_FIELDS,
        },
        "visible_fields": config.visible_fields,
        "active_filters": {
            "filings": [f.__dict__ for f in config.filings],
            "insider_trades": [f.__dict__ for f in config.insider_trades],
            "news": [f.__dict__ for f in config.news],
            "calendar": [f.__dict__ for f in config.calendar],
        },
        "sort": raw.get("sort", {}),
        "sort_order": raw.get("sort_order", {}),
        "watchlist_tickers": load_watchlist_tickers(),
    }


def _query_dataset(
    dataset: str,
    filters_key: str,
    limit: int = 100,
    extra_filters: Optional[List[Dict[str, Any]]] = None,
    project: bool = True,
) -> List[Dict[str, Any]]:
    import yaml
    from connectors.financial.filters import FieldFilter

    config = load_filter_config(DEFAULT_FILTERS_PATH)
    raw = {}
    if DEFAULT_FILTERS_PATH.exists():
        raw = yaml.safe_load(DEFAULT_FILTERS_PATH.read_text(encoding="utf-8")) or {}

    records = load_dataset(dataset, get_data_dir())
    filters = list(getattr(config, filters_key, []))
    if extra_filters:
        for item in extra_filters:
            filters.append(FieldFilter(**item))

    sort_field = (config.sort or {}).get(dataset.replace("_trades", "").replace("insider", "insider_trades"))
    sort_map = raw.get("sort", {})
    sort_field = sort_map.get(dataset) or sort_field
    sort_order = (raw.get("sort_order") or {}).get(dataset, "desc")

    filtered = apply_filters(records, filters, sort_field=sort_field, sort_order=sort_order)
    if project:
        visible = (config.visible_fields or {}).get(dataset, [])
        if visible:
            filtered = project_visible_fields(filtered, visible)
    return filtered[:limit]


def get_filings(
    limit: int = 50,
    ticker: Optional[str] = None,
    form_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    extra = []
    if ticker:
        extra.append({"field": "ticker", "operator": "eq", "value": ticker.upper()})
    if form_type:
        extra.append({"field": "form_type", "operator": "eq", "value": form_type.upper()})
    return _query_dataset("filings", "filings", limit=limit, extra_filters=extra or None, project=False)


def get_insider_trades(
    limit: int = 50,
    ticker: Optional[str] = None,
    signal: Optional[str] = None,
) -> List[Dict[str, Any]]:
    extra = []
    if ticker:
        extra.append({"field": "ticker", "operator": "eq", "value": ticker.upper()})
    if signal:
        extra.append({"field": "signal", "operator": "eq", "value": signal.lower()})
    return _query_dataset("insider_trades", "insider_trades", limit=limit, extra_filters=extra or None, project=False)


def get_news(
    limit: int = 50,
    ticker: Optional[str] = None,
    signal: Optional[str] = None,
) -> List[Dict[str, Any]]:
    extra = []
    if ticker:
        extra.append({"field": "ticker", "operator": "eq", "value": ticker.upper()})
    if signal:
        extra.append({"field": "signal", "operator": "eq", "value": signal.lower()})
    return _query_dataset("news", "news", limit=limit, extra_filters=extra or None, project=False)


def get_calendar(
    limit: int = 100,
    ticker: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    extra = []
    if ticker:
        extra.append({"field": "ticker", "operator": "eq", "value": ticker.upper()})
    if event_type:
        extra.append({"field": "event_type", "operator": "eq", "value": event_type.lower()})
    return _query_dataset("calendar", "calendar", limit=limit, extra_filters=extra or None, project=False)


def build_financial_summary() -> Dict[str, Any]:
    filings = get_filings(limit=5)
    insider = get_insider_trades(limit=5)
    news = get_news(limit=5)
    calendar = get_calendar(limit=10)
    buy_news = len([n for n in get_news(limit=200) if n.get("signal") == "buy"])
    short_news = len([n for n in get_news(limit=200) if n.get("signal") == "short"])
    insider_buy = len([t for t in get_insider_trades(limit=200) if t.get("signal") == "buy"])
    insider_sell = len([t for t in get_insider_trades(limit=200) if t.get("signal") == "short"])
    return {
        "latest_filings": filings,
        "latest_insider_trades": insider,
        "latest_news": news,
        "upcoming_events": calendar,
        "counts": {
            "filings": len(load_dataset("filings", get_data_dir())),
            "insider_trades": len(load_dataset("insider_trades", get_data_dir())),
            "news": len(load_dataset("news", get_data_dir())),
            "calendar": len(load_dataset("calendar", get_data_dir())),
            "buy_signals": buy_news + insider_buy,
            "short_signals": short_news + insider_sell,
        },
        "watchlist": load_watchlist_tickers(),
    }
