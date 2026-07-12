"""Lightweight SDK helpers for Praesagus connectors."""

from typing import Any, Dict, Optional
import json
import uuid
import os
import boto3
from botocore.exceptions import ClientError


def _boto3_client(service_name: str, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
    region = region_name or os.getenv("AWS_REGION", "us-east-1")
    endpoint = endpoint_url or os.getenv("PRAESAGUS_S3_ENDPOINT")
    if endpoint:
        return boto3.client(service_name, region_name=region, endpoint_url=endpoint)
    return boto3.client(service_name, region_name=region)


def _secrets_manager_client(region_name: Optional[str] = None):
    region = region_name or os.getenv("AWS_REGION", "us-east-1")
    endpoint = os.getenv("PRAESAGUS_SECRETS_ENDPOINT") or os.getenv("AWS_SECRETSMANAGER_ENDPOINT")
    if endpoint:
        return boto3.client("secretsmanager", region_name=region, endpoint_url=endpoint)
    return boto3.client("secretsmanager", region_name=region)


def get_secret_value(name: str, env_var: Optional[str] = None, region_name: Optional[str] = None) -> Optional[str]:
    """Resolve a secret value from environment or AWS Secrets Manager."""
    if env_var:
        value = os.getenv(env_var)
        if value:
            return value
    try:
        client = _secrets_manager_client(region_name=region_name)
        resp = client.get_secret_value(SecretId=name)
        if "SecretString" in resp and resp["SecretString"]:
            return resp["SecretString"]
        if "SecretBinary" in resp:
            return resp["SecretBinary"].decode("utf-8")
    except ClientError:
        return None
    except Exception:
        return None
    return None


def get_secret_json(name: str, env_var: Optional[str] = None, region_name: Optional[str] = None) -> Dict[str, Any]:
    """Resolve a secret as JSON, falling back to a plain string value."""
    secret = get_secret_value(name, env_var=env_var, region_name=region_name)
    if not secret:
        return {}
    try:
        return json.loads(secret)
    except json.JSONDecodeError:
        return {"value": secret}


def s3_atomic_write(bucket: str, key: str, data: Dict[str, Any], client=None) -> str:
    """Atomically write JSON data to S3 by writing to a temporary key then copying.

    Returns the final S3 URI.
    """
    client = client or _boto3_client("s3")
    temp_key = f"{key}.tmp.{uuid.uuid4().hex}"
    body = json.dumps(data).encode("utf-8")
    try:
        client.put_object(Bucket=bucket, Key=temp_key, Body=body)
        # Copy temporary to final key
        client.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": temp_key}, Key=key)
        # Delete temp
        client.delete_object(Bucket=bucket, Key=temp_key)
    except ClientError:
        # Best-effort cleanup
        try:
            client.delete_object(Bucket=bucket, Key=temp_key)
        except Exception:
            pass
        raise
    return f"s3://{bucket}/{key}"


def retry_backoff_stub(func, *args, **kwargs):
    return func(*args, **kwargs)
