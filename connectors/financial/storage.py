"""Local and S3 persistence for financial intelligence records."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from connectors.utils import s3_atomic_write

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "financial"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _dataset_path(dataset: str, data_dir: Optional[Path] = None) -> Path:
    base = data_dir or DEFAULT_DATA_DIR
    return base / f"{dataset}.json"


def load_dataset(dataset: str, data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = _dataset_path(dataset, data_dir)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload.get("records", [])
        if isinstance(payload, list):
            return payload
    except Exception:
        return []
    return []


def save_dataset(
    dataset: str,
    records: List[Dict[str, Any]],
    data_dir: Optional[Path] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    base = data_dir or DEFAULT_DATA_DIR
    _ensure_dir(base)
    path = _dataset_path(dataset, base)
    payload = {
        "dataset": dataset,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(records),
        "metadata": metadata or {},
        "records": records,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def upsert_records(
    dataset: str,
    new_records: List[Dict[str, Any]],
    key_field: str = "source_id",
    data_dir: Optional[Path] = None,
    max_records: int = 5000,
) -> List[Dict[str, Any]]:
    existing = {r.get(key_field): r for r in load_dataset(dataset, data_dir)}
    for record in new_records:
        key = record.get(key_field)
        if key:
            existing[key] = record
    merged = list(existing.values())
    merged.sort(key=lambda r: r.get("ingest_ts", ""), reverse=True)
    merged = merged[:max_records]
    save_dataset(dataset, merged, data_dir=data_dir)
    return merged


def store_to_s3(
    bucket: str,
    dataset: str,
    records: List[Dict[str, Any]],
    s3_writer=s3_atomic_write,
) -> str:
    now = datetime.utcnow()
    key = (
        f"financial/{dataset}/year={now.year}/month={now.month:02d}/"
        f"day={now.day:02d}/snapshot.json"
    )
    payload = {
        "dataset": dataset,
        "updated_at": now.isoformat() + "Z",
        "count": len(records),
        "records": records,
    }
    return s3_writer(bucket, key, payload)


def get_data_dir() -> Path:
    env_path = os.getenv("PRAESAGUS_FINANCIAL_DATA_DIR")
    if env_path:
        return Path(env_path)
    return DEFAULT_DATA_DIR
