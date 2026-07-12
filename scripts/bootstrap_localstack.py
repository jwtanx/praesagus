"""Bootstrap script to create S3 bucket and DynamoDB table in localstack for local testing."""

import os
import time
import json
import boto3


def ensure_s3_bucket(bucket_name, endpoint_url=None):
    kwargs = {}
    if endpoint_url:
        s3 = boto3.client("s3", endpoint_url=endpoint_url)
    else:
        s3 = boto3.client("s3")
    try:
        s3.create_bucket(Bucket=bucket_name)
        print("Created bucket", bucket_name)
    except Exception as e:
        print("Bucket create may have failed or already exists:", e)


def ensure_dynamo_table(table_name, endpoint_url=None, region="us-east-1"):
    if endpoint_url:
        dynamodb = boto3.client("dynamodb", region_name=region, endpoint_url=endpoint_url)
    else:
        dynamodb = boto3.client("dynamodb", region_name=region)
    existing = dynamodb.list_tables().get("TableNames", [])
    if table_name in existing:
        print("DynamoDB table already exists", table_name)
        return
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # wait until created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print("Created DynamoDB table", table_name)
    except Exception as e:
        print("DynamoDB create may have failed:", e)


if __name__ == "__main__":
    endpoint = os.getenv("PRAESAGUS_S3_ENDPOINT")
    ddb_endpoint = os.getenv("PRAESAGUS_DDB_ENDPOINT")
    bucket = os.getenv("PRAESAGUS_S3_BUCKET", "praesagus-raw-data-local")
    bronze_bucket = os.getenv("PRAESAGUS_BRONZE_BUCKET", "praesagus-bronze-data-local")
    silver_bucket = os.getenv("PRAESAGUS_SILVER_BUCKET", "praesagus-silver-data-local")
    table = os.getenv("PRAESAGUS_FEATURE_TABLE", "praesagus-feature-store-local")
    # Wait briefly for localstack to start
    time.sleep(3)
    ensure_s3_bucket(bucket, endpoint_url=endpoint)
    ensure_s3_bucket(bronze_bucket, endpoint_url=endpoint)
    ensure_s3_bucket(silver_bucket, endpoint_url=endpoint)
    ensure_dynamo_table(table, endpoint_url=ddb_endpoint)
