"""Compute simple features from normalized bronze JSON objects and write to feature store."""

import os
import json
import boto3
from collections import defaultdict
from connectors.feature_store import DynamoFeatureStore


def aggregate_mentions(bucket: str, prefix: str = "bronze/reddit/"):
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    counts = defaultdict(int)
    for page in pages:
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            resp = s3.get_object(Bucket=bucket, Key=key)
            body = resp["Body"].read()
            try:
                data = json.loads(body)
            except Exception:
                continue
            # For Reddit normalized JSON we stored metadata.subreddit
            subreddit = data.get("metadata", {}).get("subreddit") or data.get("subreddit") or "unknown"
            counts[subreddit] += 1
    return counts


def run(bucket: str, table_name: str = None):
    counts = aggregate_mentions(bucket)
    if not table_name:
        table_name = os.getenv("PRAESAGUS_FEATURE_TABLE")
    fs = DynamoFeatureStore(table_name=table_name)
    for entity, cnt in counts.items():
        # simple score: normalized mention count
        score = float(cnt)
        fs.put_feature(entity=entity, score=score, mention_count=cnt)
    print("Wrote features for", len(counts), "entities")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--table", default=None)
    args = parser.parse_args()
    run(args.bucket, args.table)
