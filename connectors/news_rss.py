"""News RSS connector for generic feed ingestion."""

from datetime import datetime
from typing import Iterator, Optional

import feedparser

from .base import RawRecord, NormalizedRecord


class NewsRSSConnector:
    def __init__(self, feed_url: str):
        self.feed_url = feed_url

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"feed_url": self.feed_url}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        feed = feedparser.parse(self.feed_url)
        for entry in feed.entries:
            if hasattr(entry, "published_parsed"):
                yield RawRecord(payload=entry)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcnow()
        if hasattr(p, "published_parsed"):
            ts = datetime.fromtimestamp(datetime.timestamp(datetime(*p.published_parsed[:6])))
        return NormalizedRecord(
            source="news_rss",
            source_id=getattr(p, "id", getattr(p, "link", "")),
            timestamp=ts,
            text=getattr(p, "title", "") + "\n" + getattr(p, "summary", ""),
            entities=[],
            metadata={"link": getattr(p, "link", ""), "feed": self.feed_url},
            provenance={"connector": "news_rss", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"source_id": getattr(raw.payload, "id", getattr(raw.payload, "link", ""))}

    def monitor(self) -> dict:
        return {"status": "ok"}
