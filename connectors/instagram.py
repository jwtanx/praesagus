"""Instagram ingestion connector placeholder using public page scraping or Graph API."""

import os
from datetime import datetime
from typing import Iterator, Optional

import httpx
from bs4 import BeautifulSoup

from .base import RawRecord, NormalizedRecord


class InstagramConnector:
    def __init__(self, username: str = "instagram"):
        self.username = username
        self.session = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"username": self.username}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        url = f"https://www.instagram.com/{self.username}/"
        resp = self.session.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        scripts = soup.find_all("script", type="text/javascript")
        for script in scripts:
            text = script.string or ""
            if text.strip().startswith("window._sharedData"):
                payload = text.split("=", 1)[1].rstrip(";")
                yield RawRecord(payload={"page_data": payload})
                return

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        return NormalizedRecord(
            source="instagram",
            source_id=self.username,
            timestamp=datetime.utcnow(),
            text=str(raw.payload),
            entities=[],
            metadata={"username": self.username},
            provenance={"connector": "instagram", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"username": self.username}

    def monitor(self) -> dict:
        return {"status": "ok"}
