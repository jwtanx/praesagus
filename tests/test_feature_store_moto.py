import os
import boto3
from moto import mock_aws
from connectors.feature_store import DynamoFeatureStore


@mock_aws
def test_feature_store_put_and_get():
    region = "us-east-1"
    table_name = "test-feature-table"
    client = boto3.client("dynamodb", region_name=region)
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    fs = DynamoFeatureStore(table_name=table_name, region_name=region)
    fs.put_feature("product_x", 2.5, mention_count=3)
    top = fs.get_top_trends(limit=10)
    assert any(item.get("entity") == "product_x" for item in top)
