from typing import Protocol
from fastapi import Depends
from app.core.config import get_settings


class StorageClient(Protocol):
    def presign_put(self, *, bucket: str, key: str, content_type: str, expires_seconds: int) -> str:
        ...


def get_storage_client(settings=Depends(get_settings)) -> StorageClient:
    """Factory dependency that returns an S3-compatible storage client.

    Tests may override this dependency to provide a fake client.
    """
    # Lazy import to avoid requiring boto3 in contexts that override dependency
    from app.core.storage_s3 import StorageS3Client

    return StorageS3Client(
        endpoint_url=settings.S3_ENDPOINT,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        region=settings.S3_REGION,
        secure=settings.S3_SECURE,
    )
