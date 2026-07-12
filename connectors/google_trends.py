"""Google Trends connector using pytrends."""

import os
from datetime import datetime
from typing import Iterator, Optional

from pytrends.request import TrendReq

from .base import RawRecord, NormalizedRecord


class GoogleTrendsConnector:
    def __init__(self, kw_list: Optional[list[str]] = None, geo: str = "US"):
        self.kw_list = kw_list or ["trending"]
        self.geo = geo
        self.pytrends = TrendReq(hl="en-US", tz=360)

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"keywords": self.kw_list, "geo": self.geo}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        self.pytrends.build_payload(self.kw_list, cat=0, timeframe="today 7-d", geo=self.geo)
        df = self.pytrends.interest_over_time()
        if df is None:
            return
        for index, row in df.iterrows():
            payload = {"date": index.strftime("%Y-%m-%d"), "data": row.to_dict()}
            yield RawRecord(payload=payload)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.fromisoformat(p["date"])
        text = " | ".join([f"{k}:{v}" for k, v in p["data"].items() if k != "isPartial"])
        return NormalizedRecord(
            source="google_trends",
            source_id=p["date"],
            timestamp=ts,
            text=text,
            entities=[],
            metadata={"geo": self.geo, "keywords": self.kw_list},
            provenance={"connector": "google_trends", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"source_id": raw.payload.get("date")}

    def monitor(self) -> dict:
        return {"status": "ok"}
