"""User-configurable field filters for financial dashboard data."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import yaml

DEFAULT_FILTERS_PATH = (
    Path(__file__).resolve().parents[2] / "ingest" / "config" / "financial_filters.yaml"
)


@dataclass
class FieldFilter:
    field: str
    operator: str = "eq"
    value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def matches(self, record: Dict[str, Any]) -> bool:
        actual = _resolve_field(record, self.field)
        if self.operator == "eq":
            return _normalize(actual) == _normalize(self.value)
        if self.operator == "neq":
            return _normalize(actual) != _normalize(self.value)
        if self.operator == "in":
            values = self.value if isinstance(self.value, list) else [self.value]
            return _normalize(actual) in {_normalize(v) for v in values}
        if self.operator == "contains":
            return str(self.value).lower() in str(actual or "").lower()
        if self.operator == "gte":
            return _to_float(actual) is not None and _to_float(actual) >= float(self.min_value if self.min_value is not None else self.value)
        if self.operator == "lte":
            return _to_float(actual) is not None and _to_float(actual) <= float(self.max_value if self.max_value is not None else self.value)
        if self.operator == "between":
            val = _to_float(actual)
            if val is None:
                return False
            lo = float(self.min_value) if self.min_value is not None else float("-inf")
            hi = float(self.max_value) if self.max_value is not None else float("inf")
            return lo <= val <= hi
        if self.operator == "exists":
            return actual is not None and actual != ""
        return True


@dataclass
class FilterConfig:
    filings: List[FieldFilter] = field(default_factory=list)
    insider_trades: List[FieldFilter] = field(default_factory=list)
    news: List[FieldFilter] = field(default_factory=list)
    calendar: List[FieldFilter] = field(default_factory=list)
    visible_fields: Dict[str, List[str]] = field(default_factory=dict)
    sort: Dict[str, str] = field(default_factory=dict)


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return value
    return value


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_field(record: Dict[str, Any], field_name: str) -> Any:
    if field_name in record:
        return record[field_name]
    if "." in field_name:
        current: Any = record
        for part in field_name.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current
    metrics = record.get("metrics") or {}
    if field_name in metrics:
        return metrics[field_name]
    return None


def load_filter_config(path: Optional[Union[str, Path]] = None) -> FilterConfig:
    config_path = Path(path) if path else DEFAULT_FILTERS_PATH
    if not config_path.exists():
        return FilterConfig()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    def parse_filters(section: str) -> List[FieldFilter]:
        items = payload.get(section, []) or []
        return [
            FieldFilter(
                field=item["field"],
                operator=item.get("operator", "eq"),
                value=item.get("value"),
                min_value=item.get("min_value"),
                max_value=item.get("max_value"),
            )
            for item in items
            if isinstance(item, dict) and item.get("field")
        ]

    return FilterConfig(
        filings=parse_filters("filings"),
        insider_trades=parse_filters("insider_trades"),
        news=parse_filters("news"),
        calendar=parse_filters("calendar"),
        visible_fields=payload.get("visible_fields", {}) or {},
        sort=payload.get("sort", {}) or {},
    )


def apply_filters(
    records: Iterable[Dict[str, Any]],
    filters: List[FieldFilter],
    sort_field: Optional[str] = None,
    sort_order: str = "desc",
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for record in records:
        if all(f.matches(record) for f in filters):
            filtered.append(record)
    if sort_field:
        reverse = sort_order.lower() != "asc"
        filtered.sort(key=lambda r: _sort_key(_resolve_field(r, sort_field)), reverse=reverse)
    return filtered


def _sort_key(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    return str(value)


def project_visible_fields(
    records: List[Dict[str, Any]],
    visible_fields: List[str],
) -> List[Dict[str, Any]]:
    if not visible_fields:
        return records
    projected = []
    for record in records:
        item: Dict[str, Any] = {}
        for field_name in visible_fields:
            value = _resolve_field(record, field_name)
            if "." in field_name:
                item[field_name.replace(".", "_")] = value
            else:
                item[field_name] = value
            if field_name in {"revenue", "net_income", "eps_basic"} and value is None:
                metrics = record.get("metrics") or {}
                item[field_name] = metrics.get(field_name)
        projected.append(item)
    return projected
