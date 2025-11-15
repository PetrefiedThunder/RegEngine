from functools import lru_cache

import boto3
import structlog
from botocore.exceptions import ClientError

from .config import settings

logger = structlog.get_logger("s3-utils")


@lru_cache(maxsize=1)
def s3_client():
    return boto3.client("s3", endpoint_url=settings.aws_endpoint_url)


def get_bytes(bucket: str, key: str, max_size: int = 100 * 1024 * 1024) -> bytes:
    try:
        cli = s3_client()
        obj = cli.get_object(Bucket=bucket, Key=key)
        content_length = obj.get("ContentLength", 0)
        if content_length > max_size:
            raise ValueError(f"Object too large: {content_length} bytes")
        return obj["Body"].read()
    except ClientError as exc:
        logger.error("s3_get_failed", bucket=bucket, key=key, error=str(exc))
        raise
