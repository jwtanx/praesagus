"""Generic connector runner for CLI use."""

import argparse
import importlib
from datetime import datetime, timedelta
from typing import Optional

from .utils import s3_atomic_write


def create_connector(module_name: str, class_name: str, **kwargs):
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls(**kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module", help="Python module path for connector, e.g. connectors.reddit")
    parser.add_argument("class_name", help="Connector class name, e.g. RedditConnector")
    parser.add_argument("--subreddit", default="all")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    args = parser.parse_args()

    kwargs = {}
    if hasattr(args, "subreddit"):
        kwargs["subreddit"] = args.subreddit

    connector = create_connector(args.module, args.class_name, **kwargs)
    start = datetime.utcnow() - timedelta(hours=1)
    end = datetime.utcnow()
    if args.start:
        start = datetime.fromisoformat(args.start)
    if args.end:
        end = datetime.fromisoformat(args.end)

    for raw in connector.fetch(start, end):
        norm = connector.normalize(raw)
        if args.bucket:
            connector.store(raw, norm, s3_bucket=args.bucket, s3_writer=s3_atomic_write)
        else:
            print(raw)
            print(norm)


if __name__ == "__main__":
    main()
