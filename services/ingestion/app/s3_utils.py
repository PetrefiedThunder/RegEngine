"""S3 helper utilities."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import boto3
from botocore.client import BaseClient

from .config import get_settings


def _client() -> BaseClient:
    settings = get_settings()
    session = boto3.session.Session()
    return session.client(
        "s3",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def put_json(bucket: str, key: str, payload: Any) -> str:
    """Serialize payload to JSON and upload to S3.

    Returns the S3 URI for the stored object.
    """

    body = json.dumps(payload, default=_json_serializer).encode("utf-8")
    _client().put_object(Bucket=bucket, Key=key, Body=body)
    return f"s3://{bucket}/{key}"


def put_bytes(bucket: str, key: str, content: bytes) -> str:
    """Upload raw bytes to S3 and return the object URI."""

    _client().put_object(Bucket=bucket, Key=key, Body=content)
    return f"s3://{bucket}/{key}"


def _json_serializer(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")
