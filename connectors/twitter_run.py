"""Runner for X/Twitter connector."""

import argparse
from datetime import datetime, timedelta

from .twitter import XConnector
from .utils import s3_atomic_write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="#trend")
    parser.add_argument("--bucket", default=None)
    args = parser.parse_args()

    connector = XConnector(query=args.query)
    now = datetime.utcnow()
    for raw in connector.fetch(now - timedelta(hours=1), now):
        norm = connector.normalize(raw)
        if args.bucket:
            connector.store(raw, norm, s3_bucket=args.bucket, s3_writer=s3_atomic_write)
        else:
            print(norm)


if __name__ == "__main__":
    main()
