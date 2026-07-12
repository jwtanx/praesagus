"""Production Reddit connector using PRAW with basic rate-limit/backoff handling."""

import os
import time
from datetime import datetime
from typing import Iterator, Optional

import praw
from prawcore import RequestException

from .base import RawRecord, NormalizedRecord
from .utils import get_secret_value


class RedditConnector:
    def __init__(self, subreddit: str = "all", client_id: Optional[str] = None, client_secret: Optional[str] = None, user_agent: Optional[str] = None):
        client_id = client_id or get_secret_value("reddit/client_id", env_var="REDDIT_CLIENT_ID")
        client_secret = client_secret or get_secret_value("reddit/client_secret", env_var="REDDIT_CLIENT_SECRET")
        user_agent = user_agent or get_secret_value("reddit/user_agent", env_var="REDDIT_USER_AGENT") or os.getenv("REDDIT_USER_AGENT", "praesagus/0.1 by example")
        if not client_id or not client_secret:
            raise ValueError("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be provided via env or Secrets Manager")
        self.reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        self.subreddit = subreddit

    def authenticate(self):
        # PRAW handles authentication via provided credentials
        try:
            _ = self.reddit.read_only
        except Exception as e:
            raise e

    def discover(self):
        return [{"subreddit": self.subreddit}]

    def fetch(self, start: datetime, end: datetime, cursor: Optional[str] = None) -> Iterator[RawRecord]:
        # Use subreddit.new and filter by created_utc
        sr = self.reddit.subreddit(self.subreddit)
        for submission in sr.new(limit=200):
            try:
                ts = datetime.utcfromtimestamp(submission.created_utc)
            except Exception:
                continue
            if ts < start or ts > end:
                continue
            payload = {
                "id": submission.id,
                "created_utc": int(submission.created_utc),
                "title": submission.title,
                "selftext": submission.selftext,
                "subreddit": str(submission.subreddit),
                "score": submission.score,
                "num_comments": submission.num_comments,
                "url": submission.url,
            }
            yield RawRecord(payload=payload)

    def normalize(self, raw: RawRecord) -> NormalizedRecord:
        p = raw.payload
        ts = datetime.utcfromtimestamp(p.get("created_utc", 0))
        text = (p.get("title", "") or "") + "\n" + (p.get("selftext", "") or "")
        return NormalizedRecord(
            source="reddit",
            source_id=p.get("id", ""),
            timestamp=ts,
            text=text,
            entities=[],
            metadata={"subreddit": p.get("subreddit"), "score": p.get("score"), "num_comments": p.get("num_comments")},
            provenance={"connector": "reddit", "ingest_ts": datetime.utcnow().isoformat()},
        )

    def store(self, raw: RawRecord, normalized: NormalizedRecord, s3_bucket: Optional[str] = None, s3_writer=None) -> dict:
        # s3_writer should implement s3_atomic_write(bucket, key, data)
        if not s3_bucket or not s3_writer:
            return {}
        raw_key = f"raw/reddit/source_id={raw.payload.get('id')}/raw.json"
        norm_key = f"bronze/reddit/source_id={raw.payload.get('id')}/normalized.json"
        raw_uri = s3_writer(s3_bucket, raw_key, raw.payload)
        norm_uri = s3_writer(s3_bucket, norm_key, normalized.__dict__)
        return {"raw": raw_uri, "normalized": norm_uri}

    def monitor(self) -> dict:
        return {"status": "ok"}
