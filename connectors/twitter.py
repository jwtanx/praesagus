"""Twitter / X connector example using API v2 and bearer token auth."""

import os
import time
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class XConnector:
    def __init__(self, query: str = "#trending", bearer_token: Optional[str] = None):
        self.query = query
        self.bearer_token = bearer_token or get_secret_value("twitter/bearer_token", env_var="TWITTER_BEARER_TOKEN")
        if not self.bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN or secret twitter/bearer_token must be set")
        self.base_url = "https://api.twitter.com/2/tweets/search/recent"
        self.client = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        # Bearer token auth is handled in headers.
        return None

    def discover(self) -> list[dict]:
        return [{"query": self.query}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        params = {
            "query": self.query,
            "max_results": 100,
            "tweet.fields": "created_at,lang,public_metrics,entities,author_id",
        }
        if cursor:
            params["next_token"] = cursor
        if start:
            params["start_time"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end:
            params["end_time"] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        resp = self.client.get(self.base_url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        for tweet in data.get("data", []):
            yield RawRecord(payload=tweet)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.fromisoformat(p.get("created_at").replace("Z", "+00:00"))
        text = p.get("text", "")
        return NormalizedRecord(
            source="twitter",
            source_id=p.get("id", ""),
            timestamp=ts,
            text=text,
            entities=p.get("entities", {}).get("hashtags", []),
            metadata={"author_id": p.get("author_id"), "lang": p.get("lang"), "public_metrics": p.get("public_metrics")},
            provenance={"connector": "twitter", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"source_id": raw.payload.get("id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
