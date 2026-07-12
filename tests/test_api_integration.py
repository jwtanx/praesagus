import json
import os
import boto3
from fastapi.testclient import TestClient
from moto import mock_aws

from backend.main import app


@mock_aws
def test_api_trends_reads_feature_store():
    table_name = "praesagus-feature-store-local"
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    # populate an item
    res = boto3.resource("dynamodb", region_name="us-east-1")
    tbl = res.Table(table_name)
    tbl.put_item(Item={"entity": "e1", "latest_score": 5, "mention_count": 10})

    os.environ["PRAESAGUS_FEATURE_TABLE"] = table_name

    test_client = TestClient(app)
    r = test_client.get("/api/v1/trends")
    assert r.status_code == 200
    data = r.json()
    assert "trends" in data


@mock_aws
def test_api_dashboard_returns_chart_data():
    table_name = "praesagus-feature-store-local"
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    res = boto3.resource("dynamodb", region_name="us-east-1")
    tbl = res.Table(table_name)
    tbl.put_item(
        Item={
            "entity": "e1",
            "latest_score": 5,
            "mention_count": 10,
            "evidence": [{"source": "reddit", "s3_uri": "s3://praesagus/raw/reddit/test1.json", "ts": "2026-07-12T00:00:00Z"}],
        }
    )

    os.environ["PRAESAGUS_FEATURE_TABLE"] = table_name

    test_client = TestClient(app)
    r = test_client.get("/api/v1/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "chart_data" in data["summary"]
    assert data["summary"]["signal_count"] == 1

    detail = test_client.get("/api/v1/trends/e1")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["trend"]["entity"] == "e1"
    assert isinstance(detail_payload["timeline"], list)
