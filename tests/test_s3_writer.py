import json
import boto3
from botocore.stub import Stubber, ANY
from connectors.utils import s3_atomic_write


def test_s3_atomic_write():
    client = boto3.client("s3")
    stubber = Stubber(client)
    bucket = "my-bucket"
    key = "path/to/file.json"
    temp_key_prefix = key + ".tmp."
    data = {"hello": "world"}

    # Expect put_object
    stubber.add_response("put_object", {}, {"Bucket": bucket, "Key": ANY, "Body": ANY})
    # Expect copy_object
    stubber.add_response("copy_object", {}, {"Bucket": bucket, "CopySource": {"Bucket": bucket, "Key": ANY}, "Key": key})
    # Expect delete_object for temp
    stubber.add_response("delete_object", {}, {"Bucket": bucket, "Key": ANY})

    stubber.activate()
    uri = s3_atomic_write(bucket, key, data, client=client)
    assert uri == f"s3://{bucket}/{key}"
    stubber.deactivate()


if __name__ == "__main__":
    test_s3_atomic_write()
    print("OK")
