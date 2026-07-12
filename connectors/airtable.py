"""Airtable connector for public base ingestion."""

import os
from datetime import datetime
from typing import Iterator, Optional

import httpx

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class AirtableConnector:
    def __init__(self, base_id: str, table_name: str, api_key: Optional[str] = None):
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = api_key or get_secret_value("airtable/api_key", env_var="AIRTABLE_API_KEY")
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY or secret airtable/api_key must be set")
        self.base_url = "https://api.airtable.com/v0"
        self.client = httpx.Client(timeout=30)

    def authenticate(self) -> None:
        return None

    def discover(self) -> list[dict]:
        return [{"base_id": self.base_id, "table_name": self.table_name}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        url = f"{self.base_url}/{self.base_id}/{self.table_name}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"pageSize": 100}
        if cursor:
            params["offset"] = cursor
        resp = self.client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        for record in data.get("records", []):
            yield RawRecord(payload=record)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        record = raw.payload
        ts = datetime.utcnow()
        fields = record.get("fields", {})
        return NormalizedRecord(
            source="airtable",
            source_id=record.get("id", ""),
            timestamp=ts,
            text=str(fields),
            entities=[],
            metadata={"fields": fields},
            provenance={"connector": "airtable", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        return {"id": raw.payload.get("id")}

    def monitor(self) -> dict:
        return {"status": "ok"}
