import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from connectors.feature_store import DynamoFeatureStore


SAMPLE_SIGNAL_PATH = Path(__file__).resolve().parents[1] / "data" / "signals.json"


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()[1:]
    data: Dict[str, Any] = {}
    current_key: Optional[str] = None
    in_block = False
    for line in lines:
        if line.strip() == "---":
            break
        if line.startswith(" ") or line.startswith("\t"):
            if in_block and current_key:
                data[current_key] += "\n" + line.strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {">-", "|-"}:
            data[key] = ""
            current_key = key
            in_block = True
        else:
            data[key] = value
            current_key = None
            in_block = False
    return data


def load_skill_catalog() -> List[Dict[str, Any]]:
    skills_dir = Path(__file__).resolve().parents[1] / "skills"
    skills: List[Dict[str, Any]] = []
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        metadata = _parse_frontmatter(content)
        skills.append(
            {
                "id": metadata.get("name", path.parent.name),
                "label": metadata.get("name", path.parent.name),
                "description": metadata.get("description", ""),
                "category": metadata.get("category", "General"),
                "path": str(path.relative_to(Path(__file__).resolve().parents[1])),
            }
        )
    return skills


def get_skill_detail(skill_id: str) -> Optional[Dict[str, Any]]:
    skills = load_skill_catalog()
    for skill in skills:
        if skill["id"] == skill_id:
            return skill
    return None


def load_sample_signals() -> List[Dict[str, Any]]:
    if not SAMPLE_SIGNAL_PATH.exists():
        return []
    try:
        raw = json.loads(SAMPLE_SIGNAL_PATH.read_text(encoding="utf-8"))
        return raw.get("trends", []) if isinstance(raw, dict) else raw
    except Exception:
        return []


def normalize_trend_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "entity": item.get("entity", "unknown"),
        "score": float(item.get("latest_score", item.get("score", 0))),
        "mention_count": int(item.get("mention_count", 0)),
        "evidence": item.get("evidence", []),
        "last_seen": item.get("updated_at") or item.get("ts") or None,
    }


def get_trends(limit: int = 10, source: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
    table_name = os.getenv("PRAESAGUS_FEATURE_TABLE")
    trends: List[Dict[str, Any]] = []
    if table_name:
        try:
            fs = DynamoFeatureStore(table_name=table_name)
            trends = fs.get_top_trends(limit=limit)
        except Exception:
            trends = []

    if not trends:
        trends = load_sample_signals()

    normalized = [normalize_trend_item(item) for item in trends]
    if source:
        normalized = [t for t in normalized if any(e.get("source") == source for e in t.get("evidence", []))]
    if query:
        query_lower = query.lower()
        normalized = [
            t for t in normalized if query_lower in t["entity"].lower() or any(query_lower in str(e.get("source", "")).lower() for e in t.get("evidence", []))
        ]
    return normalized[:limit]


def get_trend_detail(entity: str) -> Optional[Dict[str, Any]]:
    for trend in get_trends(limit=100):
        if trend["entity"] == entity:
            return trend
    return None


def build_trend_timeline(trend: Dict[str, Any], days: int = 7) -> List[Dict[str, Any]]:
    base = trend.get("score", 0.0)
    now = datetime.utcnow()
    timeline = []
    for idx in range(days):
        date = (now - timedelta(days=days - idx - 1)).isoformat() + "Z"
        offset = idx / max(days - 1, 1)
        value = round(max(0.0, base * (0.65 + offset * 0.35)), 3)
        timeline.append({"date": date, "value": value})
    return timeline


def build_dashboard_chart_data(trends: List[Dict[str, Any]]) -> Dict[str, Any]:
    top_scores = [{"entity": t["entity"], "score": t["score"]} for t in trends]
    mention_series = [{"entity": t["entity"], "mention_count": t["mention_count"]} for t in trends]
    trend_timelines = [
        {"entity": t["entity"], "series": build_trend_timeline(t)} for t in trends[:5]
    ]
    return {
        "score_breakdown": top_scores,
        "mention_breakdown": mention_series,
        "trend_timelines": trend_timelines,
    }


def load_platform_config() -> List[str]:
    config_path = Path(__file__).resolve().parents[1] / "ingest" / "config" / "platform_connectors.yaml"
    if not config_path.exists():
        return []
    platforms: List[str] = []
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            platforms.append(stripped.split(":", 1)[1].strip())
    return platforms


def load_platform_definitions() -> List[Dict[str, Any]]:
    config_path = Path(__file__).resolve().parents[1] / "ingest" / "config" / "platform_connectors.yaml"
    if not config_path.exists():
        return []
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []
        return payload.get("connectors", []) or []
    except Exception:
        return []


def get_platform_detail(name: str) -> Optional[Dict[str, Any]]:
    statuses = build_platform_statuses()
    for status in statuses:
        if status["name"] == name:
            return status
    return None


def build_platform_statuses() -> List[Dict[str, Any]]:
    platforms = load_platform_definitions()
    if not platforms:
        names = load_platform_config()
        platforms = [{"name": name, "schedule": "unknown", "execution": "unknown"} for name in names]

    return [
        {
            "name": platform.get("name", "unknown"),
            "label": platform.get("name", "unknown").replace("_", " ").title(),
            "status": "Healthy",
            "schedule": platform.get("schedule", "unknown"),
            "execution": platform.get("execution", "unknown"),
            "last_run": datetime.utcnow().isoformat() + "Z",
            "items_ingested": "n/a",
        }
        for platform in platforms
    ]


def build_pipeline_statuses() -> Dict[str, Any]:
    platforms = load_platform_config()
    dags = [
        {
            "dag_id": f"ingest_{name}",
            "status": "scheduled",
            "last_run": datetime.utcnow().isoformat() + "Z",
            "next_run": datetime.utcnow().isoformat() + "Z",
        }
        for name in platforms
    ]
    return {"dags": dags, "health": "healthy", "updated_at": datetime.utcnow().isoformat() + "Z"}


def build_dashboard_summary(limit: int = 5) -> Dict[str, Any]:
    trends = get_trends(limit=limit)
    platforms = load_platform_config()
    return {
        "top_trends": trends,
        "signal_count": len(trends),
        "platform_count": len(platforms),
        "feature_store": os.getenv("PRAESAGUS_FEATURE_TABLE", "unknown"),
        "chart_data": build_dashboard_chart_data(trends),
    }
