import io
from functools import lru_cache

import boto3
from botocore.client import Config

from .config import get_settings


@lru_cache
def client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    bucket = get_settings().minio_bucket
    try:
        client().head_bucket(Bucket=bucket)
    except Exception:
        client().create_bucket(Bucket=bucket)


def put_bytes(key: str, content: bytes, content_type: str) -> None:
    ensure_bucket()
    client().upload_fileobj(io.BytesIO(content), get_settings().minio_bucket, key, ExtraArgs={"ContentType": content_type})


def get_bytes(key: str) -> bytes:
    response = client().get_object(Bucket=get_settings().minio_bucket, Key=key)
    return response["Body"].read()


def download_url(key: str) -> str:
    return client().generate_presigned_url(
        "get_object", Params={"Bucket": get_settings().minio_bucket, "Key": key}, ExpiresIn=900
    )
