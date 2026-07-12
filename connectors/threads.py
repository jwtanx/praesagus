"""Threads connector skeleton (Meta Graph API placeholder).

This connector is a scaffold; implement using Meta's Graph API or an approved
integration. The methods follow the `Connector` interface used across the repo.
"""

import os
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class ThreadsConnector:
    def __init__(self, user_id: Optional[str] = None, access_token: Optional[str] = None):
        self.user_id = user_id or get_secret_value("threads/user_id", env_var="THREADS_USER_ID")
        self.access_token = access_token or get_secret_value("meta/access_token", env_var="META_ACCESS_TOKEN")
        self.base_url = "https://graph.facebook.com/v17.0"
        self.client = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        if not self.access_token:
            raise ValueError("META_ACCESS_TOKEN or secret meta/access_token must be set")
        if not self.user_id:
            raise ValueError("THREADS_USER_ID or secret threads/user_id must be set")
        return None

    def discover(self) -> list[dict]:
        return [{"user_id": self.user_id}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        self.authenticate()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        # Try Graph API endpoint for threads, with a fallback to user media.
        urls = [
            f"{self.base_url}/{self.user_id}/threads?fields=id,text,created_time,conversation,permalink_url,media",
            f"{self.base_url}/{self.user_id}/media?fields=id,caption,timestamp,permalink,type,media_url",
        ]
        for url in urls:
            resp = self.client.get(url, headers=headers)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("data", []):
                yield RawRecord(payload=item)
            return
        return

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcnow()
        if isinstance(p, dict):
            if p.get("created_time"):
                ts = datetime.fromisoformat(p["created_time"].replace("Z", "+00:00"))
            elif p.get("timestamp"):
                ts = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
            text = p.get("text") or p.get("caption") or str(p)
            metadata = {
                "conversation": p.get("conversation"),
                "permalink": p.get("permalink_url") or p.get("permalink"),
                "media_type": p.get("type") or p.get("media", {}).get("type"),
                "source_object": p,
            }
            source_id = p.get("id", "")
        else:
            text = str(p)
            metadata = {}
            source_id = ""
        return NormalizedRecord(
            source="threads",
            source_id=source_id,
            timestamp=ts,
            text=text,
            entities=[],
            metadata=metadata,
            provenance={"connector": "threads", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"id": raw.payload.get("id") if isinstance(raw.payload, dict) else None}

    def monitor(self) -> dict:
        return {"status": "not_implemented"}
