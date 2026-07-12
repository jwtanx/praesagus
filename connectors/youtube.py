"""YouTube connector using YouTube Data API v3."""

import os
from datetime import datetime
from typing import Iterator, Optional

from googleapiclient.discovery import build

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class YouTubeConnector:
    def __init__(self, query: str = "product", api_key: Optional[str] = None):
        self.api_key = api_key or get_secret_value("youtube/api_key", env_var="YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY or secret youtube/api_key must be set")
        self.query = query
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"query": self.query}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        request = self.youtube.search().list(
            q=self.query,
            part="snippet",
            type="video",
            maxResults=50,
            order="date",
            publishedAfter=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            publishedBefore=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            fields="items(id/videoId,snippet(publishedAt,title,description,channelTitle,tags))",
        )
        response = request.execute()
        for item in response.get("items", []):
            snippet = item["snippet"]
            payload = {
                "id": item["id"]["videoId"],
                "publishedAt": snippet["publishedAt"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channelTitle": snippet.get("channelTitle", ""),
                "tags": snippet.get("tags", []),
            }
            yield RawRecord(payload=payload)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.fromisoformat(p["publishedAt"].replace("Z", "+00:00"))
        text = f"{p.get('title','')}\n{p.get('description','')}"
        return NormalizedRecord(
            source="youtube",
            source_id=p.get("id", ""),
            timestamp=ts,
            text=text,
            entities=[{"tag": tag} for tag in p.get("tags", [])],
            metadata={"channelTitle": p.get("channelTitle")},
            provenance={"connector": "youtube", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"source_id": raw.payload.get("id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
