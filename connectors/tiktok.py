"""TikTok connector skeleton.

Notes:
- TikTok official APIs are limited; this connector is a placeholder that outlines
  the `Connector` interface and must be implemented with a supported SDK or
  a compliant scraping approach that respects Terms of Service.
"""

import json
import os
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class TikTokConnector:
    def __init__(self, username: Optional[str] = None, access_token: Optional[str] = None, query: Optional[str] = None):
        self.username = username or get_secret_value("tiktok/username", env_var="TIKTOK_USERNAME")
        self.query = query or os.getenv("TIKTOK_QUERY", "trending")
        self.access_token = access_token or get_secret_value("tiktok/access_token", env_var="TIKTOK_ACCESS_TOKEN")
        self.base_url = "https://open.tiktokapis.com/v2"
        self.client = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        if not self.access_token:
            raise ValueError("TIKTOK_ACCESS_TOKEN or secret tiktok/access_token must be set")
        return None

    def discover(self) -> list[dict]:
        return [{"username": self.username}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        self.authenticate()
        if self.username:
            url = f"{self.base_url}/research/user/info/?fields=display_name,bio_description,avatar_url,is_verified,follower_count,following_count,likes_count,video_count"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "text/plain",
            }
            body = {"username": self.username}
            resp = self.client.post(url, headers=headers, data=json.dumps(body))
            resp.raise_for_status()
            data = resp.json().get("data", {})
            yield RawRecord(payload=data)
            return
        url = f"{self.base_url}/research/video/query/?fields=id,create_time,desc,author_name,region_code,like_count,comment_count,share_count"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": {
                "and": [
                    {"operation": "EQ", "field_name": "keyword", "field_values": [self.query]}
                ]
            },
            "max_count": 50,
            "cursor": int(cursor) if cursor and str(cursor).isdigit() else 0,
            "start_date": start.strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d"),
            "is_random": False,
        }
        resp = self.client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        for item in data.get("videos", []):
            yield RawRecord(payload=item)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcnow()
        if isinstance(p, dict):
            if p.get("create_time"):
                try:
                    ts = datetime.fromtimestamp(int(p["create_time"]))
                except Exception:
                    pass
            source_id = p.get("id", "")
            text = p.get("desc", "") or p.get("bio_description", "") or str(p)
            metadata = {
                "author_name": p.get("author_name"),
                "region_code": p.get("region_code"),
                "like_count": p.get("like_count"),
                "comment_count": p.get("comment_count"),
                "share_count": p.get("share_count"),
                "follower_count": p.get("follower_count"),
                "following_count": p.get("following_count"),
                "video_count": p.get("video_count"),
            }
        else:
            source_id = ""
            text = str(p)
            metadata = {}
        return NormalizedRecord(
            source="tiktok",
            source_id=source_id,
            timestamp=ts,
            text=text,
            entities=[],
            metadata=metadata,
            provenance={"connector": "tiktok", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"id": raw.payload.get("id") if isinstance(raw.payload, dict) else None}

    def monitor(self) -> dict:
        return {"status": "not_implemented"}
