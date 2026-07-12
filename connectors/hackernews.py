"""Hacker News connector using public Firebase API feeds."""

import httpx
from datetime import datetime
from typing import Iterator, Optional

from .base import RawRecord, NormalizedRecord


class HackerNewsConnector:
    def __init__(self, category: str = "topstories"):
        self.category = category
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.client = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"category": self.category}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        resp = self.client.get(f"{self.base_url}/{self.category}.json")
        resp.raise_for_status()
        ids = resp.json()[:50]
        for item_id in ids:
            item_resp = self.client.get(f"{self.base_url}/item/{item_id}.json")
            item_resp.raise_for_status()
            yield RawRecord(payload=item_resp.json())

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcfromtimestamp(p.get("time", 0))
        text = p.get("title", "") or ""
        return NormalizedRecord(
            source="hacker_news",
            source_id=str(p.get("id", "")),
            timestamp=ts,
            text=text,
            entities=[{"type": "comment", "text": p.get("text", "")}],
            metadata={"score": p.get("score"), "type": p.get("type")},
            provenance={"connector": "hacker_news", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"id": raw.payload.get("id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
