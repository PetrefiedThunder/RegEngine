import boto3
from .config import settings


def s3_client():
    return boto3.client("s3", endpoint_url=settings.aws_endpoint_url)


def get_bytes(bucket: str, key: str) -> bytes:
    cli = s3_client()
    obj = cli.get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()
