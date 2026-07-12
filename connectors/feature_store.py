"""Simple DynamoDB-backed feature store for Praesagus."""

import os
from decimal import Decimal
from decimal import Decimal
from typing import Dict, List
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime


def normalize_dynamodb_item(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {k: normalize_dynamodb_item(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_dynamodb_item(v) for v in value]
    return value


class DynamoFeatureStore:
    def __init__(self, table_name: str = None, region_name: str = None):
        self.table_name = table_name or os.getenv("PRAESAGUS_FEATURE_TABLE")
        self.region = region_name or os.getenv("AWS_REGION", "us-east-1")
        if not self.table_name:
            raise ValueError("Feature table name must be provided via table_name or PRAESAGUS_FEATURE_TABLE")
        # Support local DynamoDB endpoint for testing (localstack)
        ddb_endpoint = os.getenv("PRAESAGUS_DDB_ENDPOINT")
        if ddb_endpoint:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region, endpoint_url=ddb_endpoint)
        else:
            self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def put_feature(self, entity: str, score: float, mention_count: int = 1):
        now = datetime.utcnow().isoformat()
        # DynamoDB expects numeric values as Decimal when using boto3.
        payload_score = Decimal(str(score))
        payload_mention_count = Decimal(str(mention_count)) if isinstance(mention_count, int) else Decimal(str(mention_count))
        # Update aggregated item per entity
        self.table.update_item(
            Key={"entity": entity},
            UpdateExpression="SET latest_score = :s, updated_at = :u ADD mention_count :m",
            ExpressionAttributeValues={
                ":s": payload_score,
                ":u": now,
                ":m": payload_mention_count,
            },
        )

    def get_top_trends(self, limit: int = 10) -> List[Dict]:
        # Scan and sort in-memory (adequate for small MVP).
        resp = self.table.scan()
        items = resp.get("Items", [])
        # sort by latest_score desc
        items_sorted = sorted(items, key=lambda x: float(x.get("latest_score", 0)), reverse=True)
        return [normalize_dynamodb_item(item) for item in items_sorted[:limit]]
