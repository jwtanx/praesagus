"""GitHub connector using the GitHub REST API."""

import os
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class GitHubConnector:
    def __init__(self, repo: str = "torvalds/linux", token: Optional[str] = None):
        self.repo = repo
        self.token = token or get_secret_value("github/token", env_var="GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN or secret github/token must be set")
        self.client = httpx.Client(timeout=30)
        self.base_url = "https://api.github.com"

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"repo": self.repo}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        url = f"{self.base_url}/repos/{self.repo}/issues"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
        }
        params = {
            "state": "all",
            "since": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "per_page": 100,
        }
        resp = self.client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        for issue in resp.json():
            yield RawRecord(payload=issue)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.fromisoformat(p.get("created_at").replace("Z", "+00:00"))
        text = p.get("title", "") + "\n" + (p.get("body", "") or "")
        return NormalizedRecord(
            source="github",
            source_id=str(p.get("id", "")),
            timestamp=ts,
            text=text,
            entities=[{"label": label.get("name")} for label in p.get("labels", [])],
            metadata={"repo": self.repo, "state": p.get("state")},
            provenance={"connector": "github", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"id": raw.payload.get("id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
