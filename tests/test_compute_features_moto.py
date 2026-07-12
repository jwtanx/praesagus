import json
import boto3
from moto import mock_aws
from pipeline.compute_features import run as compute_run


@mock_aws
def test_compute_features_flow(tmp_path):
    bucket = "praesagus-raw-data-local"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)
    # put two bronze objects
    obj1 = {"id": "1", "subreddit": "r/a", "metadata": {"subreddit": "r/a"}}
    obj2 = {"id": "2", "subreddit": "r/b", "metadata": {"subreddit": "r/b"}}
    s3.put_object(Bucket=bucket, Key="bronze/reddit/1.json", Body=json.dumps(obj1))
    s3.put_object(Bucket=bucket, Key="bronze/reddit/2.json", Body=json.dumps(obj2))

    # create dynamo table
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    table = "praesagus-feature-store-local"
    ddb.create_table(
        TableName=table,
        KeySchema=[{"AttributeName": "entity", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "entity", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # run compute features
    compute_run(bucket=bucket, table_name=table)

    # verify Dynamo has items
    res = boto3.resource("dynamodb", region_name="us-east-1")
    tbl = res.Table(table)
    items = tbl.scan().get("Items", [])
    assert len(items) >= 1
