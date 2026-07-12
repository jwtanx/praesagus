"""Example Reddit connector (skeleton)."""

from datetime import datetime, timedelta
from typing import Iterator

from connectors.base import RawRecord, NormalizedRecord


class RedditConnector:
    def __init__(self, subreddit: str = "all"):
        self.subreddit = subreddit

    def authenticate(self):
        # Placeholder for auth (e.g., OAuth)
        return None

    def discover(self):
        return [{"subreddit": self.subreddit}]

    def fetch(self, start: datetime, end: datetime, cursor=None) -> Iterator[RawRecord]:
        # Skeleton: emit a single synthetic record for testing
        sample = {
            "id": "test1",
            "created_utc": int(start.timestamp()),
            "title": "Test post",
            "selftext": "This is a synthetic test post",
            "subreddit": self.subreddit,
        }
        yield RawRecord(payload=sample)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcfromtimestamp(p.get("created_utc", 0))
        text = p.get("title", "") + "\n" + p.get("selftext", "")
        return NormalizedRecord(
            source="reddit",
            source_id=p.get("id", ""),
            timestamp=ts,
            text=text,
            entities=[],
            metadata={"subreddit": p.get("subreddit")},
            provenance={"connector": "reddit_connector", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord) -> dict:
        # For MVP, storing is a no-op: return simulated S3 URI
        return {"raw_s3": "s3://praesagus/raw/reddit/test1.json", "normalized_s3": "s3://praesagus/bronze/reddit/test1.parquet"}

    def monitor(self) -> dict:
        return {"status": "ok"}


if __name__ == "__main__":
    rc = RedditConnector(subreddit="python")
    now = datetime.utcnow()
    for r in rc.fetch(now - timedelta(hours=1), now):
        n = rc.normalize(r)
        print(n)
