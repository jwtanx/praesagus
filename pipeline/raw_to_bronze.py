"""Sample ETL job: raw -> bronze (template)

This script demonstrates how an ETL task can read raw JSON from S3 and write
Parquet bronze files. It's a template — adapt schema and partitioning as needed.
"""

import argparse
import io
import json
import pyarrow as pa
import pyarrow.parquet as pq
import boto3


def run(bucket: str, prefix: str, out_prefix: str):
    s3 = boto3.client("s3")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    items = resp.get("Contents", [])
    records = []
    for obj in items:
        key = obj["Key"]
        r = s3.get_object(Bucket=bucket, Key=key)
        body = r["Body"].read()
        data = json.loads(body)
        # perform minimal normalization
        records.append({
            "source": data.get("subreddit", "reddit"),
            "source_id": data.get("id"),
            "timestamp": data.get("created_utc"),
            "text": (data.get("title", "") or "") + "\n" + (data.get("selftext", "") or ""),
        })

    if not records:
        print("No records found")
        return

    table = pa.Table.from_pylist(records)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    out_key = f"{out_prefix}/part-0.parquet"
    s3.put_object(Bucket=bucket, Key=out_key, Body=buf.getvalue())
    print("Wrote:", out_key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="raw/reddit/")
    parser.add_argument("--out", default="bronze/reddit/")
    args = parser.parse_args()
    run(args.bucket, args.prefix, args.out)
