import sys
from datetime import datetime, timedelta

sys.path.append("")

from connectors.examples.reddit_connector import RedditConnector


def test_reddit_connector_fetch_and_normalize():
    rc = RedditConnector(subreddit="testsub")
    now = datetime.utcnow()
    records = list(rc.fetch(now - timedelta(hours=1), now))
    assert len(records) >= 1
    normalized = rc.normalize(records[0])
    assert normalized.source == "reddit"
    assert "Test post" in normalized.text


if __name__ == "__main__":
    test_reddit_connector_fetch_and_normalize()
    print("OK")
