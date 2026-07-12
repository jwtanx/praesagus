import json
from datetime import datetime, timedelta
from connectors.connector_runner import create_connector


def test_create_connector():
    conn = create_connector("connectors.examples.reddit_connector", "RedditConnector", subreddit="test")
    assert conn.discover()[0]["subreddit"] == "test"


def test_runner_fetch_normalize():
    conn = create_connector("connectors.examples.reddit_connector", "RedditConnector", subreddit="test")
    now = datetime.utcnow()
    raw = list(conn.fetch(now - timedelta(hours=1), now))[0]
    norm = conn.normalize(raw)
    assert norm.source == "reddit"
    assert "Test post" in norm.text
