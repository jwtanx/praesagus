"""Stack Overflow connector using public API."""

import os
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord


class StackOverflowConnector:
    def __init__(self, tags: Optional[list[str]] = None, site: str = "stackoverflow"):
        self.tags = tags or ["python"]
        self.site = site
        self.client = httpx.Client(timeout=30)
        self.base_url = "https://api.stackexchange.com/2.3/questions"

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"tags": self.tags, "site": self.site}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        params = {
            "order": "desc",
            "sort": "creation",
            "tagged": ";".join(self.tags),
            "site": self.site,
            "fromdate": int(start.timestamp()),
            "todate": int(end.timestamp()),
            "pagesize": 50,
        }
        r = self.client.get(self.base_url, params=params)
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            yield RawRecord(payload=item)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.fromtimestamp(p.get("creation_date", 0))
        text = p.get("title", "")
        return NormalizedRecord(
            source="stack_overflow",
            source_id=str(p.get("question_id", "")),
            timestamp=ts,
            text=text,
            entities=[{"tag": t} for t in p.get("tags", [])],
            metadata={"score": p.get("score"), "answer_count": p.get("answer_count")},
            provenance={"connector": "stack_overflow", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"question_id": raw.payload.get("question_id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
