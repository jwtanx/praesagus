"""Connector runner script for CLI use."""

import argparse
from datetime import datetime, timedelta

from connectors.reddit import RedditConnector
from connectors.utils import s3_atomic_write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subreddit", default="all")
    parser.add_argument("--bucket", default=None)
    args = parser.parse_args()

    rc = RedditConnector(subreddit=args.subreddit)
    now = datetime.utcnow()
    for r in rc.fetch(now - timedelta(hours=1), now):
        n = rc.normalize(r)
        if args.bucket:
            rc.store(r, n, s3_bucket=args.bucket, s3_writer=s3_atomic_write)
        else:
            print("Raw:", r.payload)
            print("Normalized:", n)


if __name__ == "__main__":
    main()
