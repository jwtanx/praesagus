"""SEC EDGAR ingestion connector using public index pages."""

import requests
from datetime import datetime
from typing import Iterator, Optional

from .base import RawRecord, NormalizedRecord


class EdgarConnector:
    def __init__(self, cik: str):
        self.cik = cik
        self.base_url = "https://www.sec.gov"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Praesagus/0.1"})

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"cik": self.cik}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        url = f"{self.base_url}/cgi-bin/browse-edgar?action=getcompany&CIK={self.cik}&type=&dateb=&owner=exclude&count=40"
        resp = self.session.get(url)
        resp.raise_for_status()
        return iter([RawRecord(payload={"html": resp.text, "url": url})])

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        return NormalizedRecord(
            source="edgar",
            source_id=self.cik,
            timestamp=datetime.utcnow(),
            text=raw.payload.get("html", "")[:1000],
            entities=[],
            metadata={"url": raw.payload.get("url")},
            provenance={"connector": "edgar", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"cik": self.cik}

    def monitor(self) -> dict:
        return {"status": "ok"}
