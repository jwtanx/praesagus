from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional, Protocol


@dataclass
class RawRecord:
    payload: dict


@dataclass
class NormalizedRecord:
    source: str
    source_id: str
    timestamp: datetime
    text: str
    entities: List[dict]
    metadata: dict
    provenance: dict


class BaseConnector(Protocol):
    def authenticate(self) -> None: ...

    def discover(self) -> List[dict]: ...

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]: ...

    def normalize(self, raw: RawRecord) -> NormalizedRecord: ...

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict: ...

    def monitor(self) -> dict: ...
